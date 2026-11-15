from django.db import migrations

MORNING_NAME = "Notifica mattutina (nuovi job)"


def remove_morning(apps, schema_editor):
    # Sprint 77 (SPEC-DELTA B4): niente più notifica delle 10:00; i Pro
    # ricevono una notifica a fine raccolta automatica se ci sono job nuovi.
    # Resta il promemoria di inattività.
    apps.get_model("django_celery_beat", "PeriodicTask").objects.filter(name=MORNING_NAME).delete()


def restore_morning(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    schedule, _ = IntervalSchedule.objects.get_or_create(every=15, period="minutes")
    PeriodicTask.objects.get_or_create(
        name=MORNING_NAME,
        defaults={"interval": schedule, "task": "apps.notifications.tasks.send_morning_notifications", "enabled": True},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0002_schedule_notification_tasks"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(remove_morning, restore_morning),
    ]
