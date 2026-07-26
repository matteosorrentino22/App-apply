from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv.enrichment import generate_cv_with_enrichment
from apps.cv.manual_generation import (
    ManualGenerationFailed,
    ManualGenerationRejected,
    request_manual_cv_generation,
)
from apps.cv.serializers import CvEnrichmentSerializer

from .import_service import (
    ImportDuplicate,
    ImportNotAllowed,
    ImportRejected,
    import_job_from_url,
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


class ImportJobView(APIView):
    """Import manuale di un job da link LinkedIn, riservato al piano Pro
    (Sprint 14, 01-specifiche-funzionali-v4.md §4.9)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        url = request.data.get("url", "")

        try:
            job = import_job_from_url(request.user, url)
        except ImportNotAllowed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except ImportDuplicate as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ImportRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(
            {"job_id": job.pk, "status": job.status, "score": job.score},
            status=status.HTTP_201_CREATED,
        )


class EnrichAndGenerateCvView(APIView):
    """Generazione manuale con un dettaglio di arricchimento del profilo
    applicato prima della generazione (Sprint 13, 01-specifiche-funzionali
    -v4.md §4.8)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        serializer = CvEnrichmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        detail = dict(serializer.validated_data)
        save_to_profile = detail.pop("save_to_profile")

        try:
            cv_document = generate_cv_with_enrichment(job, detail, save_to_profile=save_to_profile)
        except ManualGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ManualGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"cv_document_id": cv_document.pk}, status=status.HTTP_201_CREATED)
