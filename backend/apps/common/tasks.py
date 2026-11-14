import logging
import os
import re
import subprocess
import tarfile
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def add(a, b):
    return a + b


BACKUP_NAME_RE = re.compile(r"^(db|media)-(\d{4}-\d{2}-\d{2})\.(dump|tar\.gz)$")


def _write_backup_files(target_dir, date_stamp):
    """Scrive in `target_dir` il dump del DB (`pg_dump -Fc`) e l'archivio dei
    file media; restituisce i due path."""
    db = settings.DATABASES["default"]
    dump_path = Path(target_dir) / f"db-{date_stamp}.dump"
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

    media_path = Path(target_dir) / f"media-{date_stamp}.tar.gz"
    with tarfile.open(media_path, "w:gz") as tar:
        if Path(settings.MEDIA_ROOT).exists():
            tar.add(settings.MEDIA_ROOT, arcname="media")
    return dump_path, media_path


def _backup_to_s3(date_stamp):
    with TemporaryDirectory() as tmp_dir:
        dump_path, media_path = _write_backup_files(tmp_dir, date_stamp)
        client = boto3.client(
            "s3",
            endpoint_url=settings.BACKUP_S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.BACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.BACKUP_S3_SECRET_KEY,
            region_name=settings.BACKUP_S3_REGION,
        )
        client.upload_file(str(dump_path), settings.BACKUP_S3_BUCKET, dump_path.name)
        client.upload_file(str(media_path), settings.BACKUP_S3_BUCKET, media_path.name)


def rotate_local_backups(backup_dir, today, keep_days):
    """Cancella i backup locali con data più vecchia degli ultimi `keep_days`
    giorni (oggi compreso). La data è quella nel nome del file, non mtime:
    una copia fatta a mano non allunga la conservazione."""
    oldest_kept = today - timedelta(days=keep_days - 1)
    removed = []
    for path in Path(backup_dir).iterdir():
        match = BACKUP_NAME_RE.match(path.name)
        if not match or not path.is_file():
            continue
        if date.fromisoformat(match.group(2)) < oldest_kept:
            path.unlink()
            removed.append(path.name)
    return removed


def _backup_to_local_dir(date_stamp):
    """Backup locale ruotato (Sprint 67), quando lo storage S3 non è
    configurato: volume `local_backups` montato in BACKUP_LOCAL_DIR. Si
    scrive in una cartella temporanea dentro il volume e poi si sposta, così
    un dump interrotto non sostituisce quello buono del giorno."""
    backup_dir = Path(settings.BACKUP_LOCAL_DIR)
    backup_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=backup_dir, prefix=".tmp-") as tmp_dir:
        for path in _write_backup_files(tmp_dir, date_stamp):
            path.chmod(0o600)
            os.replace(path, backup_dir / path.name)
    removed = rotate_local_backups(backup_dir, date.fromisoformat(date_stamp), settings.BACKUP_LOCAL_KEEP_DAYS)
    if removed:
        logger.info("backup_database: rimossi %d backup locali più vecchi di %d giorni", len(removed), settings.BACKUP_LOCAL_KEEP_DAYS)


@shared_task
def backup_database():
    """Dump giornaliero del database + file media (02-specifiche-tecniche
    §8.4). Con il bucket S3 configurato si caricano lì (fuori dal VPS: un
    guasto del server non porta via anche i backup); altrimenti restano nel
    volume locale `local_backups`, conservati 7 giorni (Sprint 67)."""
    date_stamp = datetime.now().strftime("%Y-%m-%d")
    if settings.BACKUP_S3_BUCKET:
        _backup_to_s3(date_stamp)
        logger.info("backup_database: completato su S3 per %s", date_stamp)
    else:
        _backup_to_local_dir(date_stamp)
        logger.info("backup_database: completato in locale per %s", date_stamp)
