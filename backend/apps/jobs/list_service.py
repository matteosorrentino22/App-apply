import zoneinfo
from datetime import timedelta

from django.db.models import F, Q
from django.utils import timezone as dj_timezone

from .models import Job

# Le tre sezioni dipendono da origine e archiviazione, mai dallo stato
# (01-specifiche-funzionali-v4.md §4.5/§4.6).
SECTION_FILTERS = {
    "main": Q(origin=Job.Origin.COLLECTED, is_archived=False),
    "imported": Q(origin=Job.Origin.IMPORTED, is_archived=False),
    "archived": Q(is_archived=True),
}

PERIOD_CHOICES = ("today", "week", "month", "all")
DEFAULT_PERIOD = "today"

# Solo i tre stati stabili sono filtrabili: il transitorio "CV in
# generazione" non è un valore di status (§4.6 funzionali).
FILTERABLE_STATUSES = (
    Job.Status.NEW,
    Job.Status.CV_GENERATED,
    Job.Status.APPLICATION_DONE,
)


def _local_today_start(user):
    tz = zoneinfo.ZoneInfo(user.timezone)
    now_local = dj_timezone.now().astimezone(tz)
    return now_local.replace(hour=0, minute=0, second=0, microsecond=0)


def _apply_period_filter(queryset, user, period):
    if period == "today":
        return queryset.filter(date_collected__gte=_local_today_start(user))
    if period == "week":
        return queryset.filter(date_collected__gte=dj_timezone.now() - timedelta(days=7))
    if period == "month":
        return queryset.filter(date_collected__gte=dj_timezone.now() - timedelta(days=30))
    return queryset


def _apply_score_filter(queryset, scores):
    return queryset.filter(score__in=scores) if scores else queryset


def _apply_status_filter(queryset, statuses):
    return queryset.filter(status__in=statuses) if statuses else queryset


def list_jobs(user, section, period=DEFAULT_PERIOD, scores=None, statuses=None, query=""):
    """Restituisce i Job di `user` per la sezione richiesta, ordinati per
    punteggio decrescente (01-specifiche-funzionali-v4.md §4.5).

    Se `query` è presente, la ricerca testuale (titolo/azienda/località)
    resta confinata alla sezione corrente e **ignora** ogni altro filtro
    (temporale, score, stato) — così come richiesto esplicitamente dalle
    specifiche."""
    queryset = Job.objects.filter(user=user).filter(SECTION_FILTERS[section]).prefetch_related("cv_documents")

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) | Q(company__icontains=query) | Q(location__icontains=query)
        )
    else:
        queryset = _apply_period_filter(queryset, user, period)
        queryset = _apply_score_filter(queryset, scores)
        queryset = _apply_status_filter(queryset, statuses)

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
