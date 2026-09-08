import concurrent.futures

from django.utils import timezone

from apps.profiles.models import Profile

from .ai_scoring import score_job_with_claude
from .models import RunLog

# Le chiamate Bedrock di un batch sono indipendenti tra loro (nessuno stato
# condiviso oltre alla propria riga): eseguirle in parallelo accorcia di
# molto il tempo totale di una raccolta di 60-100 job (altrimenti
# sequenziale a ~7-10s/job, rischia di superare anche un timeout gunicorn
# molto alto — Sprint 45). Valore prudenziale per non saturare eventuali
# limiti di throughput di Bedrock con troppe richieste simultanee.
SCORING_CONCURRENCY = 5

# Relazioni usate da `_build_profile_summary` (ai_scoring.py): prefetchate
# una sola volta per batch così le chiamate parallele a `score_job_with_claude`
# non toccano mai l'ORM (Django non garantisce l'uso sicuro della stessa
# connessione da thread creati manualmente, e le query andrebbero comunque
# ripetute per ogni job altrimenti).
_PROFILE_PREFETCH = ("experiences", "skills", "educations", "certifications", "languages")


def _get_profile(user):
    return Profile.objects.prefetch_related(*_PROFILE_PREFETCH).filter(user=user).first()


def _apply_score_result(job, result):
    job.score = max(1, min(5, int(result["score"])))
    job.score_match = result["score_match"]
    job.score_gaps = result["score_gaps"]
    job.score_reasoning = result["score_reasoning"]
    job.date_scored = timezone.now()
    job.save(update_fields=["score", "score_match", "score_gaps", "score_reasoning", "date_scored"])


def _log_scoring_failure(job, exc, started_at):
    RunLog.objects.create(
        user=job.user,
        job=job,
        task_type=RunLog.TaskType.SCORING,
        status=RunLog.Status.FAILURE,
        message=str(exc),
        started_at=started_at,
        finished_at=timezone.now(),
    )


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
        _log_scoring_failure(job, exc, started_at)
        return False

    _apply_score_result(job, result)
    return True


def _score_call(item):
    """Solo la chiamata Bedrock (nessun accesso ORM): eseguita nel pool di
    thread da `score_jobs`. Il profilo è già stato caricato (con prefetch)
    sul thread principale prima della dispatch."""
    job, profile = item
    started_at = timezone.now()
    try:
        result = score_job_with_claude(job, profile)
    except Exception as exc:
        return job, None, exc, started_at
    return job, result, None, started_at


def score_jobs(jobs):
    """Scora un batch di Job in parallelo (pool di thread sulle sole
    chiamate Bedrock): un fallimento su un job non blocca gli altri. Il
    salvataggio su DB resta sul thread principale; `pool.map` mantiene
    l'ordine di `prepared` (non quello di completamento dei thread), ma
    l'ordine del risultato non conta per chi chiama (`apply_intake_cap`
    rimescola comunque l'intero batch prima di ordinare per punteggio)."""
    jobs = list(jobs)
    if not jobs:
        return []

    profile_cache = {}

    def profile_for(job):
        if job.user_id not in profile_cache:
            profile_cache[job.user_id] = _get_profile(job.user)
        return profile_cache[job.user_id]

    prepared = [(job, profile_for(job)) for job in jobs]

    scored = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=SCORING_CONCURRENCY) as pool:
        for job, result, exc, started_at in pool.map(_score_call, prepared):
            if exc is not None:
                _log_scoring_failure(job, exc, started_at)
                continue
            _apply_score_result(job, result)
            scored.append(job)

    return scored
