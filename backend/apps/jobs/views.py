from datetime import date

from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv.cover_letter_manual_generation import (
    CoverLetterGenerationFailed,
    CoverLetterGenerationRejected,
    get_recent_instructions,
    request_cover_letter_generation,
)
from apps.cv.draft import (
    NoCvDocumentToEdit,
    NoDraftToFinalize,
    finalize_cv_draft,
    render_draft_preview,
    seed_draft_for_job,
)
from apps.cv.draft_chat import ChatMessageFailed, ChatMessageRejected, send_chat_message
from apps.cv.gap_filling import build_extra_instructions
from apps.cv.manual_generation import (
    ManualGenerationFailed,
    ManualGenerationRejected,
    request_manual_cv_generation,
)
from apps.cv.models import CVDraft, ReferralMessageDocument
from apps.cv.referral_message_manual_generation import (
    ReferralMessageGenerationFailed,
    ReferralMessageGenerationRejected,
    get_messages_for_job,
    get_recent_instructions as get_recent_referral_instructions,
    request_referral_message_generation,
)

from .application import ApplicationMarkRejected, mark_application_done
from .import_service import (
    ImportDuplicate,
    ImportNotAllowed,
    ImportRejected,
    import_job_from_url,
)
from .manual_job_service import ManualJobRejected, create_manual_job
from .list_service import (
    APPLICANTS_RANGES,
    FILTERABLE_STATUSES,
    SECTION_FILTERS,
    archive_job,
    favorite_job,
    list_jobs,
    unarchive_job,
    unfavorite_job,
)
from .models import Job
from .serializers import JobSerializer, ManualJobCreateSerializer
from .stats import get_home_stats
from .tasks import (
    CollectionAlreadyInProgress,
    CollectionDailyLimitReached,
    ManualCollectionFailed,
    run_manual_collection_for_user,
)


class GenerateCvView(APIView):
    """Generazione manuale di CV per un Job dell'utente autenticato — anche
    rigenerazione o "riprova" dopo un fallimento automatico (Sprint 12,
    02-specifiche-tecniche-v3.md §5.2). `gaps`/`gap_instructions` (Sprint 44,
    sostituisce l'arricchimento manuale su esperienza esistente): gap
    dell'offerta selezionati dall'utente da colmare in questa generazione,
    con istruzione opzionale su come farlo — vedi `apps.cv.gap_filling`."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        gaps = request.data.get("gaps", [])
        gap_instructions = request.data.get("gap_instructions", "")
        extra_instructions = build_extra_instructions(gaps, gap_instructions)

        try:
            cv_document = request_manual_cv_generation(job, extra_instructions=extra_instructions)
        except ManualGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ManualGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"cv_document_id": cv_document.pk}, status=status.HTTP_201_CREATED)


class CvDraftView(APIView):
    """Bozza modificabile del CV in corso (Sprint 51, editor interattivo):
    GET la recupera, POST la apre/riapre a partire dall'ultimo CVDocument
    (sovrascrivendo una bozza già in corso — mai duplicata), PATCH salva le
    modifiche (autosave lato frontend, intero `content_json` sostituito a
    ogni chiamata: più semplice di operazioni granulari, e sufficiente dato
    che il frontend tiene comunque l'intero stato in memoria)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            return Response(job.cv_draft.content_json)
        except CVDraft.DoesNotExist:
            return Response({"detail": "Nessuna bozza per questo job."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            draft = seed_draft_for_job(job)
        except NoCvDocumentToEdit as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(draft.content_json, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        if not isinstance(request.data, dict):
            return Response({"detail": "Formato non valido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            draft = job.cv_draft
        except CVDraft.DoesNotExist:
            return Response({"detail": "Nessuna bozza per questo job."}, status=status.HTTP_404_NOT_FOUND)
        draft.content_json = request.data
        draft.save(update_fields=["content_json", "updated_at"])
        return Response(draft.content_json)


class CvDraftPreviewView(APIView):
    """Rendering PDF della bozza per la preview live nell'editor (Sprint
    51): accetta il contenuto corrente nel body (non necessariamente ancora
    salvato dall'autosave, cosa fondamentale per una preview che segua le
    modifiche mentre l'utente scrive) — se assente, usa l'ultimo salvato.
    Nessuna chiamata AI, solo rendering: economico, pensato per essere
    richiamato spesso (debounced) dal frontend."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            draft = job.cv_draft
        except CVDraft.DoesNotExist:
            return Response({"detail": "Nessuna bozza per questo job."}, status=status.HTTP_404_NOT_FOUND)

        draft_content = request.data if isinstance(request.data, dict) and request.data else draft.content_json
        pdf_bytes, page_count = render_draft_preview(request.user, request.user.profile, draft_content)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["X-Page-Count"] = str(page_count)
        return response


class FinalizeCvDraftView(APIView):
    """Genera il PDF finale dalla bozza corrente (Sprint 51): nessun
    consumo di quota/credito, non è una nuova generazione AI."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            cv_document = finalize_cv_draft(job)
        except NoDraftToFinalize as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"cv_document_id": cv_document.pk}, status=status.HTTP_201_CREATED)


class CvDraftChatView(APIView):
    """Chat di assistenza sulla bozza (Sprint 59, Fase 2): un messaggio
    dell'utente per richiesta, risposta con 0+ modifiche proposte — mai
    applicate automaticamente, vedi `apps.cv.draft_chat`. Il GET restituisce
    la cronologia già persistita (apertura/ricarica dell'editor)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            return Response({"history": job.cv_draft.chat_history})
        except CVDraft.DoesNotExist:
            return Response({"detail": "Nessuna bozza per questo job."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        message = (request.data.get("message") or "").strip()
        if not message:
            return Response({"detail": "Messaggio vuoto."}, status=status.HTTP_400_BAD_REQUEST)
        raw_focus_ids = request.data.get("focus_experience_ids") or []
        focus_experience_ids = [value for value in raw_focus_ids if isinstance(value, int)]

        try:
            reply, actions = send_chat_message(job, message, focus_experience_ids=focus_experience_ids)
        except ChatMessageRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except ChatMessageFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"reply": reply, "actions": actions})


class GenerateCoverLetterView(APIView):
    """Generazione (o rigenerazione) manuale di una cover letter per un Job
    dell'utente autenticato (Sprint 42): sempre manuale, mai automatica,
    budget quota/credito indipendente da quello del CV."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        instructions = request.data.get("instructions", "")

        try:
            document = request_cover_letter_generation(job, instructions=instructions)
        except CoverLetterGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except CoverLetterGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"cover_letter_document_id": document.pk}, status=status.HTTP_201_CREATED)


class CoverLetterInstructionsView(APIView):
    """Indicazioni testuali distinte usate nelle generazioni passate di
    cover letter dell'utente, più recenti in cima (Sprint 42) — alimenta il
    menu a tendina nel popup di generazione, non è legato a un job
    specifico (le indicazioni sono riusabili tra job diversi)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"instructions": get_recent_instructions(request.user)})


def _serialize_referral_message(document):
    return {
        "id": document.pk,
        "channel": document.channel,
        "recipient_name": document.recipient_name,
        "recipient_linkedin_url": document.recipient_linkedin_url,
        "subject": document.subject,
        "content": document.content,
        "generated_at": document.generated_at,
    }


class GenerateReferralMessageView(APIView):
    """Generazione di un messaggio di networking (LinkedIn o email) per un
    Job dell'utente autenticato (Sprint 50): sempre manuale, budget
    quota/credito indipendente da CV e cover letter. A differenza di questi
    ultimi, più messaggi hanno senso sullo stesso job (destinatari
    diversi): ogni generazione crea una nuova riga, nessuna sostituisce le
    precedenti — la risposta porta già il testo generato, non solo un id,
    perché qui non c'è un PDF da scaricare in un secondo giro."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        channel = request.data.get("channel", "")
        if channel not in ReferralMessageDocument.Channel.values:
            return Response({"detail": "Canale non valido."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            document = request_referral_message_generation(
                job,
                channel,
                recipient_name=request.data.get("recipient_name", ""),
                recipient_linkedin_url=request.data.get("recipient_linkedin_url", ""),
                instructions=request.data.get("instructions", ""),
            )
        except ReferralMessageGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ReferralMessageGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(_serialize_referral_message(document), status=status.HTTP_201_CREATED)


class ReferralMessageListView(APIView):
    """Storico dei messaggi di networking generati per un job (Sprint 50):
    a differenza di CV/cover letter, mostrati tutti, non solo l'ultimo."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        documents = get_messages_for_job(job)
        return Response([_serialize_referral_message(doc) for doc in documents])


class ReferralMessageInstructionsView(APIView):
    """Indicazioni testuali distinte usate nelle generazioni passate di
    messaggi di networking dell'utente, più recenti in cima (Sprint 50) —
    non è legato a un job specifico, stesso principio delle istruzioni
    cover letter."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"instructions": get_recent_referral_instructions(request.user)})


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


class CreateManualJobView(APIView):
    """Creazione manuale di un job senza fonte esterna (Sprint 43,
    sezione "Importati"): disponibile su entrambi i piani, budget
    giornaliero separato da quello dell'import da LinkedIn."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ManualJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            job = create_manual_job(request.user, serializer.validated_data)
        except ManualJobRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(
            {"job_id": job.pk, "status": job.status, "score": job.score},
            status=status.HTTP_201_CREATED,
        )


class CollectJobsView(APIView):
    """Raccolta manuale per il solo utente autenticato (sezione Home): stessa
    pipeline raccolta→scoring→cap del ciclo notturno, innescata a richiesta
    per non sprecare chiamate Apify nei giorni in cui i risultati non
    verrebbero comunque controllati."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            summary = run_manual_collection_for_user(request.user)
        except (CollectionAlreadyInProgress, CollectionDailyLimitReached) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ManualCollectionFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(summary, status=status.HTTP_200_OK)


class JobDetailView(APIView):
    """Dettaglio di un singolo Job dell'utente autenticato — serve alla UI
    (Sprint 19) per una vista di dettaglio deep-linkabile/sopravvivente al
    refresh, senza dover tenere lo stato solo lato client dalla lista."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        return Response(JobSerializer(job).data)


class JobListView(APIView):
    """Lista job per sezione, con filtri su intervallo di date/score/stato/
    location e ricerca testuale confinata alla sezione (Sprint 15,
    01-specifiche-funzionali-v4.md §4.5)."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        section = request.query_params.get("section", "main")
        if section not in SECTION_FILTERS:
            return Response(
                {"detail": f"Sezione non valida. Valori ammessi: {', '.join(SECTION_FILTERS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date_from = None
        raw_date_from = request.query_params.get("date_from")
        if raw_date_from:
            try:
                date_from = date.fromisoformat(raw_date_from)
            except ValueError:
                return Response(
                    {"detail": "Il parametro date_from deve essere una data in formato YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        date_to = None
        raw_date_to = request.query_params.get("date_to")
        if raw_date_to:
            try:
                date_to = date.fromisoformat(raw_date_to)
            except ValueError:
                return Response(
                    {"detail": "Il parametro date_to deve essere una data in formato YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        location = request.query_params.get("location", "")

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

        search_id = request.query_params.get("search")
        if search_id and search_id not in ("all", "none") and not search_id.isdigit():
            return Response(
                {"detail": 'Il filtro ricerca deve essere "all", "none" o l\'id di una ricerca salvata.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        applicants_ranges = None
        raw_applicants = request.query_params.get("applicants")
        if raw_applicants:
            applicants_ranges = [value for value in raw_applicants.split(",") if value]
            if not set(applicants_ranges) <= set(APPLICANTS_RANGES):
                return Response(
                    {"detail": f"Il filtro candidati ammette solo: {', '.join(APPLICANTS_RANGES)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        has_recruiter = None
        raw_recruiter = request.query_params.get("recruiter")
        if raw_recruiter == "yes":
            has_recruiter = True
        elif raw_recruiter == "no":
            has_recruiter = False
        elif raw_recruiter and raw_recruiter != "all":
            return Response(
                {"detail": 'Il filtro recruiter deve essere "yes", "no" o "all".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        jobs = list_jobs(
            request.user,
            section,
            date_from=date_from,
            date_to=date_to,
            scores=scores,
            statuses=statuses,
            query=query,
            search_id=search_id,
            location=location,
            applicants_ranges=applicants_ranges,
            has_recruiter=has_recruiter,
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


class FavoriteJobView(APIView):
    """Marca un Job come preferito (Sprint 46): alimenta la sezione
    "Preferiti", indipendente da origine/stato."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        favorite_job(job)
        return Response(JobSerializer(job).data)


class UnfavoriteJobView(APIView):
    """Rimuove un Job dai preferiti (Sprint 46)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        unfavorite_job(job)
        return Response(JobSerializer(job).data)


class MarkApplicationDoneView(APIView):
    """Marca un Job come "candidatura fatta" (Sprint 16, 01-specifiche
    -funzionali-v4.md §4.10)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)

        try:
            job = mark_application_done(job)
        except ApplicationMarkRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(JobSerializer(job).data)


class HomeStatsView(APIView):
    """Statistiche aggregate per la Home (Sprint 44): job trovati, CV
    generati, candidature fatte, oggi/ultima settimana/totali."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(get_home_stats(request.user))
