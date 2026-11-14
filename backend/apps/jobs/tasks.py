from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .collection import collect_jobs_for_user
from .models import DailyQuota, RunLog
from .scoring import score_jobs, unscored_jobs_to_retry

User = get_user_model()

# Massimo 1 raccolta manuale/utente/giorno (tutti i piani, nessuna estensione
# a credito): il limite esiste apposta per non sprecare chiamate Apify, che
# poterlo superare a pagamento vanificherebbe.
COLLECTION_DAILY_LIMIT = 1

# Oltre questa soglia, un `collection_in_progress=True` è considerato
# stantio e ignorato invece di bloccare l'utente: se un riavvio del server
# interrompe la raccolta a metà, il `finally` che rimette il flag a `False`
# non viene mai eseguito e l'account resterebbe bloccato a tempo
# indeterminato.
COLLECTION_STALE_AFTER = timedelta(hours=2)


class CollectionAlreadyInProgress(Exception):
    """Raccolta manuale respinta senza alcuna chiamata ad Apify: l'utente ha
    già una raccolta in corso (manuale o notturna)."""


class CollectionDailyLimitReached(Exception):
    """Raccolta manuale respinta senza alcuna chiamata ad Apify: massimale
    giornaliero (`COLLECTION_DAILY_LIMIT`) già raggiunto per questo utente."""


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


def run_nightly_cycle_for_user(user):
    """Ciclo notturno di un utente, con la stessa guardia della raccolta
    manuale (Sprint 68): se una raccolta manuale è in corso l'utente viene
    saltato (RunLog SKIPPED), e durante il ciclo una raccolta manuale viene
    respinta con 409."""
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if _collection_lock_is_active(locked_user):
            now = timezone.now()
            RunLog.objects.create(
                user=user,
                task_type=RunLog.TaskType.COLLECTION,
                status=RunLog.Status.SKIPPED,
                message="saltato: raccolta manuale in corso per questo utente",
                started_at=now,
                finished_at=now,
            )
            return {"skipped": True}
        _set_collection_lock(locked_user)

    try:
        return _run_collection_cycle(user)
    finally:
        _release_collection_lock(user)


@transaction.atomic
def _refund_collection_quota(user):
    quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
    quota.collection_count = max(0, quota.collection_count - 1)
    quota.save(update_fields=["collection_count"])


def run_manual_collection_for_user(user):
    """Innesco manuale della raccolta (sezione Home): stessa pipeline del
    ciclo notturno, per il solo utente che la richiede, con guardia di
    concorrenza (`User.collection_in_progress`, condivisa col ciclo notturno
    dallo Sprint 68, con timeout `COLLECTION_STALE_AFTER`) + massimale
    giornaliero (`COLLECTION_DAILY_LIMIT`, `DailyQuota.collection_count`).
    La quota è riservata prima della chiamata e restituita se questa
    fallisce, stesso schema di `apps.cv.manual_generation`."""
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if _collection_lock_is_active(locked_user):
            raise CollectionAlreadyInProgress("Raccolta già in corso per questo account.")

        quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
        quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
        if quota.collection_count >= COLLECTION_DAILY_LIMIT:
            raise CollectionDailyLimitReached(
                "Hai già usato la raccolta manuale per oggi. Massimo 1 al giorno."
            )
        quota.collection_count += 1
        quota.save(update_fields=["collection_count"])
        _set_collection_lock(locked_user)

    started_at = timezone.now()
    try:
        summary = _run_collection_cycle(user)
    except (Exception, SystemExit) as exc:
        # SystemExit (non un Exception) è quello che gunicorn solleva nel worker
        # quando scatta `--timeout`: senza catturarlo qui la richiesta morirebbe
        # senza RunLog né refund della quota.
        _refund_collection_quota(user)
        RunLog.objects.create(
            user=user,
            task_type=RunLog.TaskType.COLLECTION,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        raise ManualCollectionFailed("Raccolta non riuscita. Riprova più tardi.") from exc
    finally:
        _release_collection_lock(user)
    return summary


@shared_task
def run_nightly_cycle():
    """Task orchestratore schedulato (Celery Beat, 02:00 Europe/Rome —
    02-specifiche-tecniche §5.1): raccolta → scoring per ogni utente.

    Un fallimento per singolo utente (es. fonte Apify non raggiungibile) non
    deve impedire la raccolta per gli utenti successivi del batch: l'utente
    vede semplicemente nessun nuovo job quella notte, senza errore tecnico;
    la diagnosi resta in `RunLog`."""
    for user in User.objects.all():
        started_at = timezone.now()
        try:
            run_nightly_cycle_for_user(user)
        except Exception as exc:
            RunLog.objects.create(
                user=user,
                task_type=RunLog.TaskType.COLLECTION,
                status=RunLog.Status.FAILURE,
                message=str(exc),
                started_at=started_at,
                finished_at=timezone.now(),
            )
