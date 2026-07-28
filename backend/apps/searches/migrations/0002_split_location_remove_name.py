from django.db import migrations, models


def split_location_forward(apps, schema_editor):
    SavedSearch = apps.get_model("searches", "SavedSearch")
    for search in SavedSearch.objects.all():
        location = (search.location or "").strip()
        if "," in location:
            city, country = location.rsplit(",", 1)
            search.city = city.strip()
            search.country = country.strip()
        else:
            search.city = location
            search.country = ""
        search.save(update_fields=["city", "country"])


def split_location_backward(apps, schema_editor):
    SavedSearch = apps.get_model("searches", "SavedSearch")
    for search in SavedSearch.objects.all():
        parts = [part for part in (search.city, search.country) if part]
        search.location = ", ".join(parts)
        search.save(update_fields=["location"])


class Migration(migrations.Migration):

    dependencies = [
        ("searches", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedsearch",
            name="city",
            field=models.CharField(max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="savedsearch",
            name="country",
            field=models.CharField(max_length=255, default=""),
            preserve_default=False,
        ),
        migrations.RunPython(split_location_forward, split_location_backward),
        migrations.RemoveField(
            model_name="savedsearch",
            name="location",
        ),
        migrations.RemoveField(
            model_name="savedsearch",
            name="name",
        ),
    ]
