from django.db import migrations


def create_nightly_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Ciclo notturno alle 02:00 Europe/Rome (02-specifiche-tecniche-v3.md §5.1, §7).
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="0",
        hour="2",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="Europe/Rome",
    )
    PeriodicTask.objects.get_or_create(
        name="Ciclo notturno (raccolta, scoring, cap di intake)",
        defaults={
            "crontab": schedule,
            "task": "apps.jobs.tasks.run_nightly_cycle",
            "enabled": True,
        },
    )


def remove_nightly_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name="Ciclo notturno (raccolta, scoring, cap di intake)"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("jobs", "0002_job_discarded_by_cap"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_nightly_schedule, remove_nightly_schedule),
    ]
