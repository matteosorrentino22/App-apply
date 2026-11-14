from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation


def _is_api(request):
    return request.path_info.startswith("/api/")


class ApiLocaleMiddleware(LocaleMiddleware):
    """Lingua dei testi del backend (Sprint 71) dall'header Accept-Language,
    che la PWA invia a ogni chiamata con la lingua dell'interfaccia (it/en,
    `LANGUAGES`; qualunque altra lingua ricade sull'italiano). Solo per
    /api/: il Django Admin resta in italiano come prima, qualunque sia la
    lingua del browser di chi lo usa. A fine richiesta la lingua torna
    quella di default, così non resta attiva sul thread per la richiesta
    successiva (né per i test che chiamano i servizi direttamente)."""

    def process_request(self, request):
        if _is_api(request):
            super().process_request(request)
        else:
            translation.activate(settings.LANGUAGE_CODE)
            request.LANGUAGE_CODE = settings.LANGUAGE_CODE

    def process_response(self, request, response):
        if _is_api(request):
            response = super().process_response(request, response)
        translation.deactivate()
        return response
