import importlib
from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from io import StringIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests
from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.cv.models import CVDocument, CVDraft
from apps.searches.models import SavedSearch

from .collection import CollectionFailed, collect_jobs_for_user
from .import_service import ImportDuplicate, ImportRejected, import_job_from_url
from .list_service import list_jobs
from .manual_job_service import ManualJobFailed, create_manual_job
from .models import DailyQuota, Job, RunLog
from .scoring import MAX_SCORING_FAILURES, score_job
from .sources.apify_linkedin import ApifyLinkedInSource
from .tasks import (
    CollectionAlreadyInProgress,
    ManualCollectionFailed,
    run_manual_collection_for_user,
    run_automatic_collection_for_user,
)

User = get_user_model()

FAKE_SCORE = {
    "score": 7,
    "score_match": [],
    "score_gaps": [],
    "score_reasoning": "Ok.",
    "language_check": {"required": False, "language": "", "international_exception": False},
}


def _user(email="s68@example.com", **extra):
    return User.objects.create_user(username=email, email=email, password="pw-S68-12345!", **extra)


def _offer(external_id, **overrides):
    offer = {
        "external_id": external_id,
        "title": "Project Manager",
        "company": "Acme",
        "location": "Roma",
        "description": "Descrizione.",
        "apply_url": "https://linkedin.com/jobs/view/1",
        "published_at": None,
        "salary": "",
    }
    offer.update(overrides)
    return offer


def _group(offers, label="job_role · Roma, Italia", error=None):
    return {"label": label, "offers": offers, "error": error}


def _source(*groups):
    return MagicMock(fetch_groups=MagicMock(return_value=list(groups)))


def _job(user, external_id, **fields):
    return Job.objects.create(
        user=user,
        external_id=external_id,
        title=fields.pop("title", "PM"),
        company=fields.pop("company", "Acme"),
        location=fields.pop("location", "Roma"),
        description="D",
        **fields,
    )


def _add_discarded_column():
    # La colonna esiste solo prima della migrazione jobs/0019: nei test la
    # si ricrea dentro la transazione del test (DDL transazionale su
    # PostgreSQL, annullato a fine test).
    with connection.cursor() as cursor:
        cursor.execute(
            "ALTER TABLE jobs_job ADD COLUMN discarded_by_cap boolean NOT NULL DEFAULT false"
        )


def _mark_discarded(*jobs):
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE jobs_job SET discarded_by_cap = true WHERE id = ANY(%s)", [[j.pk for j in jobs]]
        )


class DeleteDiscardedByCapJobsCommandTests(TestCase):
    def setUp(self):
        self.user = _user()
        _add_discarded_column()
        self.kept = _job(self.user, "keep")
        self.discarded = _job(self.user, "gone-1")
        self.discarded_with_docs = _job(self.user, "gone-2", status=Job.Status.APPLICATION_DONE)
        _mark_discarded(self.discarded, self.discarded_with_docs)
        self.cv = CVDocument.objects.create(
            job=self.discarded_with_docs, user=self.user, html_source="<p/>", generation_type="manual"
        )
        self.cv.pdf_file.save("x.pdf", ContentFile(b"%PDF-1.4"), save=True)
        CVDraft.objects.create(job=self.discarded_with_docs, user=self.user)

    def _run(self, *args):
        out = StringIO()
        call_command("delete_discarded_by_cap_jobs", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_is_the_default_and_reports_counts(self):
        output = self._run()

        self.assertIn("Job con discarded_by_cap=True: 2", output)
        self.assertIn("stato=application_done", output)
        self.assertIn("CV (CVDocument): 1 (su 1 job)", output)
        self.assertIn("bozze CV: 1 (su 1 job)", output)
        self.assertIn("Dry-run", output)
        self.assertEqual(Job.objects.filter(user=self.user).count(), 3)

    def test_confirm_deletes_marked_jobs_with_documents_and_files(self):
        storage, name = self.cv.pdf_file.storage, self.cv.pdf_file.name
        self.assertTrue(storage.exists(name))

        with self.captureOnCommitCallbacks(execute=True):
            self._run("--confirm")

        self.assertEqual(list(Job.objects.filter(user=self.user)), [self.kept])
        self.assertFalse(CVDocument.objects.exists())
        self.assertFalse(CVDraft.objects.exists())
        self.assertFalse(storage.exists(name))
        self.assertIn("Job con discarded_by_cap=True: 0", self._run())

    def test_removal_migration_refuses_while_marked_rows_exist(self):
        migration = importlib.import_module("apps.jobs.migrations.0019_remove_job_discarded_by_cap")
        schema_editor = SimpleNamespace(connection=connection)

        with self.assertRaisesRegex(RuntimeError, "2 job con discarded_by_cap=True"):
            migration.ensure_no_discarded_jobs(django_apps, schema_editor)

        self._run("--confirm")
        migration.ensure_no_discarded_jobs(django_apps, schema_editor)


class DeleteDiscardedWithoutColumnTests(TestCase):
    def test_nothing_to_do_once_the_column_is_gone(self):
        out = StringIO()
        call_command("delete_discarded_by_cap_jobs", "--confirm", stdout=out)
        self.assertIn("già rimossa", out.getvalue())


class RescaleLegacyScoresCommandTests(TestCase):
    def setUp(self):
        self.user = _user()
        before = datetime(2026, 9, 20, tzinfo=dt_timezone.utc)
        after = datetime(2026, 9, 25, tzinfo=dt_timezone.utc)
        self.legacy = [_job(self.user, f"old-{s}", score=s, date_scored=before) for s in range(1, 6)]
        self.recent = _job(self.user, "new-3", score=3, date_scored=after)
        self.unscored = _job(self.user, "none")
        self.anomalous = _job(self.user, "odd", score=8, date_scored=before)

    def _run(self, *args):
        out = StringIO()
        call_command("rescale_legacy_scores", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_changes_nothing(self):
        output = self._run()
        self.assertIn("Da riscalare: 5", output)
        self.assertIn("Punteggi > 5 prima del taglio", output)
        self.assertEqual(sorted(Job.objects.filter(score__isnull=False).values_list("score", flat=True)), [1, 2, 3, 3, 4, 5, 8])

    def test_confirm_doubles_legacy_scores_once(self):
        self._run("--confirm")
        self._run("--confirm")

        for job, expected in zip(self.legacy, (2, 4, 6, 8, 10)):
            job.refresh_from_db()
            self.assertEqual(job.score, expected)
            self.assertTrue(job.score_rescaled_from_legacy)
        for job, expected in ((self.recent, 3), (self.anomalous, 8)):
            job.refresh_from_db()
            self.assertEqual(job.score, expected)
            self.assertFalse(job.score_rescaled_from_legacy)
        self.unscored.refresh_from_db()
        self.assertIsNone(self.unscored.score)
        self.assertIn("Da riscalare: 0", self._run())

    def test_custom_cutoff(self):
        self._run("--confirm", "--before", "2026-09-26T00:00:00+00:00")
        self.recent.refresh_from_db()
        self.assertEqual(self.recent.score, 6)


class RetryUnscoredJobsTests(TestCase):
    def setUp(self):
        self.user = _user()

    def test_failed_scoring_increments_the_failure_counter(self):
        job = _job(self.user, "x")
        with patch("apps.jobs.scoring.score_job_with_claude", side_effect=RuntimeError("bedrock")):
            score_job(job)
            score_job(job)
        job.refresh_from_db()
        self.assertEqual(job.scoring_failures, 2)

    def test_collection_retries_unscored_jobs_until_the_limit(self):
        # Sprint 77: i ritenti avvengono a ogni raccolta; senza ricerche
        # attive la manuale non consuma la quota e ritenta comunque.
        retryable = _job(self.user, "retry", scoring_failures=MAX_SCORING_FAILURES - 1)
        exhausted = _job(self.user, "exhausted", scoring_failures=MAX_SCORING_FAILURES)
        other_user_job = _job(_user("other@example.com"), "other")

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE) as mock_score:
            summary = run_manual_collection_for_user(self.user)

        self.assertEqual([call.args[0].pk for call in mock_score.call_args_list], [retryable.pk])
        self.assertEqual(summary["retried"], 1)
        self.assertEqual(summary["retried_scored"], 1)
        retryable.refresh_from_db()
        exhausted.refresh_from_db()
        other_user_job.refresh_from_db()
        self.assertEqual(retryable.score, 7)
        self.assertIsNone(exhausted.score)
        self.assertIsNone(other_user_job.score)
        log = RunLog.objects.get(user=self.user, task_type=RunLog.TaskType.COLLECTION)
        self.assertIn("ritentati=1 ritentati_scorati=1", log.message)

    def test_a_job_failing_at_every_collection_stops_being_retried(self):
        job = _job(self.user, "always-fails")
        with patch("apps.jobs.scoring.score_job_with_claude", side_effect=RuntimeError("x")) as mock_score:
            for _ in range(MAX_SCORING_FAILURES + 2):
                run_manual_collection_for_user(self.user)
        self.assertEqual(mock_score.call_count, MAX_SCORING_FAILURES)
        job.refresh_from_db()
        self.assertEqual(job.scoring_failures, MAX_SCORING_FAILURES)

    def test_manual_command_dry_run_and_ignore_limit(self):
        job = _job(self.user, "exhausted", scoring_failures=MAX_SCORING_FAILURES)
        out = StringIO()
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE) as mock_score:
            call_command("retry_unscored_jobs", stdout=out)
            call_command("retry_unscored_jobs", "--ignore-limit", "--dry-run", stdout=out)
            mock_score.assert_not_called()
            call_command("retry_unscored_jobs", "--ignore-limit", "--user-id", str(self.user.pk), stdout=out)
        self.assertIn("Job senza punteggio da ritentare: 0", out.getvalue())
        self.assertIn(f"job {job.pk}", out.getvalue())
        job.refresh_from_db()
        self.assertEqual(job.score, 7)


class MatchedSavedSearchTests(TestCase):
    def setUp(self):
        self.user = _user()
        self.search = SavedSearch.objects.create(
            user=self.user, keywords="PM", city="Roma", country="Italia", is_active=True
        )

    def test_collection_saves_the_search_reference(self):
        offer = _offer("a", matched_search="PM - Roma, Italia", saved_search_id=self.search.pk)
        foreign = _offer("b", saved_search_id=999999)
        with patch("apps.jobs.collection.get_job_source", return_value=_source(_group([offer, foreign]))):
            collect_jobs_for_user(self.user)

        self.assertEqual(Job.objects.get(external_id="a").matched_saved_search, self.search)
        self.assertIsNone(Job.objects.get(external_id="b").matched_saved_search)

    def test_filter_keeps_jobs_after_the_search_is_edited(self):
        job = _job(self.user, "a", matched_search="PM - Roma, Italia", matched_saved_search=self.search)
        SavedSearch.objects.filter(pk=self.search.pk).update(keywords="Product Manager", city="Milano")

        result = list(list_jobs(self.user, "main", search_ids=[str(self.search.pk)]))
        self.assertEqual(result, [job])

    def test_job_of_another_search_with_same_label_is_not_mixed_in(self):
        other = SavedSearch.objects.create(user=self.user, keywords="PM", city="Roma", country="Italia")
        job = _job(self.user, "a", matched_search="PM - Roma, Italia", matched_saved_search=self.search)

        self.assertEqual(list(list_jobs(self.user, "main", search_ids=[str(other.pk)])), [])
        self.assertEqual(list(list_jobs(self.user, "main", search_ids=[str(self.search.pk)])), [job])

    def test_legacy_job_without_reference_falls_back_to_the_label(self):
        legacy = _job(self.user, "a", matched_search="PM - Roma, Italia")
        imported = _job(self.user, "b", origin=Job.Origin.COLLECTED)

        self.assertEqual(list(list_jobs(self.user, "main", search_ids=[str(self.search.pk)])), [legacy])
        self.assertEqual(list(list_jobs(self.user, "main", search_ids=["none"])), [imported])

    def test_backfill_assigns_only_unambiguous_matches(self):
        company_a = SavedSearch.objects.create(
            user=self.user, search_type="company", keywords="UBS", city="Zurich", country="CH"
        )
        SavedSearch.objects.create(
            user=self.user, search_type="company", keywords="ubs", city="Basel", country="CH"
        )
        SavedSearch.objects.create(
            user=self.user, search_type="company", keywords="Acme", city="Roma", country="Italia"
        )
        role_job = _job(self.user, "1", matched_search="PM - Roma, Italia")
        ambiguous = _job(self.user, "2", matched_search="UBS")
        company_job = _job(self.user, "3", matched_search="ACME")
        orphan = _job(self.user, "4", matched_search="Gone - Torino, Italia")

        migration = importlib.import_module("apps.jobs.migrations.0018_backfill_matched_saved_search")
        migration.backfill(django_apps, None)

        for job in (role_job, ambiguous, company_job, orphan):
            job.refresh_from_db()
        self.assertEqual(role_job.matched_saved_search, self.search)
        self.assertIsNone(ambiguous.matched_saved_search)
        self.assertEqual(company_job.matched_saved_search.keywords, "Acme")
        self.assertIsNone(orphan.matched_saved_search)
        self.assertNotEqual(company_a.pk, None)

    def test_deleting_the_search_keeps_the_job(self):
        job = _job(self.user, "a", matched_search="PM - Roma, Italia", matched_saved_search=self.search)
        self.search.delete()
        job.refresh_from_db()
        self.assertIsNone(job.matched_saved_search)
        self.assertEqual(job.matched_search, "PM - Roma, Italia")


class ApifyGroupIsolationTests(TestCase):
    def setUp(self):
        self.user = _user()
        self.role_a = SavedSearch.objects.create(user=self.user, keywords="PM", city="Roma", country="Italia")
        self.role_b = SavedSearch.objects.create(user=self.user, keywords="BA", city="Roma", country="Italia")
        self.company = SavedSearch.objects.create(
            user=self.user, search_type="company", keywords="UBS", city="Zurich", country="Switzerland"
        )

    @staticmethod
    def _response(items):
        response = MagicMock()
        response.json.return_value = items
        return response

    def test_a_failing_group_does_not_lose_the_others(self):
        items = [
            {"id": 1, "title": "t", "companyName": "c", "location": "l", "description": "d",
             "jobUrl": "https://x", "searchString": "BA - Roma, Italia"},
            {"id": 2, "title": "t", "companyName": "c", "location": "l", "description": "d",
             "jobUrl": "https://x", "searchString": "Other - Roma, Italia"},
        ]

        def fake_post(url, headers, json, timeout):
            if "companyInclude" in json:
                raise requests.exceptions.HTTPError("403 credito esaurito")
            return self._response(items)

        with patch("apps.jobs.sources.apify_linkedin.requests.post", side_effect=fake_post):
            groups = ApifyLinkedInSource().fetch_groups([self.role_a, self.role_b, self.company], 24)

        by_label = {group["label"]: group for group in groups}
        role_group = by_label["job_role · Roma, Italia"]
        self.assertIsNone(role_group["error"])
        self.assertEqual([o["saved_search_id"] for o in role_group["offers"]], [self.role_b.pk, None])
        self.assertIsInstance(by_label["company · Zurich, Switzerland"]["error"], requests.exceptions.HTTPError)

    def test_company_offers_are_attributed_to_the_company_search(self):
        item = {"id": 3, "title": "t", "companyName": "ubs", "location": "l", "description": "d", "jobUrl": "https://x"}
        with patch("apps.jobs.sources.apify_linkedin.requests.post", return_value=self._response([item])):
            [group] = ApifyLinkedInSource().fetch_groups([self.company], 24)
        self.assertEqual(group["offers"][0]["saved_search_id"], self.company.pk)

    def test_collection_and_run_log_report_each_group(self):
        source = _source(
            _group([_offer("ok-1"), _offer("ok-2")]),
            _group([], label="company · Zurich, Switzerland", error=RuntimeError("403")),
        )
        SavedSearch.objects.filter(user=self.user).update(is_active=True)
        with patch("apps.jobs.collection.get_job_source", return_value=source), patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE
        ):
            summary = run_manual_collection_for_user(self.user)

        self.assertEqual(summary["collected"], 2)
        self.assertEqual(summary["groups_failed"], 1)
        log = RunLog.objects.get(user=self.user, task_type=RunLog.TaskType.COLLECTION)
        self.assertEqual(log.status, RunLog.Status.FAILURE)
        self.assertIn("gruppi=2 gruppi_falliti=1", log.message)
        self.assertIn("gruppo job_role · Roma, Italia: ok, offerte=2", log.message)
        self.assertIn("gruppo company · Zurich, Switzerland: ERRORE RuntimeError: 403", log.message)

    def test_all_groups_failing_fails_the_collection_and_refunds_manual_quota(self):
        SavedSearch.objects.filter(user=self.user).update(is_active=True)
        source = _source(_group([], error=RuntimeError("down")))
        with patch("apps.jobs.collection.get_job_source", return_value=source):
            with self.assertRaises(CollectionFailed):
                collect_jobs_for_user(self.user)
            with self.assertRaises(ManualCollectionFailed):
                run_manual_collection_for_user(self.user)
        self.assertEqual(DailyQuota.objects.get(user=self.user).collection_count, 0)


class DiscardedOffersCountTests(TestCase):
    def test_discarded_offers_are_counted_in_the_run_log(self):
        user = _user()
        SavedSearch.objects.create(user=user, keywords="PM", city="Roma", country="Italia", is_active=True)
        _job(user, "already-there", source=Job.Source.LINKEDIN)
        offers = [
            _offer("new"),
            _offer("missing", company=""),
            _offer("long", title="x" * 300),
            _offer("already-there"),
            _offer("new"),
        ]
        with patch("apps.jobs.collection.get_job_source", return_value=_source(_group(offers))), patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE
        ):
            run_manual_collection_for_user(user)

        log = RunLog.objects.get(user=user, task_type=RunLog.TaskType.COLLECTION)
        self.assertIn("raccolti=1", log.message)
        self.assertIn("scartati_campi_mancanti=1 scartati_troppo_lunghi=1 scartati_duplicati=2", log.message)


class SharedCollectionGuardTests(TestCase):
    def setUp(self):
        self.user = _user()
        SavedSearch.objects.create(user=self.user, keywords="PM", city="Roma", country="Italia", is_active=True)

    def test_automatic_collection_skips_a_user_with_a_manual_collection_in_progress(self):
        User.objects.filter(pk=self.user.pk).update(
            collection_in_progress=True, collection_started_at=timezone.now()
        )
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            summary = run_automatic_collection_for_user(self.user)

        self.assertEqual(summary, {"skipped": "in_progress"})
        mock_get_source.assert_not_called()
        log = RunLog.objects.get(user=self.user)
        self.assertEqual(log.status, RunLog.Status.SKIPPED)
        self.user.refresh_from_db()
        self.assertTrue(self.user.collection_in_progress)

    def test_stale_lock_does_not_skip_the_automatic_collection(self):
        User.objects.filter(pk=self.user.pk).update(
            collection_in_progress=True, collection_started_at=timezone.now() - timedelta(hours=3)
        )
        with patch("apps.jobs.collection.get_job_source", return_value=_source(_group([]))):
            summary = run_automatic_collection_for_user(self.user)
        self.assertNotIn("skipped", summary)

    def test_manual_collection_is_rejected_while_the_automatic_collection_runs(self):
        seen = {}

        def fetch_groups(searches, window_hours):
            seen["locked"] = User.objects.get(pk=self.user.pk).collection_in_progress
            try:
                run_manual_collection_for_user(self.user)
            except CollectionAlreadyInProgress:
                seen["manual_rejected"] = True
            return [_group([])]

        with patch(
            "apps.jobs.collection.get_job_source", return_value=MagicMock(fetch_groups=fetch_groups)
        ):
            run_automatic_collection_for_user(self.user)

        self.assertEqual(seen, {"locked": True, "manual_rejected": True})
        self.user.refresh_from_db()
        self.assertFalse(self.user.collection_in_progress)
        # La quota è quella consumata dall'automatica (una sola, Sprint 77).
        self.assertEqual(DailyQuota.objects.get(user=self.user).collection_count, 1)

    def test_lock_is_released_and_quota_refunded_when_the_automatic_collection_fails(self):
        with patch("apps.jobs.collection.get_job_source", side_effect=ConnectionError("x")):
            self.assertEqual(run_automatic_collection_for_user(self.user), {"failed": True})
        self.user.refresh_from_db()
        self.assertFalse(self.user.collection_in_progress)
        self.assertEqual(DailyQuota.objects.get(user=self.user).collection_count, 0)
        self.assertEqual(RunLog.objects.get(user=self.user).status, RunLog.Status.FAILURE)


class QuotaAdminActionsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin68@example.com", email="admin68@example.com", password="pw-Admin-12345!"
        )
        self.client.force_login(self.admin)
        self.user = _user()
        today = timezone.localtime(timezone.now()).date()
        self.today = DailyQuota.objects.create(
            user=self.user, date=today, collection_count=1, manual_cv_count=1, import_count=2
        )
        self.yesterday = DailyQuota.objects.create(
            user=self.user, date=today - timedelta(days=1), collection_count=1
        )

    def _user_action(self, action):
        return self.client.post(
            reverse("admin:accounts_user_changelist"),
            {"action": action, "_selected_action": [self.user.pk]},
        )

    def test_reset_today_collection_quota_only_touches_today_collection_counter(self):
        response = self._user_action("reset_today_collection_quota")
        self.assertEqual(response.status_code, 302)
        self.today.refresh_from_db()
        self.yesterday.refresh_from_db()
        self.assertEqual((self.today.collection_count, self.today.manual_cv_count), (0, 1))
        self.assertEqual(self.yesterday.collection_count, 1)

    def test_reset_today_all_quotas(self):
        self._user_action("reset_today_all_quotas")
        self.today.refresh_from_db()
        self.assertEqual(
            (self.today.collection_count, self.today.manual_cv_count, self.today.import_count), (0, 0, 0)
        )

    def test_reset_selected_daily_quota_rows(self):
        self.client.post(
            reverse("admin:jobs_dailyquota_changelist"),
            {"action": "reset_selected_daily_quotas", "_selected_action": [self.yesterday.pk]},
        )
        self.yesterday.refresh_from_db()
        self.today.refresh_from_db()
        self.assertEqual(self.yesterday.collection_count, 0)
        self.assertEqual(self.today.collection_count, 1)

    def test_new_admin_pages_render(self):
        job = _job(self.user, "a")
        CVDraft.objects.create(job=job, user=self.user)
        for name in (
            "cv_cvdraft",
            "cv_coverletterdocument",
            "cv_coverletterdraft",
            "cv_referralmessagedocument",
            "jobs_jobfilterpreset",
            "jobs_dailyquota",
            "jobs_job",
            "accounts_user",
        ):
            response = self.client.get(reverse(f"admin:{name}_changelist"))
            self.assertEqual(response.status_code, 200, name)
        response = self.client.get(reverse("admin:accounts_user_change", args=[self.user.pk]))
        self.assertContains(response, "collection_in_progress")
        response = self.client.get(reverse("admin:cv_cvdraft_change", args=[job.cv_draft.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="content_json"')


VALID_URL = "https://www.linkedin.com/jobs/view/1234567890"


def _import_offer(**overrides):
    offer = {
        "external_id": "1234567890",
        "title": "Site Supervisor",
        "company": "Acme",
        "location": "Kuwait City",
        "description": "D.",
        "apply_url": VALID_URL,
        "published_at": None,
        "salary": "",
    }
    offer.update(overrides)
    return offer


@override_settings(PRICE_IMPORT_EXTRA=Decimal("0.50"))
class ImportRobustnessTests(TestCase):
    def setUp(self):
        self.user = _user(plan=User.Plan.PRO)

    def _quota(self):
        return DailyQuota.objects.get(user=self.user).import_count

    def test_concurrent_import_hitting_the_unique_constraint_is_a_duplicate_with_refund(self):
        def fetch_by_url(url):
            # Un'altra richiesta inserisce lo stesso job tra il controllo
            # duplicati e la creazione.
            _job(self.user, "1234567890", source=Job.Source.LINKEDIN, origin=Job.Origin.IMPORTED)
            return _import_offer()

        with patch(
            "apps.jobs.import_service.get_job_source",
            return_value=MagicMock(fetch_by_url=fetch_by_url),
        ):
            with self.assertRaises(ImportDuplicate):
                import_job_from_url(self.user, VALID_URL)

        self.assertEqual(Job.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self._quota(), 0)

    def test_field_over_max_length_is_rejected_with_refund(self):
        with patch(
            "apps.jobs.import_service.get_job_source",
            return_value=MagicMock(fetch_by_url=MagicMock(return_value=_import_offer(title="x" * 256))),
        ):
            with self.assertRaises(ImportRejected):
                import_job_from_url(self.user, VALID_URL)
        self.assertFalse(Job.objects.filter(user=self.user).exists())
        self.assertEqual(self._quota(), 0)


@override_settings(PRICE_MANUAL_JOB_EXTRA=Decimal("0.50"))
class ManualJobRefundTests(APITestCase):
    def setUp(self):
        self.user = _user(extra_credit=Decimal("1.00"))
        self.data = {
            "title": "PM",
            "company": "Acme",
            "location": "Roma",
            "description": "D",
            "published_at": timezone.now(),
        }

    def test_failure_after_the_reservation_refunds_the_quota(self):
        with patch("apps.jobs.manual_job_service.Job.objects.create", side_effect=RuntimeError("db")):
            with self.assertRaises(ManualJobFailed):
                create_manual_job(self.user, self.data)
        self.assertEqual(DailyQuota.objects.get(user=self.user).manual_job_count, 0)

    def test_failure_in_credit_mode_refunds_the_credit(self):
        DailyQuota.objects.create(
            user=self.user, date=timezone.localtime(timezone.now()).date(), manual_job_count=3
        )
        with patch("apps.jobs.manual_job_service.Job.objects.create", side_effect=RuntimeError("db")):
            with self.assertRaises(ManualJobFailed):
                create_manual_job(self.user, self.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.extra_credit, Decimal("1.00"))

    def test_api_returns_502(self):
        self.client.force_authenticate(self.user)
        with patch("apps.jobs.manual_job_service.Job.objects.create", side_effect=RuntimeError("db")):
            response = self.client.post("/api/jobs/manual/", {**self.data, "published_at": "2026-11-14T10:00"})
        self.assertEqual(response.status_code, 502)

    def test_failed_scoring_keeps_the_job_and_the_quota_and_is_retried_later(self):
        with patch("apps.jobs.scoring.score_job_with_claude", side_effect=RuntimeError("bedrock")):
            job = create_manual_job(self.user, self.data)
        job.refresh_from_db()
        self.assertIsNone(job.score)
        self.assertEqual(job.scoring_failures, 1)
        self.assertEqual(DailyQuota.objects.get(user=self.user).manual_job_count, 1)

        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE):
            run_manual_collection_for_user(self.user)
        job.refresh_from_db()
        self.assertEqual(job.score, 7)


class ScoringPromptTests(TestCase):
    def test_job_location_is_passed_to_the_model(self):
        job = _job(_user(), "a", location="Zurigo, Svizzera")
        with patch("apps.jobs.ai_scoring.call_claude_structured", return_value=FAKE_SCORE) as mock_call:
            score_job(job)
        self.assertIn("Località: Zurigo, Svizzera", mock_call.call_args.kwargs["user_content"])


class SearchTypeChangePlanLimitTests(APITestCase):
    def _setup(self, plan):
        self.user = _user(plan=plan)
        self.client.force_authenticate(self.user)
        self.role = SavedSearch.objects.create(
            user=self.user, keywords="PM", city="Roma", country="Italia", is_active=True
        )
        self.company = SavedSearch.objects.create(
            user=self.user, search_type="company", keywords="UBS", city="Roma", country="Italia", is_active=True
        )

    def test_free_type_change_of_an_active_search_deactivates_the_other_of_that_type(self):
        self._setup(User.Plan.FREE)
        response = self.client.patch(f"/api/searches/{self.role.pk}/", {"search_type": "company"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deactivated_previous"]["id"], self.company.pk)
        self.company.refresh_from_db()
        self.role.refresh_from_db()
        self.assertFalse(self.company.is_active)
        self.assertTrue(self.role.is_active)
        self.assertEqual(SavedSearch.objects.filter(user=self.user, is_active=True, search_type="company").count(), 1)

    def test_editing_other_fields_does_not_touch_other_searches(self):
        self._setup(User.Plan.FREE)
        response = self.client.patch(f"/api/searches/{self.role.pk}/", {"keywords": "BA"}, format="json")
        self.assertNotIn("deactivated_previous", response.data)
        self.company.refresh_from_db()
        self.assertTrue(self.company.is_active)

    def test_inactive_search_type_change_has_no_side_effect(self):
        self._setup(User.Plan.FREE)
        SavedSearch.objects.filter(pk=self.role.pk).update(is_active=False)
        response = self.client.patch(f"/api/searches/{self.role.pk}/", {"search_type": "company"}, format="json")
        self.assertNotIn("deactivated_previous", response.data)
        self.company.refresh_from_db()
        self.assertTrue(self.company.is_active)

    def test_pro_type_change_keeps_both_active(self):
        self._setup(User.Plan.PRO)
        response = self.client.patch(f"/api/searches/{self.role.pk}/", {"search_type": "company"}, format="json")
        self.assertNotIn("deactivated_previous", response.data)
        self.assertEqual(SavedSearch.objects.filter(user=self.user, is_active=True).count(), 2)
