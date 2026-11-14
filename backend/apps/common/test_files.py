import os
import tempfile
import time
from io import BytesIO, StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APITestCase

from apps.cv.models import CoverLetterDocument, CVDocument
from apps.jobs.models import Job
from apps.profiles.models import Profile

from .files import SIGNED_URL_MAX_AGE, signed_document_url, signed_photo_url

User = get_user_model()

RANDOM_PDF_NAME = r"^{folder}/[0-9a-f]{{32}}\.pdf$"


def _make_user(email, **extra):
    return User.objects.create_user(username=email, email=email, password="pw-Files-12345!", **extra)


def _make_job(user):
    return Job.objects.create(
        user=user,
        source=Job.Source.LINKEDIN,
        external_id=f"ext-{user.pk}",
        title="Project Manager",
        company="Acme",
        location="Roma",
        description="Descrizione.",
        apply_url="https://linkedin.com/jobs/view/1",
    )


def _make_cv(job, content=b"%PDF-1.4 cv"):
    document = CVDocument.objects.create(
        job=job, user=job.user, html_source="<html></html>", generation_type="manual"
    )
    document.pdf_file.save("cv.pdf", ContentFile(content), save=True)
    return document


def _jpeg_with_exif(size=(40, 20), orientation=6):
    image = Image.new("RGB", size, color=(200, 10, 10))
    exif = Image.Exif()
    exif[0x0112] = orientation  # Orientation: ruotata di 90°
    exif[0x010F] = "PhoneMaker"  # Make
    exif[0x8825] = {2: (41.0, 54.0, 0.0), 1: "N"}  # GPSInfo
    buffer = BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    return buffer.getvalue()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class SignedDownloadTests(APITestCase):
    def setUp(self):
        self.owner = _make_user("owner@example.com", first_name="Maria", last_name="Rossi")
        self.other = _make_user("other@example.com")
        self.job = _make_job(self.owner)
        self.cv = _make_cv(self.job)

    def test_owner_downloads_with_signed_url_without_authorization_header(self):
        response = self.client.get(signed_document_url("cv", self.cv))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 cv")
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("CV Maria Rossi - Project Manager.pdf", response["Content-Disposition"])

    def test_job_serializer_exposes_signed_urls_not_media_paths(self):
        cover = CoverLetterDocument.objects.create(job=self.job, user=self.owner, html_source="<html></html>")
        cover.pdf_file.save("cover_letter.pdf", ContentFile(b"%PDF-1.4 cl"), save=True)
        self.client.force_authenticate(self.owner)

        data = self.client.get(f"/api/jobs/{self.job.pk}/").data

        self.assertTrue(data["cv_pdf_url"].startswith(f"/api/files/cv/{self.cv.pk}/?s="))
        self.assertTrue(data["cover_letter_pdf_url"].startswith(f"/api/files/cover-letter/{cover.pk}/?s="))
        self.assertNotIn("/media/", data["cv_pdf_url"] + data["cover_letter_pdf_url"])
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(data["cover_letter_pdf_url"]).status_code, 200)

    def test_missing_signature_is_not_found(self):
        self.assertEqual(self.client.get(f"/api/files/cv/{self.cv.pk}/").status_code, 404)

    def test_tampered_signature_is_not_found(self):
        url = signed_document_url("cv", self.cv)
        self.assertEqual(self.client.get(url + "x").status_code, 404)

    def test_signature_for_another_document_is_not_found(self):
        other_cv = _make_cv(self.job, b"%PDF-1.4 other")
        url = signed_document_url("cv", self.cv).replace(f"/cv/{self.cv.pk}/", f"/cv/{other_cv.pk}/")
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_signature_of_one_kind_is_not_valid_for_another(self):
        url = signed_document_url("cv", self.cv).replace("/api/files/cv/", "/api/files/cover-letter/")
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_expired_signature_is_not_found(self):
        url = signed_document_url("cv", self.cv)
        with patch("django.core.signing.time.time", return_value=time.time() + SIGNED_URL_MAX_AGE + 5):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_document_of_another_user_is_not_found_even_if_signed_for_it(self):
        # Firma valida per l'altro utente, ma il documento non è suo.
        self.cv.user_id = self.other.pk
        url = signed_document_url("cv", self.cv)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_media_url_is_not_served_by_django(self):
        self.assertEqual(self.client.get(f"/media/{self.cv.pdf_file.name}").status_code, 404)

    def test_generated_pdf_names_are_random(self):
        self.assertRegex(self.cv.pdf_file.name, RANDOM_PDF_NAME.format(folder="cv_documents"))
        cover = CoverLetterDocument.objects.create(job=self.job, user=self.owner, html_source="<html></html>")
        cover.pdf_file.save("cover_letter.pdf", ContentFile(b"%PDF-1.4 cl"), save=True)
        self.assertRegex(cover.pdf_file.name, RANDOM_PDF_NAME.format(folder="cover_letter_documents"))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfilePhotoTests(APITestCase):
    def setUp(self):
        self.user = _make_user("photo@example.com")
        self.client.force_authenticate(self.user)

    def _upload(self, content, name="foto.jpg", content_type="image/jpeg"):
        return self.client.patch(
            "/api/profiles/me/",
            {"photo": SimpleUploadedFile(name, content, content_type=content_type)},
            format="multipart",
        )

    def test_exif_and_gps_are_removed_and_orientation_is_applied(self):
        response = self._upload(_jpeg_with_exif(size=(40, 20)))

        self.assertEqual(response.status_code, 200)
        profile = Profile.objects.get(user=self.user)
        self.assertRegex(profile.photo.name, r"^profile_photos/[0-9a-f]{32}\.jpg$")
        with Image.open(profile.photo.path) as stored:
            self.assertEqual(len(stored.getexif()), 0)
            self.assertNotIn("exif", stored.info)
            self.assertEqual(stored.size, (20, 40))

    def test_signed_photo_url_serves_only_the_owner_photo(self):
        self._upload(_jpeg_with_exif())
        url = self.client.get("/api/profiles/me/").data["photo_url"]
        self.client.force_authenticate(None)

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(self.client.get("/api/files/photo/").status_code, 404)

    def test_photo_url_is_null_without_photo(self):
        data = self.client.get("/api/profiles/me/").data
        self.assertFalse(data["has_photo"])
        self.assertIsNone(data["photo_url"])
        self.assertIsNone(signed_photo_url(Profile.objects.get(user=self.user)))

    def test_unsupported_format_is_rejected(self):
        buffer = BytesIO()
        Image.new("RGB", (10, 10)).save(buffer, format="GIF")
        response = self._upload(buffer.getvalue(), name="foto.gif", content_type="image/gif")
        self.assertEqual(response.status_code, 400)

    def test_too_large_dimensions_are_rejected(self):
        buffer = BytesIO()
        Image.new("L", (4001, 10)).save(buffer, format="PNG")
        response = self._upload(buffer.getvalue(), name="foto.png", content_type="image/png")
        self.assertEqual(response.status_code, 400)

    def test_file_over_5_mb_is_rejected(self):
        with patch("apps.common.files.PHOTO_MAX_BYTES", 100):
            response = self._upload(_jpeg_with_exif())
        self.assertEqual(response.status_code, 400)


class SecureMediaFilesCommandTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.user = _make_user("legacy@example.com")
        job = _make_job(self.user)
        self.cv = CVDocument.objects.create(job=job, user=self.user, html_source="<html></html>", generation_type="manual")
        self._write("cv_documents/cv_1_1.pdf", b"%PDF-1.4 legacy")
        CVDocument.objects.filter(pk=self.cv.pk).update(pdf_file="cv_documents/cv_1_1.pdf")
        self.profile = Profile.objects.create(user=self.user)
        self._write("profile_photos/mario_rossi.jpg", _jpeg_with_exif())
        Profile.objects.filter(pk=self.profile.pk).update(photo="profile_photos/mario_rossi.jpg")
        self._write("cv_documents/orphan.pdf", b"%PDF-1.4 orphan")

    def _write(self, name, content):
        path = os.path.join(self.media_root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(content)

    def _exists(self, name):
        return os.path.isfile(os.path.join(self.media_root, name))

    def test_dry_run_changes_nothing(self):
        call_command("secure_media_files", "--dry-run", "--delete-orphans", stdout=StringIO())

        self.cv.refresh_from_db()
        self.assertEqual(self.cv.pdf_file.name, "cv_documents/cv_1_1.pdf")
        self.assertTrue(self._exists("cv_documents/cv_1_1.pdf"))
        self.assertTrue(self._exists("cv_documents/orphan.pdf"))

    def test_renames_files_strips_photo_exif_and_is_idempotent(self):
        call_command("secure_media_files", stdout=StringIO())

        self.cv.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertRegex(self.cv.pdf_file.name, RANDOM_PDF_NAME.format(folder="cv_documents"))
        self.assertRegex(self.profile.photo.name, r"^profile_photos/[0-9a-f]{32}\.jpg$")
        self.assertFalse(self._exists("cv_documents/cv_1_1.pdf"))
        self.assertFalse(self._exists("profile_photos/mario_rossi.jpg"))
        with open(self.cv.pdf_file.path, "rb") as handle:
            self.assertEqual(handle.read(), b"%PDF-1.4 legacy")
        with Image.open(self.profile.photo.path) as stored:
            self.assertEqual(len(stored.getexif()), 0)
        self.assertTrue(self._exists("cv_documents/orphan.pdf"))

        names_after_first_run = (self.cv.pdf_file.name, self.profile.photo.name)
        call_command("secure_media_files", stdout=StringIO())
        self.cv.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual((self.cv.pdf_file.name, self.profile.photo.name), names_after_first_run)

    def test_delete_orphans_removes_only_unreferenced_files(self):
        call_command("secure_media_files", "--delete-orphans", stdout=StringIO())

        self.cv.refresh_from_db()
        self.assertFalse(self._exists("cv_documents/orphan.pdf"))
        self.assertTrue(self._exists(self.cv.pdf_file.name))
