from apps.searches.services import get_active_searches

from .models import Job
from .sources import get_job_source

REQUIRED_FIELDS = ("title", "company", "location", "description", "apply_url")

WINDOW_HOURS = 24


def _is_valid_offer(offer):
    return all(offer.get(field) for field in REQUIRED_FIELDS)


def collect_jobs_for_user(user):
    """Raccoglie le offerte per le ricerche attive di un utente.

    Interfaccia pubblica del modulo di raccolta: non espone alcun dettaglio
    della fonte sottostante (oggi Apify/LinkedIn — 02-specifiche-tecniche-v3.md
    §5.3). Applica, in quest'ordine: filtro sui campi obbligatori, deduplica
    per (user, source, external_id). Nessun tetto per notte lato nostro oltre
    al limite per chiamata già imposto dalla fonte (`MAX_ITEMS_PER_CALL` in
    `apps.jobs.sources.apify_linkedin`): ogni chiamata ad Apify è a pagamento
    indipendentemente da quanti risultati poi usiamo, quindi non ha senso
    scartarne a valle (rimosso il tetto per piano 50/100 job-notte, sprint
    corrente — vedi conversazione con l'utente sul caso "job Ginevra/Zurigo
    scartati perché un'altra ricerca aveva già saturato il tetto"). Ritorna
    la lista dei `Job` effettivamente creati.
    """
    active_searches = list(get_active_searches(user))
    if not active_searches:
        return []

    source = get_job_source()
    raw_offers = source.fetch(active_searches, window_hours=WINDOW_HOURS, limit=None)

    existing_external_ids = set(
        Job.objects.filter(user=user, source=Job.Source.LINKEDIN).values_list(
            "external_id", flat=True
        )
    )

    created = []
    seen_in_this_run = set()
    for offer in raw_offers:
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
            matched_search=offer.get("matched_search", ""),
            applicants_count=offer.get("applicants_count"),
            applicants_bucket=offer.get("applicants_bucket", ""),
            recruiter_name=offer.get("recruiter_name", ""),
            recruiter_profile_url=offer.get("recruiter_profile_url", ""),
            origin=Job.Origin.COLLECTED,
        )
        created.append(job)
    return created
