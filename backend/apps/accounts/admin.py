from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import AuthToken, User


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
                    "last_activity_reset",
                    "last_notified_at",
                )
            },
        ),
    )
    list_display = DjangoUserAdmin.list_display + ("plan", "extra_credit")


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
