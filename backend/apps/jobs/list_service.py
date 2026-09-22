import zoneinfo
from datetime import datetime, time, timedelta

from django.db.models import F, Q
from django.utils import timezone as dj_timezone

from apps.searches.models import SavedSearch

from .models import Job

# Le sezioni dipendono da origine/archiviazione/preferito, mai dallo stato
# (01-specifiche-funzionali-v4.md §4.5/§4.6). "favorites" esclude i job già
# archiviati: un job preferito e poi archiviato resta visibile solo in
# "Archiviati", non sparisce dal flag `is_favorite` ma non compare più qui.
SECTION_FILTERS = {
    "main": Q(origin=Job.Origin.COLLECTED, is_archived=False),
    "imported": Q(origin=Job.Origin.IMPORTED, is_archived=False),
    "favorites": Q(is_favorite=True, is_archived=False),
    "archived": Q(is_archived=True),
}

# Solo i tre stati stabili sono filtrabili: il transitorio "CV in
# generazione" non è un valore di status (§4.6 funzionali).
FILTERABLE_STATUSES = (
    Job.Status.NEW,
    Job.Status.CV_GENERATED,
    Job.Status.APPLICATION_DONE,
)

# Fasce di candidati selezionabili come filtro: le due agli estremi
# includono sia il caso con numero esatto (`applicants_count`) sia il caso
# in cui LinkedIn mostra solo la fascia testuale (`applicants_bucket`),
# le tre centrali esistono solo come numero esatto.
APPLICANTS_RANGES = ("under_25", "25_50", "51_100", "101_200", "over_200")


def _local_today_start(user):
    tz = zoneinfo.ZoneInfo(user.timezone)
    now_local = dj_timezone.now().astimezone(tz)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def _apply_date_range_filter(queryset, user, date_from, date_to):
    """Filtra `date_collected` sull'intervallo di giorni [date_from, date_to]
    (entrambi inclusivi), convertito nel fuso locale dell'utente — non un
    riferimento unico di sistema (stesso principio di `_local_today_start`,
    Sprint 22 §7 requisiti trasversali). Nessuno dei due limiti = nessun
    filtro su quel lato (entrambi assenti = intera storia, sostituisce il
    vecchio `period="all"`)."""
    if date_from is None and date_to is None:
        return queryset
    tz = zoneinfo.ZoneInfo(user.timezone)
    if date_from is not None:
        queryset = queryset.filter(date_collected__gte=datetime.combine(date_from, time.min, tzinfo=tz))
    if date_to is not None:
        upper_bound = datetime.combine(date_to, time.min, tzinfo=tz) + timedelta(days=1)
        queryset = queryset.filter(date_collected__lt=upper_bound)
    return queryset


def _apply_score_filter(queryset, scores):
    return queryset.filter(score__in=scores) if scores else queryset


def _apply_status_filter(queryset, statuses):
    return queryset.filter(status__in=statuses) if statuses else queryset


def _apply_matched_search_filter(queryset, user, search_id):
    """Filtra per la SavedSearch che ha prodotto il job.

    `Job.matched_search` è testo libero, non una FK (vedi commento sul
    campo in models.py): qui si ricostruisce la stringa che l'actor Apify
    avrebbe restituito per la SavedSearch scelta e si confronta con quella.
    `search_id="none"` isola i job senza ricerca di provenienza (import
    manuale, o item Apify malformati — sprint-40)."""
    if not search_id or search_id == "all":
        return queryset
    if search_id == "none":
        return queryset.filter(matched_search="")

    saved_search = SavedSearch.objects.filter(user=user, pk=search_id).first()
    if saved_search is None:
        return queryset.none()

    if saved_search.search_type == SavedSearch.SearchType.COMPANY:
        # Il nome azienda restituito da LinkedIn (risolto per ID tramite
        # `companyInclude`) può differire per maiuscole/minuscole da come
        # l'ha digitato l'utente.
        return queryset.filter(matched_search__iexact=saved_search.keywords)

    location = f"{saved_search.city}, {saved_search.country}"
    return queryset.filter(matched_search=f"{saved_search.keywords} - {location}")


def _apply_location_filter(queryset, location):
    """Filtro libero su città/paese: `Job.location` è un unico campo testo
    (non strutturato in città/paese separati — vedi commento sul campo in
    models.py), quindi qui si fa una ricerca a sottostringa su di esso. A
    differenza della ricerca testuale principale (`query`), questo filtro si
    combina in AND con gli altri (data/score/stato/ricerca di provenienza),
    non li ignora."""
    return queryset.filter(location__icontains=location) if location else queryset


def _applicants_range_q(range_key):
    if range_key == "under_25":
        return Q(applicants_bucket="under_25") | Q(applicants_count__lt=25)
    if range_key == "25_50":
        return Q(applicants_count__gte=25, applicants_count__lte=50)
    if range_key == "51_100":
        return Q(applicants_count__gte=51, applicants_count__lte=100)
    if range_key == "101_200":
        return Q(applicants_count__gte=101, applicants_count__lte=200)
    if range_key == "over_200":
        return Q(applicants_bucket="over_200") | Q(applicants_count__gt=200)
    return Q(pk__in=[])


def _apply_applicants_filter(queryset, applicants_ranges):
    """Filtro multi-selezione sulle fasce di candidati (sprint corrente):
    ogni fascia selezionata si combina in OR con le altre (come score/stato),
    nessuna selezione = nessun filtro."""
    if not applicants_ranges:
        return queryset
    combined = Q(pk__in=[])
    for range_key in applicants_ranges:
        combined |= _applicants_range_q(range_key)
    return queryset.filter(combined)


def _apply_recruiter_filter(queryset, has_recruiter):
    """Filtro binario su presenza del nome recruiter. `has_recruiter=None`
    (default) = nessun filtro; `True`/`False` isola rispettivamente i job
    con e senza `recruiter_name`."""
    if has_recruiter is None:
        return queryset
    if has_recruiter:
        return queryset.exclude(recruiter_name="")
    return queryset.filter(recruiter_name="")


def list_jobs(
    user,
    section,
    date_from=None,
    date_to=None,
    scores=None,
    statuses=None,
    query="",
    search_id=None,
    location="",
    applicants_ranges=None,
    has_recruiter=None,
):
    """Restituisce i Job di `user` per la sezione richiesta, ordinati per
    punteggio decrescente (01-specifiche-funzionali-v4.md §4.5).

    Se `query` è presente, la ricerca testuale (titolo/azienda/località)
    resta confinata alla sezione corrente e **ignora** ogni altro filtro
    (intervallo di date, score, stato, ricerca di provenienza, location,
    candidati, recruiter) — così come richiesto esplicitamente dalle
    specifiche. Gli altri filtri si combinano invece tutti in AND tra loro."""
    queryset = Job.objects.filter(user=user).filter(SECTION_FILTERS[section]).prefetch_related("cv_documents")

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) | Q(company__icontains=query) | Q(location__icontains=query)
        )
    else:
        queryset = _apply_date_range_filter(queryset, user, date_from, date_to)
        queryset = _apply_score_filter(queryset, scores)
        queryset = _apply_status_filter(queryset, statuses)
        queryset = _apply_matched_search_filter(queryset, user, search_id)
        queryset = _apply_location_filter(queryset, location)
        queryset = _apply_applicants_filter(queryset, applicants_ranges)
        queryset = _apply_recruiter_filter(queryset, has_recruiter)

    return queryset.order_by(F("score").desc(nulls_last=True), "-date_collected")


def archive_job(job):
    job.is_archived = True
    job.save(update_fields=["is_archived"])


def unarchive_job(job):
    """Riporta il job alla sua sezione d'origine mantenendo lo status che
    aveva: l'archiviazione è ortogonale allo stato (§4.6 funzionali), quindi
    basta invertire `is_archived` — usato sia per lo swipe "rimuovi da
    archivio" sia per l'undo di uno swipe "archivia" accidentale."""
    job.is_archived = False
    job.save(update_fields=["is_archived"])


def favorite_job(job):
    job.is_favorite = True
    job.save(update_fields=["is_favorite"])


def unfavorite_job(job):
    job.is_favorite = False
    job.save(update_fields=["is_favorite"])
