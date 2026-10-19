"""Keep Alabama-only users inside the /alabama/ site.

A logged-in user is "Alabama only" when their username is listed in
settings.ALABAMA_ONLY_USERS or they belong to the 'alabama_only' group. Such a
user may use /alabama/* (pages and API) but not the main CRM site; anything
else is redirected to /alabama/ (or answered with 403 for /api/ calls).
Everyone else, and anonymous visitors, are untouched.
"""
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect

ALABAMA_GROUP = 'alabama_only'

# Paths an Alabama-only user may still reach outside /alabama/.
ALLOWED_PREFIXES = (
    '/alabama/',
    '/accounts/',   # login / logout
    '/static/',
    '/media/',
)


def is_alabama_only(user):
    if not user.is_authenticated:
        return False
    listed = {u.lower() for u in getattr(settings, 'ALABAMA_ONLY_USERS', [])}
    if user.get_username().lower() in listed:
        return True
    return user.groups.filter(name=ALABAMA_GROUP).exists()


class AlabamaOnlyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path != '/alabama' and not path.startswith(ALLOWED_PREFIXES) and is_alabama_only(request.user):
            if path.startswith('/api/'):
                return JsonResponse({'detail': 'Not allowed for this account.'}, status=403)
            return redirect(settings.ALABAMA_URL)
        return self.get_response(request)
