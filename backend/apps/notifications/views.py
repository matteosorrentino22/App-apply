from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PushSubscription
from .serializers import PushSubscriptionSerializer


class PushSubscriptionView(APIView):
    """Registra (o aggiorna) la sottoscrizione Web Push del browser
    dell'utente autenticato (Sprint 17, 02-specifiche-tecniche-v3.md §3.8)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PushSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        PushSubscription.objects.update_or_create(
            user=request.user,
            endpoint=data["endpoint"],
            defaults={
                "p256dh_key": data["keys"]["p256dh"],
                "auth_key": data["keys"]["auth"],
            },
        )
        return Response(status=status.HTTP_201_CREATED)
