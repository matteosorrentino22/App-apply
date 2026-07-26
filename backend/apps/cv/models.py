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
    enrichment_used = models.TextField(blank=True, default="")

    def __str__(self):
        return f"CV — {self.job} ({self.generated_at})"
