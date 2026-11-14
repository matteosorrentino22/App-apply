import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobs", "0016_dailyquota_cv_import_count"),
        ("searches", "0003_savedsearch_search_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="job",
            name="matched_saved_search",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="jobs",
                to="searches.savedsearch",
            ),
        ),
        migrations.AddField(
            model_name="job",
            name="score_rescaled_from_legacy",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="job",
            name="scoring_failures",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        # Default lato database per la colonna che la 0019 rimuove: tra il
        # deploy del codice (che non conosce più il campo) e l'eliminazione
        # dei job marcati, gli INSERT di Django non valorizzano la colonna e
        # senza un default fallirebbero sul NOT NULL.
        migrations.AlterField(
            model_name="job",
            name="discarded_by_cap",
            field=models.BooleanField(default=False, db_default=False),
        ),
        migrations.AlterField(
            model_name="runlog",
            name="status",
            field=models.CharField(
                choices=[("success", "Successo"), ("failure", "Fallimento"), ("skipped", "Saltato")],
                max_length=10,
            ),
        ),
    ]
