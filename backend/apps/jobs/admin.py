from django.contrib import admin

from .admin_actions import QUOTA_COUNTER_FIELDS, reset_selected_daily_quotas
from .models import DailyQuota, Job, JobFilterPreset, RunLog


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "user",
        "source",
        "origin",
        "status",
        "score",
        "is_archived",
        "score_rescaled_from_legacy",
        "scoring_failures",
    )
    list_filter = ("origin", "status", "is_archived", "source", "score_rescaled_from_legacy")
    search_fields = ("title", "company", "location", "external_id")
    raw_id_fields = ("user", "matched_saved_search")


@admin.register(DailyQuota)
class DailyQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "date", *QUOTA_COUNTER_FIELDS)
    list_filter = ("date",)
    search_fields = ("user__email",)
    raw_id_fields = ("user",)
    actions = (reset_selected_daily_quotas,)


@admin.register(RunLog)
class RunLogAdmin(admin.ModelAdmin):
    list_display = ("task_type", "status", "user", "job", "started_at", "finished_at")
    list_filter = ("task_type", "status")
    raw_id_fields = ("user", "job")


@admin.register(JobFilterPreset)
class JobFilterPresetAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "created_at")
    search_fields = ("name", "user__email")
    readonly_fields = (
        "user",
        "name",
        "scores",
        "statuses",
        "search_ids",
        "location",
        "applicants_ranges",
        "has_recruiter",
        "created_at",
    )

    def has_add_permission(self, request):
        return False
