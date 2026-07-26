from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone as django_timezone


class User(AbstractUser):
    class Plan(models.TextChoices):
        FREE = "free", "Free"
        PRO = "pro", "Pro"

    class InterfaceLanguage(models.TextChoices):
        IT = "it", "Italiano"
        EN = "en", "English"

    class CvLanguageMode(models.TextChoices):
        ENGLISH = "english", "English"
        JOB_LANGUAGE = "job_language", "Lingua dell'offerta"

    # L'email è l'identificativo di accesso (§3.7, §4.1 tecniche); lo username
    # nativo resta valorizzato uguale all'email in fase di registrazione (§5 vista).
    email = models.EmailField("email address", unique=True)
    plan = models.CharField(max_length=10, choices=Plan.choices, default=Plan.FREE)
    timezone = models.CharField(max_length=50, default="Europe/Rome")
    interface_language = models.CharField(
        max_length=2, choices=InterfaceLanguage.choices, default=InterfaceLanguage.IT
    )
    cv_language_mode = models.CharField(
        max_length=20, choices=CvLanguageMode.choices, default=CvLanguageMode.JOB_LANGUAGE
    )
    cv_include_photo = models.BooleanField(default=False)
    objective_statement = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=django_timezone.now)
    # Inizializzati a created_at in save(): niente scheduler o migrazione dati
    # a parte, l'inattività/notifica partono dalla creazione dell'utente (§4.1, §4.12 funzionali).
    last_activity_reset = models.DateTimeField(null=True, blank=True)
    last_notified_at = models.DateTimeField(null=True, blank=True)
    # Guardia anti-spam per il promemoria di inattività (Sprint 17): senza
    # questo timestamp, il task (che gira ogni ~15 minuti) rinvierebbe la
    # notifica a ogni giro per tutta la durata dell'inattività, non solo una
    # volta. Si azzera implicitamente perché confrontato con
    # last_activity_reset: dopo una nuova "candidatura fatta" (che aggiorna
    # last_activity_reset), il promemoria può ripartire da capo.
    last_inactivity_notified_at = models.DateTimeField(null=True, blank=True)
    extra_credit = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and (self.last_activity_reset is None or self.last_notified_at is None):
            self.last_activity_reset = self.last_activity_reset or self.created_at
            self.last_notified_at = self.last_notified_at or self.created_at
            super().save(update_fields=["last_activity_reset", "last_notified_at"])
