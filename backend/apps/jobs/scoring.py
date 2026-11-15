import concurrent.futures
import re

from django.db.models import F
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.profiles.language_options import LANGUAGE_NAME_LABELS
from apps.profiles.models import Profile

from .ai_scoring import score_job_with_claude
from .models import Job, RunLog

# Tentativi di scoring per job (Sprint 68): un job rimasto senza punteggio
# (errore Bedrock/output fuori schema, raccolta interrotta prima dello
# scoring) viene ritentato a ogni raccolta (automatica o manuale, Sprint 77) finché i fallimenti non
# arrivano a questo numero, poi resta senza punteggio (ritentabile solo a
# mano con `retry_unscored_jobs --ignore-limit`).
MAX_SCORING_FAILURES = 3

# Punteggio massimo se la lingua richiesta dall'offerta (language_check,
# ai_scoring.py) non è presente nel profilo a nessun livello: verifica
# deterministica, non lasciata al modello — osservato in produzione che il
# modello citava testualmente il requisito come gap e assegnava comunque un
# punteggio alto (Sprint 48).
LANGUAGE_MISMATCH_SCORE_CAP = 3

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


_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)


def _words(text):
    """Tokenizza in parole intere, case-insensitive. Confrontare per parola
    intera (non per sottostringa) è necessario: il codice lingua a due
    lettere di una lingua del profilo può comparire per puro caso dentro il
    nome di un'altra lingua (es. "es" — codice spagnolo — è una sottostringa
    di "tedesco"), causando un match spurio con una sottostringa naive."""
    return {w.casefold() for w in _WORD_RE.findall(text)}


def _profile_language_words(profile):
    """Parole di tutte le etichette localizzate (it/en/fr/de/es) di ogni
    lingua del profilo, per confrontare in modo tollerante con la stringa
    libera restituita dal modello in `language_check.language` (può essere
    in qualunque lingua: "German", "Tedesco", "Deutsch"). Il codice ISO a
    due lettere non è incluso: troppo corto, rischia collisioni spurie, e il
    prompt chiede comunque un nome esteso, non un codice."""
    if profile is None:
        return set()
    words = set()
    for lang in profile.languages.all():
        for label in LANGUAGE_NAME_LABELS.get(lang.language, {}).values():
            words.update(_words(label))
    return words


def _language_score_cap(result, profile):
    """None se nessun cap si applica, altrimenti il punteggio massimo
    consentito (vedi LANGUAGE_MISMATCH_SCORE_CAP)."""
    check = result.get("language_check") or {}
    if not check.get("required") or check.get("international_exception"):
        return None
    required_words = _words(check.get("language") or "")
    if not required_words:
        return None
    if required_words & _profile_language_words(profile):
        return None
    return LANGUAGE_MISMATCH_SCORE_CAP


def _apply_score_result(job, result, profile):
    score = max(1, min(10, int(result["score"])))
    reasoning = result["score_reasoning"]

    cap = _language_score_cap(result, profile)
    if cap is not None and score > cap:
        score = cap
        # Il prefisso è salvato nel DB insieme alla motivazione: lingua
        # dell'interfaccia del proprietario al momento dello scoring
        # (Sprint 71; lo scoring gira anche nella raccolta automatica, fuori da una
        # richiesta). La motivazione scritta dal modello non cambia.
        with translation.override(job.user.interface_language):
            prefix = _("Punteggio limitato a %(cap)s/10: lingua richiesta (%(language)s) assente dal profilo.") % {
                "cap": cap,
                "language": result["language_check"]["language"],
            }
        reasoning = f"{prefix} {reasoning}"

    job.score = score
    job.score_match = result["score_match"]
    job.score_gaps = result["score_gaps"]
    job.score_reasoning = reasoning
    job.date_scored = timezone.now()
    job.save(update_fields=["score", "score_match", "score_gaps", "score_reasoning", "date_scored"])


def _log_scoring_failure(job, exc, started_at):
    Job.objects.filter(pk=job.pk).update(scoring_failures=F("scoring_failures") + 1)
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
    profile = _get_profile(job.user)
    try:
        result = score_job_with_claude(job, profile)
    except Exception as exc:
        _log_scoring_failure(job, exc, started_at)
        return False

    _apply_score_result(job, result, profile)
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
        return job, profile, None, exc, started_at
    return job, profile, result, None, started_at


def score_jobs(jobs):
    """Scora un batch di Job in parallelo (pool di thread sulle sole
    chiamate Bedrock): un fallimento su un job non blocca gli altri. Il
    salvataggio su DB resta sul thread principale; `pool.map` mantiene
    l'ordine di `prepared` (non quello di completamento dei thread), ma
    l'ordine del risultato non conta per chi chiama: la lista finale in UI è
    comunque riordinata per punteggio da `list_service.list_jobs`."""
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
        for job, profile, result, exc, started_at in pool.map(_score_call, prepared):
            if exc is not None:
                _log_scoring_failure(job, exc, started_at)
                continue
            _apply_score_result(job, result, profile)
            scored.append(job)

    return scored


def unscored_jobs_to_retry(user=None, ignore_limit=False):
    """Job senza punteggio da ritentare, dal più vecchio."""
    queryset = Job.objects.filter(score__isnull=True)
    if user is not None:
        queryset = queryset.filter(user=user)
    if not ignore_limit:
        queryset = queryset.filter(scoring_failures__lt=MAX_SCORING_FAILURES)
    return queryset.select_related("user").order_by("date_collected", "pk")
