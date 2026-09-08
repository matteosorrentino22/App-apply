from celery import shared_task
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .collection import collect_jobs_for_user
from .intake import apply_intake_cap
from .models import DailyQuota, RunLog
from .scoring import score_jobs

User = get_user_model()

# Massimo 1 raccolta manuale/utente/giorno (tutti i piani, nessuna estensione
# a credito): il limite esiste apposta per non sprecare chiamate Apify, che
# poterlo superare a pagamento vanificherebbe.
COLLECTION_DAILY_LIMIT = 1


class CollectionAlreadyInProgress(Exception):
    """Raccolta manuale respinta senza alcuna chiamata ad Apify: l'utente ha
    già una raccolta in corso."""


class CollectionDailyLimitReached(Exception):
    """Raccolta manuale respinta senza alcuna chiamata ad Apify: massimale
    giornaliero (`COLLECTION_DAILY_LIMIT`) già raggiunto per questo utente."""


class ManualCollectionFailed(Exception):
    """La raccolta manuale è stata avviata (guardia e quota rilasciate) ma è
    fallita — es. fonte Apify irraggiungibile."""


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


def run_nightly_cycle_for_user(user):
    """Raccolta → scoring → cap di intake per un singolo utente. Nessuna
    generazione automatica di CV (rimossa: la generazione è sempre manuale,
    §4.7/§4.11 funzionali).

    Un fallimento isolato non deve mai bloccare il ciclo per l'utente stesso
    né per gli altri: le eccezioni di scoring per singolo job sono già
    gestite in `score_job` (Sprint 08).
    """
    started_at = timezone.now()

    collected = collect_jobs_for_user(user)
    scored = score_jobs(collected)
    kept, discarded_by_cap = apply_intake_cap(user, scored)

    RunLog.objects.create(
        user=user,
        task_type=RunLog.TaskType.COLLECTION,
        status=RunLog.Status.SUCCESS,
        message=(
            f"raccolti={len(collected)} scorati={len(scored)} "
            f"scartati_scoring={len(collected) - len(scored)} "
            f"scartati_cap={len(discarded_by_cap)} tenuti={len(kept)}"
        ),
        started_at=started_at,
        finished_at=timezone.now(),
    )
    return {
        "collected": len(collected),
        "scored": len(scored),
        "discarded_scoring": len(collected) - len(scored),
        "discarded_cap": len(discarded_by_cap),
        "kept": len(kept),
    }


@transaction.atomic
def _refund_collection_quota(user):
    quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
    quota.collection_count = max(0, quota.collection_count - 1)
    quota.save(update_fields=["collection_count"])


def run_manual_collection_for_user(user):
    """Innesco manuale della raccolta (sezione Home): stessa pipeline di
    `run_nightly_cycle_for_user`, ma per il solo utente che la richiede, con
    guardia di concorrenza (`User.collection_in_progress`, stesso schema di
    `Job.cv_generation_in_progress`) + massimale giornaliero
    (`COLLECTION_DAILY_LIMIT`, `DailyQuota.collection_count`) per non
    sprecare chiamate Apify con doppi trigger o click ripetuti nello stesso
    giorno. La quota è riservata prima della chiamata e restituita se questa
    fallisce, stesso schema di `apps.cv.manual_generation`."""
    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)
        if locked_user.collection_in_progress:
            raise CollectionAlreadyInProgress("Raccolta già in corso per questo account.")

        quota, _ = DailyQuota.objects.get_or_create(user=user, date=_today_europe_rome())
        quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
        if quota.collection_count >= COLLECTION_DAILY_LIMIT:
            raise CollectionDailyLimitReached(
                "Hai già usato la raccolta manuale per oggi. Massimo 1 al giorno."
            )
        quota.collection_count += 1
        quota.save(update_fields=["collection_count"])

        locked_user.collection_in_progress = True
        locked_user.save(update_fields=["collection_in_progress"])

    started_at = timezone.now()
    try:
        summary = run_nightly_cycle_for_user(user)
    except (Exception, SystemExit) as exc:
        # SystemExit (non un Exception) è quello che gunicorn solleva nel worker
        # quando scatta `--timeout`: osservato in produzione su una raccolta di
        # ~100 job, dove lo scoring sequenziale supera il timeout mentre è
        # bloccato in attesa della risposta di Bedrock. Senza catturarlo qui,
        # la richiesta muore senza RunLog né refund della quota, e i job
        # restanti rimangono senza score senza che l'utente lo sappia.
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
        User.objects.filter(pk=user.pk).update(collection_in_progress=False)
    return summary


@shared_task
def run_nightly_cycle():
    """Task orchestratore schedulato (Celery Beat, 02:00 Europe/Rome —
    02-specifiche-tecniche-v3.md §5.1, §7): raccolta → scoring → cap di
    intake per ogni utente. Nessuna generazione automatica di CV: la
    generazione è sempre manuale (§4.7/§4.11 funzionali).

    Un fallimento per singolo utente (es. fonte Apify non raggiungibile) non
    deve impedire la raccolta per gli utenti successivi del batch: l'utente
    vede semplicemente nessun nuovo job quella notte, senza errore tecnico
    (01-specifiche-funzionali-v4.md §6); la diagnosi resta in `RunLog`."""
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
