import hashlib

from django.contrib import admin
from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.throttling import BaseThrottle

# Tentativi di login falliti all'admin per IP (Sprint 66): finestra fissa
# che parte dal primo errore, azzerata da un login riuscito.
ADMIN_LOGIN_MAX_FAILURES = 10
ADMIN_LOGIN_WINDOW_SECONDS = 15 * 60


def _failures_key(request):
    # Stesso calcolo dell'IP del throttling DRF (X-Forwarded-For di Caddy, NUM_PROXIES).
    ident = BaseThrottle().get_ident(request)
    return "admin_login_failures:" + hashlib.sha256(ident.encode()).hexdigest()


def throttled_admin_login(request, extra_context=None):
    key = _failures_key(request)
    if request.method == "POST" and (cache.get(key) or 0) >= ADMIN_LOGIN_MAX_FAILURES:
        return HttpResponse("Troppi tentativi di accesso. Riprova più tardi.", status=429)

    response = admin.site.login(request, extra_context)

    if request.method == "POST":
        if response.status_code == 302:
            cache.delete(key)
        else:
            cache.add(key, 0, ADMIN_LOGIN_WINDOW_SECONDS)
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, ADMIN_LOGIN_WINDOW_SECONDS)
    return response
