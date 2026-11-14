import tempfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APITestCase

from apps.cv.models import CoverLetterDraft, CVDraft
from apps.profiles.cv_import import MAX_TEXT_LENGTH
from apps.profiles.models import Profile
from apps.profiles.views import CV_IMPORT_DAILY_LIMIT

from .models import DailyQuota, Job

User = get_user_model()


def _cv_content(**overrides):
    content = {
        "summary": "Sommario",
        "qualification": "Project Manager",
        "translated_city": "Roma",
        "content_language": "it",
        "areas_of_expertise": ["Pianificazione"],
        "experiences": [
            {
                "profile_experience_id": 1,
                "company": "Acme",
                "role": "PM",
                "location": "Roma, IT",
                "dates": "2020 - 2024",
                "technologies": ["Jira"],
                "shown": True,
                "bullets": [{"text": "Guidato un team.", "shown": True}],
            }
        ],
        "educations": [{"institution": "Uni", "title": "Laurea", "location": "", "dates": "2019", "notes": ""}],
        "skills": ["Scrum"],
        "certifications": [],
        "languages": [{"language": "it", "level": "mother_tongue"}],
    }
    content.update(overrides)
    return content


class InputLimitTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="limits@example.com", email="limits@example.com", password="pw-Limits-12345!")
        Profile.objects.create(user=self.user)
        self.client.force_authenticate(self.user)
        self.job = Job.objects.create(
            user=self.user,
            source=Job.Source.LINKEDIN,
            external_id="ext-limits",
            title="PM",
            company="Acme",
            location="Roma",
            description="Descrizione.",
            apply_url="https://linkedin.com/jobs/view/1",
        )

    def test_manual_job_description_over_limit_is_rejected(self):
        response = self.client.post(
            "/api/jobs/manual/",
            {
                "title": "PM",
                "company": "Acme",
                "location": "Roma",
                "description": "x" * 20_001,
                "published_at": "2026-11-01T10:00:00Z",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("description", response.data)

    @patch("apps.jobs.views.send_chat_message")
    def test_chat_message_over_limit_is_rejected_before_calling_ai(self, mock_send):
        response = self.client.post(f"/api/jobs/{self.job.pk}/cv-draft/chat/", {"message": "x" * 2_001}, format="json")
        self.assertEqual(response.status_code, 400)
        mock_send.assert_not_called()

    @patch("apps.jobs.views.send_cover_letter_chat_message")
    def test_cover_letter_chat_message_over_limit_is_rejected(self, mock_send):
        response = self.client.post(
            f"/api/jobs/{self.job.pk}/cover-letter-draft/chat/", {"message": "x" * 2_001}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        mock_send.assert_not_called()

    @patch("apps.jobs.views.request_cover_letter_generation")
    def test_cover_letter_instructions_over_limit_are_rejected(self, mock_generate):
        response = self.client.post(
            f"/api/jobs/{self.job.pk}/generate-cover-letter/", {"instructions": "x" * 2_001}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        mock_generate.assert_not_called()

    @patch("apps.jobs.views.request_manual_cv_generation")
    def test_gap_instructions_over_limit_are_rejected(self, mock_generate):
        response = self.client.post(
            f"/api/jobs/{self.job.pk}/generate-cv/", {"gaps": ["SQL"], "gap_instructions": "x" * 2_001}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        mock_generate.assert_not_called()

    @patch("apps.jobs.views.request_referral_message_generation")
    def test_referral_recipient_and_instructions_are_limited(self, mock_generate):
        response = self.client.post(
            f"/api/jobs/{self.job.pk}/generate-referral-message/",
            {"channel": "linkedin", "recipient_name": "x" * 256},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        mock_generate.assert_not_called()

    def test_cv_draft_patch_accepts_valid_content_and_rejects_invalid(self):
        CVDraft.objects.create(job=self.job, user=self.user, content_json=_cv_content())
        url = f"/api/jobs/{self.job.pk}/cv-draft/"

        self.assertEqual(self.client.patch(url, _cv_content(summary="Nuovo"), format="json").status_code, 200)
        invalid_payloads = [
            _cv_content(summary=123),
            _cv_content(summary="x" * 5_001),
            _cv_content(skills=["s"] * 101),
            _cv_content(unexpected="x"),
            {key: value for key, value in _cv_content().items() if key != "experiences"},
            _cv_content(experiences=[{"company": "Acme"}]),
        ]
        for payload in invalid_payloads:
            self.assertEqual(self.client.patch(url, payload, format="json").status_code, 400)
        self.assertEqual(CVDraft.objects.get(job=self.job).content_json["summary"], "Nuovo")

    def test_cv_draft_preview_rejects_invalid_content_without_rendering(self):
        CVDraft.objects.create(job=self.job, user=self.user, content_json=_cv_content())
        with patch("apps.jobs.views.render_draft_preview") as mock_render:
            response = self.client.post(
                f"/api/jobs/{self.job.pk}/cv-draft/preview/",
                _cv_content(experiences=[_cv_content()["experiences"][0]] * 31),
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        mock_render.assert_not_called()

    def test_cover_letter_draft_patch_is_validated(self):
        CoverLetterDraft.objects.create(
            job=self.job, user=self.user, content_json={"content_language": "it", "translated_city": "Roma", "paragraphs": ["A"]}
        )
        url = f"/api/jobs/{self.job.pk}/cover-letter-draft/"
        valid = {"content_language": "it", "translated_city": "Roma", "paragraphs": ["A", "B"]}
        self.assertEqual(self.client.patch(url, valid, format="json").status_code, 200)
        self.assertEqual(self.client.patch(url, {**valid, "paragraphs": ["x"] * 16}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {**valid, "paragraphs": [{"a": 1}]}, format="json").status_code, 400)


def _mock_pdf(page_text, pages=1):
    mock_page = MagicMock()
    mock_page.extract_text.return_value = page_text
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page] * pages
    mock_pdf.__enter__.return_value = mock_pdf
    return mock_pdf


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CvImportLimitTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="import@example.com", email="import@example.com", password="pw-Import-12345!")
        self.client.force_authenticate(self.user)

    def _post(self, content=b"%PDF-1.4 fake", name="cv.pdf"):
        upload = SimpleUploadedFile(name, content, content_type="application/pdf")
        return self.client.post("/api/profile/import-cv/", {"file": upload}, format="multipart")

    def test_file_over_5_mb_is_rejected(self):
        with patch("apps.profiles.cv_import.MAX_UPLOAD_BYTES", 10):
            response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_format_is_decided_by_content_not_by_name(self):
        response = self._post(content=b"plain text pretending", name="cv.pdf")
        self.assertEqual(response.status_code, 400)

    @patch("apps.profiles.cv_import.pdfplumber.open")
    @patch("apps.profiles.cv_import.call_claude_structured")
    def test_pdf_over_10_pages_is_rejected(self, mock_claude, mock_open):
        mock_open.return_value = _mock_pdf("Testo del CV abbastanza lungo da superare la soglia minima.", pages=11)
        response = self._post()
        self.assertEqual(response.status_code, 400)
        mock_claude.assert_not_called()

    @patch("apps.profiles.cv_import.pdfplumber.open")
    @patch("apps.profiles.cv_import.call_claude_structured", return_value={"summary": ""})
    def test_extracted_text_is_truncated(self, mock_claude, mock_open):
        mock_open.return_value = _mock_pdf("x" * (MAX_TEXT_LENGTH + 5_000))
        self.assertEqual(self._post().status_code, 200)
        self.assertEqual(len(mock_claude.call_args.kwargs["user_content"]), MAX_TEXT_LENGTH)

    @patch("apps.profiles.cv_import.pdfplumber.open")
    @patch("apps.profiles.cv_import.call_claude_structured", return_value={"summary": ""})
    def test_daily_quota_without_credit(self, mock_claude, mock_open):
        mock_open.return_value = _mock_pdf("Testo del CV abbastanza lungo da superare la soglia minima.")
        for _ in range(CV_IMPORT_DAILY_LIMIT):
            self.assertEqual(self._post().status_code, 200)
        self.assertEqual(self._post().status_code, 409)
        self.assertEqual(mock_claude.call_count, CV_IMPORT_DAILY_LIMIT)
        self.assertEqual(DailyQuota.objects.get(user=self.user).cv_import_count, CV_IMPORT_DAILY_LIMIT)

    @patch("apps.profiles.cv_import.pdfplumber.open")
    @patch("apps.profiles.cv_import.call_claude_structured", side_effect=RuntimeError("bedrock down"))
    def test_ai_failure_returns_502_and_refunds_the_quota(self, mock_claude, mock_open):
        mock_open.return_value = _mock_pdf("Testo del CV abbastanza lungo da superare la soglia minima.")
        with self.assertLogs("apps.profiles.views", level="ERROR"):
            response = self._post()
        self.assertEqual(response.status_code, 502)
        self.assertEqual(DailyQuota.objects.get(user=self.user).cv_import_count, 0)


class ExperienceLimitTests(APITestCase):
    def test_bullets_are_limited(self):
        user = User.objects.create_user(username="exp@example.com", email="exp@example.com", password="pw-Exp-12345!")
        self.client.force_authenticate(user)
        base = {"company": "Acme", "role": "PM", "technologies": []}
        self.assertEqual(self.client.post("/api/experiences/", {**base, "bullets": ["x" * 2_001]}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/experiences/", {**base, "bullets": ["x"] * 31}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/experiences/", {**base, "bullets": ["ok"]}, format="json").status_code, 201)
