from django.contrib import admin

from .models import SavedSearch


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    list_display = ("keywords", "city", "country", "user", "is_active")
    list_filter = ("is_active",)
