import logging
import zoneinfo
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import formats, timezone
from django.utils.translation import gettext as _

from apps.searches.services import get_active_searches

from .collection import collect_jobs_for_user
from .models import DailyQuota, RunLog
from .scoring import score_jobs, unscored_jobs_to_retry

User = get_user_model()
logger = logging.getLogger(__name__)

# Una raccolta al giorno per utente (Sprint 77), automatica o manuale, su
# tutti i piani e senza estensione a credito: il limite esiste apposta per
# non sprecare chiamate Apify, che poterlo superare a pagamento
# vanificherebbe. Il giorno è quello di Europe/Rome (azzeramento a
# mezzanotte, come gli altri massimali).
COLLECTION_DAILY_LIMIT = 1

# Fuso di riserva se `User.timezone` non è un nome IANA valido.
DEFAULT_TIMEZONE = "Europe/Rome"

# Oltre questa soglia, un `collection_in_progress=True` è considerato
# stantio e ignorato invece di bloccare l'utente: se un riavvio del server
# interrompe la raccolta a metà, il `finally` che rimette il flag a `False`
# non viene mai eseguito e l'account resterebbe bloccato a tempo
# indeterminato.
COLLECTION_STALE_AFTER = timedelta(hours=2)


class CollectionAlreadyInProgress(Exception):
    """Raccolta manuale respinta senza alcuna chiamata ad Apify: l'utente ha
    già una raccolta in corso (manuale o automatica)."""


class CollectionDailyLimitReached(Exception):
    """Raccolta manuale respinta senza alcuna chiamata ad Apify: la raccolta
    di oggi (`COLLECTION_DAILY_LIMIT`, automatica o manuale) è già stata
    fatta."""


class ManualCollectionFailed(Exception):
    """La raccolta manuale è stata avviata (guardia e quota rilasciate) ma è
    fallita — es. fonte Apify irraggiungibile su tutti i gruppi."""


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


def _collection_lock_is_active(locked_user):
    # `collection_started_at` assente (flag rimasto `True` da prima che il
    # campo esistesse, o qualunque stato anomalo) non permette di giudicare
    # l'età del flag: trattato come stantio, mai un blocco senza scadenza.
    return (
        locked_user.collection_in_progress
        and locked_user.collection_started_at is not None
        and timezone.now() - locked_user.collection_started_at <= COLLECTION_STALE_AFTER
    )


def _set_collection_lock(locked_user):
    locked_user.collection_in_progress = True
    locked_user.collection_started_at = timezone.now()
    locked_user.save(update_fields=["collection_in_progress", "collection_started_at"])


def _release_collection_lock(user):
    User.objects.filter(pk=user.pk).update(collection_in_progress=False, collection_started_at=None)


def _run_collection_cycle(user):
    """Raccolta → scoring dei job nuovi → nuovo tentativo sui job rimasti
    senza punteggio (Sprint 68), con un RunLog `collection` per l'utente che
    riporta scarti ed esito per gruppo. Nessuna generazione automatica di CV.
    Solleva `CollectionFailed` se tutte le chiamate di gruppo falliscono."""
    started_at = timezone.now()

    result = collect_jobs_for_user(user)
    created_ids = {job.pk for job in result.created}
    retry = list(unscored_jobs_to_retry(user).exclude(pk__in=created_ids))
    scored_ids = {job.pk for job in score_jobs(result.created + retry)}

    collected = len(result.created)
    scored = len(created_ids & scored_ids)
    retried_scored = len(scored_ids - created_ids)
    groups_failed = len(result.failed_groups)

    lines = [
        f"raccolti={collected} scorati={scored} scartati_scoring={collected - scored} "
        f"ritentati={len(retry)} ritentati_scorati={retried_scored} "
        f"scartati_campi_mancanti={result.discarded_missing} "
        f"scartati_troppo_lunghi={result.discarded_too_long} "
        f"scartati_duplicati={result.discarded_duplicate} "
        f"gruppi={len(result.groups)} gruppi_falliti={groups_failed}"
    ]
    for group in result.groups:
        outcome = f"ERRORE {group['error']}" if group["error"] else f"ok, offerte={group['offers']}"
        lines.append(f"gruppo {group['label']}: {outcome}")

    RunLog.objects.create(
        user=user,
        task_type=RunLog.TaskType.COLLECTION,
        # Un gruppo fallito rende l'esito FAILURE anche se gli altri gruppi
        # sono stati raccolti, per renderlo visibile filtrando in Admin.
        status=RunLog.Status.FAILURE if groups_failed else RunLog.Status.SUCCESS,
        message="\n".join(lines),
        started_at=started_at,
        finished_at=timezone.now(),
    )
    return {
        "collected": collected,
        "scored": scored,
        "discarded_scoring": collected - scored,
        "kept": scored,
        "retried": len(retry),
        "retried_scored": retried_scored,
        "groups_failed": groups_failed,
    }


def user_zone(user):
    try:
        return zoneinfo.ZoneInfo(user.timezone or DEFAULT_TIMEZONE)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        return zoneinfo.ZoneInfo(DEFAULT_TIMEZONE)


def collection_done_message(user, done_at):
    """"Già eseguita oggi alle HH:MM", con data e ora nel fuso dell'utente:
    la quota è sul giorno di Europe/Rome, che per chi vive in un altro fuso
    può non coincidere con il suo "oggi" (Sprint 77)."""
    if done_at is None:
        return _("La raccolta di oggi è già stata fatta. Massimo 1 al giorno.")
    local = done_at.astimezone(user_zone(user))
    time_text = formats.time_format(local, "H:i")
    if local.date() == timezone.now().astimezone(user_zone(user)).date():
        return _("Raccolta di oggi già eseguita alle %(time)s. Massimo 1 al giorno.") % {"time": time_text}
    return _("Raccolta di oggi già eseguita il %(date)s alle %(time)s. Massimo 1 al giorno.") % {
        "date": formats.date_format(local, "SHORT_DATE_FORMAT"),
        "time": time_text,
    }


def _reserve_collection_quota(user):
    """Riserva la raccolta di oggi (da chiamare dentro una transazione, con
    l'utente bloccato). Restituisce la riga di quota riservata, oppure solleva
    `CollectionDailyLimitReached` con l'ora della raccolta già fatta."""
    quota, _created = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
    if quota.collection_count >= COLLECTION_DAILY_LIMIT:
        raise CollectionDailyLimitReached(collection_done_message(user, quota.collection_done_at))
    quota.collection_count += 1
    quota.collection_done_at = timezone.now()
    quota.save(update_fields=["collection_count", "collection_done_at"])
    return quota


@transaction.atomic
def _refund_collection_quota(quota_pk):
    """Restituisce la raccolta sulla **stessa riga** riservata (Sprint 77):
    prima si restituiva sul giorno corrente, sbagliando giorno per una
    raccolta iniziata prima di mezzanotte e fallita dopo."""
    quota = DailyQuota.objects.select_for_update().filter(pk=quota_pk).first()
    if quota is None:
        return
    quota.collection_count = max(0, quota.collection_count - 1)
    if quota.collection_count == 0:
        quota.collection_done_at = None
    quota.save(update_fields=["collection_count", "collection_done_at"])


def _log(user, status, message, started_at=None):
    now = timezone.now()
    RunLog.objects.create(
        user=user,
        task_type=RunLog.TaskType.COLLECTION,
        status=status,
        message=message,
        started_at=started_at or now,
        finished_at=now,
    )


def run_manual_collection_for_user(user):
    """"Raccogli" dalla lista: raccolta → scoring per il solo utente che la
    richiede, con guardia di concorrenza (`User.collection_in_progress`,
    condivisa con la raccolta automatica, scadenza `COLLECTION_STALE_AFTER`)
    e la quota giornaliera condivisa con l'automatica
    (`DailyQuota.collection_count`). Senza ricerche attive non si chiama la
    fonte e la quota non si consuma (Sprint 77); si ritentano comunque i job
    senza punteggio. La quota è riservata prima della chiamata e restituita
    se la raccolta fallisce del tutto, stesso schema di
    `apps.cv.manual_generation`."""
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if _collection_lock_is_active(locked_user):
            raise CollectionAlreadyInProgress(_("Raccolta già in corso per questo account."))
        quota = _reserve_collection_quota(user) if get_active_searches(user).exists() else None
        _set_collection_lock(locked_user)

    started_at = timezone.now()
    try:
        summary = _run_collection_cycle(user)
    except (Exception, SystemExit) as exc:
        # SystemExit (non un Exception) è quello che gunicorn solleva nel worker
        # quando scatta `--timeout`: senza catturarlo qui la richiesta morirebbe
        # senza RunLog né refund della quota.
        if quota is not None:
            _refund_collection_quota(quota.pk)
        _log(user, RunLog.Status.FAILURE, str(exc), started_at)
        raise ManualCollectionFailed(_("Raccolta non riuscita. Riprova più tardi.")) from exc
    finally:
        _release_collection_lock(user)
    return summary


def run_automatic_collection_for_user(user):
    """Raccolta automatica di un utente Pro all'orario scelto (Sprint 77, al
    posto del ciclo notturno delle 02:00): stessa pipeline, stessa guardia e
    **stessa quota** della manuale. Saltata (RunLog SKIPPED, nessuna quota)
    se una raccolta è in corso, se non ci sono ricerche attive o se la
    raccolta di oggi è già stata fatta (per esempio a mano prima
    dell'orario). Se fallisce del tutto la quota torna sulla riga riservata;
    se fallisce dopo chiamate già pagate (alcuni gruppi riusciti) resta
    consumata. Notifica push a fine raccolta se ci sono job nuovi."""
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if _collection_lock_is_active(locked_user):
            _log(user, RunLog.Status.SKIPPED, "automatica saltata: raccolta già in corso per questo utente")
            return {"skipped": "in_progress"}
        if not get_active_searches(user).exists():
            _log(user, RunLog.Status.SKIPPED, "automatica saltata: nessuna ricerca attiva")
            return {"skipped": "no_searches"}
        try:
            quota = _reserve_collection_quota(user)
        except CollectionDailyLimitReached:
            _log(user, RunLog.Status.SKIPPED, "automatica saltata: raccolta di oggi già eseguita")
            return {"skipped": "daily_limit"}
        _set_collection_lock(locked_user)

    started_at = timezone.now()
    try:
        summary = _run_collection_cycle(user)
    except (Exception, SystemExit) as exc:
        _refund_collection_quota(quota.pk)
        _log(user, RunLog.Status.FAILURE, f"automatica: {exc}", started_at)
        return {"failed": True}
    finally:
        _release_collection_lock(user)

    if summary["collected"] > 0:
        from apps.notifications.tasks import send_new_jobs_notification

        try:
            send_new_jobs_notification(user)
        except Exception:
            logger.exception("notifica di fine raccolta non inviata per l'utente %s", user.pk)
    return summary


@shared_task
def run_automatic_collection(user_id):
    """Task del worker per un utente: ricontrolla piano e attivazione al
    momento dell'esecuzione (un Pro tornato Free nel frattempo non raccoglie)."""
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None or user.plan != User.Plan.PRO or not user.auto_collection_enabled:
        return {"skipped": "not_eligible"}
    return run_automatic_collection_for_user(user)


def automatic_collection_due(user, now=None):
    """Data locale da segnare se la raccolta automatica di `user` è dovuta
    ora, altrimenti None. Dovuta quando l'ora locale ha raggiunto l'orario
    scelto e oggi (data locale) non è ancora stata avviata. Il confronto è
    sull'ora locale "da orologio": un orario che non esiste il giorno del
    passaggio all'ora legale (es. 02:30) scatta al primo giro dopo (03:00);
    uno ripetuto al ritorno all'ora solare non riparte, perché la data
    locale è già segnata."""
    local = (now or timezone.now()).astimezone(user_zone(user))
    if user.auto_collection_last_local_date == local.date():
        return None
    if local.time() < user.auto_collection_time:
        return None
    return local.date()


@shared_task
def run_automatic_collections():
    """Ogni 15 minuti (Celery Beat, Sprint 77): avvia nel worker la raccolta
    automatica dei Pro per cui è l'ora. La data locale si segna prima di
    avviarla, così il giro successivo non la ripete mentre è in coda o in
    corso; la quota giornaliera resta comunque il limite vero."""
    users = User.objects.filter(is_active=True, plan=User.Plan.PRO, auto_collection_enabled=True)
    for user in users:
        try:
            due_date = automatic_collection_due(user)
            if due_date is None:
                continue
            User.objects.filter(pk=user.pk).update(auto_collection_last_local_date=due_date)
            run_automatic_collection.delay(user.pk)
        except Exception:
            logger.exception("raccolta automatica: errore per l'utente %s, si prosegue", user.pk)
