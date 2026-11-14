from django.db import migrations

# Rimozione del marcatore del vecchio cap di intake (Sprint 68). I job
# marcati vanno eliminati PRIMA con `manage.py delete_discarded_by_cap_jobs
# --confirm` (DEPLOY.md §4.6): se ne restano, la migrazione si ferma qui
# invece di cancellare il marcatore e lasciare quei job in lista come normali.


def ensure_no_discarded_jobs(apps, schema_editor):
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, "jobs_job")
        }
        if "discarded_by_cap" not in columns:
            return
        cursor.execute("SELECT COUNT(*) FROM jobs_job WHERE discarded_by_cap")
        remaining = cursor.fetchone()[0]
    if remaining:
        raise RuntimeError(
            f"Ci sono ancora {remaining} job con discarded_by_cap=True: eseguire prima "
            "`python manage.py delete_discarded_by_cap_jobs --confirm` "
            "(vedi DEPLOY.md §4.6), poi rilanciare `migrate`."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0018_backfill_matched_saved_search"),
    ]

    operations = [
        migrations.RunPython(ensure_no_discarded_jobs, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="job",
            name="discarded_by_cap",
        ),
    ]
