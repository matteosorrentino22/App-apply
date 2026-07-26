from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv.manual_generation import (
    ManualGenerationFailed,
    ManualGenerationRejected,
    request_manual_cv_generation,
)

from .models import Job


class GenerateCvView(APIView):
    """Generazione manuale di CV per un Job dell'utente autenticato — anche
    rigenerazione o "riprova" dopo un fallimento automatico (Sprint 12,
    02-specifiche-tecniche-v3.md §5.2)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        enrichment = request.data.get("enrichment", "")

        try:
            cv_document = request_manual_cv_generation(job, enrichment=enrichment)
        except ManualGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ManualGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"cv_document_id": cv_document.pk}, status=status.HTTP_201_CREATED)
