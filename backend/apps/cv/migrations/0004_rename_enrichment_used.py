# Sprint 44: l'arricchimento manuale su esperienza esistente è sostituito
# dalla selezione di gap da colmare (apps.cv.gap_filling) — il campo
# mantiene i dati storici, solo il nome cambia per riflettere il nuovo uso.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cv", "0003_cover_letter_support"),
    ]

    operations = [
        migrations.RenameField(
            model_name="cvdocument",
            old_name="enrichment_used",
            new_name="extra_instructions_used",
        ),
    ]
