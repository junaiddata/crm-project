import hashlib
import hmac
import json
import logging
import threading

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from crm_project.alabama_db import (
    tpl, pick, is_alabama, wa_phone_ids, wa_labels, wa_default_phone_id,
)
from .models import (
    BroadcastJob, Lead, WhatsAppLead, WhatsAppOutbound,
    AlabamaBroadcastJob, AlabamaLead, AlabamaWhatsAppLead, AlabamaWhatsAppOutbound,
)
from .serializers import LeadSerializer, AlabamaLeadSerializer

logger = logging.getLogger(__name__)


def _verify_meta_signature(request):
    """Validate Meta's X-Hub-Signature-256 (HMAC-SHA256 of the raw body, App Secret key)."""
    app_secret = getattr(settings, 'WHATSAPP_APP_SECRET', None)
    if not app_secret:
        return False
    header_sig = request.headers.get('X-Hub-Signature-256', '')
    if not header_sig.startswith('sha256='):
        return False
    expected = 'sha256=' + hmac.new(
        app_secret.encode(), request.body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, header_sig)


def _lead_model_for_phone_id(business_phone_id):
    """Pick WhatsAppLead vs AlabamaWhatsAppLead by which site owns this Phone Number ID.

    Meta allows only ONE webhook callback URL per App, and Junaid + Alabama share
    the same App — so a single inbound POST can't be routed by which URL it hit.
    Route by the message's own phone_number_id instead."""
    alabama_ids = getattr(settings, 'ALABAMA_WHATSAPP_PHONE_NUMBER_IDS', [])
    return AlabamaWhatsAppLead if business_phone_id in alabama_ids else WhatsAppLead


def _process_whatsapp_payload(payload, allowed_phone_ids=None):
    """Store inbound messages. When allowed_phone_ids is given, only messages
    received on those of OUR numbers are processed (others are ignored).

    Which inbox (Junaid vs Alabama) a message lands in is decided per-message
    by its own phone_number_id, not by which URL the request hit."""
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            value = change.get('value', {})
            business_phone_id = value.get('metadata', {}).get('phone_number_id', '')

            # Only handle numbers we own natively; ignore anything else.
            if allowed_phone_ids is not None and business_phone_id not in allowed_phone_ids:
                continue

            lead_model = _lead_model_for_phone_id(business_phone_id)

            # Map wa_id → profile name from the contacts block
            contact_names = {
                c.get('wa_id', ''): c.get('profile', {}).get('name', '')
                for c in value.get('contacts', [])
            }
            for msg in value.get('messages', []):
                msg_type   = msg.get('type', '')
                message_id = msg.get('id', '')
                sender     = msg.get('from', '')
                if not message_id or not sender:
                    continue
                sender_name = contact_names.get(sender, '')

                if msg_type == 'text':
                    text_body = msg.get('text', {}).get('body', '')
                    lead_model.objects.get_or_create(
                        message_id=message_id,
                        defaults={'sender': sender, 'sender_name': sender_name,
                                  'business_phone_id': business_phone_id,
                                  'text_body': text_body, 'msg_type': 'text'},
                    )

                elif msg_type in ('image', 'video', 'audio', 'document', 'sticker'):
                    stored_type = 'image' if msg_type == 'sticker' else msg_type
                    media_data  = msg.get(msg_type, {})
                    media_id    = media_data.get('id', '')
                    caption     = media_data.get('caption', '')

                    lead, created = lead_model.objects.get_or_create(
                        message_id=message_id,
                        defaults={'sender': sender, 'sender_name': sender_name,
                                  'business_phone_id': business_phone_id,
                                  'text_body': caption, 'msg_type': stored_type},
                    )

                    if created and media_id:
                        from .utils import download_whatsapp_media
                        from django.core.files.base import ContentFile
                        file_bytes, mime_type, filename = download_whatsapp_media(media_id)
                        if file_bytes:
                            lead.media_name = filename
                            lead.media_file.save(filename, ContentFile(file_bytes), save=True)


@csrf_exempt
def whatsapp_webhook(request):
    # ── Meta webhook verification handshake (GET) ─────────────────────────────
    if request.method == 'GET':
        mode      = request.GET.get('hub.mode')
        token     = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge', '')
        verify_token = getattr(settings, 'WHATSAPP_VERIFY_TOKEN', None)
        if mode == 'subscribe' and verify_token and token == verify_token:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Forbidden', status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # ── Authenticate the POST ────────────────────────────────────────────────
    # Path 1 (legacy): the other app forwards with our internal secret.
    internal_ok = request.headers.get('X-Internal-Secret', '') == settings.CRM_WEBHOOK_SECRET
    # Path 2 (direct from Meta): valid X-Hub-Signature-256.
    meta_ok = _verify_meta_signature(request)

    if not internal_ok and not meta_ok:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': True})  # always 200 to avoid retries

    try:
        if internal_ok:
            # Trusted forward (e.g. old-number loop-back) — process everything.
            _process_whatsapp_payload(payload)
        else:
            # Direct from Meta — only handle numbers we own natively (Junaid + Alabama).
            owned_ids = (getattr(settings, 'WHATSAPP_PHONE_NUMBER_IDS', []) +
                         getattr(settings, 'ALABAMA_WHATSAPP_PHONE_NUMBER_IDS', []))
            _process_whatsapp_payload(payload, allowed_phone_ids=owned_ids)
    except Exception:
        logger.exception('Error processing WhatsApp webhook payload')

    return JsonResponse({'ok': True})


@login_required
@csrf_exempt
def whatsapp_reply(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    WhatsAppLeadM = pick(request, WhatsAppLead, AlabamaWhatsAppLead)
    wa_lead = get_object_or_404(WhatsAppLeadM, pk=pk)

    try:
        body = json.loads(request.body)
        message = body.get('message', '').strip()
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    also_mark_ids = [int(i) for i in body.get('also_mark_ids', []) if str(i).isdigit()]

    # Undo: mark as new
    if body.get('undo'):
        wa_lead.replied = False
        wa_lead.reply_text = ''
        wa_lead.save()
        if also_mark_ids:
            WhatsAppLeadM.objects.filter(pk__in=also_mark_ids).update(replied=False, reply_text='')
        return JsonResponse({'ok': True})

    if not message:
        return JsonResponse({'error': 'Message is required'}, status=400)

    from .utils import send_whatsapp_reply as send_reply
    success = send_reply(wa_lead.sender, message, phone_number_id=wa_lead.business_phone_id)

    if success:
        wa_lead.replied = True
        wa_lead.reply_text = message
        wa_lead.save()
        if also_mark_ids:
            WhatsAppLeadM.objects.filter(pk__in=also_mark_ids).update(replied=True, reply_text=message)
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Failed to send — check WHATSAPP_ACCESS_TOKEN and phone number ID'}, status=502)


CRM_SALESPEOPLE = ['RAFIQ', 'SIYAB', 'MUZAIN', 'AIJAZ', 'MUSHARAF']


class LeadListCreateView(APIView):
    def get(self, request):
        LeadM = pick(request, Lead, AlabamaLead)
        LeadSer = pick(request, LeadSerializer, AlabamaLeadSerializer)
        leads = LeadM.objects.all()
        serializer = LeadSer(leads, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        LeadM = pick(request, Lead, AlabamaLead)
        LeadSer = pick(request, LeadSerializer, AlabamaLeadSerializer)
        # When adding from WhatsApp: one lead per customer per DAY.
        #   • same number + same date  → append only the NEW selected messages
        #   • same number, different day → fall through and create a separate lead
        if request.data.get('dedupeBySender'):
            mobile    = (request.data.get('mobileNo') or '').strip()
            lead_date = (request.data.get('date') or '').strip()
            if mobile:
                lookup = LeadM.objects.filter(mobile_no=mobile)
                if lead_date:
                    lookup = lookup.filter(date=lead_date)
                existing = lookup.first()
                if existing:
                    existing_lines = {l.strip() for l in existing.items.splitlines() if l.strip()}
                    new_lines = (request.data.get('items') or '').splitlines()
                    to_add = [l for l in new_lines if l.strip() and l.strip() not in existing_lines]

                    if to_add:
                        base = existing.items.rstrip('\n')
                        addition = '\n'.join(to_add)
                        existing.items = (base + '\n' + addition) if base else addition
                        existing.save()
                        serializer = LeadSer(existing, context={'request': request})
                        return Response(
                            {'appended': True, 'added': len(to_add), **serializer.data},
                            status=status.HTTP_200_OK,
                        )

                    serializer = LeadSer(existing, context={'request': request})
                    return Response(
                        {'duplicate': True, 'added': 0, **serializer.data},
                        status=status.HTTP_200_OK,
                    )

        # When adding from Email: each "Add to Leads" click creates its own
        # separate lead entry, keyed on email — we only skip creating one when
        # the exact same message was already added, to avoid true duplicates.
        if request.data.get('dedupeByEmail'):
            email_addr = (request.data.get('emailId') or '').strip()
            lead_date  = (request.data.get('date') or '').strip()
            if email_addr:
                lookup = LeadM.objects.filter(email_id__iexact=email_addr)
                if lead_date:
                    lookup = lookup.filter(date=lead_date)
                existing_lines = {
                    l.strip()
                    for lead in lookup
                    for l in lead.items.splitlines() if l.strip()
                }
                new_lines = {l.strip() for l in (request.data.get('items') or '').splitlines() if l.strip()}
                existing = lookup.first()
                if existing and new_lines and new_lines.issubset(existing_lines):
                    serializer = LeadSer(existing, context={'request': request})
                    return Response(
                        {'duplicate': True, 'added': 0, **serializer.data},
                        status=status.HTTP_200_OK,
                    )
                # Otherwise fall through and create a brand-new, separate lead entry.

        serializer = LeadSer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Mark auto-added leads so their identifying fields stay locked.
            if request.data.get('dedupeBySender'):
                source = 'whatsapp'
            elif request.data.get('dedupeByEmail'):
                source = 'email'
            else:
                source = ''
            serializer.save(source=source)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LeadDetailView(APIView):
    def get_object(self, request, pk):
        LeadM = pick(request, Lead, AlabamaLead)
        return get_object_or_404(LeadM, pk=pk)

    def get(self, request, pk):
        LeadSer = pick(request, LeadSerializer, AlabamaLeadSerializer)
        lead = self.get_object(request, pk)
        serializer = LeadSer(lead, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, pk):
        LeadSer = pick(request, LeadSerializer, AlabamaLeadSerializer)
        lead = self.get_object(request, pk)
        data = request.data
        # Identifying fields are locked for auto-added leads.
        if lead.source == 'whatsapp':
            data = {k: v for k, v in data.items() if k not in ('date', 'mobileNo')}
        elif lead.source == 'email':
            data = {k: v for k, v in data.items() if k not in ('date', 'emailId')}
        # The quotation uploader's name is write-once: once set it can't be changed.
        if lead.quotation_uploaded_by:
            data = {k: v for k, v in data.items() if k != 'quotationUploadedBy'}
        serializer = LeadSer(lead, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        lead = self.get_object(request, pk)
        if lead.quotation_file:
            lead.quotation_file.delete(save=False)
        lead.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        LeadM = pick(request, Lead, AlabamaLead)
        lead = get_object_or_404(LeadM, pk=pk)
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)
        if lead.quotation_file:
            lead.quotation_file.delete(save=False)
        lead.quotation_file = file
        lead.save()
        url = request.build_absolute_uri(lead.quotation_file.url)
        return Response({'name': file.name, 'data': url})

    def delete(self, request, pk):
        LeadM = pick(request, Lead, AlabamaLead)
        lead = get_object_or_404(LeadM, pk=pk)
        if lead.quotation_file:
            lead.quotation_file.delete(save=False)
            lead.quotation_file = None
            lead.save()
        return Response({'success': True})


class SalespersonListView(APIView):
    def get(self, request):
        return Response(CRM_SALESPEOPLE)


# ── WhatsApp dashboard (server-rendered) ──────────────────────────────────────

def _conversations_by_sender(qs):
    """One conversation card per sender, showing the latest message.

    qs is ordered newest-first; the first time we meet a sender is their latest
    message, so the result is naturally ordered by most-recent activity."""
    messages = list(qs)  # newest first
    if not messages:
        return []

    labels = getattr(settings, 'WHATSAPP_NUMBER_LABELS', {})
    convs = {}
    order = []
    for msg in messages:  # newest first
        if msg.sender not in convs:
            convs[msg.sender] = {'sender': msg.sender, 'latest': msg, 'messages': [msg]}
            order.append(msg.sender)
        else:
            convs[msg.sender]['messages'].append(msg)

    result = []
    for sender in order:
        c = convs[sender]
        msgs = c['messages']      # newest first
        latest = c['latest']
        # distinct numbers this sender contacted, most-recent first
        distinct = []
        for m in msgs:
            if m.business_phone_id and m.business_phone_id not in distinct:
                distinct.append(m.business_phone_id)
        result.append({
            'sender': sender,
            'sender_name': next((m.sender_name for m in msgs if m.sender_name), ''),
            'latest': latest,
            'first_time': latest.received_at,   # template shows this as the timestamp
            'count': len(msgs),
            'messages': list(reversed(msgs)),   # chronological (for Add-to-Leads payload)
            'all_ids': [m.id for m in msgs],
            'any_unreplied': any(not m.replied for m in msgs),
            'all_replied': all(m.replied for m in msgs),
            'reply_pk': latest.id,
            'reply_text': latest.reply_text,
            'business_phone_id': latest.business_phone_id,
            'business_label': labels.get(latest.business_phone_id, ''),
            'numbers': [{'id': pid, 'label': labels.get(pid, pid)} for pid in distinct],
        })
    return result


def _wa_preview(msg):
    """Short last-message preview for a conversation row (WhatsApp-list style)."""
    t = msg.msg_type
    if t == 'image':    return '📷 ' + (msg.text_body or 'Photo')
    if t == 'video':    return '🎥 ' + (msg.text_body or 'Video')
    if t == 'audio':    return '🎤 Voice message'
    if t == 'document': return '📄 ' + (msg.media_name or 'Document')
    return msg.text_body or ''


def _wa_conversations(qs, labels):
    """One row per (customer ↔ our-number) pair — each number is its own chat.

    qs is ordered newest-first, so the first time we meet a (sender, number)
    pair is its latest message and rows come out by most-recent activity."""
    convs, order = {}, []
    for msg in qs:  # newest first
        key = (msg.sender, msg.business_phone_id)
        if key not in convs:
            convs[key] = {'latest': msg, 'messages': [msg]}
            order.append(key)
        else:
            convs[key]['messages'].append(msg)

    result = []
    for key in order:
        c = convs[key]
        msgs, latest = c['messages'], c['latest']
        sender, pid = key
        unread_count = sum(1 for m in msgs if not m.read)
        result.append({
            'sender': sender,
            'business_phone_id': pid,
            'business_label': labels.get(pid, pid or ''),
            'sender_name': next((m.sender_name for m in msgs if m.sender_name), ''),
            'latest': latest,
            'preview': _wa_preview(latest),
            'first_time': latest.received_at,
            'count': len(msgs),
            'unread_count': unread_count,   # how many messages are still unread (to read)
            'unread': unread_count > 0,
        })
    return result


@login_required
def whatsapp_dashboard(request):
    WhatsAppLeadM = pick(request, WhatsAppLead, AlabamaWhatsAppLead)
    base = WhatsAppLeadM.objects.all()

    # ── Filter by which of OUR numbers received the messages ──
    active_number = request.GET.get('number', 'all')
    number_base = base
    if active_number != 'all':
        number_base = base.filter(business_phone_id=active_number)

    qs = number_base
    active_filter = request.GET.get('filter', 'all')
    if active_filter == 'unread':
        # show only conversations that still have unread messages
        unread_senders = (number_base.filter(read=False)
                          .values_list('sender', 'business_phone_id'))
        unread_keys = set(unread_senders)
        # fall through; we filter the built conversations below by these keys
    else:
        unread_keys = None

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(sender__icontains=search) | Q(text_body__icontains=search)
                       | Q(sender_name__icontains=search))

    # Counts respect the selected number. "unread" = messages not yet opened.
    total  = number_base.count()
    unread = number_base.filter(read=False).count()

    # Per-number chips (independent of the reply filter)
    labels = wa_labels(request)
    numbers = [
        {'id': pid, 'label': labels.get(pid, pid),
         'count': base.filter(business_phone_id=pid).count()}
        for pid in wa_phone_ids(request)
    ]

    conversations = _wa_conversations(qs, labels)
    if unread_keys is not None:
        conversations = [c for c in conversations
                         if (c['sender'], c['business_phone_id']) in unread_keys]

    return render(request, tpl(request, 'whatsapp_dashboard.html'), {
        'conversations': conversations,
        'shown_count': len(conversations),
        'active_filter': active_filter,
        'active_number': active_number,
        'numbers': numbers,
        'all_count': base.count(),
        'search': search,
        'total': total,
        'unread': unread,
        'open_sender': request.GET.get('open', ''),
        'open_number': request.GET.get('open_number', ''),
    })


@login_required
def mark_replied(request, pk):
    from django.http import HttpResponseRedirect
    home = '/alabama/whatsapp/' if is_alabama(request) else '/whatsapp/'
    if request.method != 'POST':
        return HttpResponseRedirect(home)
    WhatsAppLeadM = pick(request, WhatsAppLead, AlabamaWhatsAppLead)
    wa = get_object_or_404(WhatsAppLeadM, pk=pk)
    action = request.POST.get('action', 'reply')
    if action == 'unreply':
        wa.replied = False
        wa.reply_text = ''
    else:
        wa.replied = True
        wa.reply_text = request.POST.get('reply_text', '').strip()
    wa.save()
    next_url = request.POST.get('next', home)
    return HttpResponseRedirect(next_url)


# ── Broadcast page (send an approved template to a CSV of numbers) ─────────────

def _broadcast_worker(job_id, recipients, *, template, language, phone_id, caption,
                      image_bytes, image_mime, image_name,
                      job_model=BroadcastJob, outbound_model=WhatsAppOutbound):
    """Run the broadcast off the request thread, updating the BroadcastJob row as
    it goes. Sending 100+ template messages is one API call each (no bulk
    endpoint), so it must not block the HTTP request or nginx returns a 504.

    The model args are passed explicitly because this runs in a background
    thread with no request, so the path-based resolver isn't available."""
    from django.db import connections
    from .broadcast import send_broadcast, stage_chat_image, upload_header_image

    try:
        header_image_id = chat_media_name = None
        if image_bytes:
            header_image_id = upload_header_image(image_bytes, image_mime, image_name, phone_id)
            if not header_image_id:
                job_model.objects.filter(pk=job_id).update(
                    status='error',
                    message='Failed to upload the header image to WhatsApp — check API credentials.')
                return
            chat_media_name = stage_chat_image(image_bytes, image_name)

        counts = {'sent': 0, 'failed': 0}

        def progress(i, number, ok):
            counts['sent' if ok else 'failed'] += 1
            job_model.objects.filter(pk=job_id).update(
                sent=counts['sent'], failed=counts['failed'])

        result = send_broadcast(
            recipients, template=template, language=language, phone_id=phone_id,
            caption=caption or None, header_image_id=header_image_id,
            chat_media_name=chat_media_name, on_progress=progress,
            outbound_model=outbound_model,
        )
        job_model.objects.filter(pk=job_id).update(
            status='done', sent=result['sent'], failed=result['failed'],
            errors='\n'.join(result['errors']),
            message=f"{result['sent']} of {len(recipients)} delivered to the API"
                    + (f" · {result['failed']} failed" if result['failed'] else ''))
    except Exception as exc:  # noqa: BLE001 — record any failure on the job
        logger.exception('Broadcast job %s failed', job_id)
        job_model.objects.filter(pk=job_id).update(status='error', message=str(exc)[:255])
    finally:
        connections.close_all()  # threads get their own DB connection — release it


@login_required
def whatsapp_broadcast(request):
    from .broadcast import parse_numbers

    BroadcastJobM = pick(request, BroadcastJob, AlabamaBroadcastJob)
    WhatsAppOutboundM = pick(request, WhatsAppOutbound, AlabamaWhatsAppOutbound)

    labels   = wa_labels(request)
    id_order = wa_phone_ids(request)
    default_phone_id = wa_default_phone_id(request)
    numbers_choices = [{'id': pid, 'label': labels.get(pid, pid)} for pid in id_order]

    ctx = {
        'numbers_choices': numbers_choices,
        'default_phone_id': default_phone_id,
        'template': 'plumbing_marketing',
        'language': 'en',
    }

    if request.method != 'POST':
        return render(request, tpl(request, 'whatsapp_broadcast.html'), ctx)

    template = request.POST.get('template', '').strip()
    language = request.POST.get('language', 'en').strip() or 'en'
    phone_id = request.POST.get('phone_id', '').strip() or default_phone_id
    caption  = request.POST.get('caption', '').strip()
    csv_file = request.FILES.get('csv')
    image    = request.FILES.get('image')

    # Preserve what the user typed so the form repopulates on error.
    ctx.update({'template': template, 'language': language,
                'caption': caption, 'selected_phone_id': phone_id})

    if not template:
        ctx['error'] = 'Template name is required.'
        return render(request, tpl(request, 'whatsapp_broadcast.html'), ctx)
    if not csv_file:
        ctx['error'] = 'Please upload a CSV file of recipient numbers.'
        return render(request, tpl(request, 'whatsapp_broadcast.html'), ctx)

    try:
        raw = csv_file.read().decode('utf-8-sig')
    except (UnicodeDecodeError, ValueError):
        ctx['error'] = 'Could not read the CSV file — make sure it is a plain CSV/text file.'
        return render(request, tpl(request, 'whatsapp_broadcast.html'), ctx)

    recipients = parse_numbers(raw)
    if not recipients:
        ctx['error'] = 'No valid phone numbers found in the first column of the CSV.'
        return render(request, tpl(request, 'whatsapp_broadcast.html'), ctx)

    # Read the optional header image now (in the request); the actual Meta upload
    # happens in the worker so a slow upload doesn't block the response.
    image_bytes = image_mime = image_name = None
    if image:
        image_mime = image.content_type or 'application/octet-stream'
        if not image_mime.startswith('image/'):
            ctx['error'] = 'The header file must be an image (JPG or PNG).'
            return render(request, tpl(request, 'whatsapp_broadcast.html'), ctx)
        image_bytes = image.read()
        image_name  = image.name

    job = BroadcastJobM.objects.create(
        template=template, label=labels.get(phone_id, phone_id),
        phone_id=phone_id, total=len(recipients), status='running')

    threading.Thread(
        target=_broadcast_worker, args=(job.id, recipients),
        kwargs=dict(template=template, language=language, phone_id=phone_id,
                    caption=caption, image_bytes=image_bytes,
                    image_mime=image_mime, image_name=image_name,
                    job_model=BroadcastJobM, outbound_model=WhatsAppOutboundM),
        daemon=True,
    ).start()

    ctx['job'] = {'id': job.id, 'total': len(recipients), 'label': labels.get(phone_id, phone_id)}
    return render(request, tpl(request, 'whatsapp_broadcast.html'), ctx)


@login_required
def whatsapp_broadcast_status(request, job_id):
    """JSON progress for a running/finished broadcast, polled by the page."""
    BroadcastJobM = pick(request, BroadcastJob, AlabamaBroadcastJob)
    job = get_object_or_404(BroadcastJobM, pk=job_id)
    err_lines = [e for e in job.errors.split('\n') if e] if job.errors else []
    return JsonResponse({
        'status': job.status,
        'total': job.total,
        'sent': job.sent,
        'failed': job.failed,
        'message': job.message,
        'label': job.label,
        'errors': err_lines[:20],
        'more_errors': max(0, len(err_lines) - 20),
    })


# ── Per-sender chat thread ────────────────────────────────────────────────────

@login_required
@xframe_options_sameorigin  # allow this page to load inside the WhatsApp shell's iframe (same origin only)
def whatsapp_chat(request, sender):
    from datetime import timedelta

    WhatsAppLeadM = pick(request, WhatsAppLead, AlabamaWhatsAppLead)
    WhatsAppOutboundM = pick(request, WhatsAppOutbound, AlabamaWhatsAppOutbound)

    all_incoming = WhatsAppLeadM.objects.filter(sender=sender)

    # Each (customer ↔ our number) is its own conversation. Build a tab per number.
    labels   = wa_labels(request)
    id_order = wa_phone_ids(request)
    distinct = list(all_incoming.exclude(business_phone_id='')
                                .order_by()  # clear default ordering so DISTINCT works
                                .values_list('business_phone_id', flat=True).distinct())
    distinct.sort(key=lambda pid: id_order.index(pid) if pid in id_order else 999)

    # Active number: from query string, else the most recent one this sender used.
    active_number = request.GET.get('number', '')
    if active_number not in distinct:
        latest = all_incoming.order_by('-received_at').first()
        active_number = latest.business_phone_id if latest and latest.business_phone_id else ''

    numbers = [{'id': pid, 'label': labels.get(pid, pid), 'active': pid == active_number}
               for pid in distinct]

    # Scope the thread to the active number (fall back to everything for legacy data).
    if active_number:
        thread_in = all_incoming.filter(business_phone_id=active_number)
        outbound = list(WhatsAppOutboundM.objects.filter(recipient=sender, business_phone_id=active_number).order_by('sent_at'))
    else:
        thread_in = all_incoming
        outbound = list(WhatsAppOutboundM.objects.filter(recipient=sender).order_by('sent_at'))

    # Opening the conversation = reading it (WhatsApp-style). Mark its inbound
    # messages seen so the unread badge clears and stays cleared after refresh.
    thread_in.filter(read=False).update(read=True)
    incoming = list(thread_in.order_by('received_at'))

    timeline = []
    for msg in incoming:
        timeline.append({
            'dir':        'in',
            'id':         msg.id,
            'text':       msg.text_body,
            'time':       msg.received_at,
            'msg_type':   msg.msg_type,
            'media_url':  msg.media_file.url if msg.media_file else '',
            'media_name': msg.media_name,
        })
        if msg.reply_text:
            timeline.append({'dir': 'out', 'text': msg.reply_text,
                              'time': msg.received_at + timedelta(seconds=1), 'legacy': True})

    for msg in outbound:
        timeline.append({
            'dir':        'out',
            'text':       msg.text_body,
            'time':       msg.sent_at,
            'msg_type':   msg.msg_type,
            'media_url':  msg.media_file.url if msg.media_file else '',
            'media_name': msg.media_name,
        })

    timeline.sort(key=lambda x: x['time'])

    sender_name = next((m.sender_name for m in incoming if m.sender_name), '')

    return render(request, tpl(request, 'whatsapp_chat.html'), {
        'sender': sender,
        'sender_name': sender_name,
        'timeline': timeline,
        'message_count': len(incoming),
        'numbers': numbers,
        'active_number': active_number,
        'active_label': labels.get(active_number, ''),
        # When loaded inside the WhatsApp-Web shell's right pane, hide the
        # standalone CRM chrome and show only the conversation.
        'embed': request.GET.get('embed') == '1',
    })


def _business_phone_id_for(sender, lead_model=WhatsAppLead):
    """The number this customer last contacted us on — so we reply from the same one."""
    lead = (lead_model.objects
            .filter(sender=sender)
            .exclude(business_phone_id='')
            .order_by('-received_at')
            .first())
    return lead.business_phone_id if lead else ''


@login_required
@csrf_exempt
def whatsapp_chat_send(request, sender):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    WhatsAppLeadM = pick(request, WhatsAppLead, AlabamaWhatsAppLead)
    WhatsAppOutboundM = pick(request, WhatsAppOutbound, AlabamaWhatsAppOutbound)

    try:
        body = json.loads(request.body)
        message = body.get('message', '').strip()
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not message:
        return JsonResponse({'error': 'Message is required'}, status=400)

    business_phone_id = body.get('number') or _business_phone_id_for(sender, WhatsAppLeadM)
    from .utils import send_whatsapp_reply as send_reply
    success = send_reply(sender, message, phone_number_id=business_phone_id)

    if success:
        WhatsAppOutboundM.objects.create(recipient=sender, msg_type='text', text_body=message,
                                         business_phone_id=business_phone_id)
        # Mark the customer's messages on this number as replied (outbound record
        # holds the text — don't also write reply_text or it shows twice).
        mark = WhatsAppLeadM.objects.filter(sender=sender, replied=False)
        if business_phone_id:
            mark = mark.filter(business_phone_id=business_phone_id)
        mark.update(replied=True)
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Failed to send — check WHATSAPP_ACCESS_TOKEN and phone number ID'}, status=502)


@login_required
@csrf_exempt
def whatsapp_chat_send_media(request, sender):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    WhatsAppLeadM = pick(request, WhatsAppLead, AlabamaWhatsAppLead)
    WhatsAppOutboundM = pick(request, WhatsAppOutbound, AlabamaWhatsAppOutbound)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    caption    = request.POST.get('caption', '').strip()
    mime_type  = file.content_type or 'application/octet-stream'

    business_phone_id = request.POST.get('number') or _business_phone_id_for(sender, WhatsAppLeadM)
    from .utils import upload_whatsapp_media, send_whatsapp_media, mime_to_whatsapp_type
    media_type = mime_to_whatsapp_type(mime_type)

    file_bytes = file.read()
    media_id   = upload_whatsapp_media(file_bytes, mime_type, file.name, phone_number_id=business_phone_id)

    if not media_id:
        return JsonResponse({'error': 'Failed to upload media to WhatsApp — check API credentials'}, status=502)

    success = send_whatsapp_media(sender, media_type, media_id, caption=caption,
                                  filename=file.name, phone_number_id=business_phone_id)

    if success:
        from django.core.files.base import ContentFile
        outbound = WhatsAppOutboundM(
            recipient=sender, msg_type=media_type,
            text_body=caption, media_name=file.name,
            business_phone_id=business_phone_id,
        )
        outbound.media_file.save(file.name, ContentFile(file_bytes), save=True)
        mark = WhatsAppLeadM.objects.filter(sender=sender, replied=False)
        if business_phone_id:
            mark = mark.filter(business_phone_id=business_phone_id)
        mark.update(replied=True)
        media_url = request.build_absolute_uri(outbound.media_file.url)
        return JsonResponse({'ok': True, 'media_type': media_type, 'media_url': media_url, 'media_name': file.name, 'caption': caption})

    return JsonResponse({'error': 'Failed to send media via WhatsApp'}, status=502)
