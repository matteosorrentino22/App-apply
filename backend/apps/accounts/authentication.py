from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication, get_authorization_header

from .models import AuthToken
from .tokens import hash_token_key

# `last_used_at` viene riscritto al più una volta l'ora: abbastanza preciso
# per una scadenza a 30 giorni, senza una UPDATE a ogni richiesta.
LAST_USED_UPDATE_INTERVAL = timedelta(hours=1)


class ExpiringTokenAuthentication(BaseAuthentication):
    """Header `Authorization: Token <chiave>` (stesso formato del Token DRF
    usato fino allo Sprint 65, il frontend non cambia). Un token inattivo da
    più di AUTH_TOKEN_IDLE_DAYS giorni viene cancellato e rifiutato (401)."""

    keyword = "Token"

    def authenticate(self, request):
        parts = get_authorization_header(request).split()
        if not parts or parts[0].lower() != self.keyword.lower().encode():
            return None
        if len(parts) != 2:
            raise exceptions.AuthenticationFailed(_("Token non valido."))
        try:
            key = parts[1].decode()
        except UnicodeError as exc:
            raise exceptions.AuthenticationFailed(_("Token non valido.")) from exc

        token = (
            AuthToken.objects.select_related("user").filter(key_hash=hash_token_key(key)).first()
        )
        if token is None or not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("Token non valido."))

        now = timezone.now()
        if now - token.last_used_at > timedelta(days=settings.AUTH_TOKEN_IDLE_DAYS):
            token.delete()
            raise exceptions.AuthenticationFailed(_("Sessione scaduta, accedi di nuovo."))
        if now - token.last_used_at > LAST_USED_UPDATE_INTERVAL:
            AuthToken.objects.filter(pk=token.pk).update(last_used_at=now)
            token.last_used_at = now

        return token.user, token

    def authenticate_header(self, request):
        return self.keyword
