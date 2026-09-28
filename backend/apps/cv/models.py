from django.conf import settings
from django.db import models

from apps.jobs.models import Job


class CVDocument(models.Model):
    class GenerationType(models.TextChoices):
        AUTOMATIC = "automatic", "Automatica"
        MANUAL = "manual", "Manuale"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="cv_documents")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cv_documents"
    )
    html_source = models.TextField()
    pdf_file = models.FileField(upload_to="cv_documents/")
    generated_at = models.DateTimeField(auto_now_add=True)
    generation_type = models.CharField(max_length=10, choices=GenerationType.choices)
    # Testo "gap da colmare + istruzioni" usato per questa generazione
    # (Sprint 44, apps.cv.gap_filling) — prima era il testo dell'arricchimento
    # manuale su un'esperienza scelta dall'utente, funzione ora rimossa.
    extra_instructions_used = models.TextField(blank=True, default="")
    # Riferimento interno di provenienza per ogni Area of Expertise prodotta
    # (Docs/03 §5.3, §13): mai mostrato all'utente, serve solo alla diagnosi
    # in fase di tuning del prompt (verificare che le aree siano riconducibili
    # a contenuto reale del profilo). Dato di servizio, non una nuova tabella.
    areas_of_expertise_grounding = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"CV — {self.job} ({self.generated_at})"


class CoverLetterDocument(models.Model):
    """Mirror di CVDocument (Sprint 42): artefatto indipendente, mai generato
    automaticamente, sempre su richiesta esplicita dell'utente per un job."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="cover_letter_documents")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cover_letter_documents"
    )
    html_source = models.TextField()
    pdf_file = models.FileField(upload_to="cover_letter_documents/")
    generated_at = models.DateTimeField(auto_now_add=True)
    # Testo libero fornito dall'utente in questa generazione (indicazioni di
    # tono/enfasi e/o dettagli reali non ancora nel profilo, sotto la sua
    # responsabilità di veridicità — stesso principio dell'arricchimento
    # CV): alimenta anche il menu "indicazioni precedenti" nel popup di
    # generazione, tra tutti i job dell'utente.
    instructions_used = models.TextField(blank=True, default="")

    def __str__(self):
        return f"Cover letter — {self.job} ({self.generated_at})"
