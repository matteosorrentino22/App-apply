from django.conf import settings
from django.db import models


class SavedSearch(models.Model):
    class SearchType(models.TextChoices):
        JOB_ROLE = "job_role", "Job role keyword"
        COMPANY = "company", "Company"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="saved_searches"
    )
    # Job role: la keyword è cercata come testo libero (campo `keyword`
    # dell'actor Apify). Company: la keyword è cercata anche via
    # `companyInclude` (risoluzione per ID azienda LinkedIn, non full-text) —
    # introdotto per correggere la scarsa selettività osservata cercando nomi
    # di azienda come testo libero (sprint-23 "Bug 2").
    search_type = models.CharField(
        max_length=20, choices=SearchType.choices, default=SearchType.JOB_ROLE
    )
    keywords = models.CharField(max_length=255)
    # Città e paese separati (invece di un unico campo "location" libero) per
    # poter usare l'autocomplete geografico in UI e costruire una stringa
    # location coerente per la fonte offerte (apps.jobs.sources.apify_linkedin).
    city = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.keywords} — {self.city}, {self.country}"
