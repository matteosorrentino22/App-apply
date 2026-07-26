from django.contrib import admin

from .models import SavedSearch


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "keywords", "location", "is_active")
    list_filter = ("is_active",)
