from django.db import migrations, models


def _delete_educations_without_end_date(apps, schema_editor):
    """L'app è in fase di test, senza profili da preservare (Docs/03 §10.3):
    le uniche righe esistenti non hanno mai avuto una data di fine
    strutturata (il vecchio campo libero `dates` era spesso vuoto), quindi
    non c'è modo di derivarne una automaticamente. Le rimuoviamo invece di
    inventare una data fittizia: l'utente le reinserirà con date reali."""
    Education = apps.get_model("profiles", "Education")
    Education.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("profiles", "0002_profile_city_profile_linkedin_url_profile_phone"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="key_achievements",
        ),
        migrations.RunPython(
            _delete_educations_without_end_date, migrations.RunPython.noop
        ),
        migrations.RemoveField(
            model_name="education",
            name="dates",
        ),
        migrations.AddField(
            model_name="education",
            name="start_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="education",
            name="end_date",
            field=models.DateField(default="2000-01-01"),
            preserve_default=False,
        ),
    ]
