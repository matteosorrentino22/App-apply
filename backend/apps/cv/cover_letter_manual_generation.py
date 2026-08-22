from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.jobs.models import DailyQuota, Job, RunLog

from .cover_letter_generation import generate_cover_letter
from .models import CoverLetterDocument

# Stessi tetti Free/Pro della generazione manuale del CV (§4.11), ma budget
# indipendente (Sprint 42): generare l'uno non consuma il massimale
# dell'altro. Oltre il massimale si prosegue a credito scalando
# PRICE_COVER_LETTER_EXTRA, se il saldo lo consente — stessa logica di
# apps.cv.manual_generation, duplicata qui perché i due contatori/prezzi
# sono ora deliberatamente indipendenti, non un dettaglio implementativo
# condivisibile senza accoppiare i due budget.
COVER_LETTER_PLAN_LIMITS = {
    "free": 1,
    "pro": 10,
}


class CoverLetterGenerationRejected(Exception):
    """Richiesta respinta senza alcun consumo di quota/credito: job già in
    generazione, oppure massimale raggiunto con saldo insufficiente."""


class CoverLetterGenerationFailed(Exception):
    """La generazione è stata avviata (quota/credito riservati) ma è
    fallita: la riserva è già stata restituita quando questa eccezione
    viene sollevata."""


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


def _reserve_quota_or_credit(user):
    quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)

    limit = COVER_LETTER_PLAN_LIMITS[user.plan]
    if quota.cover_letter_count < limit:
        quota.cover_letter_count += 1
        quota.save(update_fields=["cover_letter_count"])
        return "quota"

    locked_user = type(user).objects.select_for_update().get(pk=user.pk)
    price = settings.PRICE_COVER_LETTER_EXTRA
    if locked_user.extra_credit >= price:
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])
        return "credit"

    raise CoverLetterGenerationRejected(
        "Hai raggiunto il limite giornaliero di generazioni di cover letter e "
        "il saldo credito non è sufficiente."
    )


@transaction.atomic
def _refund(user, charge_mode):
    if charge_mode == "quota":
        quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
        quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
        quota.cover_letter_count = max(0, quota.cover_letter_count - 1)
        quota.save(update_fields=["cover_letter_count"])
    else:
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        locked_user.extra_credit += settings.PRICE_COVER_LETTER_EXTRA
        locked_user.save(update_fields=["extra_credit"])


@transaction.atomic
def _guard_and_reserve(job):
    """Guardia di concorrenza + riserva quota/credito in un'unica
    transazione, indipendente da quella del CV: il `select_for_update` sul
    Job serializza le richieste concorrenti di cover letter sullo stesso
    job, ma non blocca né è bloccato da una generazione di CV in corso."""
    locked_job = Job.objects.select_for_update().get(pk=job.pk)
    if locked_job.cover_letter_generation_in_progress:
        raise CoverLetterGenerationRejected("Generazione già in corso per questo job.")

    charge_mode = _reserve_quota_or_credit(locked_job.user)

    locked_job.cover_letter_generation_in_progress = True
    locked_job.save(update_fields=["cover_letter_generation_in_progress"])
    return charge_mode


def request_cover_letter_generation(job, instructions=""):
    """Punto d'ingresso della generazione di cover letter (Sprint 42):
    guardia di concorrenza → controllo/riserva quota o credito →
    generazione → aggiornamento del flag transitorio. A differenza del CV,
    non tocca mai `Job.status`: la cover letter è un artefatto indipendente,
    non uno dei tre stati stabili del job.

    Solleva `CoverLetterGenerationRejected` se la guardia o la quota/credito
    respingono la richiesta (nessun consumo). Solleva
    `CoverLetterGenerationFailed` se la generazione stessa fallisce (la
    riserva viene restituita prima di sollevare l'eccezione)."""
    charge_mode = _guard_and_reserve(job)

    started_at = timezone.now()
    try:
        document = generate_cover_letter(job, instructions=instructions)
    except Exception as exc:
        _refund(job.user, charge_mode)
        RunLog.objects.create(
            user=job.user,
            job=job,
            task_type=RunLog.TaskType.COVER_LETTER_GENERATION,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        Job.objects.filter(pk=job.pk).update(cover_letter_generation_in_progress=False)
        raise CoverLetterGenerationFailed(
            "Impossibile creare la cover letter per questo job."
        ) from exc

    Job.objects.filter(pk=job.pk).update(cover_letter_generation_in_progress=False)
    return document


def get_recent_instructions(user, limit=20):
    """Indicazioni testuali distinte usate nelle generazioni passate di
    cover letter dell'utente, su qualunque job, più recenti in cima (Sprint
    42) — alimenta il menu a tendina nel popup di generazione."""
    seen = set()
    recent = []
    queryset = (
        CoverLetterDocument.objects.filter(user=user)
        .exclude(instructions_used="")
        .order_by("-generated_at", "-id")
        .values_list("instructions_used", flat=True)
    )
    for text in queryset:
        if text in seen:
            continue
        seen.add(text)
        recent.append(text)
        if len(recent) >= limit:
            break
    return recent
