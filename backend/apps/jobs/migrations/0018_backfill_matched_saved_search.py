from django.db import migrations

# Backfill del riferimento stabile alla ricerca di provenienza (Sprint 68)
# dai valori *attuali* delle ricerche salvate, con la stessa regola testuale
# usata finora dal filtro "Ricerca" (apps.jobs.list_service): Job role
# "<keywords> - <città>, <paese>" esatto, Company nome azienda senza
# distinzione di maiuscole. Si assegna solo quando la corrispondenza è
# univoca: con più ricerche candidate (es. la stessa azienda cercata in due
# città) il job resta senza FK e il filtro continua a usare il confronto
# testuale, cioè il comportamento di prima.


def matching_search_ids(searches, label):
    return [
        search.pk
        for search in searches
        if (search.search_type == "company" and search.keywords.casefold() == label.casefold())
        or (
            search.search_type != "company"
            and label == f"{search.keywords} - {search.city}, {search.country}"
        )
    ]


def backfill(apps, schema_editor):
    Job = apps.get_model("jobs", "Job")
    SavedSearch = apps.get_model("searches", "SavedSearch")

    pending = Job.objects.filter(matched_saved_search__isnull=True).exclude(matched_search="")
    for user_id in pending.values_list("user_id", flat=True).distinct():
        searches = list(SavedSearch.objects.filter(user_id=user_id))
        if not searches:
            continue
        labels = pending.filter(user_id=user_id).values_list("matched_search", flat=True).distinct()
        for label in list(labels):
            candidates = matching_search_ids(searches, label)
            if len(candidates) == 1:
                pending.filter(user_id=user_id, matched_search=label).update(
                    matched_saved_search_id=candidates[0]
                )


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0017_sprint68_job_fields"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
