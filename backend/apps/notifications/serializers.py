from urllib.parse import urlsplit

from rest_framework import serializers

# Push service dei browser supportati (Sprint 66): l'endpoint arriva dal
# client e viene chiamato dal worker Celery, quindi niente URL arbitrari
# (rete interna, host che non rispondono). Chrome/Android: FCM; Firefox:
# Mozilla autopush; Safari: Apple; Edge: Windows Push Notification Services.
PUSH_SERVICE_HOSTS = {"fcm.googleapis.com", "updates.push.services.mozilla.com"}
PUSH_SERVICE_HOST_SUFFIXES = (".push.apple.com", ".notify.windows.com")


def is_allowed_push_endpoint(endpoint):
    try:
        parts = urlsplit(endpoint)
        port = parts.port
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return (
        parts.scheme == "https"
        and port is None
        and not parts.username
        and not parts.password
        and (host in PUSH_SERVICE_HOSTS or host.endswith(PUSH_SERVICE_HOST_SUFFIXES))
    )


class PushSubscriptionSerializer(serializers.Serializer):
    """Rispecchia la forma restituita da `PushSubscription.toJSON()` nel
    browser (standard Web Push), così il frontend può inoltrarla senza
    trasformazioni (Sprint 17)."""

    endpoint = serializers.URLField(max_length=1000)
    keys = serializers.DictField(child=serializers.CharField(max_length=255))

    def validate_endpoint(self, value):
        if not is_allowed_push_endpoint(value):
            raise serializers.ValidationError("Endpoint di notifica non supportato.")
        return value

    def validate_keys(self, value):
        if "p256dh" not in value or "auth" not in value:
            raise serializers.ValidationError("Richiede le chiavi 'p256dh' e 'auth'.")
        return value
