from collections import Counter

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.cv.models import CoverLetterDocument, CoverLetterDraft, CVDocument, CVDraft, ReferralMessageDocument
from apps.jobs.models import Job

# Sprint 68: i job marcati dal vecchio cap di intake (rimosso nello Sprint
# 46, mai reintegrati) vengono eliminati per decisione del committente,
# insieme a documenti e bozze collegati (cascata). Il campo non esiste più
# nel modello Django (migrazione jobs/0019): la colonna si legge con SQL
# finché la 0019 non l'ha rimossa.


def _discarded_job_ids():
    with connection.cursor() as cursor:
        columns = {
            column.name for column in connection.introspection.get_table_description(cursor, "jobs_job")
        }
        if "discarded_by_cap" not in columns:
            return None
        cursor.execute("SELECT id FROM jobs_job WHERE discarded_by_cap ORDER BY id")
        return [row[0] for row in cursor.fetchall()]


class Command(BaseCommand):
    help = (
        "Elimina i job marcati discarded_by_cap (vecchio cap di intake) con i loro documenti "
        "e bozze. Di default è un dry-run: con --confirm elimina davvero."
    )

    def add_arguments(self, parser):
        parser.add_argument("--confirm", action="store_true", help="Esegue l'eliminazione.")

    def handle(self, *args, confirm=False, **options):
        job_ids = _discarded_job_ids()
        if job_ids is None:
            self.stdout.write("Colonna discarded_by_cap già rimossa (migrazione jobs/0019): niente da fare.")
            return

        jobs = Job.objects.filter(pk__in=job_ids)
        self.stdout.write(f"Job con discarded_by_cap=True: {len(job_ids)}")
        breakdown = Counter(jobs.values_list("status", "is_archived", "is_favorite"))
        for (status, archived, favorite), count in sorted(breakdown.items()):
            self.stdout.write(f"  stato={status} archiviato={archived} preferito={favorite}: {count}")
        related = {
            "CV (CVDocument)": CVDocument.objects.filter(job__in=jobs),
            "cover letter (CoverLetterDocument)": CoverLetterDocument.objects.filter(job__in=jobs),
            "messaggi di networking": ReferralMessageDocument.objects.filter(job__in=jobs),
            "bozze CV": CVDraft.objects.filter(job__in=jobs),
            "bozze cover letter": CoverLetterDraft.objects.filter(job__in=jobs),
        }
        for label, queryset in related.items():
            count = queryset.count()
            jobs_with = queryset.values("job_id").distinct().count()
            self.stdout.write(f"  {label}: {count} (su {jobs_with} job)")

        if not confirm:
            self.stdout.write(self.style.WARNING("Dry-run: nulla è stato eliminato. Usa --confirm per eseguire."))
            return

        files = [
            document.pdf_file
            for model in (CVDocument, CoverLetterDocument)
            for document in model.objects.filter(job__in=jobs)
            if document.pdf_file
        ]
        with transaction.atomic():
            deleted, per_model = jobs.delete()
            # I PDF si cancellano dal disco solo a transazione confermata.
            transaction.on_commit(lambda: [f.storage.delete(f.name) for f in files])
        self.stdout.write(self.style.SUCCESS(f"Eliminati {deleted} record: {dict(per_model)}"))
