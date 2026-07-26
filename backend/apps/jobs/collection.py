from apps.searches.services import get_active_searches

from .models import Job
from .sources import get_job_source

REQUIRED_FIELDS = ("title", "company", "location", "description", "apply_url")

# Limite di raccolta per piano, job/notte (01-specifiche-funzionali-v4.md §4.4).
COLLECTION_LIMITS = {
    "free": 50,
    "pro": 100,
}

WINDOW_HOURS = 24


def _is_valid_offer(offer):
    return all(offer.get(field) for field in REQUIRED_FIELDS)


def collect_jobs_for_user(user):
    """Raccoglie le offerte per le ricerche attive di un utente.

    Interfaccia pubblica del modulo di raccolta: non espone alcun dettaglio
    della fonte sottostante (oggi Apify/LinkedIn — 02-specifiche-tecniche-v3.md
    §5.3). Applica, in quest'ordine: limite di piano job/notte, filtro sui
    campi obbligatori, deduplica per (user, source, external_id). Ritorna la
    lista dei `Job` effettivamente creati.
    """
    active_searches = list(get_active_searches(user))
    if not active_searches:
        return []

    limit = COLLECTION_LIMITS[user.plan]
    source = get_job_source()
    raw_offers = source.fetch(active_searches, window_hours=WINDOW_HOURS, limit=limit)

    existing_external_ids = set(
        Job.objects.filter(user=user, source=Job.Source.LINKEDIN).values_list(
            "external_id", flat=True
        )
    )

    created = []
    seen_in_this_run = set()
    for offer in raw_offers:
        if len(created) >= limit:
            break
        if not _is_valid_offer(offer):
            continue
        external_id = offer.get("external_id")
        if not external_id or external_id in existing_external_ids or external_id in seen_in_this_run:
            continue
        seen_in_this_run.add(external_id)

        job = Job.objects.create(
            user=user,
            source=Job.Source.LINKEDIN,
            external_id=external_id,
            title=offer["title"],
            company=offer["company"],
            location=offer["location"],
            description=offer["description"],
            apply_url=offer["apply_url"],
            published_at=offer.get("published_at"),
            salary=offer.get("salary", ""),
            origin=Job.Origin.COLLECTED,
        )
        created.append(job)
    return created
