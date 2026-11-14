from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PushSubscription
from .serializers import PushSubscriptionSerializer


class VapidPublicKeyView(APIView):
    """Espone la chiave pubblica VAPID: il frontend la usa per
    `PushManager.subscribe()` (Sprint 20) — non era esposta da nessun
    endpoint, solo letta lato server per firmare gli invii (Sprint 17)."""


    def get(self, request):
        return Response({"public_key": settings.VAPID_PUBLIC_KEY})


# Una sottoscrizione per browser/dispositivo: oltre questo numero si
# eliminano le più vecchie (Sprint 66), così un nuovo dispositivo non resta
# mai escluso dalle notifiche per colpa di sottoscrizioni abbandonate.
MAX_PUSH_SUBSCRIPTIONS_PER_USER = 10


class PushSubscriptionView(APIView):
    """Registra (o aggiorna) la sottoscrizione Web Push del browser
    dell'utente autenticato (Sprint 17, 02-specifiche-tecniche-v3.md §3.8)."""


    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Attivare le notifiche su un dispositivo è un consenso esplicito:
        # riaccende anche la preferenza dell'account (Sprint 67).
        if not request.user.notifications_enabled:
            request.user.notifications_enabled = True
            request.user.save(update_fields=["notifications_enabled"])
        PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=data["endpoint"],
            defaults={
                "p256dh_key": data["keys"]["p256dh"],
                "auth_key": data["keys"]["auth"],
            },
        )
        stale_ids = PushSubscription.objects.filter(user=request.user).order_by("-created_at", "-id").values_list(
            "id", flat=True
        )[MAX_PUSH_SUBSCRIPTIONS_PER_USER:]
        PushSubscription.objects.filter(id__in=list(stale_ids)).delete()
        return Response(status=status.HTTP_201_CREATED)
