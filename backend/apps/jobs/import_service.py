import re

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User

from .models import DailyQuota, Job
from .scoring import score_job
from .sources import get_job_source

# Riconosce un link di un job LinkedIn ed estrae l'ID numerico dal path
# (01-specifiche-funzionali-v4.md §4.9): usato sia per validare il link sia
# per la deduplica, senza dover interrogare la fonte offerte solo per
# verificare se un job è già stato importato/raccolto in precedenza.
LINKEDIN_JOB_URL_RE = re.compile(
    r"^https?://(www\.)?linkedin\.com/jobs/view/(?:[\w-]*-)?(?P<id>\d+)/?(?:[?#].*)?$",
    re.IGNORECASE,
)

REQUIRED_FIELDS = ("title", "company", "location", "description", "apply_url")
IMPORT_DAILY_LIMIT = 3


class ImportNotAllowed(Exception):
    """L'utente non ha i permessi per importare (piano non Pro): controllo
    di piano, precede quello di quota/credito (§4.6 tecniche)."""


class ImportRejected(Exception):
    """Richiesta respinta senza consumo di quota/credito: link non valido/
    non recuperabile, oppure massimale raggiunto con credito insufficiente."""


class ImportDuplicate(Exception):
    """Il job è già presente nella lista dell'utente: nessun duplicato
    creato, nessun consumo di quota/credito."""


def _extract_external_id(url):
    match = LINKEDIN_JOB_URL_RE.match(url or "")
    return match.group("id") if match else None


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


@transaction.atomic
def _reserve_import_quota_or_credit(user):
    """Controllo e riserva atomici del contatore giornaliero `import_count`
    (Pro: 3/giorno) o del credito extra (`PRICE_IMPORT_EXTRA`), stessa
    struttura della riserva per la generazione manuale (Sprint 12)."""
    quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)

    if quota.import_count < IMPORT_DAILY_LIMIT:
        quota.import_count += 1
        quota.save(update_fields=["import_count"])
        return "quota"

    locked_user = User.objects.select_for_update().get(pk=user.pk)
    price = settings.PRICE_IMPORT_EXTRA
    if locked_user.extra_credit >= price:
        locked_user.extra_credit -= price
        locked_user.save(update_fields=["extra_credit"])
        return "credit"

    raise ImportRejected(
        "Hai raggiunto il limite giornaliero di import e il saldo credito non è sufficiente."
    )


@transaction.atomic
def _refund_import(user, charge_mode):
    if charge_mode == "quota":
        quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
        quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
        quota.import_count = max(0, quota.import_count - 1)
        quota.save(update_fields=["import_count"])
    else:
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        locked_user.extra_credit += settings.PRICE_IMPORT_EXTRA
        locked_user.save(update_fields=["extra_credit"])


def import_job_from_url(user, url):
    """Importa un job LinkedIn da un link (01-specifiche-funzionali-v4.md
    §4.9): riservato al piano Pro; scoring applicato al termine, ma nessuna
    generazione automatica di CV anche se il punteggio risulta 4-5 (a
    differenza del ciclo notturno, Sprint 11 — l'import è sempre manuale)."""
    if user.plan != User.Plan.PRO:
        raise ImportNotAllowed("L'import manuale di job è riservato al piano Pro.")

    external_id = _extract_external_id(url)
    if external_id is None:
        raise ImportRejected("Impossibile importare quel job.")

    if Job.objects.filter(
        user=user, source=Job.Source.LINKEDIN, external_id=external_id
    ).exists():
        raise ImportDuplicate("Questo job è già nella tua lista.")

    charge_mode = _reserve_import_quota_or_credit(user)

    try:
        offer = get_job_source().fetch_by_url(url)
    except Exception:
        offer = None

    if not offer or not all(offer.get(field) for field in REQUIRED_FIELDS):
        _refund_import(user, charge_mode)
        raise ImportRejected("Impossibile importare quel job.")

    job = Job.objects.create(
        user=user,
        source=Job.Source.LINKEDIN,
        external_id=offer.get("external_id") or external_id,
        title=offer["title"],
        company=offer["company"],
        location=offer["location"],
        description=offer["description"],
        apply_url=offer["apply_url"],
        published_at=offer.get("published_at"),
        salary=offer.get("salary", ""),
        origin=Job.Origin.IMPORTED,
    )
    score_job(job)
    return job
