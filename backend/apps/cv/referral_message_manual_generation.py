from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.jobs.models import DailyQuota, Job, RunLog

from .models import ReferralMessageDocument
from .referral_message_generation import generate_referral_message

# Stessi tetti Free/Pro di CV/cover letter (§4.11), ma budget indipendente
# (Sprint 50): generare un messaggio di networking non consuma il
# massimale degli altri due. Oltre il massimale si prosegue a credito
# scalando PRICE_REFERRAL_MESSAGE_EXTRA, se il saldo lo consente — stessa
# logica di apps.cv.cover_letter_manual_generation, duplicata qui per lo
# stesso motivo (budget deliberatamente non condivisibile).
REFERRAL_MESSAGE_PLAN_LIMITS = {
    "free": 1,
    "pro": 10,
}


class ReferralMessageGenerationRejected(Exception):
    """Richiesta respinta senza alcun consumo di quota/credito: job già in
    generazione, oppure massimale raggiunto con saldo insufficiente."""


class ReferralMessageGenerationFailed(Exception):
    """La generazione è stata avviata (quota/credito riservati) ma è
    fallita: la riserva è già stata restituita quando questa eccezione
    viene sollevata."""


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


def _reserve_quota_or_credit(user):
    quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)

    limit = REFERRAL_MESSAGE_PLAN_LIMITS[user.plan]
    if quota.referral_message_count < limit:
        quota.referral_message_count += 1
        quota.save(update_fields=["referral_message_count"])
        return "quota"

    locked_user = type(user).objects.select_for_update().get(pk=user.pk)
    price = settings.PRICE_REFERRAL_MESSAGE_EXTRA
    if locked_user.extra_credit >= price:
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])
        return "credit"

    raise ReferralMessageGenerationRejected(
        "Hai raggiunto il limite giornaliero di messaggi di networking e "
        "il saldo credito non è sufficiente."
    )


@transaction.atomic
def _refund(user, charge_mode):
    if charge_mode == "quota":
        quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
        quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
        quota.referral_message_count = max(0, quota.referral_message_count - 1)
        quota.save(update_fields=["referral_message_count"])
    else:
        locked_user = type(user).objects.select_for_update().get(pk=user.pk)
        locked_user.extra_credit += settings.PRICE_REFERRAL_MESSAGE_EXTRA
        locked_user.save(update_fields=["extra_credit"])


@transaction.atomic
def _guard_and_reserve(job):
    """Guardia di concorrenza + riserva quota/credito in un'unica
    transazione, indipendente da quella di CV/cover letter: il
    `select_for_update` sul Job serializza le richieste concorrenti di
    messaggi sullo stesso job, ma non blocca né è bloccato da una
    generazione di CV/cover letter in corso."""
    locked_job = Job.objects.select_for_update().get(pk=job.pk)
    if locked_job.referral_message_generation_in_progress:
        raise ReferralMessageGenerationRejected("Generazione già in corso per questo job.")

    charge_mode = _reserve_quota_or_credit(locked_job.user)

    locked_job.referral_message_generation_in_progress = True
    locked_job.save(update_fields=["referral_message_generation_in_progress"])
    return charge_mode


def request_referral_message_generation(
    job, channel, recipient_name="", recipient_linkedin_url="", instructions=""
):
    """Punto d'ingresso della generazione di un messaggio di networking
    (Sprint 50): guardia di concorrenza → controllo/riserva quota o
    credito → generazione → aggiornamento del flag transitorio. Non tocca
    mai `Job.status`, stesso principio della cover letter.

    Solleva `ReferralMessageGenerationRejected` se la guardia o la
    quota/credito respingono la richiesta (nessun consumo). Solleva
    `ReferralMessageGenerationFailed` se la generazione stessa fallisce
    (la riserva viene restituita prima di sollevare l'eccezione)."""
    charge_mode = _guard_and_reserve(job)

    started_at = timezone.now()
    try:
        document = generate_referral_message(
            job,
            channel,
            recipient_name=recipient_name,
            recipient_linkedin_url=recipient_linkedin_url,
            instructions=instructions,
        )
    except Exception as exc:
        _refund(job.user, charge_mode)
        RunLog.objects.create(
            user=job.user,
            job=job,
            task_type=RunLog.TaskType.REFERRAL_MESSAGE_GENERATION,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        Job.objects.filter(pk=job.pk).update(referral_message_generation_in_progress=False)
        raise ReferralMessageGenerationFailed(
            "Impossibile creare il messaggio per questo job."
        ) from exc

    Job.objects.filter(pk=job.pk).update(referral_message_generation_in_progress=False)
    return document


def get_recent_instructions(user, limit=20):
    """Indicazioni testuali distinte usate nelle generazioni passate di
    messaggi di networking dell'utente, su qualunque job, più recenti in
    cima (Sprint 50) — alimenta il menu "indicazioni precedenti" nel popup
    di generazione, stesso principio della cover letter."""
    seen = set()
    recent = []
    queryset = (
        ReferralMessageDocument.objects.filter(user=user)
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


def get_messages_for_job(job):
    """Storico dei messaggi generati per questo job, più recenti in cima
    (Sprint 50): a differenza di CV/cover letter, più messaggi per lo
    stesso job hanno senso (destinatari diversi) — nessuno sostituisce i
    precedenti, la UI mostra l'intero storico."""
    return ReferralMessageDocument.objects.filter(job=job).order_by("-generated_at", "-id")
