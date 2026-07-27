import tempfile
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django_celery_beat.models import PeriodicTask

from .tasks import backup_database


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
    @override_settings(BACKUP_S3_BUCKET="")
    def test_skipped_when_bucket_not_configured(self):
        with patch("apps.common.tasks.subprocess.run") as mock_run:
            backup_database()
        mock_run.assert_not_called()

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


class RestoreBackupCommandTests(TestCase):
    def test_refuses_without_confirm(self):
        with self.assertRaises(CommandError):
            call_command("restore_backup", "2026-01-01", stdout=StringIO())

    @override_settings(BACKUP_S3_BUCKET="")
    def test_refuses_without_configured_bucket(self):
        with self.assertRaises(CommandError):
            call_command("restore_backup", "2026-01-01", "--confirm", stdout=StringIO())
