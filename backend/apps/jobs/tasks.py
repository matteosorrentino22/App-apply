from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from .collection import collect_jobs_for_user
from .intake import apply_intake_cap
from .models import RunLog
from .scoring import score_jobs

User = get_user_model()


def run_nightly_cycle_for_user(user):
    """Raccolta → scoring → cap di intake per un singolo utente.

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


@shared_task
def run_nightly_cycle():
    """Task orchestratore schedulato (Celery Beat, 02:00 Europe/Rome —
    02-specifiche-tecniche-v3.md §5.1, §7): raccolta → scoring → cap di
    intake per ogni utente."""
    for user in User.objects.all():
        run_nightly_cycle_for_user(user)
