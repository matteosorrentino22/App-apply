from django.db import migrations

NIGHTLY_NAME = "Ciclo notturno (raccolta, scoring, cap di intake)"
AUTOMATIC_NAME = "Raccolte automatiche Pro (ogni 15 minuti)"


def replace_schedule(apps, schema_editor):
    # Sprint 77 (SPEC-DELTA A4/A5): niente più ciclo notturno delle 02:00 per
    # tutti; ogni 15 minuti si avviano le raccolte automatiche dei Pro per cui
    # è arrivato l'orario scelto (apps.jobs.tasks.run_automatic_collections).
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=NIGHTLY_NAME).delete()
    schedule, _ = IntervalSchedule.objects.get_or_create(every=15, period="minutes")
    PeriodicTask.objects.update_or_create(
        name=AUTOMATIC_NAME,
        defaults={"interval": schedule, "task": "apps.jobs.tasks.run_automatic_collections", "enabled": True},
    )


def restore_nightly(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name=AUTOMATIC_NAME).delete()
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0", hour="2", day_of_week="*", day_of_month="*", month_of_year="*", timezone="Europe/Rome"
    )
    PeriodicTask.objects.get_or_create(
        name=NIGHTLY_NAME,
        defaults={"crontab": schedule, "task": "apps.jobs.tasks.run_nightly_cycle", "enabled": True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0021_auto_collection"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(replace_schedule, restore_nightly),
    ]
