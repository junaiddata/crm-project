"""
Shared WhatsApp template-broadcast logic, used by both the
`broadcast_template` management command and the web Broadcast page.

Outside the 24-hour service window only an *approved template* can open a
conversation, so marketing "broadcasts" are template sends — one /messages
call per recipient (there is no bulk endpoint).
"""
import csv
import io
import os
import re

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import WhatsAppOutbound
from .utils import send_whatsapp_template, upload_whatsapp_media

# +971 54 533 8872 — the number we currently receive on.
DEFAULT_PHONE_ID = '1131190376754791'


def parse_numbers(raw_text):
    """Return de-duplicated, normalized phone numbers from CSV text.

    The number must be in the FIRST column; '+', spaces and dashes are stripped,
    and a header row / anything shorter than 8 digits is skipped.
    """
    seen, numbers = set(), []
    for row in csv.reader(io.StringIO(raw_text)):
        if not row:
            continue
        digits = re.sub(r'[^\d]', '', row[0].strip())
        if len(digits) < 8:
            continue
        if digits not in seen:
            seen.add(digits)
            numbers.append(digits)
    return numbers


def stage_chat_image(file_bytes, filename):
    """Copy the broadcast image into media storage once and return its storage
    name (e.g. 'whatsapp_outbound/plumbing.jpeg'). Every outbound record reuses
    this single file so the broadcast renders as an image bubble in the chat."""
    return default_storage.save(
        f'whatsapp_outbound/{os.path.basename(filename)}',
        ContentFile(file_bytes),
    )


def upload_header_image(file_bytes, mime_type, filename, phone_id):
    """Upload the header image to Meta; return its media_id (or None on failure)."""
    return upload_whatsapp_media(file_bytes, mime_type, filename, phone_id)


def send_broadcast(numbers, *, template, language='en', phone_id=DEFAULT_PHONE_ID,
                   caption=None, header_image_id=None, header_image_url=None,
                   chat_media_name=None, on_progress=None, outbound_model=WhatsAppOutbound):
    """Send the template to every number and record each send.

    Image inputs are pre-resolved by the caller:
      - header_image_id / header_image_url: passed to the template send.
      - chat_media_name: storage name (from stage_chat_image) used so the chat
        thread shows the broadcast as an image bubble.

    on_progress(i, number, ok) is called after each send, if given.
    `outbound_model` lets the Alabama site log into its own outbound table.
    Returns dict(sent, failed, errors).
    """
    caption = caption or f'Broadcast: {template}'
    sent = failed = 0
    errors = []

    for i, number in enumerate(numbers, 1):
        msg_id = send_whatsapp_template(
            to_number=number,
            template_name=template,
            language=language,
            header_image_url=header_image_url,
            header_image_id=header_image_id,
            phone_number_id=phone_id,
        )
        if msg_id:
            sent += 1
            rec = outbound_model(
                recipient=number,
                business_phone_id=phone_id,
                msg_type='image' if chat_media_name else 'text',
                text_body=caption,
            )
            if chat_media_name:
                rec.media_file.name = chat_media_name
                rec.media_name = os.path.basename(chat_media_name)
            rec.save()
        else:
            failed += 1
            errors.append(number)

        if on_progress:
            on_progress(i, number, bool(msg_id))

    return {'sent': sent, 'failed': failed, 'errors': errors}
