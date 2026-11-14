import re

from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.common.files import signed_document_url
from apps.cv.cover_letter_draft import is_cover_letter_draft_outdated
from apps.cv.draft import is_cv_draft_outdated

from .list_service import APPLICANTS_RANGES, FILTERABLE_STATUSES
from .models import Job, JobFilterPreset

# Caratteri non ammessi nei nomi file sui filesystem/browser più comuni:
# tolti dal nome suggerito per il download (Sprint 42), non dal nome reale
# su disco (casuale, `cv_documents/<uuid>.pdf` — vedi apps.common.files —
# mai esposto lato UI).
_FILENAME_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_filename_part(text):
    return _FILENAME_UNSAFE_CHARS.sub("", text).strip()


def _build_full_name_for_filename(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


def cv_download_filename(job):
    name = _build_full_name_for_filename(job.user)
    return f"{_sanitize_filename_part(f'CV {name} - {job.title}')}.pdf"


def cover_letter_download_filename(job):
    name = _build_full_name_for_filename(job.user)
    return f"{_sanitize_filename_part(f'Cover letter {name} - {job.title}')}.pdf"


# Limiti dei testi liberi che finiscono nei prompt AI o nei PDF (Sprint 66):
# senza, un singolo messaggio da qualche MB costerebbe centinaia di migliaia
# di token. Valori ampi rispetto all'uso reale.
MAX_DESCRIPTION_LENGTH = 20_000
MAX_INSTRUCTIONS_LENGTH = 2_000
MAX_CHAT_MESSAGE_LENGTH = 2_000
MAX_GAPS = 30
MAX_GAP_LENGTH = 500


class GenerateCvInputSerializer(serializers.Serializer):
    # Sprint 69: numeri 1-based dei gap nell'elenco completo `score_gaps`
    # (stessa numerazione del pannello). `gaps` (testi) resta accettato per
    # le schede aperte prima dell'aggiornamento.
    gap_numbers = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=1_000),
        max_length=MAX_GAPS,
        required=False,
        default=list,
    )
    gaps = serializers.ListField(
        child=serializers.CharField(max_length=MAX_GAP_LENGTH, allow_blank=True),
        max_length=MAX_GAPS,
        required=False,
        default=list,
    )
    gap_instructions = serializers.CharField(
        max_length=MAX_INSTRUCTIONS_LENGTH, required=False, allow_blank=True, default=""
    )


class InstructionsInputSerializer(serializers.Serializer):
    instructions = serializers.CharField(
        max_length=MAX_INSTRUCTIONS_LENGTH, required=False, allow_blank=True, default=""
    )


class ReferralMessageInputSerializer(InstructionsInputSerializer):
    recipient_name = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    # CharField e non URLField: oggi il frontend accetta anche link senza
    # schema ("linkedin.com/in/..."), il campo non è mai usato come link nei PDF.
    recipient_linkedin_url = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


class ChatMessageInputSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=MAX_CHAT_MESSAGE_LENGTH, required=False, allow_blank=True, allow_null=True, default=""
    )
    focus_bullets = serializers.ListField(
        child=serializers.DictField(), max_length=50, required=False, default=list
    )


class ManualJobCreateSerializer(serializers.Serializer):
    """Input della creazione manuale di un job (Sprint 43): stessi campi
    obbligatori di un job raccolto/importato (titolo, azienda, località,
    descrizione, data/ora di riferimento → `published_at`), link di
    candidatura opzionale — a differenza dell'import da LinkedIn non c'è una
    fonte esterna da cui recuperarlo per forza."""

    title = serializers.CharField(max_length=255)
    company = serializers.CharField(max_length=255)
    location = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=MAX_DESCRIPTION_LENGTH)
    published_at = serializers.DateTimeField()
    apply_url = serializers.URLField(max_length=1000, required=False, allow_blank=True, default="")


class JobSerializer(serializers.ModelSerializer):
    # Nessun endpoint dedicato ai CVDocument nelle specifiche tecniche: il
    # link di download è più semplice da esporre qui, dato dal job stesso
    # ("l'ultimo CV generato per questo job"), piuttosto che con una risorsa
    # separata che il frontend dovrebbe interrogare a parte (§4.7 funzionali).
    cv_pdf_url = serializers.SerializerMethodField()
    cv_download_filename = serializers.SerializerMethodField()
    # Stesso principio del CV, per la cover letter (Sprint 42): artefatto
    # indipendente, mai generato automaticamente, sempre legato al job.
    cover_letter_pdf_url = serializers.SerializerMethodField()
    cover_letter_download_filename = serializers.SerializerMethodField()
    # Sprint 69: un flag acceso da oltre GENERATION_STALE_AFTER (processo
    # morto a metà generazione) non viene più mostrato come "in corso".
    cv_generation_in_progress = serializers.BooleanField(source="cv_generation_active", read_only=True)
    cover_letter_generation_in_progress = serializers.BooleanField(
        source="cover_letter_generation_active", read_only=True
    )
    referral_message_generation_in_progress = serializers.BooleanField(
        source="referral_message_generation_active", read_only=True
    )

    class Meta:
        model = Job
        fields = [
            "id",
            "title",
            "company",
            "location",
            "description",
            "apply_url",
            "published_at",
            "salary",
            "matched_search",
            "applicants_count",
            "applicants_bucket",
            "recruiter_name",
            "recruiter_profile_url",
            "origin",
            "is_archived",
            "is_favorite",
            "status",
            "cv_generation_in_progress",
            "cover_letter_generation_in_progress",
            "referral_message_generation_in_progress",
            "score",
            "score_match",
            "score_gaps",
            "score_reasoning",
            "date_collected",
            "date_scored",
            "date_cv_generated",
            "date_application_done",
            "cv_pdf_url",
            "cv_download_filename",
            "cover_letter_pdf_url",
            "cover_letter_download_filename",
        ]

    def get_cv_pdf_url(self, job):
        # Ordinato anche per id: due CVDocument dello stesso job possono
        # avere lo stesso `generated_at` (auto_now_add, risoluzione al
        # secondo), l'id come spareggio garantisce che sia sempre l'ultimo
        # generato a vincere, non uno arbitrario tra i due.
        # URL firmato valido un'ora (apps.common.files), mai il path media.
        latest = job.cv_documents.order_by("-generated_at", "-id").first()
        return signed_document_url("cv", latest) if latest else None

    def get_cv_download_filename(self, job):
        return cv_download_filename(job) if job.cv_documents.exists() else None

    def get_cover_letter_pdf_url(self, job):
        latest = job.cover_letter_documents.order_by("-generated_at", "-id").first()
        return signed_document_url("cover-letter", latest) if latest else None

    def get_cover_letter_download_filename(self, job):
        return cover_letter_download_filename(job) if job.cover_letter_documents.exists() else None


class JobDetailSerializer(JobSerializer):
    """Dettaglio del job (Sprint 69): in più rispetto alla lista, lo stato
    dei documenti per il dettaglio e gli editor — pagine dell'ultimo PDF
    (avviso oltre 1 pagina), se l'ultimo documento è riapribile
    nell'editor (`content_json` non vuoto: no per i CV pre-Sprint 51 e le
    cover letter pre-Sprint 63) e se la bozza è superata da un documento
    più recente. Non nella lista per non aggiungere query per ogni job."""

    cv_page_count = serializers.SerializerMethodField()
    cv_editable = serializers.SerializerMethodField()
    cv_draft_outdated = serializers.SerializerMethodField()
    cover_letter_page_count = serializers.SerializerMethodField()
    cover_letter_editable = serializers.SerializerMethodField()
    cover_letter_draft_outdated = serializers.SerializerMethodField()

    class Meta(JobSerializer.Meta):
        fields = JobSerializer.Meta.fields + [
            "cv_page_count",
            "cv_editable",
            "cv_draft_outdated",
            "cover_letter_page_count",
            "cover_letter_editable",
            "cover_letter_draft_outdated",
        ]

    def _latest(self, job, kind):
        cache = self.context.setdefault("_latest_documents", {})
        key = (job.pk, kind)
        if key not in cache:
            related = job.cv_documents if kind == "cv" else job.cover_letter_documents
            cache[key] = related.order_by("-generated_at", "-id").first()
        return cache[key]

    def get_cv_page_count(self, job):
        latest = self._latest(job, "cv")
        return latest.page_count if latest else None

    def get_cv_editable(self, job):
        latest = self._latest(job, "cv")
        return bool(latest and latest.content_json)

    def get_cv_draft_outdated(self, job):
        latest = self._latest(job, "cv")
        return is_cv_draft_outdated(job, latest) if latest else False

    def get_cover_letter_page_count(self, job):
        latest = self._latest(job, "cover_letter")
        return latest.page_count if latest else None

    def get_cover_letter_editable(self, job):
        latest = self._latest(job, "cover_letter")
        return bool(latest and latest.content_json)

    def get_cover_letter_draft_outdated(self, job):
        latest = self._latest(job, "cover_letter")
        return is_cover_letter_draft_outdated(job, latest) if latest else False


class JobFilterPresetSerializer(serializers.ModelSerializer):
    """Combinazione di filtri lista job salvata con un nome (sprint
    corrente). Niente campo per l'intervallo di date: non viene mai salvato
    (si inserisce sempre al momento dell'applicazione del preset)."""

    class Meta:
        model = JobFilterPreset
        fields = [
            "id",
            "name",
            "scores",
            "statuses",
            "search_ids",
            "location",
            "applicants_ranges",
            "has_recruiter",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("Il nome non può essere vuoto."))
        return value

    def validate_scores(self, value):
        if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
            raise serializers.ValidationError(_("Deve essere una lista di punteggi interi."))
        return value

    def validate_statuses(self, value):
        if not isinstance(value, list) or not set(value) <= set(FILTERABLE_STATUSES):
            raise serializers.ValidationError(_("Valori ammessi: %(values)s.") % {"values": ", ".join(FILTERABLE_STATUSES)})
        return value

    def validate_search_ids(self, value):
        if not isinstance(value, list) or not all(
            item == "none" or (isinstance(item, str) and item.isdigit()) for item in value
        ):
            raise serializers.ValidationError(_('Deve essere una lista di "none" e/o id (stringa) di ricerche salvate.'))
        return value

    def validate_applicants_ranges(self, value):
        if not isinstance(value, list) or not set(value) <= set(APPLICANTS_RANGES):
            raise serializers.ValidationError(_("Valori ammessi: %(values)s.") % {"values": ", ".join(APPLICANTS_RANGES)})
        return value

    def validate_has_recruiter(self, value):
        if value not in ("", "yes", "no"):
            raise serializers.ValidationError(_('Deve essere "", "yes" o "no".'))
        return value
