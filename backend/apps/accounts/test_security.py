from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.common.testing import LOCMEM_CACHES

from .models import AuthToken
from .tokens import hash_token_key, revoke_all_tokens

User = get_user_model()
PASSWORD = "pw-Security-12345!"
# Sprint 67: le tre spunte obbligatorie della registrazione.
CONSENTS = {"accept_privacy": True, "accept_terms": True, "confirm_age": True}


def _make_user(email="secure@example.com"):
    return User.objects.create_user(username=email, email=email, password=PASSWORD)


class AuthTokenTests(APITestCase):
    def setUp(self):
        self.user = _make_user()

    def _login(self, user_agent="Browser A"):
        response = self.client.post(
            "/api/accounts/login/",
            {"email": self.user.email, "password": PASSWORD},
            format="json",
            HTTP_USER_AGENT=user_agent,
        )
        self.assertEqual(response.status_code, 200)
        return response.data["token"]

    def _me(self, token):
        return self.client.get("/api/accounts/me/", HTTP_AUTHORIZATION=f"Token {token}")

    def test_login_token_authenticates_and_only_its_hash_is_stored(self):
        token = self._login()

        self.assertEqual(self._me(token).status_code, 200)
        stored = AuthToken.objects.get(user=self.user)
        self.assertEqual(stored.key_hash, hash_token_key(token))
        self.assertNotEqual(stored.key_hash, token)
        self.assertFalse(AuthToken.objects.filter(key_hash=token).exists())
        self.assertEqual(stored.user_agent, "Browser A")

    def test_each_login_creates_a_separate_device_token(self):
        first = self._login("Phone")
        second = self._login("Laptop")

        self.assertNotEqual(first, second)
        self.assertEqual(AuthToken.objects.filter(user=self.user).count(), 2)
        self.assertEqual(self._me(first).status_code, 200)
        self.assertEqual(self._me(second).status_code, 200)

    def test_logout_revokes_only_the_current_token(self):
        first = self._login("Phone")
        second = self._login("Laptop")

        response = self.client.post("/api/accounts/logout/", HTTP_AUTHORIZATION=f"Token {first}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self._me(first).status_code, 401)
        self.assertEqual(self._me(second).status_code, 200)

    def test_token_idle_for_more_than_30_days_is_rejected_and_deleted(self):
        token = self._login()
        AuthToken.objects.update(last_used_at=timezone.now() - timedelta(days=31))

        response = self._me(token)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(AuthToken.objects.exists())

    def test_use_within_30_days_slides_the_expiry(self):
        token = self._login()
        AuthToken.objects.update(last_used_at=timezone.now() - timedelta(days=29))

        self.assertEqual(self._me(token).status_code, 200)

        self.assertGreater(AuthToken.objects.get().last_used_at, timezone.now() - timedelta(minutes=1))

    def test_last_used_at_is_written_at_most_once_per_hour(self):
        token = self._login()
        recent = timezone.now() - timedelta(minutes=10)
        AuthToken.objects.update(last_used_at=recent)

        self._me(token)

        self.assertEqual(AuthToken.objects.get().last_used_at, recent)

    def test_unknown_token_is_unauthorized(self):
        self.assertEqual(self._me("not-a-real-token").status_code, 401)

    def test_revoke_all_tokens_disconnects_every_device(self):
        first = self._login("Phone")
        second = self._login("Laptop")

        revoke_all_tokens(self.user)

        self.assertEqual(self._me(first).status_code, 401)
        self.assertEqual(self._me(second).status_code, 401)

    def test_register_returns_a_working_token(self):
        response = self.client.post(
            "/api/accounts/register/", {"email": "new@example.com", "password": PASSWORD, **CONSENTS}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self._me(response.data["token"]).status_code, 200)

    def test_login_error_is_generic_for_unknown_email_and_wrong_password(self):
        unknown = self.client.post(
            "/api/accounts/login/", {"email": "nobody@example.com", "password": PASSWORD}, format="json"
        )
        wrong = self.client.post(
            "/api/accounts/login/", {"email": self.user.email, "password": "wrong-password"}, format="json"
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.data, wrong.data)


class DefaultPermissionTests(APITestCase):
    def test_api_root_requires_authentication(self):
        self.assertEqual(self.client.get("/api/").status_code, 401)

    def test_session_login_does_not_authenticate_the_api(self):
        user = _make_user("session@example.com")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/api/accounts/me/").status_code, 401)


@override_settings(REGISTRATION_INVITE_CODE="invito-segreto")
class InviteCodeTests(APITestCase):
    def _register(self, **extra):
        return self.client.post(
            "/api/accounts/register/",
            {"email": "invited@example.com", "password": PASSWORD, **CONSENTS, **extra},
            format="json",
        )

    def test_missing_or_wrong_code_is_rejected_without_creating_the_user(self):
        self.assertEqual(self._register().status_code, 400)
        response = self._register(invite_code="sbagliato")
        self.assertEqual(response.status_code, 400)
        self.assertIn("invite_code", response.data)
        self.assertFalse(User.objects.filter(email="invited@example.com").exists())

    def test_correct_code_registers(self):
        self.assertEqual(self._register(invite_code="invito-segreto").status_code, 201)

    def test_existing_email_is_not_revealed_without_a_valid_code(self):
        _make_user("invited@example.com")
        response = self._register(invite_code="sbagliato")
        self.assertEqual(list(response.data), ["invite_code"])

    @override_settings(REGISTRATION_INVITE_CODE="")
    def test_empty_setting_means_open_registration(self):
        self.assertEqual(self._register().status_code, 201)


@override_settings(CACHES=LOCMEM_CACHES)
class ThrottlingTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = _make_user("throttle@example.com")

    def _login(self, email, ip):
        return self.client.post(
            "/api/accounts/login/",
            {"email": email, "password": "wrong-password"},
            format="json",
            HTTP_X_FORWARDED_FOR=ip,
        )

    def test_login_is_limited_per_ip(self):
        for index in range(10):
            self.assertEqual(self._login(f"user{index}@example.com", "203.0.113.1").status_code, 400)
        self.assertEqual(self._login("other@example.com", "203.0.113.1").status_code, 429)
        self.assertEqual(self._login("other@example.com", "203.0.113.2").status_code, 400)

    def test_login_is_limited_per_email_across_ips(self):
        for index in range(10):
            self.assertEqual(self._login("throttle@example.com", f"198.51.100.{index}").status_code, 400)
        self.assertEqual(self._login("Throttle@Example.com", "198.51.100.99").status_code, 429)

    def test_registration_is_limited_per_ip(self):
        for index in range(5):
            response = self.client.post(
                "/api/accounts/register/",
                {"email": f"new{index}@example.com", "password": PASSWORD, **CONSENTS},
                format="json",
                HTTP_X_FORWARDED_FOR="192.0.2.10",
            )
            self.assertEqual(response.status_code, 201)
        response = self.client.post(
            "/api/accounts/register/",
            {"email": "new-extra@example.com", "password": PASSWORD, **CONSENTS},
            format="json",
            HTTP_X_FORWARDED_FOR="192.0.2.10",
        )
        self.assertEqual(response.status_code, 429)


@override_settings(CACHES=LOCMEM_CACHES)
class AdminLoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.admin = User.objects.create_superuser(username="admin", email="admin@example.com", password=PASSWORD)

    def _post(self, password):
        return self.client.post(
            "/admin/login/", {"username": "admin", "password": password}, HTTP_X_FORWARDED_FOR="203.0.113.50"
        )

    def test_failed_admin_logins_are_limited_per_ip(self):
        for _ in range(10):
            self.assertEqual(self._post("wrong").status_code, 200)
        self.assertEqual(self._post(PASSWORD).status_code, 429)

    def test_successful_login_resets_the_counter(self):
        for _ in range(9):
            self._post("wrong")
        self.assertEqual(self._post(PASSWORD).status_code, 302)
        self.client.logout()
        for _ in range(9):
            self._post("wrong")
        self.assertEqual(self._post(PASSWORD).status_code, 302)
