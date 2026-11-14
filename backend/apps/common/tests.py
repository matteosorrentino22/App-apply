import tarfile
import tempfile
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django_celery_beat.models import PeriodicTask

from .tasks import backup_database, rotate_local_backups


class BackupScheduleTests(TestCase):
    def test_periodic_task_is_scheduled_at_0330_europe_rome(self):
        task = PeriodicTask.objects.get(name="Backup giornaliero database")
        self.assertEqual(task.task, "apps.common.tasks.backup_database")
        self.assertTrue(task.enabled)
        self.assertEqual(task.crontab.hour, "3")
        self.assertEqual(task.crontab.minute, "30")
        self.assertEqual(str(task.crontab.timezone), "Europe/Rome")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class BackupDatabaseTaskTests(TestCase):
    @override_settings(BACKUP_S3_BUCKET="app-apply-backups")
    @patch("apps.common.tasks.boto3.client")
    @patch("apps.common.tasks.subprocess.run")
    def test_dumps_database_and_uploads_dump_and_media(self, mock_run, mock_boto_client):
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client

        backup_database()

        self.assertEqual(mock_run.call_args.args[0][0], "pg_dump")
        self.assertEqual(mock_client.upload_file.call_count, 2)
        uploaded_keys = [call.args[2] for call in mock_client.upload_file.call_args_list]
        self.assertTrue(any(key.startswith("db-") for key in uploaded_keys))
        self.assertTrue(any(key.startswith("media-") for key in uploaded_keys))


def _fake_pg_dump(args, **kwargs):
    # Al posto di pg_dump: crea il file indicato da -f.
    Path(args[args.index("-f") + 1]).write_bytes(b"PGDMP fake")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), BACKUP_S3_BUCKET="")
class LocalBackupTests(TestCase):
    """Backup locale ruotato (Sprint 67), usato quando S3 non è configurato."""

    def setUp(self):
        self.backup_dir = Path(tempfile.mkdtemp())
        override = override_settings(BACKUP_LOCAL_DIR=self.backup_dir)
        override.enable()
        self.addCleanup(override.disable)

    def _touch(self, name):
        (self.backup_dir / name).write_bytes(b"old")

    @patch("apps.common.tasks.boto3.client")
    @patch("apps.common.tasks.subprocess.run", side_effect=_fake_pg_dump)
    def test_writes_dump_and_media_locally_and_keeps_seven_days(self, mock_run, mock_boto_client):
        today = date.today()
        for days_ago in (6, 7, 30):
            stamp = (today - timedelta(days=days_ago)).isoformat()
            self._touch(f"db-{stamp}.dump")
            self._touch(f"media-{stamp}.tar.gz")
        self._touch("manual_copy.dump")

        backup_database()

        self.assertEqual(mock_run.call_args.args[0][0], "pg_dump")
        self.assertIn("-Fc", mock_run.call_args.args[0])
        mock_boto_client.assert_not_called()
        names = sorted(path.name for path in self.backup_dir.iterdir())
        kept_day = (today - timedelta(days=6)).isoformat()
        self.assertEqual(
            names,
            sorted([
                f"db-{today.isoformat()}.dump", f"media-{today.isoformat()}.tar.gz",
                f"db-{kept_day}.dump", f"media-{kept_day}.tar.gz", "manual_copy.dump",
            ]),
        )
        dump = self.backup_dir / f"db-{today.isoformat()}.dump"
        self.assertEqual(dump.read_bytes(), b"PGDMP fake")
        self.assertEqual(dump.stat().st_mode & 0o777, 0o600)
        self.assertTrue(tarfile.is_tarfile(self.backup_dir / f"media-{today.isoformat()}.tar.gz"))

    def test_rotation_ignores_unrelated_files(self):
        self._touch("db-2020-01-01.dump")
        self._touch("notes.txt")
        self._touch("db-latest.dump")

        removed = rotate_local_backups(self.backup_dir, date(2026, 11, 14), 7)

        self.assertEqual(removed, ["db-2020-01-01.dump"])
        self.assertEqual(sorted(p.name for p in self.backup_dir.iterdir()), ["db-latest.dump", "notes.txt"])

    @patch("apps.common.tasks.subprocess.run", side_effect=OSError("pg_dump failed"))
    def test_failed_dump_leaves_previous_backups_untouched(self, mock_run):
        stamp = (date.today() - timedelta(days=1)).isoformat()
        self._touch(f"db-{stamp}.dump")

        with self.assertRaises(OSError):
            backup_database()

        self.assertEqual([p.name for p in self.backup_dir.iterdir()], [f"db-{stamp}.dump"])


class RestoreBackupCommandTests(TestCase):
    def test_refuses_without_confirm(self):
        with self.assertRaises(CommandError):
            call_command("restore_backup", "2026-01-01", stdout=StringIO())

    @override_settings(BACKUP_S3_BUCKET="", BACKUP_LOCAL_DIR=Path(tempfile.mkdtemp()))
    def test_refuses_when_local_backup_is_missing(self):
        with self.assertRaises(CommandError):
            call_command("restore_backup", "2026-01-01", "--confirm", stdout=StringIO())

    @patch("apps.common.management.commands.restore_backup.subprocess.run")
    def test_restores_from_local_dir_or_explicit_file(self, mock_run):
        backup_dir = Path(tempfile.mkdtemp())
        (backup_dir / "db-2026-01-01.dump").write_bytes(b"PGDMP")
        explicit = backup_dir / "copied.dump"
        explicit.write_bytes(b"PGDMP")

        with override_settings(BACKUP_S3_BUCKET="", BACKUP_LOCAL_DIR=backup_dir):
            call_command("restore_backup", "2026-01-01", "--confirm", stdout=StringIO())
        self.assertEqual(mock_run.call_args.args[0][0], "pg_restore")
        self.assertEqual(mock_run.call_args.args[0][-1], str(backup_dir / "db-2026-01-01.dump"))

        call_command("restore_backup", "--file", str(explicit), "--confirm", stdout=StringIO())
        self.assertEqual(mock_run.call_args.args[0][-1], str(explicit))
