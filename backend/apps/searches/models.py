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
    # Sprint 84 (SPEC-DELTA A17): un paese e da 1 a 5 città (Free 1, Pro 5),
    # in inglese come le restituisce l'autocomplete (Nominatim, en): la
    # fonte riceve "City, Country" per ogni città, con un raggio di 25 miglia.
    # Ogni città di una ricerca in uso conta come una ricerca attiva.
    cities = models.JSONField(default=list)
    country = models.CharField(max_length=255)

    # Modalità di lavoro (Sprint 84, A18, solo Pro): filtro `workType` della
    # fonte; vuoto = qualsiasi.
    class WorkMode(models.TextChoices):
        ANY = "", "Qualsiasi"
        REMOTE = "remote", "Remoto"
        HYBRID = "hybrid", "Ibrido"
        ON_SITE = "on_site", "In sede"

    work_mode = models.CharField(max_length=10, choices=WorkMode.choices, blank=True, default="")
    # Ricerca nascosta del lavoro dei desideri (Sprint 84, A19): creata dal
    # sistema dalle keyword ricavate dall'AI, mai mostrata né modificabile
    # dall'utente (esclusa dall'API delle ricerche salvate).
    is_wish = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Compatibilità (Sprint 84): `city` = la prima città, anche in scrittura
    # (`SavedSearch(city=...)` crea una ricerca con una sola città).
    @property
    def city(self):
        return self.cities[0] if self.cities else ""

    @city.setter
    def city(self, value):
        self.cities = [value] if value else []

    def __str__(self):
        return f"{self.keywords} — {', '.join(self.cities)}, {self.country}"


def max_cities_per_search(plan):
    """Città per ricerca secondo il piano (Sprint 84; dallo Sprint 86 da
    `settings.SEARCH_LIMITS`, configurabile dal `.env`)."""
    return settings.SEARCH_LIMITS[plan]["max_cities_per_search"]


MAX_WISH_DESCRIPTION_LENGTH = 1000
MAX_WISH_CHANGES_PER_DAY = 5


class JobWish(models.Model):
    """Lavoro dei desideri (Sprint 84, SPEC-DELTA A19): solo Pro, uno per
    utente. La descrizione è un dato personale (informativa 1.2, export,
    cancellazione con l'account). Le keyword ricavate dall'AI non si mostrano
    all'utente: diventano ricerche nascoste (`SavedSearch.is_wish`)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_wish")
    description = models.TextField(max_length=MAX_WISH_DESCRIPTION_LENGTH)
    country = models.CharField(max_length=255)
    cities = models.JSONField(default=list)
    is_active = models.BooleanField(default=False)
    keywords = models.JSONField(default=list, blank=True)
    # Modifiche della descrizione nel giorno di Europe/Rome (massimo 5).
    changes_date = models.DateField(null=True, blank=True)
    changes_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lavoro dei desideri ({self.user})"
