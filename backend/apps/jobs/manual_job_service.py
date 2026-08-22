import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import DailyQuota, Job
from .scoring import score_job

# Stesso massimale giornaliero dell'import da LinkedIn (import_service.py),
# ma contatore separato (`manual_job_count`, non `import_count`): creare un
# job a mano e importarlo da un link sono due budget indipendenti, e — a
# differenza dell'import — disponibile su entrambi i piani (nessuna verifica
# di piano qui).
MANUAL_JOB_DAILY_LIMIT = 3


class ManualJobRejected(Exception):
    """Richiesta respinta senza consumo di quota/credito: massimale
    giornaliero raggiunto e saldo credito insufficiente."""


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


@transaction.atomic
def _reserve_quota_or_credit(user):
    quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)

    if quota.manual_job_count < MANUAL_JOB_DAILY_LIMIT:
        quota.manual_job_count += 1
        quota.save(update_fields=["manual_job_count"])
        return "quota"

    locked_user = User.objects.select_for_update().get(pk=user.pk)
    price = settings.PRICE_MANUAL_JOB_EXTRA
    if locked_user.extra_credit >= price:
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])
        return "credit"

    raise ManualJobRejected(
        "Hai raggiunto il limite giornaliero di job creati manualmente e il "
        "saldo credito non è sufficiente."
    )


def create_manual_job(user, data):
    """Crea un job inserito manualmente dall'utente, senza fonte esterna
    (Sprint 43): stesso trattamento post-creazione dell'import da LinkedIn —
    scoring applicato subito, nessuna generazione automatica di CV anche con
    punteggio alto (sempre manuale). `external_id` non ha un equivalente
    naturale (nessun link/offerta esterna da cui derivarlo): un UUID è
    sufficiente a soddisfare il vincolo di unicità per
    `(user, source, external_id)`, non serve altro."""
    _reserve_quota_or_credit(user)

    job = Job.objects.create(
        user=user,
        source=Job.Source.MANUAL,
        external_id=f"manual-{uuid.uuid4()}",
        title=data["title"],
        company=data["company"],
        location=data["location"],
        description=data["description"],
        apply_url=data.get("apply_url") or "",
        published_at=data["published_at"],
        origin=Job.Origin.IMPORTED,
    )
    score_job(job)
    return job
