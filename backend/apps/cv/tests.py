import tempfile
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

import pdfplumber
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.jobs.models import DailyQuota, Job
from apps.profiles.models import Education, Experience, Profile, Skill

from .enrichment import generate_cv_with_enrichment
from .generation import generate_cv
from .manual_generation import (
    ManualGenerationFailed,
    ManualGenerationRejected,
    request_manual_cv_generation,
)
from .models import CVDocument

User = get_user_model()


def _make_image_file():
    buffer = BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("photo.png", buffer.read(), content_type="image/png")


def _make_job(user, description="Ricerchiamo un Project Manager per Milano.", external_id="ext-1"):
    return Job.objects.create(
        user=user,
        source=Job.Source.LINKEDIN,
        external_id=external_id,
        title="Project Manager",
        company="Acme S.p.A.",
        location="Milano",
        description=description,
        apply_url="https://linkedin.com/jobs/view/1",
    )


def _fake_content(num_experiences=3):
    return {
        "summary": "Project manager con 8 anni di esperienza.",
        "key_achievements": ["Consegnato progetto da 2M€ in anticipo"],
        "experiences": [
            {
                "company": f"Azienda {i}",
                "role": "Project Manager",
                "location": "Milano",
                "dates": "2020-01 - presente",
                "bullets": [f"Bullet {i}.1", f"Bullet {i}.2"],
            }
            for i in range(num_experiences)
        ],
        "skills": ["Project Management"],
    }


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class GenerateCvTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cv@example.com",
            email="cv@example.com",
            password="pw-Cv-12345!",
            first_name="Maria",
            last_name="Rossi",
        )
        self.profile = Profile.objects.create(
            user=self.user,
            summary="Sommario originale.",
            phone="+39 333 1234567",
            city="Milano",
            linkedin_url="https://linkedin.com/in/mariarossi",
        )
        Skill.objects.create(profile=self.profile, name="Project Management")
        Education.objects.create(
            profile=self.profile,
            institution="Università Bocconi",
            title="Laurea in Economia",
            location="Milano",
            dates="2010 - 2013",
            notes="Tesi su project management internazionale.",
        )
        self.job = _make_job(self.user)

    def _add_experiences(self, count):
        for i in range(count):
            Experience.objects.create(
                profile=self.profile,
                company=f"Azienda reale {i}",
                role="Project Manager",
                bullets=[f"Punto {i}"],
            )

    def test_html_contains_one_experience_block_per_profile_experience(self):
        self._add_experiences(1)
        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(1)
        ):
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        self.assertEqual(cv_document.html_source.count('class="experience"'), 1)

    def test_html_contains_three_experience_blocks_per_profile_experience(self):
        self._add_experiences(3)
        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(3)
        ):
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        self.assertEqual(cv_document.html_source.count('class="experience"'), 3)

    def test_pdf_is_a_single_page_for_a_standard_profile(self):
        self._add_experiences(2)
        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(2)
        ):
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        with pdfplumber.open(cv_document.pdf_file.path) as pdf:
            self.assertEqual(len(pdf.pages), 1)

    def test_photo_included_when_option_is_on_and_photo_uploaded(self):
        self._add_experiences(1)
        self.profile.photo = _make_image_file()
        self.profile.save()
        self.user.cv_include_photo = True
        self.user.save()

        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(1)
        ):
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        self.assertIn("<img", cv_document.html_source)
        with pdfplumber.open(cv_document.pdf_file.path) as pdf:
            self.assertEqual(len(pdf.pages[0].images), 1)

    def test_photo_excluded_when_option_is_off_even_if_photo_uploaded(self):
        self._add_experiences(1)
        self.profile.photo = _make_image_file()
        self.profile.save()
        self.user.cv_include_photo = False
        self.user.save()

        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(1)
        ):
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        self.assertNotIn("<img", cv_document.html_source)
        with pdfplumber.open(cv_document.pdf_file.path) as pdf:
            self.assertEqual(len(pdf.pages[0].images), 0)

    def test_education_section_matches_profile_data_verbatim(self):
        self._add_experiences(1)
        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(1)
        ):
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        self.assertIn("Università Bocconi", cv_document.html_source)
        self.assertIn("Laurea in Economia", cv_document.html_source)
        self.assertIn("Tesi su project management internazionale.", cv_document.html_source)

    def test_english_mode_requests_english_regardless_of_job_language(self):
        self._add_experiences(1)
        self.user.cv_language_mode = User.CvLanguageMode.ENGLISH
        self.user.save()
        job = _make_job(
            self.user, description="Nous recherchons un chef de projet.", external_id="ext-2"
        )

        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(1)
        ) as mock_content:
            cv_document = generate_cv(job, CVDocument.GenerationType.MANUAL)

        mock_content.assert_called_once_with(self.profile, job, User.CvLanguageMode.ENGLISH, "")
        self.assertEqual(cv_document.html_source.split('lang="')[1][:2], "en")

    def test_job_language_mode_is_forwarded_to_content_generation(self):
        self._add_experiences(1)
        self.user.cv_language_mode = User.CvLanguageMode.JOB_LANGUAGE
        self.user.save()

        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(1)
        ) as mock_content:
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        mock_content.assert_called_once_with(
            self.profile, self.job, User.CvLanguageMode.JOB_LANGUAGE, ""
        )
        self.assertEqual(cv_document.html_source.split('lang="')[1][:2], "it")

    def test_cv_document_references_job_and_user(self):
        self._add_experiences(1)
        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(1)
        ):
            cv_document = generate_cv(self.job, CVDocument.GenerationType.MANUAL)

        self.assertEqual(cv_document.job, self.job)
        self.assertEqual(cv_document.user, self.user)
        self.assertEqual(cv_document.generation_type, CVDocument.GenerationType.MANUAL)


@override_settings(PRICE_MANUAL_CV_EXTRA=Decimal("1.50"))
class ManualCvGenerationTests(TestCase):
    def _make_user(self, plan=User.Plan.FREE, extra_credit=Decimal("0")):
        return User.objects.create_user(
            username=f"manual-{plan}-{extra_credit}@example.com",
            email=f"manual-{plan}-{extra_credit}@example.com",
            password="pw-Manual-12345!",
            plan=plan,
            extra_credit=extra_credit,
        )

    def _make_job(self, user, external_id="ext-1", score=None, status=Job.Status.NEW):
        return Job.objects.create(
            user=user,
            source=Job.Source.LINKEDIN,
            external_id=external_id,
            title="Project Manager",
            company="Acme S.p.A.",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
            score=score,
            status=status,
        )

    def test_free_user_first_manual_generation_consumes_quota(self):
        user = self._make_user(plan=User.Plan.FREE)
        job = self._make_job(user)

        with patch("apps.cv.manual_generation.generate_cv") as mock_generate_cv:
            mock_generate_cv.return_value = "cv-doc"
            request_manual_cv_generation(job)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_cv_count, 1)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.CV_GENERATED)
        self.assertFalse(job.cv_generation_in_progress)
        self.assertIsNotNone(job.date_cv_generated)

    def test_free_user_second_generation_rejected_without_enough_credit(self):
        user = self._make_user(plan=User.Plan.FREE, extra_credit=Decimal("0.50"))
        job_1 = self._make_job(user, external_id="ext-1")
        job_2 = self._make_job(user, external_id="ext-2")

        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(job_1)

        with self.assertRaises(ManualGenerationRejected):
            request_manual_cv_generation(job_2)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_cv_count, 1)
        user.refresh_from_db()
        self.assertEqual(user.extra_credit, Decimal("0.50"))

    def test_free_user_second_generation_proceeds_on_credit_and_scales_price(self):
        user = self._make_user(plan=User.Plan.FREE, extra_credit=Decimal("5.00"))
        job_1 = self._make_job(user, external_id="ext-1")
        job_2 = self._make_job(user, external_id="ext-2")

        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(job_1)
            request_manual_cv_generation(job_2)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_cv_count, 1)
        user.refresh_from_db()
        self.assertEqual(user.extra_credit, Decimal("3.50"))
        job_2.refresh_from_db()
        self.assertEqual(job_2.status, Job.Status.CV_GENERATED)

    def test_pro_user_first_ten_consume_quota_eleventh_without_credit_is_rejected(self):
        user = self._make_user(plan=User.Plan.PRO)
        jobs = [self._make_job(user, external_id=f"ext-{i}") for i in range(11)]

        with patch("apps.cv.manual_generation.generate_cv"):
            for job in jobs[:10]:
                request_manual_cv_generation(job)

            with self.assertRaises(ManualGenerationRejected):
                request_manual_cv_generation(jobs[10])

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_cv_count, 10)

    def test_concurrent_request_on_same_job_is_rejected_without_consuming_quota(self):
        user = self._make_user(plan=User.Plan.FREE)
        job = self._make_job(user)
        job.cv_generation_in_progress = True
        job.save(update_fields=["cv_generation_in_progress"])

        with patch("apps.cv.manual_generation.generate_cv") as mock_generate_cv:
            with self.assertRaises(ManualGenerationRejected):
                request_manual_cv_generation(job)
            mock_generate_cv.assert_not_called()

        self.assertFalse(DailyQuota.objects.filter(user=user).exists())

    def test_failed_generation_refunds_quota_and_resets_job_to_new(self):
        user = self._make_user(plan=User.Plan.FREE)
        job = self._make_job(user)

        with patch(
            "apps.cv.manual_generation.generate_cv", side_effect=RuntimeError("errore simulato")
        ):
            with self.assertRaises(ManualGenerationFailed):
                request_manual_cv_generation(job)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_cv_count, 0)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.NEW)
        self.assertFalse(job.cv_generation_in_progress)

    def test_failed_generation_refunds_credit_when_charged_to_credit(self):
        user = self._make_user(plan=User.Plan.FREE, extra_credit=Decimal("5.00"))
        job_1 = self._make_job(user, external_id="ext-1")
        job_2 = self._make_job(user, external_id="ext-2")

        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(job_1)

        with patch(
            "apps.cv.manual_generation.generate_cv", side_effect=RuntimeError("errore simulato")
        ):
            with self.assertRaises(ManualGenerationFailed):
                request_manual_cv_generation(job_2)

        user.refresh_from_db()
        self.assertEqual(user.extra_credit, Decimal("5.00"))

    def test_retry_after_automatic_failure_uses_same_manual_counter(self):
        user = self._make_user(plan=User.Plan.FREE)
        job = self._make_job(user, score=5, status=Job.Status.NEW)

        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(job)

        quota = DailyQuota.objects.get(user=user)
        self.assertEqual(quota.manual_cv_count, 1)
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.CV_GENERATED)

    def test_successful_generation_removes_job_from_archive(self):
        user = self._make_user(plan=User.Plan.FREE)
        job = self._make_job(user)
        job.is_archived = True
        job.save(update_fields=["is_archived"])

        with patch("apps.cv.manual_generation.generate_cv"):
            request_manual_cv_generation(job)

        job.refresh_from_db()
        self.assertFalse(job.is_archived)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class EnrichAndGenerateCvTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="enrich@example.com", email="enrich@example.com", password="pw-Enrich-12345!"
        )
        self.profile = Profile.objects.create(user=self.user)
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
        self.detail = {
            "company": "Kuwait Petroleum",
            "role": "Site Supervisor",
            "location": "Kuwait City",
            "start_date": None,
            "end_date": None,
            "bullets": ["Coordinato un team di 12 persone"],
            "technologies": [],
        }

    def test_enrichment_not_saved_to_profile_by_default(self):
        with patch(
            "apps.cv.generation.generate_cv_content", return_value=_fake_content(0)
        ) as mock_content:
            cv_document = generate_cv_with_enrichment(self.job, self.detail, save_to_profile=False)

        self.assertFalse(
            self.profile.experiences.filter(company="Kuwait Petroleum").exists()
        )
        self.assertIn("Kuwait Petroleum", cv_document.enrichment_used)
        self.assertIn("Kuwait Petroleum", mock_content.call_args.args[3])

    def test_enrichment_saved_to_profile_when_requested(self):
        with patch("apps.cv.generation.generate_cv_content", return_value=_fake_content(0)):
            generate_cv_with_enrichment(self.job, self.detail, save_to_profile=True)

        experience = self.profile.experiences.get(company="Kuwait Petroleum")
        self.assertEqual(experience.role, "Site Supervisor")
        self.assertEqual(experience.bullets, ["Coordinato un team di 12 persone"])

    def test_enrichment_does_not_change_job_score(self):
        score_before = self.job.score

        with patch("apps.cv.generation.generate_cv_content", return_value=_fake_content(0)):
            generate_cv_with_enrichment(self.job, self.detail, save_to_profile=False)

        self.job.refresh_from_db()
        self.assertEqual(self.job.score, score_before)
