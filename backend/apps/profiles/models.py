from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    summary = models.TextField(blank=True, default="")
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    # Dati di contatto per l'intestazione del CV generato (Sprint 10): non
    # coperti dai campi esistenti di Profile/User, ma richiesti esplicitamente
    # da 02-specifiche-tecniche-v3.md §6.3 ("nome, contatti, città, link
    # LinkedIn stanno in User/Profile e vengono iniettati nell'HTML").
    phone = models.CharField(max_length=50, blank=True, default="")
    city = models.CharField(max_length=255, blank=True, default="")
    # Acronimo ISO 3166-1 alpha-2 (2 lettere, es. "IT"), derivato
    # dall'autocomplete città/paese: mostrato nell'intestazione del CV come
    # "Città, XX" — il nome completo del paese non serve altrove.
    country_code = models.CharField(max_length=2, blank=True, default="")
    linkedin_url = models.URLField(max_length=500, blank=True, default="")

    def __str__(self):
        return f"Profile({self.user})"

    @property
    def is_complete(self):
        """Un profilo è generabile solo con almeno 1 voce di istruzione
        (Docs/03 §3.2, §10.2) — le esperienze possono restare a zero (caso
        neolaureato, §3.1, §8)."""
        return self.educations.exists()


class Experience(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, default="")
    # Acronimo ISO 3166-1 alpha-2 derivato dall'autocomplete città, come
    # `Profile.country_code`: mostrato sul CV come "Città, XX" per ogni
    # esperienza (Sprint 34).
    location_country_code = models.CharField(max_length=2, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    # Nullable = esperienza in corso ("Present" sul CV): un'esperienza senza
    # data di fine è già trattata come la più recente dall'ordinamento SQL
    # (NULL prima in un ORDER BY DESC su PostgreSQL), nessuna gestione
    # speciale necessaria per le esperienze (a differenza dell'istruzione,
    # ordinata in Python — vedi selection.py).
    end_date = models.DateField(null=True, blank=True)
    bullets = models.JSONField(default=list, blank=True)
    technologies = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.role} @ {self.company}"


class Education(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="educations")
    institution = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, default="")
    location_country_code = models.CharField(max_length=2, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    # Nullable = istruzione in corso ("Present" sul CV, Sprint 34): a
    # differenza delle esperienze, il tie-break di selezione è calcolato in
    # Python (selection.py), quindi None va trattato esplicitamente come
    # "più recente di qualunque data passata" per non rompere l'ordinamento.
    end_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.title} @ {self.institution}"


class Skill(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="skills")
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Certification(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Language(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="languages")
    language = models.CharField(max_length=100)
    level = models.CharField(max_length=50, blank=True, default="")

    def __str__(self):
        return f"{self.language} ({self.level})" if self.level else self.language
