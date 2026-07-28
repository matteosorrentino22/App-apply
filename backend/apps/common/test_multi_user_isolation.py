import tempfile

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.jobs.models import Job
from apps.profiles.models import Profile
from apps.searches.models import SavedSearch

User = get_user_model()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class MultiUserIsolationTests(APITestCase):
    """Sprint 22, criteri di accettazione §7 "Requisiti trasversali": due
    utenti di test, verifica diretta via API con il token dell'uno sulle
    risorse (profilo, ricerche, job, CV) dell'altro — nessuna deve essere
    raggiungibile. Le singole app hanno già test di isolamento mirati
    (`apps.profiles.tests.ProfileApiTests.test_user_cannot_read_another_users_profile`,
    `apps.jobs.tests.JobDetailApiTests.test_another_users_job_is_not_found`);
    qui si copre in un unico posto anche ciò che non era ancora testato:
    ricerche salvate e le azioni sul job (genera CV, arricchisci, archivia,
    disarchivia, candidatura fatta)."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="isolation-a@example.com", email="isolation-a@example.com", password="pw-IsoA-12345!"
        )
        self.user_b = User.objects.create_user(
            username="isolation-b@example.com", email="isolation-b@example.com", password="pw-IsoB-12345!"
        )

        Profile.objects.create(user=self.user_a, summary="Profilo di A")

        self.search_a = SavedSearch.objects.create(
            user=self.user_a, keywords="developer", city="Roma", country="Italia"
        )

        self.job_a = Job.objects.create(
            user=self.user_a,
            source=Job.Source.LINKEDIN,
            external_id="isolation-ext-1",
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            status=Job.Status.NEW,
        )

        self.client.force_authenticate(self.user_b)

    def test_cannot_read_another_users_profile(self):
        response = self.client.get(f"/api/profiles/{self.user_a.profile.pk}/")
        self.assertIn(response.status_code, (403, 404))

    def test_cannot_read_another_users_saved_search(self):
        response = self.client.get(f"/api/searches/{self.search_a.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_modify_another_users_saved_search(self):
        response = self.client.patch(
            f"/api/searches/{self.search_a.pk}/", {"keywords": "Rubata"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.search_a.refresh_from_db()
        self.assertEqual(self.search_a.keywords, "developer")

    def test_cannot_delete_another_users_saved_search(self):
        response = self.client.delete(f"/api/searches/{self.search_a.pk}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(SavedSearch.objects.filter(pk=self.search_a.pk).exists())

    def test_cannot_activate_another_users_saved_search(self):
        response = self.client.post(f"/api/searches/{self.search_a.pk}/activate/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_read_another_users_job(self):
        response = self.client.get(f"/api/jobs/{self.job_a.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_generate_cv_on_another_users_job(self):
        response = self.client.post(f"/api/jobs/{self.job_a.pk}/generate-cv/")
        self.assertEqual(response.status_code, 404)

    def test_cannot_enrich_another_users_job(self):
        response = self.client.post(
            f"/api/jobs/{self.job_a.pk}/enrich-and-generate-cv/",
            {"company": "Beta", "role": "Dev", "location": "Milano", "activities": [], "save_to_profile": False},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_archive_another_users_job(self):
        response = self.client.post(f"/api/jobs/{self.job_a.pk}/archive/")
        self.assertEqual(response.status_code, 404)
        self.job_a.refresh_from_db()
        self.assertFalse(self.job_a.is_archived)

    def test_cannot_unarchive_another_users_job(self):
        self.job_a.is_archived = True
        self.job_a.save(update_fields=["is_archived"])

        response = self.client.post(f"/api/jobs/{self.job_a.pk}/unarchive/")

        self.assertEqual(response.status_code, 404)
        self.job_a.refresh_from_db()
        self.assertTrue(self.job_a.is_archived)

    def test_cannot_mark_another_users_job_application_done(self):
        self.job_a.status = Job.Status.CV_GENERATED
        self.job_a.save(update_fields=["status"])

        response = self.client.post(f"/api/jobs/{self.job_a.pk}/mark-application-done/")

        self.assertEqual(response.status_code, 404)
        self.job_a.refresh_from_db()
        self.assertEqual(self.job_a.status, Job.Status.CV_GENERATED)
