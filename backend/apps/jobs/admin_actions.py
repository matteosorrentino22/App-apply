"""Azioni Django Admin per azzerare i contatori giornalieri (Sprint 68),
al posto della shell (DEPLOY.md §7.3). Usate dalla lista utenti
(`apps.accounts.admin`) e dalla lista `DailyQuota` (`apps.jobs.admin`)."""

from django.contrib import admin, messages
from django.utils import timezone

from .models import DailyQuota

QUOTA_COUNTER_FIELDS = (
    "manual_cv_count",
    "cover_letter_count",
    "referral_message_count",
    "import_count",
    "manual_job_count",
    "collection_count",
    "cv_import_count",
)


def _today_europe_rome():
    return timezone.localtime(timezone.now()).date()


def _reset_today(modeladmin, request, users, fields):
    updated = DailyQuota.objects.filter(user__in=users, date=_today_europe_rome()).update(
        **{name: 0 for name in fields}
    )
    modeladmin.message_user(
        request,
        f"Contatori di oggi azzerati per {updated} utenti "
        f"(gli altri non avevano ancora consumato nulla oggi).",
        messages.SUCCESS,
    )


@admin.action(description="Azzera la quota di raccolta manuale di oggi")
def reset_today_collection_quota(modeladmin, request, queryset):
    _reset_today(modeladmin, request, queryset, ("collection_count",))


@admin.action(description="Azzera tutti i contatori giornalieri di oggi")
def reset_today_all_quotas(modeladmin, request, queryset):
    _reset_today(modeladmin, request, queryset, QUOTA_COUNTER_FIELDS)


@admin.action(description="Azzera tutti i contatori delle righe selezionate")
def reset_selected_daily_quotas(modeladmin, request, queryset):
    updated = queryset.update(**{name: 0 for name in QUOTA_COUNTER_FIELDS})
    modeladmin.message_user(request, f"Contatori azzerati su {updated} righe.", messages.SUCCESS)
