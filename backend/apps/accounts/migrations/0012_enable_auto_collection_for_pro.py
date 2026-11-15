from django.db import migrations


def leave_automatic_collection_off(apps, schema_editor):
    # Sprint 77 attivava qui la raccolta automatica alle 07:00 per i Pro
    # esistenti. Sprint 81, su richiesta del committente: nessuna attivazione
    # preimpostata, anche per i Pro già presenti; ognuno la accende (e sceglie
    # l'orario) dal pannello di raccolta o da Impostazioni. La migrazione
    # resta, vuota, perché il nome è già nello storico delle migrazioni dei
    # database di prova.
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_auto_collection"),
    ]

    operations = [
        migrations.RunPython(leave_automatic_collection_off, migrations.RunPython.noop),
    ]
