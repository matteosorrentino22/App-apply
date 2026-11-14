# Sprint 69: documento di riferimento delle bozze esistenti. Non si sa da
# quale documento siano state seminate: si assume l'ultimo documento del job
# generato prima della creazione della bozza (quello che il seed avrebbe
# usato). Se dopo ne esiste uno più recente (rigenerazione o finalizzazione),
# alla prossima apertura l'editor chiede una volta sola se riseminare o
# continuare: meglio una domanda in più che un documento nuovo nascosto.
from django.db import migrations


def _backfill(draft_model, document_model, apps):
    Draft = apps.get_model("cv", draft_model)
    Document = apps.get_model("cv", document_model)
    for draft in Draft.objects.filter(source_document__isnull=True).iterator():
        documents = Document.objects.filter(job_id=draft.job_id).order_by("-generated_at", "-id")
        source = documents.filter(generated_at__lte=draft.created_at).first() or documents.last()
        if source is not None:
            Draft.objects.filter(pk=draft.pk).update(source_document=source)


def backfill(apps, schema_editor):
    _backfill("CVDraft", "CVDocument", apps)
    _backfill("CoverLetterDraft", "CoverLetterDocument", apps)


class Migration(migrations.Migration):

    dependencies = [
        ("cv", "0010_draft_source_document_page_count"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
