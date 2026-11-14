from django.db import migrations


def mark_existing_users_verified(apps, schema_editor):
    # Gli account creati prima dello Sprint 67 non hanno mai ricevuto
    # un'email di verifica: si considerano verificati (decisione del
    # committente). L'accettazione di informativa e termini invece no: la
    # chiede la schermata bloccante al primo accesso.
    User = apps.get_model("accounts", "User")
    User.objects.update(email_verified=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0009_user_email_verified_legalacceptance"),
    ]

    operations = [
        migrations.RunPython(mark_existing_users_verified, migrations.RunPython.noop),
    ]
