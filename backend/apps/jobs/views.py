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
from .list_service import (
    DEFAULT_PERIOD,
    FILTERABLE_STATUSES,
    PERIOD_CHOICES,
    SECTION_FILTERS,
    archive_job,
    list_jobs,
    unarchive_job,
)
from .models import Job
from .serializers import JobSerializer


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


class JobListView(APIView):
    """Lista job per sezione, con filtri temporali/score/stato e ricerca
    testuale confinata alla sezione (Sprint 15, 01-specifiche-funzionali-v4.md
    §4.5)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        section = request.query_params.get("section", "main")
        if section not in SECTION_FILTERS:
            return Response(
                {"detail": f"Sezione non valida. Valori ammessi: {', '.join(SECTION_FILTERS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period = request.query_params.get("period", DEFAULT_PERIOD)
        if period not in PERIOD_CHOICES:
            return Response(
                {"detail": f"Periodo non valido. Valori ammessi: {', '.join(PERIOD_CHOICES)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scores = None
        raw_scores = request.query_params.get("score")
        if raw_scores:
            try:
                scores = [int(value) for value in raw_scores.split(",") if value]
            except ValueError:
                return Response(
                    {"detail": "Il filtro score deve essere una lista di interi separati da virgola."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        statuses = None
        raw_statuses = request.query_params.get("status")
        if raw_statuses:
            statuses = [value for value in raw_statuses.split(",") if value]
            if not set(statuses) <= set(FILTERABLE_STATUSES):
                return Response(
                    {
                        "detail": (
                            "Il filtro stato ammette solo: "
                            f"{', '.join(FILTERABLE_STATUSES)}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        query = request.query_params.get("q", "")

        jobs = list_jobs(
            request.user, section, period=period, scores=scores, statuses=statuses, query=query
        )
        return Response(JobSerializer(jobs, many=True).data)


class ArchiveJobView(APIView):
    """Swipe "archivia" (Sprint 15, §4.5 funzionali)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        archive_job(job)
        return Response(JobSerializer(job).data)


class UnarchiveJobView(APIView):
    """Swipe "rimuovi da archivio", riusato anche come undo di uno swipe
    "archivia" accidentale (Sprint 15, §4.5 funzionali): in entrambi i casi
    si tratta di riportare `is_archived` a `False`, mantenendo lo status."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        unarchive_job(job)
        return Response(JobSerializer(job).data)
