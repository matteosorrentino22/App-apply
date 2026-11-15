import datetime
import zoneinfo

from django.db import migrations
from django.utils import timezone


def enable_for_existing_pro(apps, schema_editor):
    # Sprint 77: i Pro esistenti avevano la raccolta notturna delle 02:00, che
    # viene tolta; per non lasciarli senza raccolta si attiva l'automatica
    # alle 07:00 (nel loro fuso). La data locale di oggi si segna come già
    # fatta: il giorno del rilascio il ciclo notturno ha già raccolto, la
    # prima automatica parte domani (nessuna seconda chiamata Apify oggi).
    # I nuovi Pro partono con l'automatica spenta (default del campo).
    User = apps.get_model("accounts", "User")
    now = timezone.now()
    for user in User.objects.filter(plan="pro"):
        try:
            zone = zoneinfo.ZoneInfo(user.timezone or "Europe/Rome")
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            zone = zoneinfo.ZoneInfo("Europe/Rome")
        user.auto_collection_enabled = True
        user.auto_collection_time = datetime.time(7, 0)
        user.auto_collection_last_local_date = now.astimezone(zone).date()
        user.save(update_fields=["auto_collection_enabled", "auto_collection_time", "auto_collection_last_local_date"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_auto_collection"),
    ]

    operations = [
        migrations.RunPython(enable_for_existing_pro, migrations.RunPython.noop),
    ]
