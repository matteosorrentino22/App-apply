from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    summary = models.TextField(blank=True, default="")
    photo = models.ImageField(upload_to="profile_photos/", blank=True, null=True)
    key_achievements = models.TextField(blank=True, default="")
    # Dati di contatto per l'intestazione del CV generato (Sprint 10): non
    # coperti dai campi esistenti di Profile/User, ma richiesti esplicitamente
    # da 02-specifiche-tecniche-v3.md §6.3 ("nome, contatti, città, link
    # LinkedIn stanno in User/Profile e vengono iniettati nell'HTML").
    phone = models.CharField(max_length=50, blank=True, default="")
    city = models.CharField(max_length=255, blank=True, default="")
    linkedin_url = models.URLField(max_length=500, blank=True, default="")

    def __str__(self):
        return f"Profile({self.user})"


class Experience(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
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
    dates = models.CharField(max_length=255, blank=True, default="")
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
