from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.jobs.admin_actions import reset_today_all_quotas, reset_today_collection_quota

from .models import AuthToken, LegalAcceptance, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "App di ricerca lavoro",
            {
                "fields": (
                    "plan",
                    "timezone",
                    "interface_language",
                    "cv_language_mode",
                    "cv_include_photo",
                    "objective_statement",
                    "extra_credit",
                    "email_verified",
                    "notifications_enabled",
                    "last_activity_reset",
                    "last_notified_at",
                )
            },
        ),
        (
            "Raccolta e inattività",
            {
                "fields": (
                    "collection_in_progress",
                    "collection_started_at",
                    "last_inactivity_notified_at",
                )
            },
        ),
    )
    list_display = DjangoUserAdmin.list_display + ("plan", "extra_credit")
    actions = (reset_today_collection_quota, reset_today_all_quotas)


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    """Sola lettura, eliminabile: cancellare una riga disconnette quel
    dispositivo. La chiave non è recuperabile (nel DB c'è solo l'hash)."""

    list_display = ("user", "created_at", "last_used_at", "user_agent")
    search_fields = ("user__email",)
    readonly_fields = ("user", "created_at", "last_used_at", "user_agent")
    exclude = ("key_hash",)

    def has_add_permission(self, request):
        return False


@admin.register(LegalAcceptance)
class LegalAcceptanceAdmin(admin.ModelAdmin):
    """Registro append-only (Sprint 67): sola lettura. La cancellazione resta
    permessa perché serve alla cascata quando si elimina un utente dall'admin."""

    list_display = ("user", "document", "version", "accepted_at")
    list_filter = ("document", "version")
    search_fields = ("user__email",)
    readonly_fields = ("user", "document", "version", "accepted_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
