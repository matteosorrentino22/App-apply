import re

from rest_framework import serializers

from .models import Job

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
            "origin",
            "is_archived",
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
