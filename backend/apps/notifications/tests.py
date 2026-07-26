from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.jobs.models import Job

from .models import PushSubscription
from .tasks import send_inactivity_notification_for_user, send_morning_notification_for_user

User = get_user_model()


def _make_job(user, external_id, date_collected):
    job = Job.objects.create(
        user=user,
        source=Job.Source.LINKEDIN,
        external_id=external_id,
        title="Project Manager",
        company="Acme S.p.A.",
        location="Roma",
        description="Descrizione.",
        apply_url="https://linkedin.com/jobs/view/1",
    )
    Job.objects.filter(pk=job.pk).update(date_collected=date_collected)
    job.refresh_from_db()
    return job


class MorningNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="morning@example.com",
            email="morning@example.com",
            password="pw-Morning-12345!",
            timezone="Europe/Rome",
        )
        self.user.last_notified_at = timezone.now() - timedelta(days=1)
        self.user.save(update_fields=["last_notified_at"])
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/abc",
            p256dh_key="p256dh-key",
            auth_key="auth-key",
        )

    def test_sends_and_updates_last_notified_at_when_ten_local_and_new_jobs(self):
        previous_last_notified = self.user.last_notified_at
        _make_job(self.user, "ext-1", timezone.now())

        with patch("apps.notifications.tasks._is_around_ten_local", return_value=True), patch(
            "apps.notifications.tasks.send_web_push"
        ) as mock_send:
            sent = send_morning_notification_for_user(self.user)

        self.assertTrue(sent)
        mock_send.assert_called_once()
        self.user.refresh_from_db()
        self.assertGreater(self.user.last_notified_at, previous_last_notified)

    def test_no_send_when_ten_local_but_no_new_jobs(self):
        with patch("apps.notifications.tasks._is_around_ten_local", return_value=True), patch(
            "apps.notifications.tasks.send_web_push"
        ) as mock_send:
            sent = send_morning_notification_for_user(self.user)

        self.assertFalse(sent)
        mock_send.assert_not_called()

    def test_no_send_when_not_around_ten_local_even_with_new_jobs(self):
        _make_job(self.user, "ext-1", timezone.now())

        with patch("apps.notifications.tasks._is_around_ten_local", return_value=False), patch(
            "apps.notifications.tasks.send_web_push"
        ) as mock_send:
            sent = send_morning_notification_for_user(self.user)

        self.assertFalse(sent)
        mock_send.assert_not_called()

    def test_running_twice_in_the_same_window_does_not_double_send(self):
        _make_job(self.user, "ext-1", timezone.now())

        with patch("apps.notifications.tasks._is_around_ten_local", return_value=True), patch(
            "apps.notifications.tasks.send_web_push"
        ) as mock_send:
            first = send_morning_notification_for_user(self.user)
            self.user.refresh_from_db()
            second = send_morning_notification_for_user(self.user)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(mock_send.call_count, 1)

    def test_user_in_far_east_timezone_gets_notified_on_next_useful_run_without_double_send(self):
        # Simula un utente il cui giro utile (10:00 locali) cade prima del
        # batch europeo più recente non ancora annunciato: il meccanismo
        # basato su last_notified_at copre il caso senza codice speciale
        # (02-specifiche-tecniche-v3.md §5.5).
        far_east_user = User.objects.create_user(
            username="fareast@example.com",
            email="fareast@example.com",
            password="pw-FarEast-12345!",
            timezone="Pacific/Auckland",
        )
        far_east_user.last_notified_at = timezone.now() - timedelta(days=1)
        far_east_user.save(update_fields=["last_notified_at"])
        PushSubscription.objects.create(
            user=far_east_user,
            endpoint="https://push.example.com/far-east",
            p256dh_key="p256dh-key",
            auth_key="auth-key",
        )
        _make_job(far_east_user, "ext-fe-1", timezone.now())

        with patch("apps.notifications.tasks._is_around_ten_local", return_value=True), patch(
            "apps.notifications.tasks.send_web_push"
        ) as mock_send:
            first_run = send_morning_notification_for_user(far_east_user)
            far_east_user.refresh_from_db()
            second_run = send_morning_notification_for_user(far_east_user)

        self.assertTrue(first_run)
        self.assertFalse(second_run)
        self.assertEqual(mock_send.call_count, 1)


class InactivityNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="inactive@example.com",
            email="inactive@example.com",
            password="pw-Inactive-12345!",
        )
        PushSubscription.objects.create(
            user=self.user,
            endpoint="https://push.example.com/inactive",
            p256dh_key="p256dh-key",
            auth_key="auth-key",
        )

    def test_sends_when_older_than_seven_days(self):
        self.user.last_activity_reset = timezone.now() - timedelta(days=8)
        self.user.save(update_fields=["last_activity_reset"])

        with patch("apps.notifications.tasks.send_web_push") as mock_send:
            sent = send_inactivity_notification_for_user(self.user)

        self.assertTrue(sent)
        mock_send.assert_called_once()
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.last_inactivity_notified_at)

    def test_no_send_when_more_recent_than_seven_days(self):
        self.user.last_activity_reset = timezone.now() - timedelta(days=3)
        self.user.save(update_fields=["last_activity_reset"])

        with patch("apps.notifications.tasks.send_web_push") as mock_send:
            sent = send_inactivity_notification_for_user(self.user)

        self.assertFalse(sent)
        mock_send.assert_not_called()

    def test_does_not_resend_while_inactivity_persists_without_a_new_reset(self):
        self.user.last_activity_reset = timezone.now() - timedelta(days=8)
        self.user.save(update_fields=["last_activity_reset"])

        with patch("apps.notifications.tasks.send_web_push") as mock_send:
            first = send_inactivity_notification_for_user(self.user)
            self.user.refresh_from_db()
            second = send_inactivity_notification_for_user(self.user)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(mock_send.call_count, 1)


class PushSubscriptionApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="subscriber@example.com",
            email="subscriber@example.com",
            password="pw-Subscriber-12345!",
        )
        self.client.force_authenticate(self.user)

    def test_registers_a_new_subscription(self):
        payload = {
            "endpoint": "https://push.example.com/xyz",
            "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
        }

        response = self.client.post(
            "/api/notifications/push-subscriptions/", payload, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 1)

    def test_registering_the_same_endpoint_again_updates_instead_of_duplicating(self):
        payload = {
            "endpoint": "https://push.example.com/xyz",
            "keys": {"p256dh": "p256dh-key-1", "auth": "auth-key-1"},
        }
        self.client.post("/api/notifications/push-subscriptions/", payload, format="json")

        payload["keys"] = {"p256dh": "p256dh-key-2", "auth": "auth-key-2"}
        response = self.client.post(
            "/api/notifications/push-subscriptions/", payload, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 1)
        subscription = PushSubscription.objects.get(user=self.user)
        self.assertEqual(subscription.p256dh_key, "p256dh-key-2")
