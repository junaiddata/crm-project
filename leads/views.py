import json
import logging

from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
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


@csrf_exempt
@require_POST
def whatsapp_webhook(request):
    # Verify internal secret
    secret = request.headers.get('X-Internal-Secret', '')
    if secret != settings.CRM_WEBHOOK_SECRET:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'ok': True})  # always 200 to avoid retries

    try:
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') != 'messages':
                    continue
                value = change.get('value', {})
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
                                      'text_body': caption, 'msg_type': stored_type},
                        )

                        if created and media_id:
                            from .utils import download_whatsapp_media
                            from django.core.files.base import ContentFile
                            file_bytes, mime_type, filename = download_whatsapp_media(media_id)
                            if file_bytes:
                                lead.media_name = filename
                                lead.media_file.save(filename, ContentFile(file_bytes), save=True)
    except Exception:
        logger.exception('Error processing WhatsApp webhook payload')

    return JsonResponse({'ok': True})


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
    success = send_reply(wa_lead.sender, message)

    if success:
        wa_lead.replied = True
        wa_lead.reply_text = message
        wa_lead.save()
        if also_mark_ids:
            WhatsAppLead.objects.filter(pk__in=also_mark_ids).update(replied=True, reply_text=message)
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Failed to send — check WHATSAPP_API_URL and WHATSAPP_ACCESS_TOKEN'}, status=502)


CRM_SALESPEOPLE = ['RAFIQ', 'SIYAB', 'MUZAIN', 'AIJAZ', 'MUSHARAF']


class LeadListCreateView(APIView):
    def get(self, request):
        leads = Lead.objects.all()
        serializer = LeadSerializer(leads, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        # When adding from the WhatsApp dashboard, avoid creating a duplicate
        # lead if one already exists for the same sender number.
        if request.data.get('dedupeBySender'):
            mobile = (request.data.get('mobileNo') or '').strip()
            if mobile:
                existing = Lead.objects.filter(mobile_no=mobile).first()
                if existing:
                    serializer = LeadSerializer(existing, context={'request': request})
                    return Response(
                        {'duplicate': True, **serializer.data},
                        status=status.HTTP_200_OK,
                    )

        serializer = LeadSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Mark WhatsApp-originated leads so their number/date stay locked.
            source = 'whatsapp' if request.data.get('dedupeBySender') else ''
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
        # Number and date are locked for WhatsApp-sourced leads.
        if lead.source == 'whatsapp':
            data = {k: v for k, v in data.items() if k not in ('date', 'mobileNo')}
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

def _group_whatsapp_messages(qs, gap_seconds=60):
    """Group consecutive messages from the same sender within gap_seconds into conversation groups."""
    messages = list(qs)  # ordered -received_at (newest first)
    if not messages:
        return []

    # Process in chronological order for proper consecutive grouping
    chrono = list(reversed(messages))
    groups = []
    current = None

    for msg in chrono:
        if (current is None
                or msg.sender != current['sender']
                or (msg.received_at - current['last_time']).total_seconds() > gap_seconds):
            if current:
                groups.append(current)
            current = {
                'sender': msg.sender,
                'messages': [msg],
                'first_time': msg.received_at,
                'last_time': msg.received_at,
            }
        else:
            current['messages'].append(msg)
            current['last_time'] = msg.received_at

    if current:
        groups.append(current)

    for g in groups:
        g['all_ids'] = [m.id for m in g['messages']]
        g['all_replied'] = all(m.replied for m in g['messages'])
        g['any_unreplied'] = any(not m.replied for m in g['messages'])
        # use last (most recent) message pk for the reply endpoint
        g['reply_pk'] = g['messages'][-1].id
        g['reply_text'] = g['messages'][-1].reply_text
        # first available WhatsApp profile name for this sender
        g['sender_name'] = next((m.sender_name for m in g['messages'] if m.sender_name), '')

    groups.reverse()  # newest group first
    return groups


def whatsapp_dashboard(request):
    qs = WhatsAppLead.objects.all()

    active_filter = request.GET.get('filter', 'all')
    if active_filter == 'unreplied':
        qs = qs.filter(replied=False)
    elif active_filter == 'replied':
        qs = qs.filter(replied=True)

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(Q(sender__icontains=search) | Q(text_body__icontains=search))

    total     = WhatsAppLead.objects.count()
    unreplied = WhatsAppLead.objects.filter(replied=False).count()
    replied   = WhatsAppLead.objects.filter(replied=True).count()

    groups = _group_whatsapp_messages(qs)

    return render(request, 'whatsapp_dashboard.html', {
        'groups': groups,
        'shown_count': len(groups),
        'active_filter': active_filter,
        'search': search,
        'total': total,
        'unreplied': unreplied,
        'replied_count': replied,
    })


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

def whatsapp_chat(request, sender):
    from datetime import timedelta

    incoming = list(WhatsAppLead.objects.filter(sender=sender).order_by('received_at'))
    outbound = list(WhatsAppOutbound.objects.filter(recipient=sender).order_by('sent_at'))

    timeline = []
    for msg in incoming:
        timeline.append({
            'dir':        'in',
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
    })


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

    from .utils import send_whatsapp_reply as send_reply
    success = send_reply(sender, message)

    if success:
        WhatsAppOutbound.objects.create(recipient=sender, msg_type='text', text_body=message)
        WhatsAppLead.objects.filter(sender=sender, replied=False).update(replied=True, reply_text=message)
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Failed to send — check WHATSAPP_API_URL and WHATSAPP_ACCESS_TOKEN'}, status=502)


@csrf_exempt
def whatsapp_chat_send_media(request, sender):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    caption    = request.POST.get('caption', '').strip()
    mime_type  = file.content_type or 'application/octet-stream'

    from .utils import upload_whatsapp_media, send_whatsapp_media, mime_to_whatsapp_type
    media_type = mime_to_whatsapp_type(mime_type)

    file_bytes = file.read()
    media_id   = upload_whatsapp_media(file_bytes, mime_type, file.name)

    if not media_id:
        return JsonResponse({'error': 'Failed to upload media to WhatsApp — check API credentials'}, status=502)

    success = send_whatsapp_media(sender, media_type, media_id, caption=caption, filename=file.name)

    if success:
        from django.core.files.base import ContentFile
        outbound = WhatsAppOutbound(
            recipient=sender, msg_type=media_type,
            text_body=caption, media_name=file.name,
        )
        outbound.media_file.save(file.name, ContentFile(file_bytes), save=True)
        WhatsAppLead.objects.filter(sender=sender, replied=False).update(
            replied=True, reply_text=f'[Sent {media_type}: {file.name}]'
        )
        media_url = request.build_absolute_uri(outbound.media_file.url)
        return JsonResponse({'ok': True, 'media_type': media_type, 'media_url': media_url, 'media_name': file.name, 'caption': caption})

    return JsonResponse({'error': 'Failed to send media via WhatsApp'}, status=502)
