from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


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
