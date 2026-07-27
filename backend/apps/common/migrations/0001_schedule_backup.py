from django.db import migrations


def create_backup_schedule(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # 03:30 Europe/Rome, dopo il ciclo notturno delle 02:00 (apps.jobs
    # 0003_schedule_nightly_cycle), per non contendere I/O sul database
    # durante la raccolta/scoring (02-specifiche-tecniche-v3.md §8.4).
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute="30",
        hour="3",
        day_of_week="*",
        day_of_month="*",
        month_of_year="*",
        timezone="Europe/Rome",
    )
    PeriodicTask.objects.get_or_create(
        name="Backup giornaliero database",
        defaults={
            "crontab": schedule,
            "task": "apps.common.tasks.backup_database",
            "enabled": True,
        },
    )


def remove_backup_schedule(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name="Backup giornaliero database").delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_backup_schedule, remove_backup_schedule),
    ]
