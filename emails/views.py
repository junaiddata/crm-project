import json
import logging

from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from .models import EmailLog, EmailSettings
from .utils import fetch_emails, send_email, test_connection

logger = logging.getLogger(__name__)


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _threads_by_counterpart(qs):
    """One card per counterpart, showing the latest inbound email.

    qs is inbound-only, ordered newest-first; the first time we meet an address
    is its latest message, so cards are ordered by most-recent activity."""
    messages = list(qs)
    threads = {}
    order = []
    for msg in messages:  # newest first
        if msg.counterpart not in threads:
            threads[msg.counterpart] = {'counterpart': msg.counterpart, 'latest': msg, 'messages': [msg]}
            order.append(msg.counterpart)
        else:
            threads[msg.counterpart]['messages'].append(msg)

    result = []
    for addr in order:
        t = threads[addr]
        msgs = t['messages']  # newest first
        latest = t['latest']
        result.append({
            'counterpart': addr,
            'counterpart_name': next((m.counterpart_name for m in msgs if m.counterpart_name), ''),
            'latest': latest,
            'first_time': latest.received_at,
            'count': len(msgs),
            'all_ids': [m.id for m in msgs],
            'any_unreplied': any(not m.replied for m in msgs),
            'all_replied': all(m.replied for m in msgs),
            'reply_pk': latest.id,
        })
    return result


@login_required
def email_dashboard(request):
    cfg = EmailSettings.load()
    base = EmailLog.objects.filter(direction='in')

    qs = base
    active_filter = request.GET.get('filter', 'all')
    if active_filter == 'unreplied':
        qs = qs.filter(replied=False)
    elif active_filter == 'replied':
        qs = qs.filter(replied=True)

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(counterpart__icontains=search) | Q(counterpart_name__icontains=search)
            | Q(subject__icontains=search) | Q(body__icontains=search)
        )

    total     = base.count()
    unreplied = base.filter(replied=False).count()
    replied   = base.filter(replied=True).count()

    groups = _threads_by_counterpart(qs)

    return render(request, 'email_dashboard.html', {
        'groups': groups,
        'shown_count': len(groups),
        'active_filter': active_filter,
        'search': search,
        'total': total,
        'unreplied': unreplied,
        'replied_count': replied,
        'cfg': cfg,
    })


# ── Per-address thread ────────────────────────────────────────────────────────

@login_required
def email_thread(request, address):
    address = address.strip().lower()
    msgs = list(EmailLog.objects.filter(counterpart=address).order_by('received_at'))

    timeline = []
    for m in msgs:
        timeline.append({
            'dir': m.direction,
            'id': m.id,
            'subject': m.subject,
            'body': m.body,
            'time': m.received_at,
            'date': m.received_at.date().isoformat(),
            'attachments': list(m.attachments.all()),
        })

    incoming = [m for m in msgs if m.direction == 'in']
    latest_in = incoming[-1] if incoming else None
    counterpart_name = next((m.counterpart_name for m in reversed(incoming) if m.counterpart_name), '')

    reply_subject = ''
    if latest_in and latest_in.subject:
        reply_subject = latest_in.subject if latest_in.subject.lower().startswith('re:') else f'Re: {latest_in.subject}'

    return render(request, 'email_thread.html', {
        'address': address,
        'counterpart_name': counterpart_name,
        'timeline': timeline,
        'message_count': len(incoming),
        'reply_subject': reply_subject,
    })


@login_required
@csrf_exempt
def email_thread_send(request, address):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    address = address.strip().lower()
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    subject = (body.get('subject') or '').strip()
    message = (body.get('message') or '').strip()
    if not message:
        return JsonResponse({'error': 'Message is required'}, status=400)

    # Reply threading: In-Reply-To points at the customer's latest inbound
    # message; References carries every Message-ID in the conversation so
    # Outlook/Gmail group the reply under the original instead of starting a
    # new thread.
    thread = list(EmailLog.objects.filter(counterpart=address)
                  .exclude(message_id='').order_by('received_at'))
    latest_in = next((m for m in reversed(thread) if m.direction == 'in'), None)
    in_reply_to = latest_in.message_id if latest_in else ''
    references = ' '.join(m.message_id for m in thread)

    # Clients (Gmail especially) also thread on subject and require it to match
    # the original after stripping Re:. Mirror the customer's subject exactly —
    # if theirs was empty, keep ours empty too (a literal "(no subject)" counts
    # as a different subject and breaks threading).
    if not subject:
        base = (latest_in.subject or '').strip() if latest_in else ''
        if not base or base.lower().startswith('re:'):
            subject = base
        else:
            subject = f'Re: {base}'

    ok, error = send_email(address, subject, message, in_reply_to=in_reply_to, references=references)
    if ok:
        EmailLog.objects.filter(counterpart=address, direction='in', replied=False).update(replied=True)
        return JsonResponse({'ok': True})
    return JsonResponse({'error': error or 'Failed to send'}, status=502)


@login_required
@csrf_exempt
def email_mark(request, pk):
    """Flip replied/new on an inbound email (plus optional extra ids) without sending."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    msg = get_object_or_404(EmailLog, pk=pk)
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        body = {}

    replied = not body.get('undo')
    also_ids = [int(i) for i in body.get('also_mark_ids', []) if str(i).isdigit()]
    EmailLog.objects.filter(pk__in=[msg.pk] + also_ids).update(replied=replied)
    return JsonResponse({'ok': True})


@login_required
@csrf_exempt
def email_fetch_now(request):
    """Manual 'Check mail now' from the dashboard (cron does this automatically on the VPS)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    count, info = fetch_emails()
    return JsonResponse({'ok': True, 'new': count, 'info': info})


# ── Settings page ─────────────────────────────────────────────────────────────

PROVIDER_PRESETS = [
    {'key': 'zoho',   'label': 'Zoho Mail',        'imap_host': 'imap.zoho.com',  'imap_port': 993, 'smtp_host': 'smtp.zoho.com',  'smtp_port': 465, 'ssl': True},
    {'key': 'junaid', 'label': 'junaid.ae (emailapps.net)', 'imap_host': 'pop.emailapps.net', 'imap_port': 993, 'smtp_host': 'smtp.emailapps.net', 'smtp_port': 587, 'ssl': False},
    {'key': 'gmail',  'label': 'Gmail',             'imap_host': 'imap.gmail.com', 'imap_port': 993, 'smtp_host': 'smtp.gmail.com', 'smtp_port': 465, 'ssl': True},
    {'key': 'outlook', 'label': 'Outlook / M365',   'imap_host': 'outlook.office365.com', 'imap_port': 993, 'smtp_host': 'smtp.office365.com', 'smtp_port': 587, 'ssl': False},
]


@login_required
def email_settings_page(request):
    cfg = EmailSettings.load()
    saved = False
    test_results = None

    if request.method == 'POST':
        cfg.email_address = request.POST.get('email_address', '').strip()
        cfg.display_name  = request.POST.get('display_name', '').strip()
        # Blank password field means "keep the existing one".
        new_password = request.POST.get('password', '').strip()
        if new_password:
            cfg.password = new_password
        cfg.imap_host = request.POST.get('imap_host', '').strip()
        cfg.smtp_host = request.POST.get('smtp_host', '').strip()
        try:
            cfg.imap_port = int(request.POST.get('imap_port') or 993)
            cfg.smtp_port = int(request.POST.get('smtp_port') or 465)
        except ValueError:
            pass
        cfg.smtp_use_ssl = request.POST.get('smtp_use_ssl') == 'on'
        cfg.enabled      = request.POST.get('enabled') == 'on'
        fetch_since = request.POST.get('fetch_since', '').strip()
        cfg.fetch_since = fetch_since or None
        cfg.save()
        saved = True

        if request.POST.get('action') == 'test':
            if cfg.is_configured:
                test_results = test_connection(cfg)
            else:
                test_results = {'imap': 'Fill in mailbox, password and hosts first', 'smtp': '—'}

    return render(request, 'email_settings.html', {
        'cfg': cfg,
        'saved': saved,
        'test_results': test_results,
        'presets': PROVIDER_PRESETS,
    })
