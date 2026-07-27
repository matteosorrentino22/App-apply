import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Scarica il dump `db-<data>.dump` prodotto da `backup_database` (Sprint
    21, §8.4 tecniche) e lo ripristina nel database a cui questo comando è
    puntato — pensato per un ambiente separato di test restore, non per la
    produzione: `pg_restore --clean` sovrascrive gli oggetti esistenti."""

    help = "Ripristina un backup del database da storage S3 in un ambiente di test (richiede --confirm)."

    def add_arguments(self, parser):
        parser.add_argument("date", type=str, help="Data del backup, formato YYYY-MM-DD")
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Conferma esplicita: il comando sovrascrive il database corrente.",
        )

    def handle(self, *args, **options):
        if not options["confirm"]:
            raise CommandError(
                "Il ripristino sovrascrive il database corrente: rilanciare con --confirm "
                "solo su un ambiente di test separato."
            )
        if not settings.BACKUP_S3_BUCKET:
            raise CommandError("BACKUP_S3_BUCKET non configurato.")

        date_stamp = options["date"]
        db = settings.DATABASES["default"]

        client = boto3.client(
            "s3",
            endpoint_url=settings.BACKUP_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
            region_name=settings.BACKUP_S3_REGION,
        )

        with TemporaryDirectory() as tmp_dir:
            dump_path = Path(tmp_dir) / f"db-{date_stamp}.dump"
            key = dump_path.name
            try:
                client.download_file(settings.BACKUP_S3_BUCKET, key, str(dump_path))
            except Exception as exc:
                raise CommandError(f"Impossibile scaricare {key} da {settings.BACKUP_S3_BUCKET}: {exc}") from exc

            subprocess.run(
                [
                    "pg_restore",
                    "--clean",
                    "--if-exists",
                    "-h", db["HOST"],
                    "-p", str(db["PORT"]),
                    "-U", db["USER"],
                    "-d", db["NAME"],
                    str(dump_path),
                ],
                env={**os.environ, "PGPASSWORD": db["PASSWORD"]},
                check=True,
            )

        self.stdout.write(self.style.SUCCESS(f"Ripristino di {key} completato su {db['NAME']}."))
