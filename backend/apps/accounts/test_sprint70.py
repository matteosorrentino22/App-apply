import re
import tempfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.jobs.models import DailyQuota, Job
from apps.notifications.models import PushSubscription
from apps.profiles.models import Education, Experience, Profile, Skill

from .tokens import create_token

User = get_user_model()

PASSWORD = "pw-Sprint70-12345!"
CONSENTS = {"accept_privacy": True, "accept_terms": True, "confirm_age": True}
EMAIL_ON = {
    "EMAIL_HOST_USER": "sender@example.com",
    "EMAIL_HOST_PASSWORD": "app-password",
    "DEFAULT_FROM_EMAIL": "sender@example.com",
}
EMAIL_OFF = {"EMAIL_HOST_USER": "", "EMAIL_HOST_PASSWORD": ""}
ENDPOINT_A = "https://fcm.googleapis.com/fcm/send/device-a"
ENDPOINT_B = "https://fcm.googleapis.com/fcm/send/device-b"


def _make_user(email, **extra):
    extra.setdefault("email_verified", True)
    return User.objects.create_user(username=email, email=email, password=PASSWORD, **extra)


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Token {create_token(user)}")


def _today_quota(user, **counts):
    return DailyQuota.objects.create(user=user, date=timezone.localtime(timezone.now()).date(), **counts)


class UsageEndpointTests(APITestCase):
    def setUp(self):
        self.user = _make_user("usage@example.com")
        _auth(self.client, self.user)

    def _usage(self):
        response = self.client.get("/api/accounts/usage/")
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_free_user_without_activity(self):
        data = self._usage()

        self.assertEqual(data["plan"], "free")
        self.assertEqual(data["extra_credit"], "0.00")
        self.assertEqual(
            data["actions"]["cv"],
            {"used": 0, "limit": 1, "remaining": 1, "price": "1.50", "next_charge": "included"},
        )
        self.assertEqual(data["actions"]["manual_job"]["limit"], 3)
        self.assertEqual(data["actions"]["manual_job"]["price"], "0.50")
        # Import da link solo Pro, nemmeno a credito.
        self.assertEqual(data["actions"]["import"]["limit"], 0)
        self.assertEqual(data["actions"]["import"]["next_charge"], "unavailable")
        # Raccolta manuale e import CV senza estensione a credito.
        self.assertIsNone(data["actions"]["collection"]["price"])
        self.assertEqual(data["actions"]["cv_import"]["limit"], 5)
        self.assertEqual(data["chat_prices"], {"cv_draft_chat": "0.20", "cover_letter_draft_chat": "0.20"})
        self.assertIn("resets_at", data)

    def test_used_counters_credit_and_blocked(self):
        _today_quota(self.user, manual_cv_count=1, manual_job_count=3, collection_count=1, cover_letter_count=1)
        User.objects.filter(pk=self.user.pk).update(extra_credit=Decimal("1.00"))

        actions = self._usage()["actions"]

        # Oltre il massimale: a credito solo se il saldo copre il prezzo.
        self.assertEqual(actions["cv"]["next_charge"], "blocked")  # 1,50 > 1,00
        self.assertEqual(actions["manual_job"]["next_charge"], "credit")  # 0,50 <= 1,00
        self.assertEqual(actions["manual_job"]["remaining"], 0)
        self.assertEqual(actions["collection"]["next_charge"], "blocked")
        self.assertEqual(actions["referral_message"]["next_charge"], "included")

    def test_pro_limits(self):
        User.objects.filter(pk=self.user.pk).update(plan="pro")
        _today_quota(self.user, import_count=3)

        actions = self._usage()["actions"]

        self.assertEqual(actions["cv"]["limit"], 10)
        self.assertEqual(actions["import"]["limit"], 3)
        self.assertEqual(actions["import"]["next_charge"], "blocked")

    def test_other_days_do_not_count(self):
        DailyQuota.objects.create(
            user=self.user, date=timezone.localtime(timezone.now()).date() - timedelta(days=1), manual_cv_count=1
        )
        self.assertEqual(self._usage()["actions"]["cv"]["used"], 0)

    def test_requires_authentication(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/accounts/usage/").status_code, 401)

    @override_settings(LEGAL_GATE_ENABLED=True)
    def test_behind_the_legal_gate(self):
        response = self.client.get("/api/accounts/usage/")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "legal_acceptance_required")


@override_settings(**EMAIL_OFF)
class TimezoneAndProfileStatusTests(APITestCase):
    def _register(self, **extra):
        payload = {"email": "tz@example.com", "password": PASSWORD, **CONSENTS, **extra}
        return self.client.post("/api/accounts/register/", payload, format="json")

    def test_registration_stores_the_browser_timezone(self):
        self.assertEqual(self._register(timezone="America/New_York").status_code, 201)
        self.assertEqual(User.objects.get(email="tz@example.com").timezone, "America/New_York")

    def test_invalid_or_missing_timezone_keeps_the_default(self):
        self.assertEqual(self._register(timezone="Mars/Olympus").status_code, 201)
        self.assertEqual(User.objects.get(email="tz@example.com").timezone, "Europe/Rome")

    def test_timezone_is_editable_and_validated(self):
        user = _make_user("tz2@example.com")
        _auth(self.client, user)
        self.assertEqual(
            self.client.patch("/api/accounts/me/", {"timezone": "Asia/Tokyo"}, format="json").status_code, 200
        )
        user.refresh_from_db()
        self.assertEqual(user.timezone, "Asia/Tokyo")
        self.assertEqual(
            self.client.patch("/api/accounts/me/", {"timezone": "Nowhere"}, format="json").status_code, 400
        )

    def test_profile_status(self):
        user = _make_user("status@example.com")
        _auth(self.client, user)
        self.assertEqual(self.client.get("/api/accounts/me/").data["profile_status"], "empty")

        profile = Profile.objects.create(user=user)
        self.assertEqual(self.client.get("/api/accounts/me/").data["profile_status"], "empty")

        Experience.objects.create(profile=profile, company="Acme", role="PM")
        self.assertEqual(self.client.get("/api/accounts/me/").data["profile_status"], "incomplete")

        Education.objects.create(profile=profile, institution="Uni", title="Laurea")
        self.assertEqual(self.client.get("/api/accounts/me/").data["profile_status"], "complete")

    def test_objective_statement_is_editable(self):
        user = _make_user("objective@example.com")
        _auth(self.client, user)
        response = self.client.patch(
            "/api/accounts/me/", {"objective_statement": "Passare al product management"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertEqual(user.objective_statement, "Passare al product management")


class LogoutPushTests(APITestCase):
    def setUp(self):
        self.user = _make_user("logout@example.com")
        for endpoint in (ENDPOINT_A, ENDPOINT_B):
            PushSubscription.objects.create(user=self.user, endpoint=endpoint, p256dh_key="k", auth_key="a")
        _auth(self.client, self.user)

    def test_logout_removes_only_the_current_device_subscription(self):
        response = self.client.post("/api/accounts/logout/", {"push_endpoint": ENDPOINT_A}, format="json")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            list(PushSubscription.objects.filter(user=self.user).values_list("endpoint", flat=True)), [ENDPOINT_B]
        )
        self.assertEqual(self.client.get("/api/accounts/me/").status_code, 401)

    def test_logout_without_endpoint_keeps_subscriptions(self):
        self.assertEqual(self.client.post("/api/accounts/logout/").status_code, 204)
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 2)

    def test_logout_cannot_remove_other_users_subscriptions(self):
        other = _make_user("other@example.com")
        PushSubscription.objects.create(user=other, endpoint=ENDPOINT_A, p256dh_key="k", auth_key="a")

        self.client.post("/api/accounts/logout/", {"push_endpoint": ENDPOINT_A}, format="json")

        self.assertTrue(PushSubscription.objects.filter(user=other, endpoint=ENDPOINT_A).exists())


class NotificationRealignTests(APITestCase):
    def setUp(self):
        self.user = _make_user("realign@example.com", notifications_enabled=False)
        long_ago = timezone.now() - timedelta(days=10)
        User.objects.filter(pk=self.user.pk).update(last_notified_at=long_ago)
        job = Job.objects.create(
            user=self.user, source=Job.Source.LINKEDIN, external_id="silence-1", title="Durante il silenzio",
            company="Acme", location="Roma", description="Descrizione.", apply_url="https://linkedin.com/jobs/view/1",
        )
        Job.objects.filter(pk=job.pk).update(date_collected=timezone.now() - timedelta(days=5))
        _auth(self.client, self.user)

    def _assert_realigned(self):
        self.user.refresh_from_db()
        self.assertTrue(self.user.notifications_enabled)
        self.assertGreater(self.user.last_notified_at, timezone.now() - timedelta(minutes=1))

    def test_reenabling_the_preference_realigns_last_notified_at(self):
        response = self.client.patch("/api/accounts/me/", {"notifications_enabled": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self._assert_realigned()

    def test_registering_a_subscription_realigns_last_notified_at(self):
        response = self.client.post(
            "/api/notifications/push-subscriptions/",
            {"endpoint": ENDPOINT_A, "keys": {"p256dh": "k", "auth": "a"}},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self._assert_realigned()

    def test_patch_when_already_enabled_does_not_move_last_notified_at(self):
        User.objects.filter(pk=self.user.pk).update(notifications_enabled=True)
        before = User.objects.get(pk=self.user.pk).last_notified_at

        self.client.patch("/api/accounts/me/", {"notifications_enabled": True}, format="json")

        self.assertEqual(User.objects.get(pk=self.user.pk).last_notified_at, before)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ProfileEditTests(APITestCase):
    def setUp(self):
        self.user = _make_user("profile70@example.com")
        self.profile = Profile.objects.create(user=self.user)
        _auth(self.client, self.user)

    def test_photo_removal_deletes_the_file(self):
        self.profile.photo.save("x.jpg", ContentFile(b"fake image bytes"))
        name = self.profile.photo.name
        self.assertTrue(default_storage.exists(name))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete("/api/profiles/me/photo/")

        self.assertEqual(response.status_code, 204)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.photo)
        self.assertFalse(default_storage.exists(name))
        data = self.client.get("/api/profiles/me/").data
        self.assertFalse(data["has_photo"])
        self.assertIsNone(data["photo_url"])

    def test_photo_removal_without_photo_is_harmless(self):
        self.assertEqual(self.client.delete("/api/profiles/me/photo/").status_code, 204)

    def test_technologies_are_editable(self):
        experience = Experience.objects.create(profile=self.profile, company="Acme", role="Dev", technologies=["Java"])
        response = self.client.patch(
            f"/api/experiences/{experience.id}/", {"technologies": ["Python", "Django"]}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        experience.refresh_from_db()
        self.assertEqual(experience.technologies, ["Python", "Django"])

    def test_new_bullets_are_limited_to_15_by_400(self):
        base = {"company": "Acme", "role": "Dev"}
        self.assertEqual(
            self.client.post("/api/experiences/", {**base, "bullets": ["ok"] * 16}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.post("/api/experiences/", {**base, "bullets": ["x" * 401]}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.post(
                "/api/experiences/", {**base, "bullets": ["x" * 400] * 15}, format="json"
            ).status_code,
            201,
        )

    def test_existing_profiles_over_the_limit_can_still_be_saved(self):
        legacy = ["y" * 900] + [f"bullet {n}" for n in range(19)]  # 20 bullet, uno da 900 caratteri
        experience = Experience.objects.create(profile=self.profile, company="Acme", role="Dev", bullets=legacy)
        url = f"/api/experiences/{experience.id}/"

        # Salvataggio della pagina Profilo: stessi bullet, altro campo cambiato.
        response = self.client.patch(url, {"role": "Senior Dev", "bullets": legacy}, format="json")
        self.assertEqual(response.status_code, 200)
        # Togliere bullet o modificarne uno corto resta possibile.
        trimmed = legacy[:10] + ["bullet modificato"]
        self.assertEqual(self.client.patch(url, {"bullets": trimmed}, format="json").status_code, 200)
        # Ma non si può crescere oltre il numero attuale né aggiungere testi lunghi nuovi.
        self.assertEqual(
            self.client.patch(url, {"bullets": legacy + ["uno in più"]}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.patch(url, {"bullets": trimmed + ["z" * 401]}, format="json").status_code, 400
        )

    def test_number_of_section_items_is_capped(self):
        Skill.objects.bulk_create([Skill(profile=self.profile, name=f"skill {n}") for n in range(100)])
        response = self.client.post("/api/skills/", {"name": "una di troppo"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Skill.objects.filter(profile=self.profile).count(), 100)


def _mock_pdf(text):
    page = MagicMock()
    page.extract_text.return_value = text
    pdf = MagicMock()
    pdf.pages = [page]
    pdf.__enter__.return_value = pdf
    return pdf


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class CvImportErrorCodeTests(APITestCase):
    def setUp(self):
        self.user = _make_user("cvimport70@example.com")
        _auth(self.client, self.user)

    def _post(self, content=b"%PDF-1.4 fake", name="cv.pdf"):
        upload = SimpleUploadedFile(name, content, content_type="application/pdf")
        return self.client.post("/api/profile/import-cv/", {"file": upload}, format="multipart")

    def test_file_codes(self):
        with patch("apps.profiles.cv_import.MAX_UPLOAD_BYTES", 10):
            self.assertEqual(self._post().data["code"], "file_too_large")
        self.assertEqual(self._post(content=b"just text").data["code"], "unsupported_type")
        self.assertEqual(
            self.client.post("/api/profile/import-cv/", {}, format="multipart").data["code"], "file_missing"
        )

    @patch("apps.profiles.cv_import.pdfplumber.open")
    def test_too_many_pages_code(self, mock_open):
        pdf = _mock_pdf("testo")
        pdf.pages = [MagicMock()] * 11
        mock_open.return_value = pdf
        response = self._post()
        self.assertEqual((response.status_code, response.data["code"]), (400, "too_many_pages"))

    @patch("apps.profiles.cv_import.pdfplumber.open")
    @patch("apps.profiles.cv_import.call_claude_structured", side_effect=RuntimeError("bedrock down"))
    def test_ai_unavailable_and_quota_codes(self, mock_claude, mock_open):
        mock_open.return_value = _mock_pdf("Testo del CV abbastanza lungo da superare la soglia minima.")
        with self.assertLogs("apps.profiles.views", level="ERROR"):
            response = self._post()
        self.assertEqual((response.status_code, response.data["code"]), (502, "ai_unavailable"))

        DailyQuota.objects.filter(user=self.user).update(cv_import_count=5)
        response = self._post()
        self.assertEqual((response.status_code, response.data["code"]), (409, "quota_exceeded"))


def _email_change_token():
    match = re.search(r"https?://\S+/confirm-email-change\?\S+", mail.outbox[0].body)
    return parse_qs(urlsplit(match.group(0)).query)["t"][0]


@override_settings(**EMAIL_ON)
class EmailChangeTests(APITestCase):
    def setUp(self):
        self.user = _make_user("old@example.com")
        _auth(self.client, self.user)

    def _request(self, new_email="new@example.com", password=PASSWORD):
        return self.client.post(
            "/api/accounts/email/change/", {"password": password, "new_email": new_email}, format="json"
        )

    def _confirm(self, token):
        self.client.credentials()
        return self.client.post("/api/accounts/email/change/confirm/", {"token": token}, format="json")

    def test_request_sends_confirmation_to_new_and_notice_to_old(self):
        response = self._request()

        self.assertEqual(response.status_code, 200)
        self.assertEqual([m.to for m in mail.outbox], [["new@example.com"], ["old@example.com"]])
        self.assertIn("/confirm-email-change?t=", mail.outbox[0].body)
        self.assertNotIn("confirm-email-change", mail.outbox[1].body)
        # Prima della conferma l'email di accesso non cambia.
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")

    def test_confirmation_changes_the_login_email(self):
        self._request(new_email="New@Example.com")
        token = _email_change_token()

        response = self._confirm(token)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual((self.user.email, self.user.username), ("new@example.com", "new@example.com"))
        self.assertTrue(self.user.email_verified)
        login = self.client.post(
            "/api/accounts/login/", {"email": "new@example.com", "password": PASSWORD}, format="json"
        )
        self.assertEqual(login.status_code, 200)
        old_login = self.client.post(
            "/api/accounts/login/", {"email": "old@example.com", "password": PASSWORD}, format="json"
        )
        self.assertEqual(old_login.status_code, 400)
        # Il link non vale una seconda volta (l'email attuale è cambiata).
        self.assertEqual(self._confirm(token).data["code"], "invalid")

    def test_wrong_password_or_same_email(self):
        self.assertEqual(self._request(password="wrong").status_code, 400)
        self.assertEqual(self._request(new_email="OLD@example.com").status_code, 400)
        self.assertEqual(mail.outbox, [])

    def test_taken_address_gets_the_same_response_and_no_email(self):
        _make_user("taken@example.com")
        response = self._request(new_email="taken@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "confirmation_sent"})
        self.assertEqual(mail.outbox, [])

    def test_address_taken_before_confirmation(self):
        self._request()
        token = _email_change_token()
        _make_user("new@example.com")

        response = self._confirm(token)

        self.assertEqual(response.data["code"], "email_taken")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")

    def test_tampered_and_expired_links(self):
        self._request()
        token = _email_change_token()
        self.assertEqual(self._confirm(token + "x").data["code"], "invalid")
        with patch("apps.accounts.emails.signing.TimestampSigner.unsign_object", side_effect=signing.SignatureExpired):
            self.assertEqual(self._confirm(token).data["code"], "expired")

    @override_settings(**EMAIL_OFF)
    def test_not_available_without_email(self):
        response = self._request()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "email_unavailable")
