from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.searches.models import SavedSearch

from .collection import collect_jobs_for_user
from .models import Job, RunLog
from .scoring import score_job, score_jobs

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
