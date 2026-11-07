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


RETENTION_DAYS = 90


def purge_old_emails(days=RETENTION_DAYS, *, log_model=EmailLog, attachment_model=EmailAttachment):
    """Delete EmailLog rows (and their attachment files) older than `days`.

    Keeps storage from growing without bound. Django cascades the attachment
    rows on delete but does NOT remove the FileField files from disk, so we
    delete those first. Returns the number of EmailLog rows removed.

    The model args let the Alabama site purge its own alabama_* tables.
    """
    cutoff = timezone.now() - timedelta(days=days)
    old = log_model.objects.filter(received_at__lt=cutoff)
    for att in attachment_model.objects.filter(email__in=old):
        att.file.delete(save=False)  # remove file from storage, not the row
    _, by_model = old.delete()
    return by_model.get(log_model._meta.label, 0)


def fetch_emails(limit=500, *, settings_model=EmailSettings, log_model=EmailLog,
                 attachment_model=EmailAttachment):
    """Pull new messages from the IMAP inbox into EmailLog.

    Returns (new_count, info). Re-scans a 1-day window before the newest stored
    message; the unique Message-ID makes the overlap harmless. Each run also
    purges mail older than RETENTION_DAYS to cap storage.

    The model args let the Alabama site fetch into its own alabama_* tables.
    """
    cfg = settings_model.load()
    if not cfg.enabled:
        return 0, 'Email integration is disabled — enable it in Email Settings'
    if not cfg.is_configured:
        return 0, 'Email integration is not configured — fill in Email Settings'

    purged = purge_old_emails(log_model=log_model, attachment_model=attachment_model)
    purged_note = f', purged {purged} old' if purged else ''

    from imap_tools import AND, MailBox

    latest = log_model.objects.filter(direction='in').order_by('-received_at').first()
    if latest:
        since = (latest.received_at - timedelta(days=1)).date()
    elif cfg.fetch_since:
        since = cfg.fetch_since
    else:
        since = (timezone.now() - timedelta(days=30)).date()

    new_count = 0
    try:
        with MailBox(cfg.imap_host, cfg.imap_port, timeout=30).login(cfg.email_address, cfg.password) as mailbox:
            # Two-pass fetch. The 1-day re-scan window means most messages in
            # range are already stored, so a full download every click would
            # re-pull megabytes of bodies + attachments we already have. First
            # pass is headers-only (cheap) to find which Message-IDs are new;
            # second pass downloads full content for only those UIDs.
            #
            # Fetch newest-first (reverse=True): on a busy mailbox the in-window
            # match set can exceed `limit`, and the IMAP default order is oldest-
            # first — so today's mail would sit past the cutoff and never load.
            new_uids = []
            for hdr in mailbox.fetch(AND(date_gte=since), mark_seen=False, headers_only=True,
                                     bulk=True, limit=limit, reverse=True):
                from_addr = (hdr.from_ or '').strip().lower()
                if not from_addr or from_addr == cfg.email_address.lower():
                    continue  # skip our own copies / malformed senders
                message_id = (hdr.headers.get('message-id', ('',))[0] or '').strip()
                if not message_id:
                    message_id = f'<no-id-{hdr.uid}-{hdr.date_str}@{cfg.imap_host}>'
                if log_model.objects.filter(message_id=message_id).exists():
                    continue  # already stored — don't re-download body/attachments
                new_uids.append(hdr.uid)

            if not new_uids:
                cfg.last_fetch_at = timezone.now()
                cfg.last_fetch_info = f'OK — 0 new message(s){purged_note}'
                cfg.save(update_fields=['last_fetch_at', 'last_fetch_info'])
                return 0, f'Fetched 0 new message(s){purged_note}'

            for msg in mailbox.fetch(AND(uid=new_uids), mark_seen=False, bulk=True):
                from_addr = (msg.from_ or '').strip().lower()
                if not from_addr or from_addr == cfg.email_address.lower():
                    continue  # skip our own copies / malformed senders

                message_id = (msg.headers.get('message-id', ('',))[0] or '').strip()
                if not message_id:
                    message_id = f'<no-id-{msg.uid}-{msg.date_str}@{cfg.imap_host}>'

                from_name = ''
                if msg.from_values:
                    from_name = (msg.from_values.name or '').strip()

                log, created = log_model.objects.get_or_create(
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
                    record = attachment_model(
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
    cfg.last_fetch_info = f'OK — {new_count} new message(s){purged_note}'
    cfg.save(update_fields=['last_fetch_at', 'last_fetch_info'])
    return new_count, f'Fetched {new_count} new message(s){purged_note}'


def _smtp_connect(cfg, timeout=30):
    if cfg.smtp_use_ssl:
        return smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=timeout)
    server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=timeout)
    server.starttls(context=ssl.create_default_context())
    return server


def send_email(to_addr, subject, body, in_reply_to='', references='', *,
               settings_model=EmailSettings, log_model=EmailLog):
    """Send via SMTP and log as an outbound EmailLog. Returns (ok, error).

    `in_reply_to` is the Message-ID of the message being answered; `references`
    is the space-separated chain of Message-IDs for the whole conversation
    (oldest→newest). Both headers are what mail clients use to thread the reply
    under the original instead of showing it as a new message.

    The model args let the Alabama site send from its own mailbox/tables.
    """
    cfg = settings_model.load()
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

    log_model.objects.create(
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
        with MailBox(cfg.imap_host, cfg.imap_port, timeout=20).login(cfg.email_address, cfg.password):
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
