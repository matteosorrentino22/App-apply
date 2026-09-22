from datetime import timedelta

from django.utils import timezone as dj_timezone

from apps.cv.models import CVDocument

from .list_service import _local_today_start
from .models import Job


def _period_counts(queryset, date_field, today_start, week_start):
    return {
        "today": queryset.filter(**{f"{date_field}__gte": today_start}).count(),
        "week": queryset.filter(**{f"{date_field}__gte": week_start}).count(),
        "total": queryset.count(),
    }


def get_home_stats(user):
    """Statistiche aggregate per la Home (Sprint 44): job trovati, CV
    generati, candidature fatte, oggi/ultima settimana/totali."""
    today_start = _local_today_start(user)
    week_start = dj_timezone.now() - timedelta(days=7)

    jobs_qs = Job.objects.filter(user=user)
    jobs = _period_counts(jobs_qs, "date_collected", today_start, week_start)
    jobs["manual"] = _period_counts(
        jobs_qs.filter(origin=Job.Origin.IMPORTED), "date_collected", today_start, week_start
    )

    cvs = _period_counts(CVDocument.objects.filter(user=user), "generated_at", today_start, week_start)

    applications = _period_counts(
        Job.objects.filter(user=user, status=Job.Status.APPLICATION_DONE),
        "date_application_done",
        today_start,
        week_start,
    )

    return {"jobs": jobs, "cvs": cvs, "applications": applications}
