"""Helpers for serving the Alabama sister-company site at /alabama/* on this
same Django project.

Alabama shares Junaid's Postgres database (crm_db) but keeps its own data in
separate, prefixed tables (alabama_lead, alabama_calllead, ...). The CRM views
and serializers are reused; they simply select the Alabama model/serializer set
when the request is under /alabama/.
"""


def is_alabama(request):
    """True when the current request is being served under /alabama/."""
    return request.path.startswith('/alabama/')


def pick(request, crm, alabama):
    """Return the Alabama object for /alabama/ requests, else the CRM one.

    Used by the shared views/serializers to select the right model or serializer
    class (alabama_* tables vs the default CRM tables) based on the URL.
    """
    return alabama if is_alabama(request) else crm


# ── Per-site WhatsApp config ───────────────────────────────────────────────────
# Alabama uses different WhatsApp numbers but the same Meta app/token, so only
# the phone-number IDs, labels and broadcast default are resolved per request.

def wa_phone_ids(request):
    from django.conf import settings
    return pick(request,
                getattr(settings, 'WHATSAPP_PHONE_NUMBER_IDS', []),
                getattr(settings, 'ALABAMA_WHATSAPP_PHONE_NUMBER_IDS', []))


def wa_labels(request):
    from django.conf import settings
    return pick(request,
                getattr(settings, 'WHATSAPP_NUMBER_LABELS', {}),
                getattr(settings, 'ALABAMA_WHATSAPP_NUMBER_LABELS', {}))


def wa_default_phone_id(request):
    from django.conf import settings
    from leads.broadcast import DEFAULT_PHONE_ID
    return pick(request, DEFAULT_PHONE_ID,
                getattr(settings, 'ALABAMA_WHATSAPP_DEFAULT_PHONE_ID', ''))


def tpl(request, name):
    """Return the alabama/-prefixed template for /alabama/ requests, else `name`.

    Lets the existing page views serve the Alabama-branded copies under
    templates/alabama/ without duplicating their data-prep logic.
    """
    return f'alabama/{name}' if is_alabama(request) else name
