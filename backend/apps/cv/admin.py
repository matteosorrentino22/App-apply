from django.contrib import admin

from .models import CVDocument


@admin.register(CVDocument)
class CVDocumentAdmin(admin.ModelAdmin):
    list_display = ("job", "user", "generation_type", "generated_at")
    list_filter = ("generation_type",)
