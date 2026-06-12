import logging
import re
import smtplib
import ssl
from datetime import timedelta
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr, make_msgid

from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.html import strip_tags

from .models import EmailAttachment, EmailLog, EmailSettings

logger = logging.getLogger(__name__)

MAX_ATTACHMENT_BYTES = 15 * 1024 * 1024


def _clean_body(text_part, html_part):
    """Prefer the plain-text part; fall back to de-tagged HTML."""
    if text_part and text_part.strip():
        return text_part.strip()
    if html_part:
        no_blocks = re.sub(r'(?is)<(style|script).*?</\1>', '', html_part)
        text = strip_tags(no_blocks)
        return re.sub(r'\n{3,}', '\n\n', text).strip()
    return ''


def _aware(dt):
    if dt and timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_default_timezone())
    return dt or timezone.now()


def fetch_emails(limit=500):
    """Pull new messages from the IMAP inbox into EmailLog.

    Returns (new_count, info). Re-scans a 1-day window before the newest stored
    message; the unique Message-ID makes the overlap harmless.
    """
    cfg = EmailSettings.load()
    if not cfg.enabled:
        return 0, 'Email integration is disabled — enable it in Email Settings'
    if not cfg.is_configured:
        return 0, 'Email integration is not configured — fill in Email Settings'

    from imap_tools import AND, MailBox

    latest = EmailLog.objects.filter(direction='in').order_by('-received_at').first()
    if latest:
        since = (latest.received_at - timedelta(days=1)).date()
    elif cfg.fetch_since:
        since = cfg.fetch_since
    else:
        since = (timezone.now() - timedelta(days=30)).date()

    new_count = 0
    try:
        with MailBox(cfg.imap_host, cfg.imap_port).login(cfg.email_address, cfg.password) as mailbox:
            for msg in mailbox.fetch(AND(date_gte=since), mark_seen=False, bulk=True, limit=limit):
                from_addr = (msg.from_ or '').strip().lower()
                if not from_addr or from_addr == cfg.email_address.lower():
                    continue  # skip our own copies / malformed senders

                message_id = (msg.headers.get('message-id', ('',))[0] or '').strip()
                if not message_id:
                    message_id = f'<no-id-{msg.uid}-{msg.date_str}@{cfg.imap_host}>'

                from_name = ''
                if msg.from_values:
                    from_name = (msg.from_values.name or '').strip()

                log, created = EmailLog.objects.get_or_create(
                    message_id=message_id,
                    defaults={
                        'direction': 'in',
                        'counterpart': from_addr,
                        'counterpart_name': from_name,
                        'subject': (msg.subject or '').strip(),
                        'body': _clean_body(msg.text, msg.html),
                        'in_reply_to': (msg.headers.get('in-reply-to', ('',))[0] or '').strip(),
                        'received_at': _aware(msg.date),
                    },
                )
                if not created:
                    continue
                new_count += 1

                for att in msg.attachments:
                    payload = att.payload
                    if not payload or len(payload) > MAX_ATTACHMENT_BYTES:
                        continue
                    record = EmailAttachment(
                        email=log,
                        filename=att.filename or 'attachment',
                        content_type=att.content_type or '',
                        size=len(payload),
                    )
                    record.file.save(att.filename or f'attachment-{log.pk}', ContentFile(payload), save=True)
    except Exception as exc:
        logger.exception('IMAP fetch failed')
        cfg.last_fetch_at = timezone.now()
        cfg.last_fetch_info = f'Fetch failed: {exc}'[:255]
        cfg.save(update_fields=['last_fetch_at', 'last_fetch_info'])
        return 0, f'Fetch failed: {exc}'

    cfg.last_fetch_at = timezone.now()
    cfg.last_fetch_info = f'OK — {new_count} new message(s)'
    cfg.save(update_fields=['last_fetch_at', 'last_fetch_info'])
    return new_count, f'Fetched {new_count} new message(s)'


def _smtp_connect(cfg, timeout=30):
    if cfg.smtp_use_ssl:
        return smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=timeout)
    server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=timeout)
    server.starttls(context=ssl.create_default_context())
    return server


def send_email(to_addr, subject, body, in_reply_to='', references=''):
    """Send via SMTP and log as an outbound EmailLog. Returns (ok, error).

    `in_reply_to` is the Message-ID of the message being answered; `references`
    is the space-separated chain of Message-IDs for the whole conversation
    (oldest→newest). Both headers are what mail clients use to thread the reply
    under the original instead of showing it as a new message.
    """
    cfg = EmailSettings.load()
    if not cfg.is_configured:
        return False, 'Email is not configured — open Email Settings first'

    mime = MimeMessage()
    message_id = make_msgid(domain=cfg.email_address.split('@')[-1])
    mime['Message-ID'] = message_id
    mime['From'] = formataddr((cfg.display_name or cfg.email_address, cfg.email_address))
    mime['To'] = to_addr
    mime['Subject'] = subject
    if in_reply_to:
        mime['In-Reply-To'] = in_reply_to
        # References should list the full chain; fall back to just the parent.
        mime['References'] = references.strip() or in_reply_to
    mime.set_content(body)

    try:
        with _smtp_connect(cfg) as server:
            server.login(cfg.email_address, cfg.password)
            server.send_message(mime)
    except Exception as exc:
        logger.exception('SMTP send failed')
        return False, str(exc)

    EmailLog.objects.create(
        direction='out',
        counterpart=to_addr.strip().lower(),
        subject=subject,
        body=body,
        message_id=message_id,
        in_reply_to=in_reply_to or '',
    )
    return True, ''


def test_connection(cfg):
    """Try IMAP and SMTP logins with the given settings. Returns {'imap': ..., 'smtp': ...} ('ok' or error text)."""
    results = {}

    from imap_tools import MailBox
    try:
        with MailBox(cfg.imap_host, cfg.imap_port).login(cfg.email_address, cfg.password):
            results['imap'] = 'ok'
    except Exception as exc:
        results['imap'] = str(exc) or exc.__class__.__name__

    try:
        with _smtp_connect(cfg, timeout=20) as server:
            server.login(cfg.email_address, cfg.password)
        results['smtp'] = 'ok'
    except Exception as exc:
        results['smtp'] = str(exc) or exc.__class__.__name__

    return results
