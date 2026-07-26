from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.cv.generation import generate_cv
from apps.cv.models import CVDocument

from .collection import collect_jobs_for_user
from .intake import apply_intake_cap
from .models import Job, RunLog
from .scoring import score_jobs

User = get_user_model()

# Soglia di punteggio per la generazione automatica del CV nel ciclo
# notturno (01-specifiche-funzionali-v4.md §4.7, 02-specifiche-tecniche-v3.md
# §5.1 punto 4): job 4-5 tenuti dal cap.
AUTO_GENERATION_SCORE_THRESHOLD = 4


def _generate_automatic_cv(job):
    """Genera automaticamente il CV per un Job 4-5 tenuto dal cap. In caso di
    successo il Job passa a `cv_generated`; in caso di fallimento resta
    `new`, senza `CVDocument` e senza bloccare la generazione degli altri Job
    del batch (§5.1 tecniche)."""
    started_at = timezone.now()
    try:
        generate_cv(job, CVDocument.GenerationType.AUTOMATIC)
    except Exception as exc:
        RunLog.objects.create(
            user=job.user,
            job=job,
            task_type=RunLog.TaskType.CV_GENERATION,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        return False

    job.status = Job.Status.CV_GENERATED
    job.date_cv_generated = timezone.now()
    job.save(update_fields=["status", "date_cv_generated"])
    return True


def run_nightly_cycle_for_user(user):
    """Raccolta → scoring → cap di intake → CV automatico (4-5) per un
    singolo utente.

    Un fallimento isolato non deve mai bloccare il ciclo per l'utente stesso
    né per gli altri: le eccezioni di scoring per singolo job sono già
    gestite in `score_job` (Sprint 08), quelle di generazione CV in
    `_generate_automatic_cv` (Sprint 11).
    """
    started_at = timezone.now()

    collected = collect_jobs_for_user(user)
    scored = score_jobs(collected)
    kept, discarded_by_cap = apply_intake_cap(user, scored)

    cv_generated = sum(
        1
        for job in kept
        if job.score >= AUTO_GENERATION_SCORE_THRESHOLD and _generate_automatic_cv(job)
    )

    RunLog.objects.create(
        user=user,
        task_type=RunLog.TaskType.COLLECTION,
        status=RunLog.Status.SUCCESS,
        message=(
            f"raccolti={len(collected)} scorati={len(scored)} "
            f"scartati_scoring={len(collected) - len(scored)} "
            f"scartati_cap={len(discarded_by_cap)} tenuti={len(kept)} "
            f"cv_generati={cv_generated}"
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
        "cv_generated": cv_generated,
    }


@shared_task
def run_nightly_cycle():
    """Task orchestratore schedulato (Celery Beat, 02:00 Europe/Rome —
    02-specifiche-tecniche-v3.md §5.1, §7): raccolta → scoring → cap di
    intake → CV automatico per ogni utente."""
    for user in User.objects.all():
        run_nightly_cycle_for_user(user)
