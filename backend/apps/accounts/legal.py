# Versioni correnti dei testi legali (Sprint 67). Il testo è nella PWA
# (frontend/src/legal/) e, come riferimento versionato, in Docs/legal/.
# Una modifica sostanziale dei testi va accompagnata da un nuovo numero di
# versione e data: gli utenti che hanno accettato la versione precedente
# vedono di nuovo la schermata di accettazione al primo accesso.
from django.conf import settings

from .models import LegalAcceptance

PRIVACY_VERSION = "1.1"
PRIVACY_DATE = "2026-11-15"
TERMS_VERSION = "1.0"
TERMS_DATE = "2026-11-14"
MIN_AGE = 16
# Versione della dichiarazione d'età: è l'età minima stessa, così un
# eventuale cambio del requisito richiede una nuova dichiarazione.
AGE_VERSION = str(MIN_AGE)

CURRENT_VERSIONS = {
    LegalAcceptance.Document.PRIVACY: PRIVACY_VERSION,
    LegalAcceptance.Document.TERMS: TERMS_VERSION,
    LegalAcceptance.Document.AGE: AGE_VERSION,
}


def missing_acceptances(user):
    """Documenti (privacy, terms, age) di cui `user` non ha ancora accettato
    la versione corrente. Calcolato una volta per richiesta."""
    cached = getattr(user, "_missing_legal_acceptances", None)
    if cached is not None:
        return cached
    accepted = set(
        LegalAcceptance.objects.filter(user=user).values_list("document", "version")
    )
    missing = [doc.value for doc, version in CURRENT_VERSIONS.items() if (doc.value, version) not in accepted]
    user._missing_legal_acceptances = missing
    return missing


def record_acceptances(user, documents=None):
    """Registra l'accettazione delle versioni correnti (tutte, o solo
    `documents`)."""
    rows = [
        LegalAcceptance(user=user, document=doc, version=version)
        for doc, version in CURRENT_VERSIONS.items()
        if documents is None or doc in documents
    ]
    LegalAcceptance.objects.bulk_create(rows)
    user._missing_legal_acceptances = None


def public_legal_info():
    return {
        "privacy": {"version": PRIVACY_VERSION, "date": PRIVACY_DATE},
        "terms": {"version": TERMS_VERSION, "date": TERMS_DATE},
        "min_age": MIN_AGE,
        "controller": {
            "name": settings.LEGAL_CONTROLLER_NAME,
            "address": settings.LEGAL_CONTROLLER_ADDRESS,
            "email": settings.LEGAL_CONTROLLER_EMAIL,
            "complete": bool(settings.LEGAL_CONTROLLER_NAME and settings.LEGAL_CONTROLLER_EMAIL),
        },
    }
