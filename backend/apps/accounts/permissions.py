from django.conf import settings
from rest_framework import exceptions
from rest_framework.permissions import BasePermission

from .legal import missing_acceptances

LEGAL_ACCEPTANCE_REQUIRED_CODE = "legal_acceptance_required"


class LegalAcceptanceRequired(BasePermission):
    """Gate delle accettazioni legali (Sprint 67), nei permessi di default
    dell'API: un utente autenticato che non ha accettato le versioni
    correnti di informativa, termini ed età minima riceve 403 con codice
    `legal_acceptance_required`. Non si applica alle view che dichiarano
    `permission_classes` (me, logout, accettazione, export, cancellazione
    account, cambio password, endpoint pubblici)."""

    def has_permission(self, request, view):
        user = request.user
        if not settings.LEGAL_GATE_ENABLED or not (user and user.is_authenticated):
            return True
        if missing_acceptances(user):
            raise exceptions.PermissionDenied(
                {
                    "detail": "Per continuare devi accettare l'informativa privacy e i termini di servizio.",
                    "code": LEGAL_ACCEPTANCE_REQUIRED_CODE,
                }
            )
        return True
