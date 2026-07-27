import logging
import os
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def add(a, b):
    return a + b


@shared_task
def backup_database():
    """Dump giornaliero del database + file media, caricati su uno storage a
    oggetti esterno al VPS (02-specifiche-tecniche-v3.md §8.4): un guasto del
    server non deve portare via anche i backup. I PDF dei CV sono
    rigenerabili dall'HTML salvato, ma vengono comunque inclusi per comodità
    (stessa nota tecnica)."""
    if not settings.BACKUP_S3_BUCKET:
        logger.warning("backup_database: BACKUP_S3_BUCKET non configurato, backup saltato.")
        return

    date_stamp = datetime.now().strftime("%Y-%m-%d")
    db = settings.DATABASES["default"]

    with TemporaryDirectory() as tmp_dir:
        dump_path = Path(tmp_dir) / f"db-{date_stamp}.dump"
        subprocess.run(
            [
                "pg_dump",
                "-h", db["HOST"],
                "-p", str(db["PORT"]),
                "-U", db["USER"],
                "-Fc",
                "-f", str(dump_path),
                db["NAME"],
            ],
            env={**os.environ, "PGPASSWORD": db["PASSWORD"]},
            check=True,
        )

        media_path = Path(tmp_dir) / f"media-{date_stamp}.tar.gz"
        with tarfile.open(media_path, "w:gz") as tar:
            if Path(settings.MEDIA_ROOT).exists():
                tar.add(settings.MEDIA_ROOT, arcname="media")

        client = boto3.client(
            "s3",
            endpoint_url=settings.BACKUP_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
            region_name=settings.BACKUP_S3_REGION,
        )
        client.upload_file(str(dump_path), settings.BACKUP_S3_BUCKET, dump_path.name)
        client.upload_file(str(media_path), settings.BACKUP_S3_BUCKET, media_path.name)

    logger.info("backup_database: completato per %s", date_stamp)
