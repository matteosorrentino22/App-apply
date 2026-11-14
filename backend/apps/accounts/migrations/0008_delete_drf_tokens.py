from django.db import migrations

DRF_TOKEN_TABLE = "authtoken_token"


def delete_drf_tokens(apps, schema_editor):
    # Sprint 66: i Token DRF (permanenti, salvati in chiaro) sono sostituiti
    # da AuthToken. L'app rest_framework.authtoken non è più installata, ma
    # la sua tabella esiste ancora nei DB creati prima di questo sprint:
    # tutti gli utenti dovranno rifare il login.
    connection = schema_editor.connection
    if DRF_TOKEN_TABLE in connection.introspection.table_names():
        with connection.cursor() as cursor:
            cursor.execute(f"DELETE FROM {connection.ops.quote_name(DRF_TOKEN_TABLE)}")


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0007_authtoken"),
    ]

    operations = [
        migrations.RunPython(delete_drf_tokens, migrations.RunPython.noop),
    ]
