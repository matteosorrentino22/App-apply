from django.contrib import admin

from .models import CoverLetterDocument, CoverLetterDraft, CVDocument, CVDraft, ReferralMessageDocument


@admin.register(CVDocument)
class CVDocumentAdmin(admin.ModelAdmin):
    list_display = ("job", "user", "generation_type", "generated_at")
    list_filter = ("generation_type",)


class ReadOnlyAdmin(admin.ModelAdmin):
    """Consultazione in sola lettura (Sprint 68): documenti e bozze si
    creano e modificano solo dall'app. L'HTML sorgente dei PDF non è
    mostrato (troppo voluminoso)."""

    exclude = ("html_source",)
    raw_id_fields = ("job", "user")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CVDraft)
class CVDraftAdmin(ReadOnlyAdmin):
    list_display = ("job", "user", "created_at", "updated_at")
    search_fields = ("user__email", "job__title")


@admin.register(CoverLetterDocument)
class CoverLetterDocumentAdmin(ReadOnlyAdmin):
    list_display = ("job", "user", "generated_at")
    search_fields = ("user__email", "job__title")


@admin.register(CoverLetterDraft)
class CoverLetterDraftAdmin(ReadOnlyAdmin):
    list_display = ("job", "user", "created_at", "updated_at")
    search_fields = ("user__email", "job__title")


@admin.register(ReferralMessageDocument)
class ReferralMessageDocumentAdmin(ReadOnlyAdmin):
    list_display = ("job", "user", "channel", "recipient_name", "generated_at")
    list_filter = ("channel",)
    search_fields = ("user__email", "job__title")
