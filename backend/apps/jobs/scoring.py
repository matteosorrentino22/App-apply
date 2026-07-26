from django.utils import timezone

from apps.profiles.models import Profile

from .ai_scoring import score_job_with_claude
from .models import RunLog


def _get_profile(user):
    try:
        return user.profile
    except Profile.DoesNotExist:
        return None


def score_job(job):
    """Assegna punteggio/motivazione a un Job chiamando Claude.

    Ritorna True se lo scoring è riuscito. In caso di fallimento, il Job
    resta privo di score (scartato per quella notte) e l'evento è tracciato
    in RunLog (01-specifiche-funzionali-v4.md §4.4).
    """
    started_at = timezone.now()
    try:
        result = score_job_with_claude(job, _get_profile(job.user))
    except Exception as exc:
        RunLog.objects.create(
            user=job.user,
            job=job,
            task_type=RunLog.TaskType.SCORING,
            status=RunLog.Status.FAILURE,
            message=str(exc),
            started_at=started_at,
            finished_at=timezone.now(),
        )
        return False

    job.score = max(1, min(5, int(result["score"])))
    job.score_match = result["score_match"]
    job.score_gaps = result["score_gaps"]
    job.score_reasoning = result["score_reasoning"]
    job.date_scored = timezone.now()
    job.save(update_fields=["score", "score_match", "score_gaps", "score_reasoning", "date_scored"])
    return True


def score_jobs(jobs):
    """Scora un batch di Job; un fallimento su un job non blocca gli altri."""
    return [job for job in jobs if score_job(job)]
