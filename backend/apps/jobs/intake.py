import random

from .models import Job

# Cap giornaliero di intake, job/utente (01-specifiche-funzionali-v4.md §4.4).
INTAKE_CAP = 15


def apply_intake_cap(user, scored_jobs):
    """Applica il cap di intake ai Job scorati in questa esecuzione.

    Tiene i 15 a punteggio più alto. Tie-break al confine del taglio: prima
    per `published_at` più recente; se la data manca su uno o entrambi, o il
    pareggio persiste, la scelta è casuale (mescoliamo l'intero batch prima
    di ordinare per punteggio/data — l'ordinamento è stabile, quindi le righe
    che restano a pari merito mantengono l'ordine casuale pre-esistente).

    Gli eccedenti restano in DB (marcati `discarded_by_cap=True`, mai
    visibili/riproposti) anziché essere cancellati: la deduplica per
    `(user, source, external_id)` (Sprint 07) continua così a valere anche su
    di loro, evitando che la stessa offerta rientri in una raccolta futura.

    Ritorna `(kept, discarded)`.
    """
    shuffled = list(scored_jobs)
    random.shuffle(shuffled)

    def sort_key(job):
        published_ts = job.published_at.timestamp() if job.published_at else float("-inf")
        return (-job.score, -published_ts)

    ordered = sorted(shuffled, key=sort_key)
    kept = ordered[:INTAKE_CAP]
    discarded = ordered[INTAKE_CAP:]

    if discarded:
        Job.objects.filter(pk__in=[job.pk for job in discarded]).update(discarded_by_cap=True)

    return kept, discarded
