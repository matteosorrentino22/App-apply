from dataclasses import dataclass, field

from apps.searches.services import get_active_searches

from .models import Job
from .sources import get_job_source

REQUIRED_FIELDS = ("title", "company", "location", "description", "apply_url")

# Campi testuali con un max_length sul modello: un'offerta che lo supera (es.
# un apply_url LinkedIn con tracking query-string molto lungo) fa fallire
# `Job.objects.create()` con un DataError non catturato — osservato in
# produzione, interrompe l'intero batch a metà, lasciando le offerte già
# create senza possibilità di essere scorate (Sprint 49). Scartata come le
# offerte con campi obbligatori mancanti, non troncata: un apply_url
# troncato porterebbe a un link di candidatura rotto.
_LENGTH_CHECKED_FIELDS = (
    "title",
    "company",
    "location",
    "apply_url",
    "matched_search",
    "salary",
    "recruiter_name",
    "recruiter_profile_url",
)

WINDOW_HOURS = 24


def offer_rejection_reason(offer):
    """None se l'offerta è utilizzabile, altrimenti il motivo dello scarto:
    `"missing"` (campo obbligatorio vuoto) o `"too_long"` (campo oltre il
    `max_length` del modello). Usato da raccolta e import da link."""
    if not all(offer.get(name) for name in REQUIRED_FIELDS):
        return "missing"
    for name in _LENGTH_CHECKED_FIELDS:
        max_length = Job._meta.get_field(name).max_length
        if max_length and len(str(offer.get(name) or "")) > max_length:
            return "too_long"
    return None


class CollectionFailed(Exception):
    """Tutte le chiamate di gruppo alla fonte sono fallite: nessuna offerta
    raccolta per l'utente."""


@dataclass
class CollectionResult:
    created: list = field(default_factory=list)
    discarded_missing: int = 0
    discarded_too_long: int = 0
    discarded_duplicate: int = 0
    # Un elemento per gruppo (tipo × città × paese): `{"label", "offers",
    # "error"}`, con `offers` = numero di offerte restituite dalla fonte ed
    # `error` = testo dell'errore o None.
    groups: list = field(default_factory=list)

    @property
    def failed_groups(self):
        return [group for group in self.groups if group["error"] is not None]


def collect_jobs_for_user(user):
    """Raccoglie le offerte per le ricerche attive di un utente.

    Non espone alcun dettaglio della fonte sottostante (oggi Apify/LinkedIn,
    02-specifiche-tecniche §5.3). Applica, in quest'ordine: campi
    obbligatori, lunghezze, deduplica per (user, source, external_id); gli
    scarti sono contati per il RunLog (Sprint 68). Nessun tetto per notte
    oltre al limite per chiamata della fonte (`MAX_ITEMS_PER_CALL`): ogni
    chiamata ad Apify è a pagamento indipendentemente da quanti risultati
    poi usiamo.

    Un gruppo di ricerche la cui chiamata fallisce non fa perdere gli altri
    (Sprint 68); se falliscono tutti si solleva `CollectionFailed`."""
    result = CollectionResult()
    active_searches = list(get_active_searches(user))
    if not active_searches:
        return result

    groups = get_job_source().fetch_groups(active_searches, window_hours=WINDOW_HOURS)
    result.groups = [
        {
            "label": group["label"],
            "offers": len(group["offers"]),
            "error": None
            if group["error"] is None
            else f"{type(group['error']).__name__}: {group['error']}",
        }
        for group in groups
    ]
    if groups and len(result.failed_groups) == len(groups):
        raise CollectionFailed(
            "Tutte le chiamate alla fonte sono fallite: "
            + "; ".join(f"{group['label']}: {group['error']}" for group in result.groups)
        )

    existing_external_ids = set(
        Job.objects.filter(user=user, source=Job.Source.LINKEDIN).values_list(
            "external_id", flat=True
        )
    )
    valid_search_ids = {search.pk for search in active_searches}

    seen_in_this_run = set()
    for group in groups:
        for offer in group["offers"]:
            reason = offer_rejection_reason(offer)
            external_id = offer.get("external_id")
            if reason == "missing" or not external_id:
                result.discarded_missing += 1
                continue
            if reason == "too_long":
                result.discarded_too_long += 1
                continue
            if external_id in existing_external_ids or external_id in seen_in_this_run:
                result.discarded_duplicate += 1
                continue
            seen_in_this_run.add(external_id)

            saved_search_id = offer.get("saved_search_id")
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
                contract_type=offer.get("contract_type", ""),
                matched_search=offer.get("matched_search", ""),
                matched_saved_search_id=(
                    saved_search_id if saved_search_id in valid_search_ids else None
                ),
                applicants_count=offer.get("applicants_count"),
                applicants_bucket=offer.get("applicants_bucket", ""),
                recruiter_name=offer.get("recruiter_name", ""),
                recruiter_profile_url=offer.get("recruiter_profile_url", ""),
                origin=Job.Origin.COLLECTED,
            )
            result.created.append(job)
    return result
