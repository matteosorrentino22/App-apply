import json
import logging
from urllib.parse import urlsplit

from django.conf import settings
from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)

PUSH_TIMEOUT_SECONDS = 10


def send_web_push(subscription, payload):
    """Invia una notifica Web Push standard a una singola sottoscrizione
    (02-specifiche-tecniche-v3.md §3.8): nessun servizio a pagamento,
    autenticazione tramite chiavi VAPID. Se il push service risponde che la
    sottoscrizione non esiste più (404/410: permesso revocato, browser
    disinstallato) la si elimina; ogni altro errore risale al chiamante."""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
            },
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
            timeout=PUSH_TIMEOUT_SECONDS,
        )
    except WebPushException as exc:
        if getattr(exc.response, "status_code", None) in (404, 410):
            logger.info(
                "Push: sottoscrizione %s scaduta (%s), eliminata",
                subscription.pk,
                urlsplit(subscription.endpoint).hostname,
            )
            subscription.delete()
            return
        raise
