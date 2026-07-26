from rest_framework import serializers


class PushSubscriptionSerializer(serializers.Serializer):
    """Rispecchia la forma restituita da `PushSubscription.toJSON()` nel
    browser (standard Web Push), così il frontend può inoltrarla senza
    trasformazioni (Sprint 17)."""

    endpoint = serializers.URLField(max_length=1000)
    keys = serializers.DictField(child=serializers.CharField())

    def validate_keys(self, value):
        if "p256dh" not in value or "auth" not in value:
            raise serializers.ValidationError("Richiede le chiavi 'p256dh' e 'auth'.")
        return value
