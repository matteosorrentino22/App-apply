import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """Ripristina il dump `db-<data>.dump` prodotto da `backup_database`
    (Sprint 21, §8.4 tecniche) nel database a cui questo comando è puntato —
    pensato per un ambiente separato di test restore, non per la
    produzione: `pg_restore --clean` sovrascrive gli oggetti esistenti.
    Sorgente (Sprint 67): `--file` esplicito, altrimenti il bucket S3 se
    configurato, altrimenti la cartella dei backup locali (BACKUP_LOCAL_DIR)."""

    help = "Ripristina un backup del database (S3, cartella locale o --file) in un ambiente di test (richiede --confirm)."

    def add_arguments(self, parser):
        parser.add_argument("date", type=str, nargs="?", help="Data del backup, formato YYYY-MM-DD")
        parser.add_argument("--file", type=str, help="Path di un dump locale da ripristinare (al posto della data)")
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
        if not options["file"] and not options["date"]:
            raise CommandError("Indicare la data del backup (YYYY-MM-DD) oppure --file <path>.")

        with TemporaryDirectory() as tmp_dir:
            dump_path = self._resolve_dump(options, tmp_dir)
            self._restore(dump_path)

        self.stdout.write(self.style.SUCCESS(f"Ripristino di {dump_path.name} completato."))

    def _resolve_dump(self, options, tmp_dir):
        if options["file"]:
            dump_path = Path(options["file"])
            if not dump_path.is_file():
                raise CommandError(f"File non trovato: {dump_path}")
            return dump_path

        name = f"db-{options['date']}.dump"
        if settings.BACKUP_S3_BUCKET:
            dump_path = Path(tmp_dir) / name
            client = boto3.client(
                "s3",
                endpoint_url=settings.BACKUP_S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
                aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
                region_name=settings.BACKUP_S3_REGION,
            )
            try:
                client.download_file(settings.BACKUP_S3_BUCKET, name, str(dump_path))
            except Exception as exc:
                raise CommandError(f"Impossibile scaricare {name} da {settings.BACKUP_S3_BUCKET}: {exc}") from exc
            return dump_path

        dump_path = Path(settings.BACKUP_LOCAL_DIR) / name
        if not dump_path.is_file():
            raise CommandError(
                f"{name} non trovato in {settings.BACKUP_LOCAL_DIR} (bucket S3 non configurato)."
            )
        return dump_path

    def _restore(self, dump_path):
        db = settings.DATABASES["default"]
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
