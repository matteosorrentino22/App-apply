from datetime import timedelta
from unittest.mock import MagicMock, patch

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
            "endpoint": "https://fcm.googleapis.com/fcm/send/xyz",
            "keys": {"p256dh": "p256dh-key", "auth": "auth-key"},
        }

        response = self.client.post(
            "/api/notifications/push-subscriptions/", payload, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 1)

    def test_registering_the_same_endpoint_again_updates_instead_of_duplicating(self):
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/xyz",
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


class VapidPublicKeyApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="vapid@example.com", email="vapid@example.com", password="pw-Vapid-12345!"
        )
        self.client.force_authenticate(self.user)

    @patch("apps.notifications.views.settings.VAPID_PUBLIC_KEY", "test-public-key")
    def test_returns_the_configured_public_key(self):
        response = self.client.get("/api/notifications/vapid-public-key/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["public_key"], "test-public-key")

    def test_requires_authentication(self):
        self.client.force_authenticate(None)

        response = self.client.get("/api/notifications/vapid-public-key/")

        self.assertEqual(response.status_code, 401)


class PushSecurityTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pushsec@example.com", email="pushsec@example.com", password="pw-PushSec-12345!"
        )
        self.client.force_authenticate(self.user)

    def _subscribe(self, endpoint):
        return self.client.post(
            "/api/notifications/push-subscriptions/",
            {"endpoint": endpoint, "keys": {"p256dh": "k", "auth": "a"}},
            format="json",
        )

    def test_only_known_push_services_over_https_are_accepted(self):
        for endpoint in [
            "https://fcm.googleapis.com/fcm/send/abc",
            "https://updates.push.services.mozilla.com/wpush/v2/abc",
            "https://web.push.apple.com/abc",
            "https://wns2-par02p.notify.windows.com/w/?token=abc",
        ]:
            self.assertEqual(self._subscribe(endpoint).status_code, 201, endpoint)
        for endpoint in [
            "http://fcm.googleapis.com/fcm/send/abc",
            "https://fcm.googleapis.com:8443/fcm/send/abc",
            "https://169.254.169.254/latest",
            "https://web:8000/api/",
            "https://push.apple.com.evil.example/abc",
            "https://evilpush.apple.com/abc",
        ]:
            self.assertEqual(self._subscribe(endpoint).status_code, 400, endpoint)

    def test_at_most_ten_subscriptions_per_user_keeping_the_newest(self):
        for index in range(12):
            self._subscribe(f"https://fcm.googleapis.com/fcm/send/{index}")

        endpoints = set(PushSubscription.objects.filter(user=self.user).values_list("endpoint", flat=True))
        self.assertEqual(len(endpoints), 10)
        self.assertIn("https://fcm.googleapis.com/fcm/send/11", endpoints)
        self.assertNotIn("https://fcm.googleapis.com/fcm/send/0", endpoints)

    def test_webpush_is_called_with_a_timeout(self):
        from .services import send_web_push

        subscription = PushSubscription.objects.create(
            user=self.user, endpoint="https://fcm.googleapis.com/fcm/send/t", p256dh_key="k", auth_key="a"
        )
        with patch("apps.notifications.services.webpush") as mock_webpush:
            send_web_push(subscription, {"title": "t"})
        self.assertEqual(mock_webpush.call_args.kwargs["timeout"], 10)

    def test_gone_subscription_is_deleted(self):
        from pywebpush import WebPushException

        from .services import send_web_push

        subscription = PushSubscription.objects.create(
            user=self.user, endpoint="https://fcm.googleapis.com/fcm/send/gone", p256dh_key="k", auth_key="a"
        )
        error = WebPushException("gone", response=MagicMock(status_code=410))
        with patch("apps.notifications.services.webpush", side_effect=error):
            send_web_push(subscription, {"title": "t"})
        self.assertFalse(PushSubscription.objects.filter(pk=subscription.pk).exists())

    def test_an_error_does_not_stop_other_subscriptions_or_users(self):
        from .tasks import send_inactivity_notifications

        other = User.objects.create_user(
            username="pushsec2@example.com", email="pushsec2@example.com", password="pw-PushSec-12345!"
        )
        old = timezone.now() - timedelta(days=8)
        User.objects.filter(pk__in=[self.user.pk, other.pk]).update(last_activity_reset=old)
        for user, name in [(self.user, "a"), (self.user, "b"), (other, "c")]:
            PushSubscription.objects.create(
                user=user, endpoint=f"https://fcm.googleapis.com/fcm/send/{name}", p256dh_key="k", auth_key="a"
            )

        with patch(
            "apps.notifications.tasks.send_web_push", side_effect=[RuntimeError("500"), None, None]
        ) as mock_send, self.assertLogs("apps.notifications.tasks", level="WARNING"):
            send_inactivity_notifications()

        self.assertEqual(mock_send.call_count, 3)
        self.assertTrue(User.objects.get(pk=other.pk).last_inactivity_notified_at)

    def test_an_exception_for_one_user_does_not_stop_the_round(self):
        from .tasks import send_morning_notifications

        User.objects.create_user(username="pushsec3@example.com", email="pushsec3@example.com", password="pw-X-12345!aa")
        with patch(
            "apps.notifications.tasks.send_morning_notification_for_user", side_effect=[RuntimeError("tz"), None]
        ) as mock_user, self.assertLogs("apps.notifications.tasks", level="ERROR"):
            send_morning_notifications()
        self.assertEqual(mock_user.call_count, 2)
