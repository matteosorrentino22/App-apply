from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

User = get_user_model()


class MeEndpointTests(APITestCase):
    """Copertura mirata sul campo `extra_credit` aggiunto in Sprint 20 (la
    schermata account mostra il saldo credito, gestito solo da
    amministratore): nessun test preesistente su questo endpoint."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="account@example.com",
            email="account@example.com",
            password="pw-Account-12345!",
            extra_credit=Decimal("12.50"),
        )
        self.client.force_authenticate(self.user)

    def test_me_exposes_plan_and_credit(self):
        response = self.client.get("/api/accounts/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["plan"], "free")
        self.assertEqual(response.data["extra_credit"], "12.50")

    def test_extra_credit_is_read_only(self):
        response = self.client.patch("/api/accounts/me/", {"extra_credit": "999.00"}, format="json")

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.extra_credit, Decimal("12.50"))


class SetE2eAccountCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="e2e-account@example.com",
            email="e2e-account@example.com",
            password="pw-E2eAcc-12345!",
        )

    @override_settings(DEBUG=True)
    def test_sets_plan_and_credit(self):
        call_command(
            "set_e2e_account", "e2e-account@example.com", "--plan=pro", "--credit=42.00", stdout=StringIO()
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.plan, "pro")
        self.assertEqual(self.user.extra_credit, Decimal("42.00"))

    @override_settings(DEBUG=False)
    def test_refuses_to_run_without_debug(self):
        with self.assertRaises(CommandError):
            call_command("set_e2e_account", "e2e-account@example.com", stdout=StringIO())
