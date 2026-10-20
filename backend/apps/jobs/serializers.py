import re

from rest_framework import serializers

from .list_service import APPLICANTS_RANGES, FILTERABLE_STATUSES
from .models import Job, JobFilterPreset

# Caratteri non ammessi nei nomi file sui filesystem/browser più comuni:
# tolti dal nome suggerito per il download (Sprint 42), non dal nome reale
# su disco (che resta quello interno, `cv_documents/cv_<job>_<doc>.pdf` —
# vedi apps.cv.generation/cover_letter_generation — mai esposto lato UI).
_FILENAME_UNSAFE_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_filename_part(text):
    return _FILENAME_UNSAFE_CHARS.sub("", text).strip()


def _build_full_name_for_filename(user):
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


class ManualJobCreateSerializer(serializers.Serializer):
    """Input della creazione manuale di un job (Sprint 43): stessi campi
    obbligatori di un job raccolto/importato (titolo, azienda, località,
    descrizione, data/ora di riferimento → `published_at`), link di
    candidatura opzionale — a differenza dell'import da LinkedIn non c'è una
    fonte esterna da cui recuperarlo per forza."""

    title = serializers.CharField(max_length=255)
    company = serializers.CharField(max_length=255)
    location = serializers.CharField(max_length=255)
    description = serializers.CharField()
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
        latest = job.cv_documents.order_by("-generated_at", "-id").first()
        return latest.pdf_file.url if latest else None

    def get_cv_download_filename(self, job):
        if not job.cv_documents.exists():
            return None
        name = _build_full_name_for_filename(job.user)
        return f"{_sanitize_filename_part(f'CV {name} - {job.title}')}.pdf"

    def get_cover_letter_pdf_url(self, job):
        latest = job.cover_letter_documents.order_by("-generated_at", "-id").first()
        return latest.pdf_file.url if latest else None

    def get_cover_letter_download_filename(self, job):
        if not job.cover_letter_documents.exists():
            return None
        name = _build_full_name_for_filename(job.user)
        return f"{_sanitize_filename_part(f'Cover letter {name} - {job.title}')}.pdf"


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
            raise serializers.ValidationError("Il nome non può essere vuoto.")
        return value

    def validate_scores(self, value):
        if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
            raise serializers.ValidationError("Deve essere una lista di punteggi interi.")
        return value

    def validate_statuses(self, value):
        if not isinstance(value, list) or not set(value) <= set(FILTERABLE_STATUSES):
            raise serializers.ValidationError(f"Valori ammessi: {', '.join(FILTERABLE_STATUSES)}.")
        return value

    def validate_search_ids(self, value):
        if not isinstance(value, list) or not all(
            item == "none" or (isinstance(item, str) and item.isdigit()) for item in value
        ):
            raise serializers.ValidationError('Deve essere una lista di "none" e/o id (stringa) di ricerche salvate.')
        return value

    def validate_applicants_ranges(self, value):
        if not isinstance(value, list) or not set(value) <= set(APPLICANTS_RANGES):
            raise serializers.ValidationError(f"Valori ammessi: {', '.join(APPLICANTS_RANGES)}.")
        return value

    def validate_has_recruiter(self, value):
        if value not in ("", "yes", "no"):
            raise serializers.ValidationError('Deve essere "", "yes" o "no".')
        return value
