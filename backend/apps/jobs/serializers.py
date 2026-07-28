from rest_framework import serializers

from .models import Job


class JobSerializer(serializers.ModelSerializer):
    # Nessun endpoint dedicato ai CVDocument nelle specifiche tecniche: il
    # link di download è più semplice da esporre qui, dato dal job stesso
    # ("l'ultimo CV generato per questo job"), piuttosto che con una risorsa
    # separata che il frontend dovrebbe interrogare a parte (§4.7 funzionali).
    cv_pdf_url = serializers.SerializerMethodField()

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
            "score",
            "score_match",
            "score_gaps",
            "score_reasoning",
            "date_collected",
            "date_scored",
            "date_cv_generated",
            "date_application_done",
            "cv_pdf_url",
        ]

    def get_cv_pdf_url(self, job):
        # Ordinato anche per id: due CVDocument dello stesso job possono
        # avere lo stesso `generated_at` (auto_now_add, risoluzione al
        # secondo), l'id come spareggio garantisce che sia sempre l'ultimo
        # generato a vincere, non uno arbitrario tra i due.
        latest = job.cv_documents.order_by("-generated_at", "-id").first()
        return latest.pdf_file.url if latest else None
