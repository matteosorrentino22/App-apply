import tempfile
from io import BytesIO
from unittest.mock import patch

import pdfplumber
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.jobs.models import Job
from apps.profiles.models import Education, Experience, Profile, Skill

from .generation import generate_cv
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
