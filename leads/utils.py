import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

WHATSAPP_MEDIA_TYPES = {
    # mime prefix → WhatsApp message type
    'image/':  'image',
    'video/':  'video',
    'audio/':  'audio',
}

WHATSAPP_IMAGE_MIMES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


def _api_url():
    return getattr(settings, 'WHATSAPP_API_URL', None)

def _token():
    return getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)

def _media_upload_url():
    """Derive /media endpoint from /messages URL."""
    url = _api_url()
    if not url:
        return None
    return url.replace('/messages', '/media')


def send_whatsapp_reply(to_number, message_text):
    api_url      = _api_url()
    access_token = _token()

    if not api_url or not access_token:
        logger.error('WHATSAPP_API_URL or WHATSAPP_ACCESS_TOKEN not set in settings')
        return False

    payload = {
        'messaging_product': 'whatsapp',
        'to': to_number,
        'type': 'text',
        'text': {'body': message_text},
    }

    try:
        resp = requests.post(
            api_url,
            json=payload,
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info(f'WhatsApp text sent to {to_number}')
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f'WhatsApp API error sending to {to_number}: {e}')
        if getattr(e, 'response', None) is not None:
            logger.error(f'Meta API response: {e.response.text}')
        return False


def upload_whatsapp_media(file_bytes, mime_type, filename):
    """Upload file to Meta and return media_id, or None on failure."""
    upload_url   = _media_upload_url()
    access_token = _token()

    if not upload_url or not access_token:
        logger.error('WHATSAPP_API_URL or WHATSAPP_ACCESS_TOKEN not set')
        return None

    try:
        resp = requests.post(
            upload_url,
            files={'file': (filename, file_bytes, mime_type)},
            data={'messaging_product': 'whatsapp'},
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=60,
        )
        resp.raise_for_status()
        media_id = resp.json().get('id')
        logger.info(f'WhatsApp media uploaded: {media_id}')
        return media_id
    except requests.exceptions.RequestException as e:
        logger.error(f'WhatsApp media upload error: {e}')
        if getattr(e, 'response', None) is not None:
            logger.error(f'Meta API response: {e.response.text}')
        return None


def send_whatsapp_media(to_number, media_type, media_id, caption='', filename=''):
    """Send a media message using an already-uploaded media_id."""
    api_url      = _api_url()
    access_token = _token()

    if not api_url or not access_token:
        logger.error('WHATSAPP_API_URL or WHATSAPP_ACCESS_TOKEN not set')
        return False

    media_obj = {'id': media_id}
    if caption:
        media_obj['caption'] = caption
    if media_type == 'document' and filename:
        media_obj['filename'] = filename

    payload = {
        'messaging_product': 'whatsapp',
        'to': to_number,
        'type': media_type,
        media_type: media_obj,
    }

    try:
        resp = requests.post(
            api_url,
            json=payload,
            headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
            timeout=15,
        )
        resp.raise_for_status()
        logger.info(f'WhatsApp {media_type} sent to {to_number}')
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f'WhatsApp media send error to {to_number}: {e}')
        if getattr(e, 'response', None) is not None:
            logger.error(f'Meta API response: {e.response.text}')
        return False


def mime_to_whatsapp_type(mime_type):
    """Map a MIME type to the WhatsApp message type string."""
    if mime_type in WHATSAPP_IMAGE_MIMES:
        return 'image'
    for prefix, wa_type in WHATSAPP_MEDIA_TYPES.items():
        if mime_type.startswith(prefix):
            return wa_type
    return 'document'
