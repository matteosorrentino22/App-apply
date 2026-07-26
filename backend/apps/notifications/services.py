import json

from django.conf import settings
from pywebpush import webpush


def send_web_push(subscription, payload):
    """Invia una notifica Web Push standard a una singola sottoscrizione
    (02-specifiche-tecniche-v3.md §3.8): nessun servizio a pagamento,
    autenticazione tramite chiavi VAPID."""
    webpush(
        subscription_info={
            "endpoint": subscription.endpoint,
            "keys": {"p256dh": subscription.p256dh_key, "auth": subscription.auth_key},
        },
        data=json.dumps(payload),
        vapid_private_key=settings.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
    )
