from django.contrib import admin

from .models import DailyQuota, Job, RunLog


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
        "discarded_by_cap",
    )
    list_filter = ("origin", "status", "is_archived", "source", "discarded_by_cap")
    search_fields = ("title", "company", "location", "external_id")


@admin.register(DailyQuota)
class DailyQuotaAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "manual_cv_count", "import_count")
    list_filter = ("date",)


@admin.register(RunLog)
class RunLogAdmin(admin.ModelAdmin):
    list_display = ("task_type", "status", "user", "job", "started_at", "finished_at")
    list_filter = ("task_type", "status")
