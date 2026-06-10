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


def _token():
    return getattr(settings, 'WHATSAPP_ACCESS_TOKEN', None)

def _api_version():
    return getattr(settings, 'WHATSAPP_API_VERSION', 'v22.0')

def _default_phone_id():
    """Fallback number to send from when a message has no recorded business_phone_id."""
    ids = getattr(settings, 'WHATSAPP_PHONE_NUMBER_IDS', [])
    return ids[0] if ids else None

def _messages_url(phone_number_id=None):
    """Build the Graph /messages endpoint for a given phone_number_id."""
    pid = phone_number_id or _default_phone_id()
    if not pid:
        return None
    return f'https://graph.facebook.com/{_api_version()}/{pid}/messages'

def _media_upload_url(phone_number_id=None):
    """Build the Graph /media endpoint for a given phone_number_id."""
    pid = phone_number_id or _default_phone_id()
    if not pid:
        return None
    return f'https://graph.facebook.com/{_api_version()}/{pid}/media'


def send_whatsapp_reply(to_number, message_text, phone_number_id=None):
    api_url      = _messages_url(phone_number_id)
    access_token = _token()

    if not api_url or not access_token:
        logger.error('No send URL (missing phone number ID) or WHATSAPP_ACCESS_TOKEN not set')
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


def upload_whatsapp_media(file_bytes, mime_type, filename, phone_number_id=None):
    """Upload file to Meta and return media_id, or None on failure."""
    upload_url   = _media_upload_url(phone_number_id)
    access_token = _token()

    if not upload_url or not access_token:
        logger.error('No send URL (missing phone number ID) or WHATSAPP_ACCESS_TOKEN not set')
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


def send_whatsapp_media(to_number, media_type, media_id, caption='', filename='', phone_number_id=None):
    """Send a media message using an already-uploaded media_id."""
    api_url      = _messages_url(phone_number_id)
    access_token = _token()

    if not api_url or not access_token:
        logger.error('No send URL (missing phone number ID) or WHATSAPP_ACCESS_TOKEN not set')
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


def download_whatsapp_media(media_id):
    """Fetch inbound media from Meta. Returns (bytes, mime_type, filename) or (None, None, None)."""
    access_token = _token()
    if not access_token:
        logger.error('WHATSAPP_ACCESS_TOKEN not set — cannot download media')
        return None, None, None

    try:
        meta_resp = requests.get(
            f'https://graph.facebook.com/v22.0/{media_id}',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=15,
        )
        meta_resp.raise_for_status()
        meta = meta_resp.json()
        media_url = meta.get('url')
        mime_type = meta.get('mime_type', 'application/octet-stream')
        if not media_url:
            logger.error(f'No URL in Meta media response for {media_id}: {meta}')
            return None, None, None

        dl_resp = requests.get(
            media_url,
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=60,
        )
        dl_resp.raise_for_status()

        ext_map = {
            'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp', 'image/gif': 'gif',
            'video/mp4': 'mp4', 'video/3gpp': '3gp',
            'audio/ogg': 'ogg', 'audio/mpeg': 'mp3', 'audio/aac': 'aac',
            'application/pdf': 'pdf',
        }
        ext = ext_map.get(mime_type, mime_type.split('/')[-1])
        filename = f'{media_id}.{ext}'

        logger.info(f'Downloaded inbound WhatsApp media {media_id} ({mime_type}, {len(dl_resp.content)} bytes)')
        return dl_resp.content, mime_type, filename

    except requests.exceptions.RequestException as e:
        logger.error(f'WhatsApp media download error for {media_id}: {e}')
        if getattr(e, 'response', None) is not None:
            logger.error(f'Meta API response: {e.response.text}')
        return None, None, None


def mime_to_whatsapp_type(mime_type):
    """Map a MIME type to the WhatsApp message type string."""
    if mime_type in WHATSAPP_IMAGE_MIMES:
        return 'image'
    for prefix, wa_type in WHATSAPP_MEDIA_TYPES.items():
        if mime_type.startswith(prefix):
            return wa_type
    return 'document'
