import tempfile
from io import BytesIO

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
