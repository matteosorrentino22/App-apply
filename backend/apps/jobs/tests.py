from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.searches.models import SavedSearch

from .collection import collect_jobs_for_user
from .models import Job

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
