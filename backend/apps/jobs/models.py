from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Job(models.Model):
    class Source(models.TextChoices):
        LINKEDIN = "linkedin", "LinkedIn"
        MANUAL = "manual", "Manuale"

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
    # Testo libero che identifica la ricerca salvata che ha prodotto questo
    # job (dal campo `searchString` restituito da Apify per la raccolta
    # notturna; per l'import manuale non c'è una ricerca associata, resta
    # vuoto). Non un FK a SavedSearch: la ricerca può essere modificata o
    # eliminata in seguito, mentre l'attribuzione del job resta uno storico
    # immutabile di ciò che l'ha prodotto quella notte.
    matched_search = models.CharField(max_length=255, blank=True, default="")
    # Opzionale (Sprint 43): per un job inserito manualmente l'utente può non
    # avere ancora un link di candidatura (es. si candida di persona/via
    # email) — per LinkedIn/raccolta notturna resta sempre popolato.
    apply_url = models.URLField(max_length=1000, blank=True, default="")
    published_at = models.DateTimeField(null=True, blank=True)
    salary = models.CharField(max_length=255, blank=True, default="")

    # Numero di candidati riportato da LinkedIn (solo raccolta via Apify,
    # sprint corrente): quando l'annuncio è troppo recente/troppo popolare
    # per un numero esatto, LinkedIn mostra una fascia testuale ("Be among
    # the first 25 applicants" / "Over 200 applicants") invece di un intero
    # — da cui i due campi separati: `applicants_count` per il numero
    # esatto, `applicants_bucket` per l'estremo quando il numero non c'è.
    # Mai entrambi popolati insieme; entrambi vuoti se il dato manca del
    # tutto (import da link, job manuale).
    class ApplicantsBucket(models.TextChoices):
        UNDER_25 = "under_25", "Meno di 25"
        OVER_200 = "over_200", "Più di 200"

    applicants_count = models.PositiveIntegerField(null=True, blank=True)
    applicants_bucket = models.CharField(max_length=10, choices=ApplicantsBucket.choices, blank=True, default="")

    # Nome/profilo di chi ha pubblicato l'annuncio (`posterFullName`/
    # `posterProfileUrl` da Apify): LinkedIn non lo espone per tutti gli
    # annunci, resta vuoto quando assente — stessa natura di `salary`.
    recruiter_name = models.CharField(max_length=255, blank=True, default="")
    recruiter_profile_url = models.URLField(max_length=500, blank=True, default="")

    origin = models.CharField(max_length=20, choices=Origin.choices, default=Origin.COLLECTED)
    is_archived = models.BooleanField(default=False)
    # Flag organizzativo dell'utente, ortogonale a origine/archiviazione:
    # alimenta la sezione "Preferiti" (esclusi però i job già archiviati, che
    # restano visibili solo in "Archiviati" — vedi SECTION_FILTERS).
    is_favorite = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    # Stato transitorio "CV in generazione": non un valore di status, ma un flag
    # a parte che funge anche da guardia di concorrenza (§4.6, §5.2 tecniche).
    cv_generation_in_progress = models.BooleanField(default=False)
    # Stessa natura di `cv_generation_in_progress`, ma indipendente: generare
    # una cover letter non tocca lo status del job né interferisce con una
    # generazione di CV in corso sullo stesso job (Sprint 42).
    cover_letter_generation_in_progress = models.BooleanField(default=False)
    # Stessa natura delle due guardie sopra, indipendente (Sprint 50): un
    # messaggio di networking non tocca lo status del job né interferisce
    # con una generazione di CV/cover letter in corso sullo stesso job.
    referral_message_generation_in_progress = models.BooleanField(default=False)
    # Storico: cap di intake giornaliero (15 job/utente/notte), rimosso
    # nello sprint corrente — non più impostato da nessun percorso di
    # raccolta. Campo lasciato sul modello (righe passate già marcate,
    # nessuna migrazione di pulizia necessaria), ma sempre `False` per i job
    # creati da qui in avanti.
    discarded_by_cap = models.BooleanField(default=False)

    # Scala 1-10 da Sprint 46 (prima 1-5): i punteggi storici precedenti a
    # questo sprint restano nel vecchio range 1-5, mai retroattivamente
    # riscalati (nessuna migrazione dati — vedi ai_scoring.py).
    score = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(10)]
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
    # Massimale separato da `manual_cv_count` (stessi tetti Free/Pro, Sprint
    # 42): generare CV e cover letter sono due budget indipendenti, l'uno
    # non consuma l'altro.
    cover_letter_count = models.PositiveIntegerField(default=0)
    # Massimale separato da `import_count` (Sprint 43): creare un job a mano
    # e importarlo da un link LinkedIn sono due budget indipendenti, anche
    # se numericamente identici (3/giorno, stesso credito di sblocco).
    manual_job_count = models.PositiveIntegerField(default=0)
    # Massimale separato da CV/cover letter (Sprint 50): budget indipendente
    # anche per i messaggi di networking/referral.
    referral_message_count = models.PositiveIntegerField(default=0)
    # Raccolta manuale (sezione Home): massimo 1/utente/giorno, uguale per
    # tutti i piani e senza estensione a credito — il limite esiste per non
    # sprecare chiamate Apify, che pagare per superarlo vanificherebbe.
    collection_count = models.PositiveIntegerField(default=0)

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
        COVER_LETTER_GENERATION = "cover_letter_generation", "Generazione cover letter"
        REFERRAL_MESSAGE_GENERATION = "referral_message_generation", "Generazione messaggio di networking"

    class Status(models.TextChoices):
        SUCCESS = "success", "Successo"
        FAILURE = "failure", "Fallimento"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="run_logs"
    )
    job = models.ForeignKey(
        Job, on_delete=models.SET_NULL, null=True, blank=True, related_name="run_logs"
    )
    task_type = models.CharField(max_length=30, choices=TaskType.choices)
    status = models.CharField(max_length=10, choices=Status.choices)
    message = models.TextField(blank=True, default="")
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.task_type} — {self.status} ({self.started_at})"
