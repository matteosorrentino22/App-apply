from datetime import date

from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import gettext as _
from rest_framework import status
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
    keep_cv_draft,
    load_cv_draft,
    render_draft_preview,
    seed_draft_for_job,
)
from apps.cv.draft_chat import (
    ChatMessageFailed,
    ChatMessageRejected,
    InvalidChatDecision,
    record_action_decision,
    send_chat_message,
)
from apps.cv.cover_letter_draft import (
    NoCoverLetterDocumentToEdit,
    NoCoverLetterDraftToFinalize,
    finalize_cover_letter_draft,
    keep_cover_letter_draft,
    load_cover_letter_draft,
    render_cover_letter_draft_preview,
    seed_cover_letter_draft_for_job,
)
from apps.cv.cover_letter_draft_chat import (
    ChatMessageFailed as CoverLetterChatMessageFailed,
    ChatMessageRejected as CoverLetterChatMessageRejected,
    InvalidChatDecision as CoverLetterInvalidChatDecision,
    record_action_decision as record_cover_letter_action_decision,
    send_chat_message as send_cover_letter_chat_message,
)
from apps.accounts.throttling import PostOnlyScopeMixin
from apps.cv.draft_validation import (
    InvalidDraftContent,
    clean_cover_letter_draft_content,
    clean_cv_draft_content,
)
from apps.cv.gap_filling import build_extra_instructions, resolve_selected_gaps
from apps.cv.manual_generation import (
    ManualGenerationFailed,
    ManualGenerationRejected,
    request_manual_cv_generation,
)
from apps.cv.models import CoverLetterDraft, CVDraft, ReferralMessageDocument
from apps.cv.referral_message_manual_generation import (
    ReferralMessageGenerationFailed,
    ReferralMessageGenerationRejected,
    get_messages_for_job,
    get_recent_instructions as get_recent_referral_instructions,
    request_referral_message_generation,
)

from .application import (
    ApplicationMarkRejected,
    ApplicationUndoRejected,
    mark_application_done,
    undo_application_done,
)
from .import_service import (
    ImportDuplicate,
    ImportNotAllowed,
    ImportRejected,
    import_job_from_url,
)
from .manual_job_service import ManualJobFailed, ManualJobRejected, create_manual_job
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
from .models import Job, JobFilterPreset
from .serializers import (
    ChatMessageInputSerializer,
    GenerateCvInputSerializer,
    InstructionsInputSerializer,
    JobDetailSerializer,
    JobFilterPresetSerializer,
    JobSerializer,
    ManualJobCreateSerializer,
    ReferralMessageInputSerializer,
)
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


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        params = GenerateCvInputSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        gap_lines = resolve_selected_gaps(
            job.score_gaps, params.validated_data["gap_numbers"], params.validated_data["gaps"]
        )
        extra_instructions = build_extra_instructions(
            gap_lines, params.validated_data["gap_instructions"]
        )

        try:
            cv_document = request_manual_cv_generation(job, extra_instructions=extra_instructions)
        except ManualGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ManualGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {"cv_document_id": cv_document.pk, "page_count": getattr(cv_document, "page_count", None)},
            status=status.HTTP_201_CREATED,
        )


def _wants_keep(request):
    return isinstance(request.data, dict) and request.data.get("mode") == "keep"


def _finalize_content(request, cleaner):
    """Contenuto corrente dell'editor inviato con "Genera PDF finale"
    (Sprint 69); None se il body è vuoto (si usa la bozza salvata)."""
    if isinstance(request.data, dict) and request.data.get("content"):
        return cleaner(request.data["content"])
    return None


class CvDraftView(APIView):
    """Bozza modificabile del CV in corso (Sprint 51, editor interattivo):
    GET la recupera; POST la apre o la risemina dall'ultimo CVDocument
    (contenuto e chat sovrascritti, mai duplicata), oppure con
    `{"mode": "keep"}` (Sprint 69) la conserva com'è prendendo l'ultimo CV
    come nuovo riferimento ("continua la bozza"); PATCH salva le modifiche
    (autosave lato frontend, intero `content_json` sostituito a ogni
    chiamata)."""


    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            return Response(load_cv_draft(job).content_json)
        except CVDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        if _wants_keep(request) and CVDraft.objects.filter(job=job).exists():
            return Response(keep_cv_draft(job).content_json)
        try:
            draft = seed_draft_for_job(job)
        except NoCvDocumentToEdit as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(draft.content_json, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        if not isinstance(request.data, dict):
            return Response({"detail": _("Formato non valido.")}, status=status.HTTP_400_BAD_REQUEST)
        try:
            draft = load_cv_draft(job)
        except CVDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)
        try:
            content = clean_cv_draft_content(request.data)
        except InvalidDraftContent as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        draft.content_json = content
        draft.save(update_fields=["content_json", "updated_at"])
        return Response(draft.content_json)


class CvDraftPreviewView(APIView):
    """Rendering PDF della bozza per la preview live nell'editor (Sprint
    51): accetta il contenuto corrente nel body (non necessariamente ancora
    salvato dall'autosave, cosa fondamentale per una preview che segua le
    modifiche mentre l'utente scrive) — se assente, usa l'ultimo salvato.
    Nessuna chiamata AI, solo rendering: economico, pensato per essere
    richiamato spesso (debounced) dal frontend."""

    throttle_scope = "draft_preview"

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            draft = load_cv_draft(job)
        except CVDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)

        draft_content = request.data if isinstance(request.data, dict) and request.data else draft.content_json
        try:
            draft_content = clean_cv_draft_content(draft_content)
        except InvalidDraftContent as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        pdf_bytes, page_count = render_draft_preview(request.user, request.user.profile, draft_content)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["X-Page-Count"] = str(page_count)
        return response


class FinalizeCvDraftView(APIView):
    """Genera il PDF finale dalla bozza (Sprint 51): nessun consumo di
    quota/credito, non è una nuova generazione AI. Body facoltativo
    `{"content": …}` (Sprint 69): il contenuto corrente dell'editor, validato
    e salvato nella bozza prima del rendering."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            content = _finalize_content(request, clean_cv_draft_content)
            cv_document = finalize_cv_draft(job, content=content)
        except InvalidDraftContent as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except NoDraftToFinalize as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {"cv_document_id": cv_document.pk, "page_count": cv_document.page_count},
            status=status.HTTP_201_CREATED,
        )


def _chat_pricing(request, price):
    """Prezzo del messaggio e saldo, mostrati nel pannello prima dell'invio
    (Sprint 69)."""
    return {"price": str(price), "balance": str(request.user.extra_credit)}


class CvDraftChatView(PostOnlyScopeMixin, APIView):
    """Chat di assistenza sulla bozza (Sprint 59, Fase 2): un messaggio
    dell'utente per richiesta, risposta con 0+ modifiche proposte — mai
    applicate automaticamente, vedi `apps.cv.draft_chat`. Il GET restituisce
    la cronologia già persistita (apertura/ricarica dell'editor)."""

    post_throttle_scope = "chat"

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            history = load_cv_draft(job).chat_history
        except CVDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)
        return Response({"history": history, **_chat_pricing(request, settings.PRICE_CV_DRAFT_CHAT_MESSAGE)})

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        params = ChatMessageInputSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        message = (params.validated_data["message"] or "").strip()
        if not message:
            return Response({"detail": _("Messaggio vuoto.")}, status=status.HTTP_400_BAD_REQUEST)
        raw_focus_bullets = params.validated_data["focus_bullets"]
        # Sprint 69: riferimento per `bullet_id`; `bullet_index` resta
        # accettato dalle schede aperte prima dell'aggiornamento.
        focus_bullets = [
            item
            for item in raw_focus_bullets
            if isinstance(item, dict)
            and (
                isinstance(item.get("bullet_id"), str)
                or (
                    isinstance(item.get("profile_experience_id"), int)
                    and isinstance(item.get("bullet_index"), int)
                )
            )
        ]

        try:
            reply, actions, balance = send_chat_message(job, message, focus_bullets=focus_bullets)
        except ChatMessageRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except ChatMessageFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"reply": reply, "actions": actions, "balance": str(balance)})

    def patch(self, request, pk):
        """Registra la scelta (accetta/rifiuta) di una singola azione già
        proposta (Sprint 62): senza questo la scelta viveva solo nello
        stato locale del pannello, perdendosi chiudendo/riaprendo la chat
        o ricaricando la pagina — vedi `apps.cv.draft_chat.
        record_action_decision`."""
        job = get_object_or_404(Job, pk=pk, user=request.user)
        message_index = request.data.get("message_index")
        action_index = request.data.get("action_index")
        decision = request.data.get("decision")
        if not isinstance(message_index, int) or not isinstance(action_index, int):
            return Response({"detail": _("Indici non validi.")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            record_action_decision(job, message_index, action_index, decision)
        except InvalidChatDecision as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


class GenerateCoverLetterView(APIView):
    """Generazione (o rigenerazione) manuale di una cover letter per un Job
    dell'utente autenticato (Sprint 42): sempre manuale, mai automatica,
    budget quota/credito indipendente da quello del CV."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        params = InstructionsInputSerializer(data=request.data)
        params.is_valid(raise_exception=True)

        try:
            document = request_cover_letter_generation(
                job, instructions=params.validated_data["instructions"]
            )
        except CoverLetterGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except CoverLetterGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {"cover_letter_document_id": document.pk, "page_count": getattr(document, "page_count", None)},
            status=status.HTTP_201_CREATED,
        )


class CoverLetterDraftView(APIView):
    """Mirror di CvDraftView (Sprint 63): bozza modificabile della cover
    letter in corso, stesso pattern GET/POST/PATCH."""


    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            return Response(load_cover_letter_draft(job).content_json)
        except CoverLetterDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        if _wants_keep(request) and CoverLetterDraft.objects.filter(job=job).exists():
            return Response(keep_cover_letter_draft(job).content_json)
        try:
            draft = seed_cover_letter_draft_for_job(job)
        except NoCoverLetterDocumentToEdit as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(draft.content_json, status=status.HTTP_201_CREATED)

    def patch(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        if not isinstance(request.data, dict):
            return Response({"detail": _("Formato non valido.")}, status=status.HTTP_400_BAD_REQUEST)
        try:
            draft = load_cover_letter_draft(job)
        except CoverLetterDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)
        try:
            content = clean_cover_letter_draft_content(request.data)
        except InvalidDraftContent as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        draft.content_json = content
        draft.save(update_fields=["content_json", "updated_at"])
        return Response(draft.content_json)


class CoverLetterDraftPreviewView(APIView):
    """Mirror di CvDraftPreviewView (Sprint 63): rendering PDF economico
    della bozza corrente, nessuna chiamata AI."""

    throttle_scope = "draft_preview"

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            draft = load_cover_letter_draft(job)
        except CoverLetterDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)

        draft_content = request.data if isinstance(request.data, dict) and request.data else draft.content_json
        try:
            draft_content = clean_cover_letter_draft_content(draft_content)
        except InvalidDraftContent as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        pdf_bytes, page_count = render_cover_letter_draft_preview(request.user, request.user.profile, job, draft_content)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["X-Page-Count"] = str(page_count)
        return response


class FinalizeCoverLetterDraftView(APIView):
    """Mirror di FinalizeCvDraftView (Sprint 63): nessun consumo di
    quota/credito, non è una nuova generazione AI."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            content = _finalize_content(request, clean_cover_letter_draft_content)
            document = finalize_cover_letter_draft(job, content=content)
        except InvalidDraftContent as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except NoCoverLetterDraftToFinalize as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {"cover_letter_document_id": document.pk, "page_count": document.page_count},
            status=status.HTTP_201_CREATED,
        )


class CoverLetterDraftChatView(PostOnlyScopeMixin, APIView):
    """Mirror di CvDraftChatView (Sprint 63), senza riferimento a singoli
    elementi (niente 'focus_bullets': con 3-5 paragrafi l'ambiguità è
    bassa, il solo testo libero basta — vedi apps.cv.cover_letter_draft_chat)."""

    post_throttle_scope = "chat"

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            history = load_cover_letter_draft(job).chat_history
        except CoverLetterDraft.DoesNotExist:
            return Response({"detail": _("Nessuna bozza per questo job.")}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {"history": history, **_chat_pricing(request, settings.PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE)}
        )

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        params = ChatMessageInputSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        message = (params.validated_data["message"] or "").strip()
        if not message:
            return Response({"detail": _("Messaggio vuoto.")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            reply, actions, balance = send_cover_letter_chat_message(job, message)
        except CoverLetterChatMessageRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        except CoverLetterChatMessageFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"reply": reply, "actions": actions, "balance": str(balance)})

    def patch(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        message_index = request.data.get("message_index")
        action_index = request.data.get("action_index")
        decision = request.data.get("decision")
        if not isinstance(message_index, int) or not isinstance(action_index, int):
            return Response({"detail": _("Indici non validi.")}, status=status.HTTP_400_BAD_REQUEST)

        try:
            record_cover_letter_action_decision(job, message_index, action_index, decision)
        except CoverLetterInvalidChatDecision as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(status=status.HTTP_204_NO_CONTENT)


class CoverLetterInstructionsView(APIView):
    """Indicazioni testuali distinte usate nelle generazioni passate di
    cover letter dell'utente, più recenti in cima (Sprint 42) — alimenta il
    menu a tendina nel popup di generazione, non è legato a un job
    specifico (le indicazioni sono riusabili tra job diversi)."""


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


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        channel = request.data.get("channel", "")
        if channel not in ReferralMessageDocument.Channel.values:
            return Response({"detail": _("Canale non valido.")}, status=status.HTTP_400_BAD_REQUEST)
        params = ReferralMessageInputSerializer(data=request.data)
        params.is_valid(raise_exception=True)

        try:
            document = request_referral_message_generation(
                job,
                channel,
                recipient_name=params.validated_data["recipient_name"],
                recipient_linkedin_url=params.validated_data["recipient_linkedin_url"],
                instructions=params.validated_data["instructions"],
            )
        except ReferralMessageGenerationRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ReferralMessageGenerationFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(_serialize_referral_message(document), status=status.HTTP_201_CREATED)


class ReferralMessageListView(APIView):
    """Storico dei messaggi di networking generati per un job (Sprint 50):
    a differenza di CV/cover letter, mostrati tutti, non solo l'ultimo."""


    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        documents = get_messages_for_job(job)
        return Response([_serialize_referral_message(doc) for doc in documents])


class ReferralMessageInstructionsView(APIView):
    """Indicazioni testuali distinte usate nelle generazioni passate di
    messaggi di networking dell'utente, più recenti in cima (Sprint 50) —
    non è legato a un job specifico, stesso principio delle istruzioni
    cover letter."""


    def get(self, request):
        return Response({"instructions": get_recent_referral_instructions(request.user)})


class ImportJobView(APIView):
    """Import manuale di un job da link LinkedIn, riservato al piano Pro
    (Sprint 14, 01-specifiche-funzionali-v4.md §4.9)."""


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


    def post(self, request):
        serializer = ManualJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            job = create_manual_job(request.user, serializer.validated_data)
        except ManualJobRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except ManualJobFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(
            {"job_id": job.pk, "status": job.status, "score": job.score},
            status=status.HTTP_201_CREATED,
        )


class CollectJobsView(APIView):
    """Raccolta manuale per il solo utente autenticato ("Raccogli" della
    lista): stessa pipeline raccolta→scoring della raccolta automatica dei
    Pro, con cui condivide la quota di una raccolta al giorno (Sprint 77).
    409 se è già in corso o se la raccolta di oggi è già stata fatta."""


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


    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        return Response(JobDetailSerializer(job).data)


class JobListView(APIView):
    """Lista job per sezione, con filtri su intervallo di date/score/stato/
    location e ricerca testuale confinata alla sezione (Sprint 15,
    01-specifiche-funzionali-v4.md §4.5)."""


    def get(self, request):
        section = request.query_params.get("section", "main")
        if section not in SECTION_FILTERS:
            return Response(
                {"detail": _("Sezione non valida. Valori ammessi: %(values)s.") % {"values": ", ".join(SECTION_FILTERS)}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date_from = None
        raw_date_from = request.query_params.get("date_from")
        if raw_date_from:
            try:
                date_from = date.fromisoformat(raw_date_from)
            except ValueError:
                return Response(
                    {"detail": _("Il parametro date_from deve essere una data in formato YYYY-MM-DD.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        date_to = None
        raw_date_to = request.query_params.get("date_to")
        if raw_date_to:
            try:
                date_to = date.fromisoformat(raw_date_to)
            except ValueError:
                return Response(
                    {"detail": _("Il parametro date_to deve essere una data in formato YYYY-MM-DD.")},
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
                    {"detail": _("Il filtro score deve essere una lista di interi separati da virgola.")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        statuses = None
        raw_statuses = request.query_params.get("status")
        if raw_statuses:
            statuses = [value for value in raw_statuses.split(",") if value]
            if not set(statuses) <= set(FILTERABLE_STATUSES):
                return Response(
                    {
                        "detail": _("Il filtro stato ammette solo: %(values)s.")
                        % {"values": ", ".join(FILTERABLE_STATUSES)}
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        query = request.query_params.get("q", "")

        search_ids = None
        raw_search = request.query_params.get("search")
        if raw_search:
            search_ids = [value for value in raw_search.split(",") if value]
            if not all(value == "none" or value.isdigit() for value in search_ids):
                return Response(
                    {"detail": _('Il filtro ricerca deve essere una lista di "none" e/o id di ricerche salvate separati da virgola.')},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        applicants_ranges = None
        raw_applicants = request.query_params.get("applicants")
        if raw_applicants:
            applicants_ranges = [value for value in raw_applicants.split(",") if value]
            if not set(applicants_ranges) <= set(APPLICANTS_RANGES):
                return Response(
                    {"detail": _("Il filtro candidati ammette solo: %(values)s.") % {"values": ", ".join(APPLICANTS_RANGES)}},
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
                {"detail": _('Il filtro recruiter deve essere "yes", "no" o "all".')},
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
            search_ids=search_ids,
            location=location,
            applicants_ranges=applicants_ranges,
            has_recruiter=has_recruiter,
        )
        return Response(JobSerializer(jobs, many=True).data)


# Tetto tecnico, non legato al piano (a differenza di SavedSearch): un
# preset di filtri non costa nulla da mantenere, il limite serve solo a
# evitare un accumulo indefinito per errore (sprint corrente).
MAX_JOB_FILTER_PRESETS = 50


class JobFilterPresetListCreateView(APIView):
    """Elenco e creazione dei filtri preferiti della lista job (sprint
    corrente): combinazioni di filtri salvate con un nome, per applicarle
    di nuovo rapidamente. Mai l'intervallo di date — vedi modello."""


    def get(self, request):
        presets = JobFilterPreset.objects.filter(user=request.user)
        return Response(JobFilterPresetSerializer(presets, many=True).data)

    def post(self, request):
        if JobFilterPreset.objects.filter(user=request.user).count() >= MAX_JOB_FILTER_PRESETS:
            return Response(
                {"detail": _("Hai raggiunto il numero massimo di %(max)s filtri salvati.") % {"max": MAX_JOB_FILTER_PRESETS}},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = JobFilterPresetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JobFilterPresetDeleteView(APIView):
    """Elimina un filtro preferito dell'utente autenticato (sprint
    corrente): nessun rinomina, si ricrea da capo se serve un nome diverso."""


    def delete(self, request, pk):
        preset = get_object_or_404(JobFilterPreset, pk=pk, user=request.user)
        preset.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ArchiveJobView(APIView):
    """Swipe "archivia" (Sprint 15, §4.5 funzionali)."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        archive_job(job)
        return Response(JobSerializer(job).data)


class UnarchiveJobView(APIView):
    """Swipe "rimuovi da archivio", riusato anche come undo di uno swipe
    "archivia" accidentale (Sprint 15, §4.5 funzionali): in entrambi i casi
    si tratta di riportare `is_archived` a `False`, mantenendo lo status."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        unarchive_job(job)
        return Response(JobSerializer(job).data)


class FavoriteJobView(APIView):
    """Marca un Job come preferito (Sprint 46): alimenta la sezione
    "Preferiti", indipendente da origine/stato."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        favorite_job(job)
        return Response(JobSerializer(job).data)


class UnfavoriteJobView(APIView):
    """Rimuove un Job dai preferiti (Sprint 46)."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        unfavorite_job(job)
        return Response(JobSerializer(job).data)


class MarkApplicationDoneView(APIView):
    """Marca un Job come "candidatura fatta" (Sprint 16, 01-specifiche
    -funzionali-v4.md §4.10)."""


    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)

        try:
            job = mark_application_done(job)
        except ApplicationMarkRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(JobDetailSerializer(job).data)


class UndoApplicationDoneView(APIView):
    """Annulla "candidatura fatta" (Sprint 69): vedi
    `apps.jobs.application.undo_application_done`. Permessi di default
    (nessun `permission_classes` esplicito)."""

    def post(self, request, pk):
        job = get_object_or_404(Job, pk=pk, user=request.user)
        try:
            job = undo_application_done(job)
        except ApplicationUndoRejected as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(JobDetailSerializer(job).data)


class HomeStatsView(APIView):
    """Statistiche aggregate per la Home (Sprint 44): job trovati, CV
    generati, candidature fatte, oggi/ultima settimana/totali."""


    def get(self, request):
        return Response(get_home_stats(request.user))
