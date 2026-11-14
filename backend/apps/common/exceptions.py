import math

from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler


def _throttled_detail(wait):
    if wait is None:
        return _("Troppe richieste: riprova più tardi.")
    if wait < 60:
        return ngettext(
            "Troppe richieste: riprova tra %(count)d secondo.",
            "Troppe richieste: riprova tra %(count)d secondi.",
            wait,
        ) % {"count": wait}
    if wait < 3600:
        minutes = math.ceil(wait / 60)
        return ngettext(
            "Troppe richieste: riprova tra %(count)d minuto.",
            "Troppe richieste: riprova tra %(count)d minuti.",
            minutes,
        ) % {"count": minutes}
    hours = math.ceil(wait / 3600)
    return ngettext(
        "Troppe richieste: riprova tra %(count)d ora.",
        "Troppe richieste: riprova tra %(count)d ore.",
        hours,
    ) % {"count": hours}


def api_exception_handler(exc, context):
    """Handler DRF standard, con un messaggio proprio per il 429 (Sprint 71):
    quello di DRF in italiano è tradotto a metà ("La richiesta è stata
    limitata (throttled). Expected available in N seconds.") e per i limiti
    giornalieri conta i secondi a decine di migliaia."""
    if isinstance(exc, exceptions.Throttled):
        exc.detail = exceptions.ErrorDetail(_throttled_detail(exc.wait), code=exc.default_code)
    return drf_exception_handler(exc, context)
