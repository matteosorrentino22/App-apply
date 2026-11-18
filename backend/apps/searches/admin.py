from django.contrib import admin

from .models import SavedSearch


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    # Sprint 85: dallo Sprint 84 una ricerca ha più città (`cities`) e la
    # colonna `city` (proprietà di compatibilità) mostrava solo la prima. Si
    # vedono anche tipo, modalità e le ricerche nascoste del lavoro dei
    # desideri, filtrabili.
    list_display = ("keywords", "search_type", "cities_display", "country", "work_mode_display", "hidden_wish", "user", "is_active")
    list_filter = ("is_active", "is_wish", "search_type")

    @admin.display(description="Città")
    def cities_display(self, obj):
        return ", ".join(obj.cities or [])

    @admin.display(description="Modalità", ordering="work_mode")
    def work_mode_display(self, obj):
        return obj.get_work_mode_display()

    @admin.display(description="Nascosta (desiderio)", boolean=True, ordering="is_wish")
    def hidden_wish(self, obj):
        return obj.is_wish
