from .apify_linkedin import ApifyLinkedInSource


def get_job_source():
    """Punto unico da cui il resto dell'app ottiene la fonte offerte attiva.

    Sostituire l'implementazione qui basta a cambiare fonte senza toccare
    raccolta/scoring/CV (02-specifiche-tecniche-v3.md §5.3).
    """
    return ApifyLinkedInSource()
