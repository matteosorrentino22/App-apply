import datetime
import zoneinfo
from importlib import import_module
from unittest.mock import patch

from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.tokens import create_token
from apps.searches.models import SavedSearch

from . import tasks as tasks_module
from .models import DailyQuota, Job, RunLog
from .tasks import (
    CollectionDailyLimitReached,
    automatic_collection_due,
    run_automatic_collection,
    run_automatic_collection_for_user,
    run_automatic_collections,
    run_manual_collection_for_user,
)

User = get_user_model()
ROME = zoneinfo.ZoneInfo("Europe/Rome")

FAKE_SCORE = {
    "score": 7,
    "score_match": [],
    "score_gaps": [],
    "score_reasoning": "ok",
    "reasoning_summary": "ok",
}


def _user(email="s77@example.com", **extra):
    extra.setdefault("plan", "pro")
    return User.objects.create_user(username=email, email=email, password="pw-S77-12345!", **extra)


def _search(user):
    return SavedSearch.objects.create(user=user, keywords="PM", city="Roma", country="Italia", is_active=True)


def _offer(external_id):
    return {
        "external_id": external_id,
        "title": "Project Manager",
        "company": "Acme",
        "location": "Roma",
        "description": "Descrizione",
        "apply_url": f"https://linkedin.com/jobs/view/{external_id}",
        "date_published": timezone.now(),
    }


class _Source:
    def __init__(self, *groups):
        self.groups = groups

    def fetch_groups(self, searches, window_hours):
        return list(self.groups)


def _group(offers, error=None, label="job_role · Roma, Italia"):
    return {"label": label, "offers": offers, "error": error}


def _collect(user, function, groups=None):
    source = _Source(*(groups or [_group([_offer("a"), _offer("b")])]))
    with patch("apps.jobs.collection.get_job_source", return_value=source), patch(
        "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE
    ):
        return function(user)


def _at(year, month, day, hour, minute, zone=ROME):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=zone)


class AutomaticCollectionDueTests(TestCase):
    """Finestra oraria nel fuso dell'utente (B3), una volta per data locale."""

    def setUp(self):
        self.user = _user(auto_collection_enabled=True, auto_collection_time=datetime.time(7, 0))

    def test_due_from_the_chosen_time_once_per_local_day(self):
        self.assertIsNone(automatic_collection_due(self.user, _at(2026, 11, 16, 6, 50)))
        self.assertEqual(automatic_collection_due(self.user, _at(2026, 11, 16, 7, 5)), datetime.date(2026, 11, 16))
        self.user.auto_collection_last_local_date = datetime.date(2026, 11, 16)
        self.assertIsNone(automatic_collection_due(self.user, _at(2026, 11, 16, 23, 50)))
        self.assertEqual(automatic_collection_due(self.user, _at(2026, 11, 17, 7, 0)), datetime.date(2026, 11, 17))

    def test_uses_the_user_timezone(self):
        self.user.timezone = "America/New_York"
        utc = datetime.timezone.utc
        # 07:00 a New York (EST, UTC-5) = 12:00 UTC.
        self.assertIsNone(automatic_collection_due(self.user, datetime.datetime(2026, 11, 16, 11, 55, tzinfo=utc)))
        self.assertEqual(
            automatic_collection_due(self.user, datetime.datetime(2026, 11, 16, 12, 5, tzinfo=utc)),
            datetime.date(2026, 11, 16),
        )

    def test_invalid_timezone_falls_back_to_rome(self):
        self.user.timezone = "Non/Esiste"
        self.assertEqual(automatic_collection_due(self.user, _at(2026, 11, 16, 7, 5)), datetime.date(2026, 11, 16))

    def test_time_skipped_by_daylight_saving_runs_at_the_next_round(self):
        # 28/03/2027: a Roma le 02:00 diventano 03:00; le 02:30 non esistono.
        self.user.auto_collection_time = datetime.time(2, 30)
        utc = datetime.timezone.utc
        self.assertIsNone(automatic_collection_due(self.user, datetime.datetime(2027, 3, 28, 0, 55, tzinfo=utc)))
        self.assertEqual(
            automatic_collection_due(self.user, datetime.datetime(2027, 3, 28, 1, 0, tzinfo=utc)),  # 03:00 CEST
            datetime.date(2027, 3, 28),
        )

    def test_time_repeated_when_daylight_saving_ends_runs_once(self):
        # 25/10/2026: a Roma le 03:00 tornano 02:00; le 02:30 capitano due volte.
        self.user.auto_collection_time = datetime.time(2, 30)
        utc = datetime.timezone.utc
        first = automatic_collection_due(self.user, datetime.datetime(2026, 10, 25, 0, 35, tzinfo=utc))  # 02:35 CEST
        self.assertEqual(first, datetime.date(2026, 10, 25))
        self.user.auto_collection_last_local_date = first
        self.assertIsNone(automatic_collection_due(self.user, datetime.datetime(2026, 10, 25, 1, 35, tzinfo=utc)))  # 02:35 CET


class AutomaticCollectionDispatchTests(TestCase):
    def test_only_pro_users_with_the_option_on_are_started(self):
        pro_on = _user("on@example.com", auto_collection_enabled=True, auto_collection_time=datetime.time(0, 0))
        _user("off@example.com", auto_collection_enabled=False, auto_collection_time=datetime.time(0, 0))
        _user("free@example.com", plan="free", auto_collection_enabled=True, auto_collection_time=datetime.time(0, 0))
        with patch.object(tasks_module.run_automatic_collection, "delay") as delay:
            run_automatic_collections()
            run_automatic_collections()  # il giro dopo non la ripete
        delay.assert_called_once_with(pro_on.pk)
        pro_on.refresh_from_db()
        self.assertEqual(pro_on.auto_collection_last_local_date, timezone.now().astimezone(ROME).date())

    def test_a_failure_for_one_user_does_not_stop_the_others(self):
        first = _user("a@example.com", auto_collection_enabled=True, auto_collection_time=datetime.time(0, 0))
        second = _user("b@example.com", auto_collection_enabled=True, auto_collection_time=datetime.time(0, 0))
        started = []

        def delay(user_id):
            if user_id == first.pk:
                raise ConnectionError("broker giù")
            started.append(user_id)

        with patch.object(tasks_module.run_automatic_collection, "delay", side_effect=delay):
            run_automatic_collections()
        self.assertEqual(started, [second.pk])

    def test_the_worker_task_rechecks_plan_and_option(self):
        user = _user("downgraded@example.com", plan="free", auto_collection_enabled=True)
        _search(user)
        with patch("apps.jobs.collection.get_job_source") as source:
            self.assertEqual(run_automatic_collection(user.pk), {"skipped": "not_eligible"})
        source.assert_not_called()


class SharedDailyQuotaTests(TestCase):
    """Una raccolta al giorno, automatica o manuale (B1, B2 corretta)."""

    def setUp(self):
        self.user = _user(auto_collection_enabled=True)
        _search(self.user)

    def _quota(self):
        return DailyQuota.objects.get(user=self.user, date=timezone.localtime().date())

    def test_automatic_consumes_the_quota_and_blocks_the_manual_with_the_time(self):
        summary = _collect(self.user, run_automatic_collection_for_user)
        self.assertEqual(summary["collected"], 2)
        quota = self._quota()
        self.assertEqual(quota.collection_count, 1)
        self.assertIsNotNone(quota.collection_done_at)
        expected = quota.collection_done_at.astimezone(ROME).strftime("%H:%M")
        with self.assertRaises(CollectionDailyLimitReached) as raised:
            _collect(self.user, run_manual_collection_for_user)
        self.assertIn(f"già eseguita alle {expected}", str(raised.exception))

    def test_manual_before_the_time_skips_the_automatic(self):
        _collect(self.user, run_manual_collection_for_user)
        with patch("apps.jobs.collection.get_job_source") as source:
            self.assertEqual(run_automatic_collection_for_user(self.user), {"skipped": "daily_limit"})
        source.assert_not_called()
        log = RunLog.objects.filter(user=self.user, status=RunLog.Status.SKIPPED).get()
        self.assertIn("raccolta di oggi già eseguita", log.message)
        self.assertEqual(self._quota().collection_count, 1)

    def test_message_shows_the_date_when_the_users_today_differs(self):
        self.user.timezone = "Pacific/Auckland"
        done_at = timezone.now() - datetime.timedelta(days=1)
        message = tasks_module.collection_done_message(self.user, done_at)
        self.assertIn(" il ", message)
        self.assertIn(done_at.astimezone(zoneinfo.ZoneInfo("Pacific/Auckland")).strftime("%H:%M"), message)


class NoActiveSearchesTests(TestCase):
    def setUp(self):
        self.user = _user(auto_collection_enabled=True)

    def test_manual_without_active_searches_does_not_consume_the_quota(self):
        with patch("apps.jobs.collection.get_job_source") as source:
            run_manual_collection_for_user(self.user)
            run_manual_collection_for_user(self.user)
        source.assert_not_called()
        self.assertFalse(DailyQuota.objects.filter(user=self.user, collection_count__gt=0).exists())

    def test_automatic_without_active_searches_is_skipped_without_quota(self):
        self.assertEqual(run_automatic_collection_for_user(self.user), {"skipped": "no_searches"})
        self.assertFalse(DailyQuota.objects.filter(user=self.user, collection_count__gt=0).exists())
        self.assertEqual(RunLog.objects.get(user=self.user).status, RunLog.Status.SKIPPED)


class QuotaRefundTests(TestCase):
    def setUp(self):
        self.user = _user()
        _search(self.user)

    def test_refund_goes_back_to_the_reserved_row_even_after_midnight(self):
        # Riservata il 16 alle 23:55, fallita dopo mezzanotte: torna sulla
        # riga del 16, non su quella del 17 (difetto corretto nello Sprint 77).
        next_day = DailyQuota.objects.create(user=self.user, date=datetime.date(2026, 11, 17), collection_count=1)
        with patch.object(tasks_module, "_today_europe_rome", return_value=datetime.date(2026, 11, 16)):
            result = _collect(self.user, run_automatic_collection_for_user, [_group([], error=RuntimeError("giù"))])
        self.assertEqual(result, {"failed": True})
        reserved = DailyQuota.objects.get(user=self.user, date=datetime.date(2026, 11, 16))
        self.assertEqual(reserved.collection_count, 0)
        self.assertIsNone(reserved.collection_done_at)
        next_day.refresh_from_db()
        self.assertEqual(next_day.collection_count, 1)

    def test_manual_refund_uses_the_reserved_row(self):
        with patch.object(tasks_module, "_today_europe_rome", return_value=datetime.date(2026, 11, 16)):
            with self.assertRaises(tasks_module.ManualCollectionFailed):
                _collect(self.user, run_manual_collection_for_user, [_group([], error=RuntimeError("giù"))])
        self.assertEqual(DailyQuota.objects.get(user=self.user, date=datetime.date(2026, 11, 16)).collection_count, 0)

    def test_partial_failure_after_paid_calls_keeps_the_quota(self):
        groups = [_group([_offer("ok")]), _group([], error=RuntimeError("403"), label="company · Zurich")]
        summary = _collect(self.user, run_automatic_collection_for_user, groups)
        self.assertEqual(summary["groups_failed"], 1)
        self.assertEqual(DailyQuota.objects.get(user=self.user).collection_count, 1)


class EndOfCollectionNotificationTests(TestCase):
    def setUp(self):
        self.user = _user()
        _search(self.user)

    def test_push_after_an_automatic_collection_with_new_jobs(self):
        with patch("apps.notifications.tasks.send_new_jobs_notification") as push:
            _collect(self.user, run_automatic_collection_for_user)
        push.assert_called_once()

    def test_no_push_without_new_jobs(self):
        Job.objects.create(
            user=self.user, source=Job.Source.LINKEDIN, external_id="a", title="T", company="C", location="L",
            description="D",
        )
        with patch("apps.notifications.tasks.send_new_jobs_notification") as push:
            _collect(self.user, run_automatic_collection_for_user, [_group([_offer("a")])])
        push.assert_not_called()

    def test_no_push_after_a_manual_collection(self):
        with patch("apps.notifications.tasks.send_new_jobs_notification") as push:
            _collect(self.user, run_manual_collection_for_user)
        push.assert_not_called()


class AutomaticCollectionSettingsApiTests(APITestCase):
    def _auth(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {create_token(user)}")
        from apps.accounts.legal import record_acceptances

        record_acceptances(user)

    def test_free_users_cannot_turn_it_on(self):
        user = _user("free-api@example.com", plan="free")
        self._auth(user)
        response = self.client.patch("/api/accounts/me/", {"auto_collection_enabled": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("auto_collection_enabled", response.json())

    def test_pro_turns_it_on_with_a_quarter_hour_time(self):
        user = _user("pro-api@example.com")
        self._auth(user)
        response = self.client.patch(
            "/api/accounts/me/", {"auto_collection_enabled": True, "auto_collection_time": "08:15"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["auto_collection_time"], "08:15")
        self.assertTrue(response.json()["auto_collection_enabled"])
        bad = self.client.patch("/api/accounts/me/", {"auto_collection_time": "08:10"}, format="json")
        self.assertEqual(bad.status_code, 400)

    def test_a_time_already_passed_today_starts_tomorrow(self):
        user = _user("pro-late@example.com", timezone="Europe/Rome")
        self._auth(user)
        local_now = timezone.now().astimezone(ROME)
        past = (local_now - datetime.timedelta(minutes=30)).replace(second=0, microsecond=0)
        past = past.replace(minute=past.minute - past.minute % 15)
        if past.date() != local_now.date():
            self.skipTest("troppo vicino alla mezzanotte")
        self.client.patch(
            "/api/accounts/me/", {"auto_collection_enabled": True, "auto_collection_time": past.strftime("%H:%M")},
            format="json",
        )
        user.refresh_from_db()
        self.assertEqual(user.auto_collection_last_local_date, local_now.date())
        self.assertIsNone(automatic_collection_due(user))

    def test_usage_reports_the_time_of_todays_collection(self):
        user = _user("usage@example.com")
        _search(user)
        self._auth(user)
        _collect(user, run_manual_collection_for_user)
        collection = self.client.get("/api/accounts/usage/").json()["actions"]["collection"]
        self.assertEqual((collection["used"], collection["limit"], collection["next_charge"]), (1, 1, "blocked"))
        self.assertIsNotNone(collection["done_at"])

    def test_409_message_in_english(self):
        user = _user("en-409@example.com")
        _search(user)
        self._auth(user)
        _collect(user, run_manual_collection_for_user)
        response = self.client.post("/api/jobs/collect/", HTTP_ACCEPT_LANGUAGE="en")
        self.assertEqual(response.status_code, 409)
        self.assertIn("Today's collection already ran at", response.json()["detail"])

    def test_export_contains_the_new_settings(self):
        import json
        import zipfile

        from apps.accounts.account_data import build_export

        user = _user("export@example.com", auto_collection_enabled=True)
        with zipfile.ZipFile(build_export(user)) as archive:
            data = json.loads(archive.read("dati.json"))
        self.assertTrue(data["account"]["auto_collection_enabled"])
        self.assertEqual(data["account"]["auto_collection_time"], "07:00:00")


class ExistingProDataMigrationTests(TestCase):
    def test_existing_pro_keep_the_automatic_collection_off(self):
        # Sprint 81: la migrazione 0012 non attiva più l'automatica ai Pro
        # esistenti (la accendono loro, se vogliono).
        pro = _user("old-pro@example.com", timezone="America/New_York")
        free = _user("old-free@example.com", plan="free")
        migration = import_module("apps.accounts.migrations.0012_enable_auto_collection_for_pro")
        migration.leave_automatic_collection_off(django_apps, None)
        pro.refresh_from_db()
        free.refresh_from_db()
        self.assertFalse(pro.auto_collection_enabled)
        self.assertIsNone(pro.auto_collection_last_local_date)
        self.assertFalse(free.auto_collection_enabled)
