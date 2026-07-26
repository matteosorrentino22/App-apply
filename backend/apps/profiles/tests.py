import json
import tempfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import docx
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Profile

User = get_user_model()


def _make_image_file():
    buffer = BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("photo.png", buffer.read(), content_type="image/png")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="a@example.com", email="a@example.com", password="pw-A-12345!"
        )
        self.other_user = User.objects.create_user(
            username="b@example.com", email="b@example.com", password="pw-B-12345!"
        )
        self.other_profile = Profile.objects.create(user=self.other_user, summary="Profilo di B")

    def test_multiple_experiences_are_all_returned_on_read(self):
        self.client.force_authenticate(self.user)
        for i in range(3):
            response = self.client.post(
                "/api/experiences/",
                {"company": f"Azienda {i}", "role": "Developer", "bullets": [], "technologies": []},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get("/api/profiles/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["experiences"]), 3)

    def test_photo_upload_returns_rereadable_reference(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            "/api/profiles/me/", {"photo": _make_image_file()}, format="multipart"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["photo"])

        reread = self.client.get("/api/profiles/me/")
        self.assertEqual(reread.status_code, status.HTTP_200_OK)
        self.assertEqual(reread.data["photo"], response.data["photo"])

    def test_user_cannot_read_another_users_profile(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f"/api/profiles/{self.other_profile.pk}/")
        self.assertIn(response.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))


SAMPLE_CV_TEXT_LINES = [
    "Mario Rossi",
    "Project Manager con 8 anni di esperienza in ambito IT.",
    "ESPERIENZE",
    "Project Manager - Acme S.p.A. (2019-2024)",
    "Gestione di team cross-funzionali",
    "ISTRUZIONE",
    "Laurea in Ingegneria Gestionale - Politecnico di Milano (2014-2019)",
]

FAKE_STRUCTURED_PROFILE = {
    "summary": "Project Manager con 8 anni di esperienza in ambito IT.",
    "key_achievements": "",
    "experiences": [
        {
            "company": "Acme S.p.A.",
            "role": "Project Manager",
            "location": "",
            "start_date": "2019",
            "end_date": "2024",
            "bullets": ["Gestione di team cross-funzionali"],
            "technologies": [],
        }
    ],
    "educations": [
        {
            "institution": "Politecnico di Milano",
            "title": "Laurea in Ingegneria Gestionale",
            "location": "",
            "dates": "2014-2019",
            "notes": "",
        }
    ],
    "skills": [],
    "certifications": [],
    "languages": [],
}


def _make_docx_bytes(paragraphs):
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.read()


def _fake_anthropic_response(payload):
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [text_block]
    return response


class CVImportApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cv-import@example.com",
            email="cv-import@example.com",
            password="pw-CV-12345!",
        )
        self.client.force_authenticate(self.user)

    @patch("apps.profiles.cv_import.Anthropic")
    def test_docx_upload_prepopulates_profile_without_saving(self, mock_anthropic_cls):
        mock_client = mock_anthropic_cls.return_value
        mock_client.messages.create.return_value = _fake_anthropic_response(
            FAKE_STRUCTURED_PROFILE
        )

        upload = SimpleUploadedFile(
            "cv.docx",
            _make_docx_bytes(SAMPLE_CV_TEXT_LINES),
            content_type=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
        )
        response = self.client.post("/api/profile/import-cv/", {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"], FAKE_STRUCTURED_PROFILE["summary"])
        self.assertEqual(len(response.data["experiences"]), 1)
        self.assertEqual(len(response.data["educations"]), 1)

        # Nulla viene salvato: il profilo pre-popolato resta solo nella risposta.
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

        # A Claude va passato solo il testo estratto, mai il file binario.
        call_kwargs = mock_client.messages.create.call_args.kwargs
        sent_content = call_kwargs["messages"][0]["content"]
        self.assertIsInstance(sent_content, str)
        self.assertIn("Mario Rossi", sent_content)
        self.assertNotIn("PK\x03\x04", sent_content)  # firma binaria .docx assente dal testo

    @patch("apps.profiles.cv_import.pdfplumber.open")
    @patch("apps.profiles.cv_import.Anthropic")
    def test_pdf_upload_prepopulates_profile(self, mock_anthropic_cls, mock_pdf_open):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "\n".join(SAMPLE_CV_TEXT_LINES)
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf_open.return_value = mock_pdf

        mock_client = mock_anthropic_cls.return_value
        mock_client.messages.create.return_value = _fake_anthropic_response(
            FAKE_STRUCTURED_PROFILE
        )

        upload = SimpleUploadedFile("cv.pdf", b"%PDF-1.4 fake pdf bytes", content_type="application/pdf")
        response = self.client.post("/api/profile/import-cv/", {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"], FAKE_STRUCTURED_PROFILE["summary"])
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

    @patch("apps.profiles.cv_import.pdfplumber.open")
    def test_scanned_pdf_without_text_returns_fallback_and_saves_nothing(self, mock_pdf_open):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf_open.return_value = mock_pdf

        upload = SimpleUploadedFile("scan.pdf", b"%PDF-1.4 fake pdf bytes", content_type="application/pdf")
        response = self.client.post("/api/profile/import-cv/", {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertIn("compila il profilo manualmente", response.data["detail"])
        self.assertFalse(Profile.objects.filter(user=self.user).exists())

    def test_unsupported_file_format_is_rejected(self):
        upload = SimpleUploadedFile("cv.txt", b"plain text cv", content_type="text/plain")
        response = self.client.post("/api/profile/import-cv/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Profile.objects.filter(user=self.user).exists())
