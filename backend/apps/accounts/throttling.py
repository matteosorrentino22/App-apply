import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginEmailRateThrottle(SimpleRateThrottle):
    """Tentativi di login per email (Sprint 66), oltre al limite per IP
    (`ScopedRateThrottle`, scope "login"): un attacco distribuito su molti IP
    contro lo stesso account resta comunque limitato. Nella chiave di cache
    c'è l'hash dell'email, non l'email."""

    scope = "login_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if hasattr(request.data, "get") else None
        if not isinstance(email, str) or not email.strip():
            return None
        ident = hashlib.sha256(email.strip().lower().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}


class PostOnlyScopeMixin:
    """`ScopedRateThrottle` si applica a tutti i metodi della view: qui serve
    solo sul POST (per esempio il messaggio di chat, non la lettura della
    cronologia né l'accetta/rifiuta delle proposte)."""

    post_throttle_scope = None

    @property
    def throttle_scope(self):
        request = getattr(self, "request", None)
        return self.post_throttle_scope if request is not None and request.method == "POST" else None
