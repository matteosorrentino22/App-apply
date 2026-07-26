from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Job(models.Model):
    class Source(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"

    class Origin(models.TextChoices):
        COLLECTED = "collected", "Raccolto"
        IMPORTED = "imported", "Importato"

    class Status(models.TextChoices):
        NEW = "new", "Nuovo"
        CV_GENERATED = "cv_generated", "CV generato"
        APPLICATION_DONE = "application_done", "Candidatura fatta"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="jobs")
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.LINKEDIN)
    external_id = models.CharField(max_length=255)

    title = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField()
    apply_url = models.URLField(max_length=1000)
    published_at = models.DateTimeField(null=True, blank=True)
    salary = models.CharField(max_length=255, blank=True, default="")

    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.COLLECTED)
    is_archived = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    # Stato transitorio "CV in generazione": non un valore di status, ma un flag
    # a parte che funge anche da guardia di concorrenza (§4.6, §5.2 tecniche).
    cv_generation_in_progress = models.BooleanField(default=False)
    # Scartato definitivamente dal cap di intake giornaliero (15 job/utente/
    # giorno, §4.4 funzionali): dimensione ortogonale allo status, come
    # is_archived — non è uno dei tre stati stabili, serve solo a escludere il
    # job da vista lista e generazione automatica senza cancellare la riga
    # (la riga resta per far valere la deduplica per (user, source,
    # external_id) anche sui job scartati). Introdotto in Sprint 09.
    discarded_by_cap = models.BooleanField(default=False)

    score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    score_match = models.JSONField(default=list, blank=True)
    score_gaps = models.JSONField(default=list, blank=True)
    score_reasoning = models.TextField(blank=True, default="")

    date_collected = models.DateTimeField(auto_now_add=True)
    date_scored = models.DateTimeField(null=True, blank=True)
    date_cv_generated = models.DateTimeField(null=True, blank=True)
    date_application_done = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "source", "external_id"], name="unique_job_per_user_source_external_id"
            )
        ]

    def __str__(self):
        return f"{self.title} @ {self.company} ({self.user})"


class DailyQuota(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_quotas"
    )
    date = models.DateField()
    manual_cv_count = models.PositiveIntegerField(default=0)
    import_count = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="unique_daily_quota_per_user_date")
        ]

    def __str__(self):
        return f"{self.user} — {self.date}"


class RunLog(models.Model):
    class TaskType(models.TextChoices):
        COLLECTION = "collection", "Raccolta"
        SCORING = "scoring", "Scoring"
        CV_GENERATION = "cv_generation", "Generazione CV"

    class Status(models.TextChoices):
        SUCCESS = "success", "Successo"
        FAILURE = "failure", "Fallimento"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="run_logs"
    )
    job = models.ForeignKey(
        Job, on_delete=models.SET_NULL, null=True, blank=True, related_name="run_logs"
    )
    task_type = models.CharField(max_length=20, choices=TaskType.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.task_type} — {self.status} ({self.started_at})"
