import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Lead, WhatsAppLead, WhatsAppOutbound
from .serializers import LeadSerializer

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


def _process_whatsapp_payload(payload, allowed_phone_ids=None):
    """Store inbound messages. When allowed_phone_ids is given, only messages
    received on those of OUR numbers are processed (others are ignored)."""
    for entry in payload.get('entry', []):
        for change in entry.get('changes', []):
            if change.get('field') != 'messages':
                continue
            value = change.get('value', {})
            business_phone_id = value.get('metadata', {}).get('phone_number_id', '')

            # Only handle numbers we own natively; ignore anything else.
            if allowed_phone_ids is not None and business_phone_id not in allowed_phone_ids:
                continue

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
                    WhatsAppLead.objects.get_or_create(
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

                    lead, created = WhatsAppLead.objects.get_or_create(
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
            # Direct from Meta — only handle the numbers we own.
            _process_whatsapp_payload(payload, allowed_phone_ids=settings.WHATSAPP_PHONE_NUMBER_IDS)
    except Exception:
        logger.exception('Error processing WhatsApp webhook payload')

    return JsonResponse({'ok': True})


@login_required
@csrf_exempt
def whatsapp_reply(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    wa_lead = get_object_or_404(WhatsAppLead, pk=pk)

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
            WhatsAppLead.objects.filter(pk__in=also_mark_ids).update(replied=False, reply_text='')
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
            WhatsAppLead.objects.filter(pk__in=also_mark_ids).update(replied=True, reply_text=message)
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Failed to send — check WHATSAPP_ACCESS_TOKEN and phone number ID'}, status=502)


CRM_SALESPEOPLE = ['RAFIQ', 'SIYAB', 'MUZAIN', 'AIJAZ', 'MUSHARAF']


class LeadListCreateView(APIView):
    def get(self, request):
        leads = Lead.objects.all()
        serializer = LeadSerializer(leads, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        # When adding from WhatsApp: one lead per customer per DAY.
        #   • same number + same date  → append only the NEW selected messages
        #   • same number, different day → fall through and create a separate lead
        if request.data.get('dedupeBySender'):
            mobile    = (request.data.get('mobileNo') or '').strip()
            lead_date = (request.data.get('date') or '').strip()
            if mobile:
                lookup = Lead.objects.filter(mobile_no=mobile)
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
                        serializer = LeadSerializer(existing, context={'request': request})
                        return Response(
                            {'appended': True, 'added': len(to_add), **serializer.data},
                            status=status.HTTP_200_OK,
                        )

                    serializer = LeadSerializer(existing, context={'request': request})
                    return Response(
                        {'duplicate': True, 'added': 0, **serializer.data},
                        status=status.HTTP_200_OK,
                    )

        # When adding from Email: one lead per customer address per DAY (same
        # append-or-create behaviour as WhatsApp, keyed on email instead).
        if request.data.get('dedupeByEmail'):
            email_addr = (request.data.get('emailId') or '').strip()
            lead_date  = (request.data.get('date') or '').strip()
            if email_addr:
                lookup = Lead.objects.filter(email_id__iexact=email_addr)
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
                        serializer = LeadSerializer(existing, context={'request': request})
                        return Response(
                            {'appended': True, 'added': len(to_add), **serializer.data},
                            status=status.HTTP_200_OK,
                        )

                    serializer = LeadSerializer(existing, context={'request': request})
                    return Response(
                        {'duplicate': True, 'added': 0, **serializer.data},
                        status=status.HTTP_200_OK,
                    )

        serializer = LeadSerializer(data=request.data, context={'request': request})
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
    def get_object(self, pk):
        return get_object_or_404(Lead, pk=pk)

    def get(self, request, pk):
        lead = self.get_object(pk)
        serializer = LeadSerializer(lead, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, pk):
        lead = self.get_object(pk)
        data = request.data
        # Identifying fields are locked for auto-added leads.
        if lead.source == 'whatsapp':
            data = {k: v for k, v in data.items() if k not in ('date', 'mobileNo')}
        elif lead.source == 'email':
            data = {k: v for k, v in data.items() if k not in ('date', 'emailId')}
        serializer = LeadSerializer(lead, data=data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        lead = self.get_object(pk)
        if lead.quotation_file:
            lead.quotation_file.delete(save=False)
        lead.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LeadUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        lead = get_object_or_404(Lead, pk=pk)
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
        lead = get_object_or_404(Lead, pk=pk)
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


@login_required
def whatsapp_dashboard(request):
    base = WhatsAppLead.objects.all()

    # ── Filter by which of OUR numbers received the messages ──
    active_number = request.GET.get('number', 'all')
    number_base = base
    if active_number != 'all':
        number_base = base.filter(business_phone_id=active_number)

    qs = number_base
    active_filter = request.GET.get('filter', 'all')
    if active_filter == 'unreplied':
        qs = qs.filter(replied=False)
    elif active_filter == 'replied':
        qs = qs.filter(replied=True)

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(sender__icontains=search) | Q(text_body__icontains=search))

    # Reply/total counts respect the selected number
    total     = number_base.count()
    unreplied = number_base.filter(replied=False).count()
    replied   = number_base.filter(replied=True).count()

    # Per-number chips (independent of the reply filter)
    labels = getattr(settings, 'WHATSAPP_NUMBER_LABELS', {})
    numbers = [
        {'id': pid, 'label': labels.get(pid, pid),
         'count': base.filter(business_phone_id=pid).count()}
        for pid in getattr(settings, 'WHATSAPP_PHONE_NUMBER_IDS', [])
    ]

    groups = _conversations_by_sender(qs)

    return render(request, 'whatsapp_dashboard.html', {
        'groups': groups,
        'shown_count': len(groups),
        'active_filter': active_filter,
        'active_number': active_number,
        'numbers': numbers,
        'all_count': base.count(),
        'search': search,
        'total': total,
        'unreplied': unreplied,
        'replied_count': replied,
    })


@login_required
def mark_replied(request, pk):
    from django.http import HttpResponseRedirect
    from django.views.decorators.http import require_POST as rp
    if request.method != 'POST':
        return HttpResponseRedirect('/whatsapp/')
    wa = get_object_or_404(WhatsAppLead, pk=pk)
    action = request.POST.get('action', 'reply')
    if action == 'unreply':
        wa.replied = False
        wa.reply_text = ''
    else:
        wa.replied = True
        wa.reply_text = request.POST.get('reply_text', '').strip()
    wa.save()
    next_url = request.POST.get('next', '/whatsapp/')
    return HttpResponseRedirect(next_url)


# ── Per-sender chat thread ────────────────────────────────────────────────────

@login_required
def whatsapp_chat(request, sender):
    from datetime import timedelta

    all_incoming = WhatsAppLead.objects.filter(sender=sender)

    # Each (customer ↔ our number) is its own conversation. Build a tab per number.
    labels   = getattr(settings, 'WHATSAPP_NUMBER_LABELS', {})
    id_order = getattr(settings, 'WHATSAPP_PHONE_NUMBER_IDS', [])
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
        incoming = list(all_incoming.filter(business_phone_id=active_number).order_by('received_at'))
        outbound = list(WhatsAppOutbound.objects.filter(recipient=sender, business_phone_id=active_number).order_by('sent_at'))
    else:
        incoming = list(all_incoming.order_by('received_at'))
        outbound = list(WhatsAppOutbound.objects.filter(recipient=sender).order_by('sent_at'))

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

    return render(request, 'whatsapp_chat.html', {
        'sender': sender,
        'sender_name': sender_name,
        'timeline': timeline,
        'message_count': len(incoming),
        'numbers': numbers,
        'active_number': active_number,
        'active_label': labels.get(active_number, ''),
    })


def _business_phone_id_for(sender):
    """The number this customer last contacted us on — so we reply from the same one."""
    lead = (WhatsAppLead.objects
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

    try:
        body = json.loads(request.body)
        message = body.get('message', '').strip()
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not message:
        return JsonResponse({'error': 'Message is required'}, status=400)

    business_phone_id = body.get('number') or _business_phone_id_for(sender)
    from .utils import send_whatsapp_reply as send_reply
    success = send_reply(sender, message, phone_number_id=business_phone_id)

    if success:
        WhatsAppOutbound.objects.create(recipient=sender, msg_type='text', text_body=message,
                                        business_phone_id=business_phone_id)
        # Mark the customer's messages on this number as replied (outbound record
        # holds the text — don't also write reply_text or it shows twice).
        mark = WhatsAppLead.objects.filter(sender=sender, replied=False)
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

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    caption    = request.POST.get('caption', '').strip()
    mime_type  = file.content_type or 'application/octet-stream'

    business_phone_id = request.POST.get('number') or _business_phone_id_for(sender)
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
        outbound = WhatsAppOutbound(
            recipient=sender, msg_type=media_type,
            text_body=caption, media_name=file.name,
            business_phone_id=business_phone_id,
        )
        outbound.media_file.save(file.name, ContentFile(file_bytes), save=True)
        mark = WhatsAppLead.objects.filter(sender=sender, replied=False)
        if business_phone_id:
            mark = mark.filter(business_phone_id=business_phone_id)
        mark.update(replied=True)
        media_url = request.build_absolute_uri(outbound.media_file.url)
        return JsonResponse({'ok': True, 'media_type': media_type, 'media_url': media_url, 'media_name': file.name, 'caption': caption})

    return JsonResponse({'error': 'Failed to send media via WhatsApp'}, status=502)
