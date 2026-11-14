import importlib
import io
import json
import re
import tempfile
import time
import zipfile
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.testing import LOCMEM_CACHES
from apps.cv.models import CoverLetterDocument, CoverLetterDraft, CVDocument, CVDraft, ReferralMessageDocument
from apps.jobs.models import DailyQuota, Job, JobFilterPreset, RunLog
from apps.notifications.models import PushSubscription
from apps.notifications.tasks import send_inactivity_notifications, send_morning_notification_for_user
from apps.profiles.models import Experience, Profile, Skill
from apps.searches.models import SavedSearch

from .legal import AGE_VERSION, PRIVACY_VERSION, TERMS_VERSION, record_acceptances
from .models import AuthToken, LegalAcceptance
from .tokens import create_token

User = get_user_model()

PASSWORD = "pw-Privacy-12345!"
CONSENTS = {"accept_privacy": True, "accept_terms": True, "confirm_age": True}
EMAIL_ON = {
    "EMAIL_HOST_USER": "sender@example.com",
    "EMAIL_HOST_PASSWORD": "app-password",
    "DEFAULT_FROM_EMAIL": "sender@example.com",
}
EMAIL_OFF = {"EMAIL_HOST_USER": "", "EMAIL_HOST_PASSWORD": ""}


def _make_user(email, **extra):
    extra.setdefault("email_verified", True)
    return User.objects.create_user(username=email, email=email, password=PASSWORD, **extra)


def _auth(client, user):
    client.credentials(HTTP_AUTHORIZATION=f"Token {create_token(user)}")


def _query_from_last_email(path):
    match = re.search(rf"https?://\S+{path}\?\S+", mail.outbox[-1].body)
    return {key: values[0] for key, values in parse_qs(urlsplit(match.group(0)).query).items()}


@override_settings(**EMAIL_OFF)
class RegistrationConsentTests(APITestCase):
    def _register(self, **overrides):
        payload = {"email": "new@example.com", "password": PASSWORD, **CONSENTS, **overrides}
        return self.client.post("/api/accounts/register/", payload, format="json")

    def test_registration_without_consents_is_rejected(self):
        response = self.client.post(
            "/api/accounts/register/", {"email": "new@example.com", "password": PASSWORD}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        for field in CONSENTS:
            self.assertIn(field, response.data)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_each_consent_must_be_true(self):
        for field in CONSENTS:
            with self.subTest(field=field):
                response = self._register(**{field: False})
                self.assertEqual(response.status_code, 400)
                self.assertIn(field, response.data)
        self.assertFalse(User.objects.exists())

    def test_registration_records_current_versions(self):
        response = self._register()

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="new@example.com")
        self.assertEqual(
            set(user.legal_acceptances.values_list("document", "version")),
            {("privacy", PRIVACY_VERSION), ("terms", TERMS_VERSION), ("age", AGE_VERSION)},
        )
        me = self.client.get("/api/accounts/me/", HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        self.assertFalse(me.data["legal_acceptance_required"])
        self.assertEqual(me.data["legal_acceptances"]["privacy"]["version"], PRIVACY_VERSION)

    def test_acceptances_are_append_only(self):
        user = _make_user("a@example.com")
        record_acceptances(user)
        acceptance = user.legal_acceptances.first()
        acceptance.version = "9.9"
        with self.assertRaises(ValueError):
            acceptance.save()


@override_settings(LEGAL_GATE_ENABLED=True, **EMAIL_OFF)
class LegalGateTests(APITestCase):
    def setUp(self):
        self.user = _make_user("gated@example.com")
        _auth(self.client, self.user)

    def test_user_without_acceptance_gets_403_with_code(self):
        for path in ["/api/jobs/", "/api/searches/", "/api/profiles/me/", "/api/notifications/vapid-public-key/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.data["code"], "legal_acceptance_required")

    def test_exempt_endpoints_stay_available(self):
        me = self.client.get("/api/accounts/me/")
        self.assertEqual(me.status_code, 200)
        self.assertTrue(me.data["legal_acceptance_required"])
        self.assertEqual(set(me.data["legal_missing"]), {"privacy", "terms", "age"})
        self.assertEqual(self.client.patch("/api/accounts/me/", {"interface_language": "en"}, format="json").status_code, 200)
        self.assertEqual(self.client.get("/api/legal/").status_code, 200)
        self.assertEqual(self.client.post("/api/accounts/export/").status_code, 200)
        self.assertEqual(
            self.client.post(
                "/api/accounts/password/change/",
                {"old_password": "wrong", "new_password": "x"},
                format="json",
            ).status_code,
            400,
        )
        self.assertEqual(self.client.post("/api/accounts/delete/", {}, format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/accounts/logout/").status_code, 204)

    def test_acceptance_endpoint_requires_all_three_and_opens_the_gate(self):
        response = self.client.post(
            "/api/accounts/legal-acceptance/", {**CONSENTS, "confirm_age": False}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(LegalAcceptance.objects.exists())

        response = self.client.post("/api/accounts/legal-acceptance/", CONSENTS, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["legal_acceptance_required"])
        self.assertEqual(LegalAcceptance.objects.filter(user=self.user).count(), 3)
        self.assertEqual(self.client.get("/api/jobs/").status_code, 200)

    def test_new_version_of_a_document_closes_the_gate_again(self):
        record_acceptances(self.user)
        LegalAcceptance.objects.filter(user=self.user, document="terms").delete()
        LegalAcceptance.objects.create(user=self.user, document="terms", version="0.9")

        response = self.client.get("/api/jobs/")

        self.assertEqual(response.status_code, 403)
        self.client.post("/api/accounts/legal-acceptance/", CONSENTS, format="json")
        self.assertEqual(
            list(self.user.legal_acceptances.filter(document="terms").values_list("version", flat=True)),
            ["0.9", TERMS_VERSION],
        )
        self.assertEqual(self.client.get("/api/jobs/").status_code, 200)

    def test_unauthenticated_requests_still_get_401(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/jobs/").status_code, 401)


class LegalInfoTests(APITestCase):
    @override_settings(
        LEGAL_CONTROLLER_NAME="Titolare di prova",
        LEGAL_CONTROLLER_ADDRESS="",
        LEGAL_CONTROLLER_EMAIL="privacy@example.com",
        **EMAIL_OFF,
    )
    def test_public_endpoint_exposes_versions_controller_and_flags(self):
        response = self.client.get("/api/legal/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["privacy"]["version"], PRIVACY_VERSION)
        self.assertEqual(response.data["terms"]["version"], TERMS_VERSION)
        self.assertEqual(response.data["min_age"], 16)
        self.assertEqual(response.data["controller"]["name"], "Titolare di prova")
        self.assertTrue(response.data["controller"]["complete"])
        self.assertFalse(response.data["email_enabled"])
        self.assertIn("google_login_enabled", response.data)

    @override_settings(LEGAL_CONTROLLER_NAME="", LEGAL_CONTROLLER_EMAIL="")
    def test_missing_controller_is_flagged_incomplete(self):
        self.assertFalse(self.client.get("/api/legal/").data["controller"]["complete"])

    def test_google_flag_follows_client_id(self):
        providers = {"google": {"APPS": [{"client_id": "", "secret": "", "key": ""}]}}
        with override_settings(SOCIALACCOUNT_PROVIDERS=providers):
            self.assertFalse(self.client.get("/api/legal/").data["google_login_enabled"])
        providers["google"]["APPS"][0]["client_id"] = "abc.apps.googleusercontent.com"
        with override_settings(SOCIALACCOUNT_PROVIDERS=providers):
            self.assertTrue(self.client.get("/api/legal/").data["google_login_enabled"])


@override_settings(**EMAIL_ON)
class EmailVerificationTests(APITestCase):
    def _register(self, email="new@example.com", language="it"):
        return self.client.post(
            "/api/accounts/register/",
            {"email": email, "password": PASSWORD, "interface_language": language, **CONSENTS},
            format="json",
        )

    def _login(self, email="new@example.com"):
        return self.client.post("/api/accounts/login/", {"email": email, "password": PASSWORD}, format="json")

    def _token_from_email(self):
        return _query_from_last_email("/verify-email")["t"]

    def test_registration_sends_link_and_login_waits_for_verification(self):
        response = self._register()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data, {"verification_required": True})
        user = User.objects.get(email="new@example.com")
        self.assertFalse(user.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["new@example.com"])
        self.assertEqual(mail.outbox[0].from_email, "sender@example.com")
        self.assertIn("Conferma", mail.outbox[0].subject)

        response = self._login()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["code"], "email_not_verified")
        self.assertFalse(AuthToken.objects.exists())

        response = self.client.post("/api/accounts/verify-email/", {"token": self._token_from_email()}, format="json")
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertEqual(self._login().status_code, 200)

    def test_email_follows_the_interface_language(self):
        self._register(language="en")
        self.assertIn("Confirm your email", mail.outbox[0].subject)

    def test_wrong_password_never_reveals_verification_state(self):
        self._register()
        response = self.client.post(
            "/api/accounts/login/", {"email": "new@example.com", "password": "wrong"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("code", response.data)

    def test_expired_link_is_rejected(self):
        self._register()
        token = self._token_from_email()
        later = time.time() + settings.EMAIL_VERIFICATION_MAX_AGE + 60
        with patch("django.core.signing.time.time", return_value=later):
            response = self.client.post("/api/accounts/verify-email/", {"token": token}, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "expired")
        self.assertFalse(User.objects.get(email="new@example.com").email_verified)

    def test_tampered_link_is_rejected(self):
        self._register()
        token = self._token_from_email()
        other = _make_user("other@example.com", email_verified=False)
        forged = token.replace(f"{User.objects.get(email='new@example.com').pk}:", f"{other.pk}:", 1)

        for bad in [forged, token[:-2] + "xx", "garbage"]:
            with self.subTest(token=bad):
                response = self.client.post("/api/accounts/verify-email/", {"token": bad}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["code"], "invalid")
        other.refresh_from_db()
        self.assertFalse(other.email_verified)

    def test_resend_is_generic_and_only_sends_to_unverified_accounts(self):
        self._register()
        _make_user("verified@example.com")
        mail.outbox.clear()

        responses = [
            self.client.post("/api/accounts/verify-email/resend/", {"email": email}, format="json")
            for email in ["new@example.com", "verified@example.com", "nobody@example.com"]
        ]

        self.assertEqual({r.status_code for r in responses}, {200})
        self.assertEqual(len({json.dumps(r.data) for r in responses}), 1)
        self.assertEqual([m.to for m in mail.outbox], [["new@example.com"]])

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_resend_is_throttled_per_address(self):
        from django.core.cache import cache

        cache.clear()
        statuses = [
            self.client.post(
                "/api/accounts/verify-email/resend/", {"email": "victim@example.com"}, format="json"
            ).status_code
            for _ in range(4)
        ]
        cache.clear()
        self.assertEqual(statuses, [200, 200, 200, 429])

    def test_existing_email_is_not_revealed_at_registration(self):
        _make_user("taken@example.com")

        new = self._register("fresh@example.com")
        taken = self._register("TAKEN@example.com")

        self.assertEqual((new.status_code, new.data), (taken.status_code, taken.data))
        self.assertEqual(User.objects.filter(email__iexact="taken@example.com").count(), 1)
        self.assertEqual(mail.outbox[-1].to, ["taken@example.com"])
        self.assertIn("Tentativo di registrazione", mail.outbox[-1].subject)
        self.assertNotIn("/verify-email", mail.outbox[-1].body)


class ExistingUsersMigrationTests(TestCase):
    def test_data_migration_marks_existing_users_verified(self):
        _make_user("old1@example.com", email_verified=False)
        _make_user("old2@example.com", email_verified=False)
        migration = importlib.import_module("apps.accounts.migrations.0010_mark_existing_users_verified")

        migration.mark_existing_users_verified(django_apps, None)

        self.assertFalse(User.objects.filter(email_verified=False).exists())


@override_settings(**EMAIL_OFF)
class EmailNotConfiguredTests(APITestCase):
    def test_registration_keeps_the_previous_flow(self):
        response = self.client.post(
            "/api/accounts/register/", {"email": "new@example.com", "password": PASSWORD, **CONSENTS}, format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("token", response.data)
        self.assertTrue(User.objects.get(email="new@example.com").email_verified)
        self.assertEqual(mail.outbox, [])

    def test_unverified_users_can_log_in_and_duplicates_are_reported(self):
        _make_user("old@example.com", email_verified=False)

        login = self.client.post("/api/accounts/login/", {"email": "old@example.com", "password": PASSWORD}, format="json")
        duplicate = self.client.post(
            "/api/accounts/register/", {"email": "old@example.com", "password": PASSWORD, **CONSENTS}, format="json"
        )

        self.assertEqual(login.status_code, 200)
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("email", duplicate.data)

    def test_password_reset_and_resend_are_unavailable(self):
        for path in ["/api/accounts/password-reset/", "/api/accounts/verify-email/resend/"]:
            with self.subTest(path=path):
                response = self.client.post(path, {"email": "x@example.com"}, format="json")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.data["code"], "email_unavailable")

    def test_service_email_task_does_not_send(self):
        from .tasks import send_service_email

        self.assertFalse(send_service_email("x@example.com", "s", "b"))
        self.assertEqual(mail.outbox, [])


@override_settings(**EMAIL_ON)
class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = _make_user("reset@example.com")
        self.old_token = create_token(self.user)

    def _request(self, email):
        return self.client.post("/api/accounts/password-reset/", {"email": email}, format="json")

    def _reset_params(self):
        query = _query_from_last_email("/reset-password")
        return query["uid"], query["token"]

    def test_response_is_the_same_for_known_and_unknown_addresses(self):
        known = self._request("reset@example.com")
        unknown = self._request("nobody@example.com")

        self.assertEqual((known.status_code, known.data), (unknown.status_code, unknown.data))
        self.assertEqual([m.to for m in mail.outbox], [["reset@example.com"]])

    def test_reset_changes_password_and_revokes_every_token(self):
        self._request("reset@example.com")
        uid, token = self._reset_params()

        response = self.client.post(
            "/api/accounts/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "brand-New-pass-987"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brand-New-pass-987"))
        self.assertFalse(AuthToken.objects.filter(user=self.user).exists())
        self.assertEqual(
            self.client.get("/api/accounts/me/", HTTP_AUTHORIZATION=f"Token {self.old_token}").status_code, 401
        )
        # Il link vale una sola volta: dopo il cambio di password il token Django non è più valido.
        again = self.client.post(
            "/api/accounts/password-reset/confirm/",
            {"uid": uid, "token": token, "new_password": "another-Pass-654"},
            format="json",
        )
        self.assertEqual(again.status_code, 400)

    def test_invalid_link_and_weak_password_are_rejected(self):
        self._request("reset@example.com")
        uid, token = self._reset_params()

        bad_token = self.client.post(
            "/api/accounts/password-reset/confirm/",
            {"uid": uid, "token": "1-abc", "new_password": "brand-New-pass-987"},
            format="json",
        )
        weak = self.client.post(
            "/api/accounts/password-reset/confirm/", {"uid": uid, "token": token, "new_password": "123"}, format="json"
        )

        self.assertEqual(bad_token.status_code, 400)
        self.assertEqual(bad_token.data["code"], "invalid_link")
        self.assertEqual(weak.status_code, 400)
        self.assertIn("new_password", weak.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))


class ChangePasswordTests(APITestCase):
    def setUp(self):
        self.user = _make_user("change@example.com")
        self.other_device = create_token(self.user)
        self.current = create_token(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.current}")

    def test_wrong_old_password_or_weak_new_password_is_rejected(self):
        wrong = self.client.post(
            "/api/accounts/password/change/", {"old_password": "nope", "new_password": "brand-New-pass-987"}, format="json"
        )
        weak = self.client.post(
            "/api/accounts/password/change/", {"old_password": PASSWORD, "new_password": "12345678"}, format="json"
        )

        self.assertEqual(wrong.status_code, 400)
        self.assertIn("old_password", wrong.data)
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(AuthToken.objects.filter(user=self.user).count(), 2)

    def test_change_revokes_all_tokens_and_returns_a_new_one(self):
        response = self.client.post(
            "/api/accounts/password/change/", {"old_password": PASSWORD, "new_password": "brand-New-pass-987"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brand-New-pass-987"))
        self.assertEqual(AuthToken.objects.filter(user=self.user).count(), 1)
        self.client.credentials()
        for old in (self.current, self.other_device):
            self.assertEqual(self.client.get("/api/accounts/me/", HTTP_AUTHORIZATION=f"Token {old}").status_code, 401)
        self.assertEqual(
            self.client.get("/api/accounts/me/", HTTP_AUTHORIZATION=f"Token {response.data['token']}").status_code,
            200,
        )


def _populate(user, tag):
    """Un utente con tutti i tipi di dati e di file."""
    record_acceptances(user)
    profile = Profile.objects.create(user=user, summary=f"Sommario {tag}", phone="+39 000")
    profile.photo.save("photo.jpg", ContentFile(b"jpeg-" + tag.encode()), save=True)
    Experience.objects.create(profile=profile, company=f"Azienda {tag}", role="PM")
    Skill.objects.create(profile=profile, name=f"Skill {tag}")
    SavedSearch.objects.create(user=user, keywords=f"ricerca {tag}", city="Roma", country="Italia")
    job = Job.objects.create(
        user=user, external_id=f"ext-{tag}", title=f"Job {tag}", company="Acme", location="Roma",
        description="Descrizione.", score=8, score_match=["match"], score_gaps=["gap"],
    )
    cv = CVDocument.objects.create(job=job, user=user, html_source="<html></html>", generation_type="manual",
                                   content_json={"summary": f"cv {tag}"})
    cv.pdf_file.save("cv.pdf", ContentFile(b"%PDF cv " + tag.encode()), save=True)
    letter = CoverLetterDocument.objects.create(job=job, user=user, html_source="<html></html>")
    letter.pdf_file.save("cover_letter.pdf", ContentFile(b"%PDF cl " + tag.encode()), save=True)
    CVDraft.objects.create(job=job, user=user, content_json={"a": 1}, chat_history=[{"role": "user", "text": tag}])
    CoverLetterDraft.objects.create(job=job, user=user, content_json={"b": 2})
    ReferralMessageDocument.objects.create(
        job=job, user=user, channel="email", recipient_name=f"Destinatario {tag}", content=f"Messaggio {tag}"
    )
    JobFilterPreset.objects.create(user=user, name=f"Preset {tag}")
    DailyQuota.objects.create(user=user, date=timezone.localdate(), manual_cv_count=1)
    PushSubscription.objects.create(
        user=user, endpoint=f"https://fcm.googleapis.com/fcm/send/{tag}", p256dh_key="P256-SECRET", auth_key="AUTH-SECRET"
    )
    RunLog.objects.create(user=user, job=job, task_type="cv_generation", status="failure",
                          message=f"errore con dati di {tag}", started_at=timezone.now())
    create_token(user)
    return [cv.pdf_file.name, letter.pdf_file.name, profile.photo.name]


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(), **EMAIL_ON)
class DeleteAccountTests(APITestCase):
    def setUp(self):
        self.user = _make_user("delete@example.com", interface_language="en")
        self.files = _populate(self.user, "mine")
        self.other = _make_user("keep@example.com")
        self.other_files = _populate(self.other, "theirs")
        _auth(self.client, self.user)

    def test_wrong_password_or_missing_confirmation_deletes_nothing(self):
        for payload in [{"password": "wrong", "confirm": True}, {"password": PASSWORD, "confirm": False}, {}]:
            with self.subTest(payload=payload):
                response = self.client.post("/api/accounts/delete/", payload, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        self.assertTrue(all(default_storage.exists(name) for name in self.files))

    def test_deletion_removes_every_row_and_file_of_the_user(self):
        user_id = self.user.pk
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post("/api/accounts/delete/", {"password": PASSWORD, "confirm": True}, format="json")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=user_id).exists())
        # Nessuna riga di nessun modello punta più all'utente.
        for model in django_apps.get_models():
            for field in model._meta.get_fields():
                if getattr(field, "related_model", None) is User and field.many_to_one and field.concrete:
                    with self.subTest(model=model.__name__, field=field.name):
                        self.assertFalse(model.objects.filter(**{field.attname: user_id}).exists())
        self.assertFalse(Profile.objects.filter(summary="Sommario mine").exists())
        self.assertFalse(Job.objects.filter(title="Job mine").exists())
        self.assertFalse(PushSubscription.objects.filter(endpoint__endswith="/mine").exists())
        # I RunLog restano senza utente e senza testo.
        self.assertFalse(RunLog.objects.filter(message__contains="mine").exists())
        self.assertTrue(RunLog.objects.filter(user__isnull=True, message="").exists())
        # File su disco eliminati, quelli dell'altro utente no.
        self.assertFalse(any(default_storage.exists(name) for name in self.files))
        self.assertTrue(all(default_storage.exists(name) for name in self.other_files))
        self.assertTrue(Job.objects.filter(user=self.other).exists())
        self.assertTrue(RunLog.objects.filter(message__contains="theirs").exists())
        # Email di conferma all'indirizzo catturato prima, nella lingua dell'utente.
        self.assertEqual(mail.outbox[-1].to, ["delete@example.com"])
        self.assertIn("deleted", mail.outbox[-1].subject)

    def test_deleting_the_user_elsewhere_also_cleans_files_and_logs(self):
        # Stessa pulizia per una cancellazione da Django Admin o da shell.
        with self.captureOnCommitCallbacks(execute=True):
            User.objects.get(pk=self.user.pk).delete()

        self.assertFalse(any(default_storage.exists(name) for name in self.files))
        self.assertFalse(RunLog.objects.filter(message__contains="mine").exists())
        self.assertTrue(all(default_storage.exists(name) for name in self.other_files))

    def test_token_no_longer_works_after_deletion(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post("/api/accounts/delete/", {"password": PASSWORD, "confirm": True}, format="json")
        self.assertEqual(self.client.get("/api/accounts/me/").status_code, 401)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class DataExportTests(APITestCase):
    def setUp(self):
        self.user = _make_user("export@example.com")
        _populate(self.user, "mine")
        self.other = _make_user("someone-else@example.com")
        _populate(self.other, "theirs")
        _auth(self.client, self.user)

    def _download(self):
        url = self.client.post("/api/accounts/export/").data["url"]
        self.client.credentials()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))

    def test_zip_contains_all_user_data_and_files(self):
        archive = self._download()
        names = archive.namelist()
        data = json.loads(archive.read("dati.json"))

        self.assertIn("README.txt", names)
        self.assertEqual(data["account"]["email"], "export@example.com")
        self.assertEqual(len(data["legal_acceptances"]), 3)
        self.assertEqual(data["profile"]["summary"], "Sommario mine")
        self.assertEqual(data["profile"]["experiences"][0]["company"], "Azienda mine")
        self.assertEqual(data["saved_searches"][0]["keywords"], "ricerca mine")
        self.assertEqual(data["jobs"][0]["score"], 8)
        self.assertEqual(data["jobs"][0]["score_gaps"], ["gap"])
        self.assertEqual(data["cv_documents"][0]["content_json"], {"summary": "cv mine"})
        self.assertEqual(data["cv_drafts"][0]["chat_history"][0]["text"], "mine")
        self.assertEqual(data["referral_messages"][0]["recipient_name"], "Destinatario mine")
        self.assertEqual(data["job_filter_presets"][0]["name"], "Preset mine")
        self.assertEqual(len(data["push_subscriptions"]), 1)
        for entry in (data["cv_documents"][0]["file"], data["cover_letter_documents"][0]["file"], data["profile"]["photo_file"]):
            self.assertIn(entry, names)
        self.assertEqual(archive.read(data["cv_documents"][0]["file"]), b"%PDF cv mine")
        self.assertEqual(archive.read(data["profile"]["photo_file"]), b"jpeg-mine")

    def test_zip_has_no_secrets_and_no_other_user_data(self):
        archive = self._download()
        everything = b"".join(archive.read(name) for name in archive.namelist())
        raw_json = archive.read("dati.json").decode()

        self.assertNotIn(self.user.password, raw_json)
        self.assertNotIn('"password"', raw_json)
        self.assertNotIn("key_hash", raw_json)
        self.assertNotIn("P256-SECRET", raw_json)
        self.assertNotIn("AUTH-SECRET", raw_json)
        self.assertNotIn(b"theirs", everything)
        self.assertNotIn(b"someone-else@example.com", everything)

    def test_download_url_is_signed(self):
        url = self.client.post("/api/accounts/export/").data["url"]
        self.client.credentials()

        self.assertEqual(self.client.get(url[:-3] + "abc").status_code, 404)
        self.assertEqual(self.client.get("/api/accounts/export/download/").status_code, 404)
        later = time.time() + 11 * 60
        with patch("django.core.signing.time.time", return_value=later):
            self.assertEqual(self.client.get(url).status_code, 404)

    @override_settings(CACHES=LOCMEM_CACHES)
    def test_export_is_limited_to_three_per_day(self):
        from django.core.cache import cache

        cache.clear()
        statuses = [self.client.post("/api/accounts/export/").status_code for _ in range(4)]
        cache.clear()
        self.assertEqual(statuses, [200, 200, 200, 429])

    @override_settings(LEGAL_GATE_ENABLED=True)
    def test_export_works_without_current_acceptances(self):
        LegalAcceptance.objects.filter(user=self.user).delete()
        self.assertEqual(self.client.get("/api/jobs/").status_code, 403)
        archive = self._download()
        self.assertEqual(json.loads(archive.read("dati.json"))["legal_acceptances"], [])


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class PhotoReplacementTests(APITestCase):
    def test_replacing_the_photo_deletes_the_previous_file(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        user = _make_user("photo@example.com")
        profile = Profile.objects.create(user=user)
        self.client.force_authenticate(user)

        def upload():
            buffer = BytesIO()
            Image.new("RGB", (10, 10)).save(buffer, format="PNG")
            file = SimpleUploadedFile("p.png", buffer.getvalue(), content_type="image/png")
            response = self.client.patch("/api/profiles/me/", {"photo": file}, format="multipart")
            self.assertEqual(response.status_code, 200)
            profile.refresh_from_db()
            return profile.photo.name

        first = upload()
        second = upload()

        self.assertNotEqual(first, second)
        self.assertFalse(default_storage.exists(first))
        self.assertTrue(default_storage.exists(second))


class NotificationPreferenceTests(APITestCase):
    def setUp(self):
        self.user = _make_user("notify@example.com", timezone="Europe/Rome")
        PushSubscription.objects.create(
            user=self.user, endpoint="https://fcm.googleapis.com/fcm/send/a", p256dh_key="k", auth_key="a"
        )
        PushSubscription.objects.create(
            user=self.user, endpoint="https://fcm.googleapis.com/fcm/send/b", p256dh_key="k", auth_key="a"
        )
        self.client.force_authenticate(self.user)

    def test_turning_notifications_off_removes_subscriptions(self):
        response = self.client.patch("/api/accounts/me/", {"notifications_enabled": False}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["notifications_enabled"])
        self.assertFalse(PushSubscription.objects.filter(user=self.user).exists())

    def test_tasks_skip_users_with_notifications_off(self):
        User.objects.filter(pk=self.user.pk).update(
            notifications_enabled=False,
            last_activity_reset=timezone.now() - timedelta(days=30),
            last_notified_at=timezone.now() - timedelta(days=30),
        )
        self.user.refresh_from_db()
        Job.objects.create(user=self.user, external_id="n1", title="T", company="C", location="L", description="D")

        with patch("apps.notifications.tasks.send_web_push") as send, patch(
            "apps.notifications.tasks._is_around_ten_local", return_value=True
        ):
            self.assertFalse(send_morning_notification_for_user(self.user))
            send_inactivity_notifications()
        send.assert_not_called()

    def test_subscribing_a_device_turns_the_preference_back_on(self):
        User.objects.filter(pk=self.user.pk).update(notifications_enabled=False)
        self.user.refresh_from_db()

        response = self.client.post(
            "/api/notifications/push-subscriptions/",
            {"endpoint": "https://fcm.googleapis.com/fcm/send/c", "keys": {"p256dh": "k", "auth": "a"}},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.user.refresh_from_db()
        self.assertTrue(self.user.notifications_enabled)
