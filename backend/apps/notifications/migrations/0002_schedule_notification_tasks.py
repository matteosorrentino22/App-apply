from django.db import migrations


def create_notification_schedules(apps, schema_editor):
    IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")

    # Scheduler frequente (02-specifiche-tecniche-v3.md §5.5, §7): ogni ~15
    # minuti, per ogni utente, controlla se sono circa le 10:00 locali (per
    # la notifica mattutina) e se sono passati 7 giorni da
    # User.last_activity_reset (per il promemoria di inattività).
    schedule, _ = IntervalSchedule.objects.get_or_create(every=15, period="minutes")

    PeriodicTask.objects.get_or_create(
        name="Notifica mattutina (nuovi job)",
        defaults={
            "interval": schedule,
            "task": "apps.notifications.tasks.send_morning_notifications",
            "enabled": True,
        },
    )
    PeriodicTask.objects.get_or_create(
        name="Promemoria di inattività",
        defaults={
            "interval": schedule,
            "task": "apps.notifications.tasks.send_inactivity_notifications",
            "enabled": True,
        },
    )


def remove_notification_schedules(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(
        name__in=["Notifica mattutina (nuovi job)", "Promemoria di inattività"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0001_initial"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [
        migrations.RunPython(create_notification_schedules, remove_notification_schedules),
    ]
