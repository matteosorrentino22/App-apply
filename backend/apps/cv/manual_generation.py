from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.jobs.models import DailyQuota, Job, RunLog

from .generation import generate_cv
from .models import CVDocument

# Massimale di generazioni manuali/giorno per piano (01-specifiche-funzionali
# -v4.md §4.11: Free 1, Pro 10). Oltre il massimale si prosegue a credito
# scalando PRICE_MANUAL_CV_EXTRA, se il saldo lo consente.
MANUAL_CV_PLAN_LIMITS = {
    "free": 1,
    "pro": 10,
}


class ManualGenerationRejected(Exception):
    """Richiesta respinta senza alcun consumo di quota/credito: job già in
    generazione, oppure massimale raggiunto con saldo insufficiente."""


class ManualGenerationFailed(Exception):
    """La generazione è stata avviata (quota/credito riservati) ma è fallita:
    la riserva è già stata restituita quando questa eccezione viene sollevata."""


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


def _reserve_quota_or_credit(user):
    """Controllo e riserva atomici (§5.2, §4.6 tecniche): incrementa il
    contatore giornaliero se sotto il massimale del piano, altrimenti scala
    il prezzo unitario dal saldo extra. Ritorna la modalità di addebito
    ('quota' o 'credit') usata, per poter restituire la riserva su
    fallimento. Solleva ManualGenerationRejected senza scrivere nulla se né
    il massimale né il credito coprono la richiesta."""
    quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)

    limit = MANUAL_CV_PLAN_LIMITS[user.plan]
    if quota.manual_cv_count < limit:
        quota.manual_cv_count += 1
        quota.save(update_fields=["manual_cv_count"])
        return "quota"

    locked_user = type(user).objects.select_for_update().get(pk=user.pk)
    price = settings.PRICE_MANUAL_CV_EXTRA
    if locked_user.extra_credit >= price:
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])
        return "credit"

    raise ManualGenerationRejected(
        "Hai raggiunto il limite giornaliero di generazioni manuali e il saldo "
        "credito non è sufficiente."
    )


@transaction.atomic
def _refund(user, charge_mode):
    if charge_mode == "quota":
        quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
        quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
        quota.manual_cv_count = max(0, quota.manual_cv_count - 1)
        quota.save(update_fields=["manual_cv_count"])
    else:
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        locked_user.extra_credit += settings.PRICE_MANUAL_CV_EXTRA
        locked_user.save(update_fields=["extra_credit"])


@transaction.atomic
def _guard_and_reserve(job):
    """Guardia di concorrenza + riserva quota/credito in un'unica
    transazione: il `select_for_update` sul Job serializza le richieste
    concorrenti sullo stesso job, così una seconda richiesta vede sempre
    `cv_generation_in_progress=True` già impostato dalla prima (o viene
    bloccata finché la prima non ha finito) e viene respinta prima di
    arrivare alla riserva di quota/credito (nessun doppio addebito)."""
    locked_job = Job.objects.select_for_update().get(pk=job.pk)
    if locked_job.cv_generation_in_progress:
        raise ManualGenerationRejected("Generazione già in corso per questo job.")

    charge_mode = _reserve_quota_or_credit(locked_job.user)

    locked_job.cv_generation_in_progress = True
    locked_job.save(update_fields=["cv_generation_in_progress"])
    return charge_mode


def request_manual_cv_generation(job, enrichment=""):
    """Punto d'ingresso della generazione manuale di CV (02-specifiche-
    tecniche-v3.md §5.2): guardia di concorrenza → controllo/riserva quota o
    credito → generazione → aggiornamento stato Job. Vale sia per una prima
    generazione manuale sia per una rigenerazione, sia per il "riprova" dopo
    un fallimento automatico (stesso Job tornato a `new`, stesso contatore).

    Solleva `ManualGenerationRejected` se la guardia o la quota/credito
    respingono la richiesta (nessun consumo). Solleva
    `ManualGenerationFailed` se la generazione stessa fallisce (la riserva
    viene restituita e il Job torna a `new` prima di sollevare l'eccezione).
    """
    charge_mode = _guard_and_reserve(job)

    started_at = timezone.now()
    try:
        cv_document = generate_cv(job, CVDocument.GenerationType.MANUAL, enrichment=enrichment)
    except Exception as exc:
        _refund(job.user, charge_mode)
        RunLog.objects.create(
            user=job.user,
            job=job,
            task_type=RunLog.TaskType.CV_GENERATION,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        Job.objects.filter(pk=job.pk).update(
            status=Job.Status.NEW, cv_generation_in_progress=False
        )
        raise ManualGenerationFailed("Impossibile creare il CV per questo job.") from exc

    Job.objects.filter(pk=job.pk).update(
        status=Job.Status.CV_GENERATED,
        date_cv_generated=timezone.now(),
        cv_generation_in_progress=False,
        is_archived=False,
    )
    return cv_document
