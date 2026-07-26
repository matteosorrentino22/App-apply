import random
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from django_celery_beat.models import PeriodicTask
from rest_framework.test import APITestCase

from apps.cv.manual_generation import request_manual_cv_generation
from apps.cv.models import CVDocument
from apps.profiles.models import Profile
from apps.searches.models import SavedSearch

from .collection import collect_jobs_for_user
from .import_service import (
    ImportDuplicate,
    ImportNotAllowed,
    ImportRejected,
    import_job_from_url,
)
from .intake import INTAKE_CAP, apply_intake_cap
from .models import DailyQuota, Job, RunLog
from .scoring import score_job, score_jobs
from .tasks import run_nightly_cycle_for_user

User = get_user_model()


def _offer(external_id, **overrides):
    offer = {
        "external_id": external_id,
        "title": "Project Manager",
        "company": "Acme S.p.A.",
        "location": "Roma",
        "description": "Descrizione della posizione.",
        "apply_url": "https://linkedin.com/jobs/view/123",
        "published_at": None,
        "salary": "",
    }
    offer.update(overrides)
    return offer


class CollectJobsForUserTests(TestCase):
    def setUp(self):
        self.free_user = User.objects.create_user(
            username="free@example.com", email="free@example.com", password="pw-Free-12345!"
        )
        SavedSearch.objects.create(
            user=self.free_user,
            name="Ricerca",
            keywords="Project Manager",
            location="Roma",
            is_active=True,
        )

    def test_caps_saved_jobs_at_plan_limit_even_if_source_returns_more(self):
        offers = [_offer(f"ext-{i}") for i in range(80)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            created = collect_jobs_for_user(self.free_user)

        self.assertEqual(len(created), 50)
        self.assertEqual(Job.objects.filter(user=self.free_user).count(), 50)

    def test_offer_missing_a_required_field_is_not_saved(self):
        offers = [_offer("ext-1"), _offer("ext-2", company="")]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            created = collect_jobs_for_user(self.free_user)

        self.assertEqual(len(created), 1)
        self.assertEqual(Job.objects.filter(user=self.free_user).count(), 1)

    def test_offer_without_published_at_is_saved_with_null(self):
        offers = [_offer("ext-1", published_at=None)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            collect_jobs_for_user(self.free_user)

        job = Job.objects.get(user=self.free_user, external_id="ext-1")
        self.assertIsNone(job.published_at)

    def test_rerunning_with_same_external_id_does_not_duplicate(self):
        offers = [_offer("ext-1")]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            collect_jobs_for_user(self.free_user)
            second_run_created = collect_jobs_for_user(self.free_user)

        self.assertEqual(len(second_run_created), 0)
        self.assertEqual(Job.objects.filter(user=self.free_user, external_id="ext-1").count(), 1)

    def test_pro_user_plan_limit_is_one_hundred(self):
        pro_user = User.objects.create_user(
            username="pro@example.com",
            email="pro@example.com",
            password="pw-Pro-12345!",
            plan=User.Plan.PRO,
        )
        SavedSearch.objects.create(
            user=pro_user, name="Ricerca", keywords="PM", location="Roma", is_active=True
        )
        offers = [_offer(f"ext-{i}") for i in range(150)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            created = collect_jobs_for_user(pro_user)

        self.assertEqual(len(created), 100)

    def test_no_active_searches_collects_nothing(self):
        SavedSearch.objects.filter(user=self.free_user).update(is_active=False)
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            created = collect_jobs_for_user(self.free_user)
        mock_get_source.assert_not_called()
        self.assertEqual(created, [])


FAKE_SCORE_RESULT = {
    "score": 4,
    "score_match": ["Esperienza di project management"],
    "score_gaps": ["Nessuna certificazione PMP"],
    "score_reasoning": "Buona affinità con il ruolo richiesto.",
}


class ScoreJobTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="score@example.com", email="score@example.com", password="pw-Score-12345!"
        )

    def _make_job(self, external_id):
        return Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id=external_id,
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione della posizione.",
            apply_url="https://linkedin.com/jobs/view/1",
        )

    def test_successful_scoring_populates_all_fields(self):
        job = self._make_job("ext-1")
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT):
            result = score_job(job)

        self.assertTrue(result)
        job.refresh_from_db()
        self.assertEqual(job.score, 4)
        self.assertEqual(job.score_match, FAKE_SCORE_RESULT["score_match"])
        self.assertEqual(job.score_gaps, FAKE_SCORE_RESULT["score_gaps"])
        self.assertEqual(job.score_reasoning, FAKE_SCORE_RESULT["score_reasoning"])
        self.assertIsNotNone(job.date_scored)

    def test_failed_scoring_leaves_job_unscored_and_logs_run_log(self):
        job = self._make_job("ext-2")
        with patch(
            "apps.jobs.scoring.score_job_with_claude", side_effect=TimeoutError("timeout")
        ):
            result = score_job(job)

        self.assertFalse(result)
        job.refresh_from_db()
        self.assertIsNone(job.score)

        run_logs = RunLog.objects.filter(job=job, task_type=RunLog.TaskType.SCORING)
        self.assertEqual(run_logs.count(), 1)
        self.assertEqual(run_logs.first().status, RunLog.Status.FAILURE)

    def test_batch_scoring_isolates_single_job_failure(self):
        job_ok_1 = self._make_job("ext-3")
        job_fail = self._make_job("ext-4")
        job_ok_2 = self._make_job("ext-5")

        def fake_score(job, profile):
            if job.pk == job_fail.pk:
                raise RuntimeError("errore simulato")
            return FAKE_SCORE_RESULT

        with patch("apps.jobs.scoring.score_job_with_claude", side_effect=fake_score):
            scored = score_jobs([job_ok_1, job_fail, job_ok_2])

        self.assertEqual({job.pk for job in scored}, {job_ok_1.pk, job_ok_2.pk})
        job_fail.refresh_from_db()
        self.assertIsNone(job_fail.score)
        job_ok_1.refresh_from_db()
        self.assertEqual(job_ok_1.score, 4)


class ApplyIntakeCapTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cap@example.com", email="cap@example.com", password="pw-Cap-12345!"
        )

    def _make_scored_job(self, external_id, score, published_at=None):
        return Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id=external_id,
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            score=score,
            published_at=published_at,
        )

    def test_keeps_exactly_the_cap_and_excludes_the_rest(self):
        jobs = [self._make_scored_job(f"ext-{i}", score=(i % 5) + 1) for i in range(20)]

        kept, discarded = apply_intake_cap(self.user, jobs)

        self.assertEqual(len(kept), INTAKE_CAP)
        self.assertEqual(len(discarded), 5)
        self.assertEqual(
            Job.objects.filter(user=self.user, discarded_by_cap=False).count(), INTAKE_CAP
        )
        self.assertEqual(Job.objects.filter(user=self.user, discarded_by_cap=True).count(), 5)

    def test_tie_break_prefers_most_recently_published(self):
        now = timezone.now()
        # 14 job a punteggio 5 riempiono già il cap tranne un posto; due job a
        # punteggio 4 sono a pari merito sul confine: vince quello più recente.
        top_jobs = [self._make_scored_job(f"top-{i}", score=5) for i in range(14)]
        older = self._make_scored_job("older", score=4, published_at=now - timedelta(days=2))
        newer = self._make_scored_job("newer", score=4, published_at=now - timedelta(hours=1))

        kept, discarded = apply_intake_cap(self.user, top_jobs + [older, newer])

        kept_ids = {job.pk for job in kept}
        self.assertIn(newer.pk, kept_ids)
        self.assertNotIn(older.pk, kept_ids)

    def test_tie_break_is_random_but_deterministic_with_seed(self):
        # Due job a pari punteggio e senza published_at: il seed rende la
        # scelta deterministica nel test, come richiesto dal criterio.
        job_a = self._make_scored_job("a", score=3, published_at=None)
        job_b = self._make_scored_job("b", score=3, published_at=None)

        random.seed(1234)
        kept_first, _ = apply_intake_cap(self.user, [job_a, job_b])

        Job.objects.filter(pk__in=[job_a.pk, job_b.pk]).update(discarded_by_cap=False)

        random.seed(1234)
        kept_second, _ = apply_intake_cap(self.user, [job_a, job_b])

        self.assertEqual([job.pk for job in kept_first], [job.pk for job in kept_second])


class RunNightlyCycleForUserTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="nightly@example.com", email="nightly@example.com", password="pw-Night-12345!"
        )
        SavedSearch.objects.create(
            user=self.user, name="Ricerca", keywords="PM", location="Roma", is_active=True
        )

    def test_orchestrates_collection_scoring_and_cap_with_run_log(self):
        offers = [_offer(f"ext-{i}") for i in range(20)]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            summary = run_nightly_cycle_for_user(self.user)

        self.assertEqual(summary["collected"], 20)
        self.assertEqual(summary["scored"], 20)
        self.assertEqual(summary["kept"], INTAKE_CAP)
        self.assertEqual(summary["discarded_cap"], 5)

        run_log = RunLog.objects.get(user=self.user, task_type=RunLog.TaskType.COLLECTION)
        self.assertEqual(run_log.status, RunLog.Status.SUCCESS)
        self.assertIn("raccolti=20", run_log.message)
        self.assertIn("scartati_cap=5", run_log.message)


class AutomaticCvGenerationInNightlyCycleTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="autocv@example.com", email="autocv@example.com", password="pw-Auto-12345!"
        )
        SavedSearch.objects.create(
            user=self.user, name="Ricerca", keywords="PM", location="Roma", is_active=True
        )

    def _run_cycle_with_scores(self, scores):
        offers = [_offer(f"ext-{i}") for i in range(len(scores))]
        score_cycle = iter(scores)

        def fake_score(job, profile):
            score = next(score_cycle)
            return {**FAKE_SCORE_RESULT, "score": score}

        with patch("apps.jobs.collection.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", side_effect=fake_score
        ):
            mock_get_source.return_value = MagicMock(fetch=MagicMock(return_value=offers))
            summary = run_nightly_cycle_for_user(self.user)
        return summary

    def test_high_score_jobs_get_automatic_cv_and_cv_generated_status(self):
        with patch("apps.jobs.tasks.generate_cv") as mock_generate_cv:
            mock_generate_cv.return_value = MagicMock()
            summary = self._run_cycle_with_scores([5, 4, 3, 2, 1])

        self.assertEqual(summary["cv_generated"], 2)
        high_score_jobs = Job.objects.filter(user=self.user, score__gte=4)
        low_score_jobs = Job.objects.filter(user=self.user, score__lte=3)
        self.assertEqual(high_score_jobs.count(), 2)
        self.assertTrue(all(job.status == Job.Status.CV_GENERATED for job in high_score_jobs))
        self.assertTrue(all(job.date_cv_generated is not None for job in high_score_jobs))
        self.assertEqual(low_score_jobs.count(), 3)
        self.assertTrue(all(job.status == Job.Status.NEW for job in low_score_jobs))
        self.assertEqual(mock_generate_cv.call_count, 2)
        for call in mock_generate_cv.call_args_list:
            self.assertEqual(call.args[1], CVDocument.GenerationType.AUTOMATIC)

    def test_low_score_jobs_have_no_cv_document(self):
        with patch("apps.jobs.tasks.generate_cv") as mock_generate_cv:
            self._run_cycle_with_scores([2, 1])

        mock_generate_cv.assert_not_called()

    def test_failed_generation_leaves_job_new_without_blocking_others(self):
        job_scores = [5, 5]

        def fake_generate(job, generation_type):
            if job.score == 5 and job.external_id == "ext-0":
                raise RuntimeError("errore simulato di generazione")
            return MagicMock()

        with patch(
            "apps.jobs.tasks.generate_cv", side_effect=fake_generate
        ) as mock_generate_cv:
            summary = self._run_cycle_with_scores(job_scores)

        self.assertEqual(mock_generate_cv.call_count, 2)
        self.assertEqual(summary["cv_generated"], 1)
        failed_job = Job.objects.get(user=self.user, external_id="ext-0")
        succeeded_job = Job.objects.get(user=self.user, external_id="ext-1")
        self.assertEqual(failed_job.status, Job.Status.NEW)
        self.assertIsNone(failed_job.date_cv_generated)
        self.assertEqual(succeeded_job.status, Job.Status.CV_GENERATED)

        run_log = RunLog.objects.get(
            user=self.user, job=failed_job, task_type=RunLog.TaskType.CV_GENERATION
        )
        self.assertEqual(run_log.status, RunLog.Status.FAILURE)

    def test_automatic_generation_does_not_consume_daily_quota(self):
        with patch("apps.jobs.tasks.generate_cv") as mock_generate_cv:
            mock_generate_cv.return_value = MagicMock()
            self._run_cycle_with_scores([5, 4])

        self.assertFalse(DailyQuota.objects.filter(user=self.user).exists())


class NightlyCycleScheduleTests(TestCase):
    def test_periodic_task_is_scheduled_at_2am_europe_rome(self):
        task = PeriodicTask.objects.get(
            name="Ciclo notturno (raccolta, scoring, cap di intake)"
        )
        self.assertEqual(task.task, "apps.jobs.tasks.run_nightly_cycle")
        self.assertTrue(task.enabled)
        self.assertEqual(task.crontab.hour, "2")
        self.assertEqual(task.crontab.minute, "0")
        self.assertEqual(str(task.crontab.timezone), "Europe/Rome")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class EnrichAndGenerateCvApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="enrichapi@example.com",
            email="enrichapi@example.com",
            password="pw-EnrichApi-12345!",
        )
        Profile.objects.create(user=self.user)
        self.job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            score=3,
        )
        self.client.force_authenticate(self.user)

    def test_enrichment_with_save_to_profile_is_visible_via_profile_api(self):
        payload = {
            "company": "Kuwait Petroleum",
            "role": "Site Supervisor",
            "bullets": ["Coordinato un team di 12 persone"],
            "save_to_profile": True,
        }
        with patch("apps.cv.manual_generation.generate_cv") as mock_generate_cv:
            mock_generate_cv.return_value = MagicMock(pk=1)
            response = self.client.post(
                f"/api/jobs/{self.job.pk}/enrich-and-generate-cv/", payload, format="json"
            )

        self.assertEqual(response.status_code, 201)

        profile_response = self.client.get("/api/profiles/me/")
        experiences = profile_response.json()["experiences"]
        self.assertTrue(
            any(exp["company"] == "Kuwait Petroleum" for exp in experiences)
        )

    def test_enrichment_without_save_to_profile_is_not_in_profile_api(self):
        payload = {
            "company": "Kuwait Petroleum",
            "role": "Site Supervisor",
            "bullets": ["Coordinato un team di 12 persone"],
            "save_to_profile": False,
        }
        with patch("apps.cv.manual_generation.generate_cv") as mock_generate_cv:
            mock_generate_cv.return_value = MagicMock(pk=1)
            response = self.client.post(
                f"/api/jobs/{self.job.pk}/enrich-and-generate-cv/", payload, format="json"
            )

        self.assertEqual(response.status_code, 201)

        profile_response = self.client.get("/api/profiles/me/")
        experiences = profile_response.json()["experiences"]
        self.assertFalse(
            any(exp["company"] == "Kuwait Petroleum" for exp in experiences)
        )


VALID_LINKEDIN_URL = "https://www.linkedin.com/jobs/view/1234567890"


def _import_offer(**overrides):
    offer = {
        "external_id": "1234567890",
        "title": "Site Supervisor",
        "company": "Kuwait Petroleum",
        "location": "Kuwait City",
        "description": "Descrizione della posizione importata.",
        "apply_url": VALID_LINKEDIN_URL,
        "published_at": None,
        "salary": "",
    }
    offer.update(overrides)
    return offer


@override_settings(PRICE_IMPORT_EXTRA=Decimal("0.50"))
class ImportJobTests(TestCase):
    def _make_user(self, plan=User.Plan.FREE, extra_credit=Decimal("0")):
        return User.objects.create_user(
            username=f"import-{plan}-{extra_credit}@example.com",
            email=f"import-{plan}-{extra_credit}@example.com",
            password="pw-Import-12345!",
            plan=plan,
            extra_credit=extra_credit,
        )

    def test_pro_user_imports_valid_link_scored_without_automatic_cv(self):
        user = self._make_user(plan=User.Plan.PRO)

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(return_value=_import_offer())
            )
            job = import_job_from_url(user, VALID_LINKEDIN_URL)

        self.assertEqual(job.origin, Job.Origin.IMPORTED)
        self.assertEqual(job.status, Job.Status.NEW)
        self.assertEqual(job.score, FAKE_SCORE_RESULT["score"])
        self.assertFalse(CVDocument.objects.filter(job=job).exists())

    def test_free_user_cannot_import_even_with_credit(self):
        user = self._make_user(plan=User.Plan.FREE, extra_credit=Decimal("100"))

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source:
            with self.assertRaises(ImportNotAllowed):
                import_job_from_url(user, VALID_LINKEDIN_URL)
            mock_get_source.assert_not_called()

        self.assertEqual(Job.objects.filter(user=user).count(), 0)
        self.assertFalse(DailyQuota.objects.filter(user=user).exists())

    def test_invalid_link_is_rejected_without_creating_a_job(self):
        user = self._make_user(plan=User.Plan.PRO)

        with self.assertRaises(ImportRejected):
            import_job_from_url(user, "https://example.com/not-a-linkedin-job")

        self.assertEqual(Job.objects.filter(user=user).count(), 0)

    def test_importing_an_already_present_job_is_flagged_as_duplicate(self):
        user = self._make_user(plan=User.Plan.PRO)
        Job.objects.create(
            user=user,
            source=Job.Source.LINKEDIN,
            external_id="1234567890",
            title="Site Supervisor",
            company="Kuwait Petroleum",
            location="Kuwait City",
            description="Già presente.",
            apply_url=VALID_LINKEDIN_URL,
        )

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source:
            with self.assertRaises(ImportDuplicate):
                import_job_from_url(user, VALID_LINKEDIN_URL)
            mock_get_source.assert_not_called()

        self.assertEqual(Job.objects.filter(user=user).count(), 1)
        self.assertFalse(DailyQuota.objects.filter(user=user).exists())

    def _import_n(self, user, count, start=1000):
        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            for i in range(count):
                mock_get_source.return_value = MagicMock(
                    fetch_by_url=MagicMock(
                        return_value=_import_offer(
                            external_id=f"ext-{start + i}",
                            apply_url=f"{VALID_LINKEDIN_URL}-{start + i}",
                        )
                    )
                )
                import_job_from_url(user, f"https://www.linkedin.com/jobs/view/{start + i}")

    def test_fourth_import_without_credit_is_rejected(self):
        user = self._make_user(plan=User.Plan.PRO, extra_credit=Decimal("0"))
        self._import_n(user, 3)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.import_count, 3)

        with self.assertRaises(ImportRejected):
            import_job_from_url(user, "https://www.linkedin.com/jobs/view/2000")

        quota.refresh_from_db()
        self.assertEqual(quota.import_count, 3)

    def test_fourth_import_with_enough_credit_proceeds_and_scales_price(self):
        user = self._make_user(plan=User.Plan.PRO, extra_credit=Decimal("5.00"))
        self._import_n(user, 3)

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(
                    return_value=_import_offer(external_id="ext-2000", apply_url=f"{VALID_LINKEDIN_URL}-2000")
                )
            )
            import_job_from_url(user, "https://www.linkedin.com/jobs/view/2000")

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.import_count, 3)
        user.refresh_from_db()
        self.assertEqual(user.extra_credit, Decimal("4.50"))

    def test_import_and_manual_cv_generation_consume_separate_counters(self):
        user = self._make_user(plan=User.Plan.PRO)

        with patch("apps.jobs.import_service.get_job_source") as mock_get_source, patch(
            "apps.jobs.scoring.score_job_with_claude", return_value=FAKE_SCORE_RESULT
        ):
            mock_get_source.return_value = MagicMock(
                fetch_by_url=MagicMock(return_value=_import_offer())
            )
            job = import_job_from_url(user, VALID_LINKEDIN_URL)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.import_count, 1)
        self.assertEqual(quota.manual_cv_count, 0)

        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(job)

        quota.refresh_from_db()
        self.assertEqual(quota.import_count, 1)
        self.assertEqual(quota.manual_cv_count, 1)
