import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from config.settings import _search_limit

from . import services
from .models import SavedSearch

User = get_user_model()

# Sprint 86: massimali delle ricerche configurabili dal `.env`
# (`settings.SEARCH_LIMITS`), con i valori predefiniti di prima.

CUSTOM = {
    "free": {"max_saved": 3, "max_active_per_type": 2, "max_cities_per_search": 2},
    "pro": {"max_saved": 4, "max_active_cities": 3, "max_cities_per_search": 2},
}


def _user(email, plan="free"):
    return User.objects.create_user(username=email, email=email, password="pw-S86-12345!", plan=plan)


def _search(user, cities, **fields):
    return SavedSearch.objects.create(
        user=user, keywords=fields.pop("keywords", "PM"), country="Italy", cities=cities, **fields
    )


class DefaultLimitsTests(APITestCase):
    def test_defaults_are_the_previous_values(self):
        self.client.force_authenticate(_user("def@example.com"))
        data = self.client.get("/api/search-limits/").data
        self.assertEqual((data["max_cities_per_search"], data["pro_max_cities_per_search"], data["max_active_cities"]), (1, 5, None))
        free, pro = services.get_limits(_user("f2@example.com")), services.get_limits(_user("p2@example.com", "pro"))
        self.assertEqual(free["max_saved"], 10)
        self.assertEqual(set(free["max_active_per_type"].values()), {1})
        self.assertEqual((pro["max_saved"], pro["max_active_total"]), (100, 50))


@override_settings(SEARCH_LIMITS=CUSTOM)
class CustomLimitsTests(APITestCase):
    def test_free_saved_active_per_type_and_cities(self):
        user = _user("free86@example.com")
        self.client.force_authenticate(user)
        ok = self.client.post("/api/searches/", {"keywords": "A", "country": "Italy", "cities": ["Milan", "Turin"]}, format="json")
        self.assertEqual(ok.status_code, 201)
        three = self.client.post("/api/searches/", {"keywords": "B", "country": "Italy", "cities": ["Milan", "Turin", "Rome"]}, format="json")
        self.assertEqual(three.status_code, 400)
        a = SavedSearch.objects.get(pk=ok.data["id"])
        b, c = _search(user, ["Rome"], keywords="B"), _search(user, ["Rome"], keywords="C")
        self.assertEqual(self.client.post("/api/searches/", {"keywords": "D", "country": "Italy", "cities": ["Rome"]}, format="json").status_code, 400)
        # Due attive per tipo: la seconda non spegne la prima, la terza è rifiutata.
        for search in (a, b):
            self.assertEqual(self.client.post(f"/api/searches/{search.pk}/activate/").status_code, 200)
        self.assertEqual(SavedSearch.objects.filter(user=user, is_active=True).count(), 2)
        self.assertEqual(self.client.post(f"/api/searches/{c.pk}/activate/").status_code, 400)
        limits = self.client.get("/api/search-limits/").data
        self.assertEqual((limits["max_cities_per_search"], limits["pro_max_cities_per_search"]), (2, 2))

    def test_pro_saved_and_active_cities(self):
        user = _user("pro86@example.com", "pro")
        self.client.force_authenticate(user)
        first = _search(user, ["Milan", "Turin"])
        second = _search(user, ["Rome", "Bologna"])
        self.assertEqual(self.client.post(f"/api/searches/{first.pk}/activate/").status_code, 200)
        response = self.client.post(f"/api/searches/{second.pk}/activate/")
        self.assertEqual(response.status_code, 400)
        self.assertIn("3", str(response.data))
        self.assertEqual(self.client.get("/api/search-limits/").data["max_active_cities"], 3)
        _search(user, ["Naples"]), _search(user, ["Florence"])
        self.assertEqual(self.client.post("/api/searches/", {"keywords": "X", "country": "Italy", "cities": ["Bari"]}, format="json").status_code, 400)

    def test_free_search_over_the_city_limit_cannot_be_activated(self):
        user = _user("down86@example.com")
        search = _search(user, ["Milan", "Turin", "Rome"])
        with self.assertRaises(services.PlanLimitExceeded):
            services.activate_search(search)


class SettingParsingTests(TestCase):
    def test_empty_uses_default_and_invalid_values_stop_the_start(self):
        with patch.dict(os.environ, {"SEARCH_X": ""}):
            self.assertEqual(_search_limit("SEARCH_X", 7), 7)
        with patch.dict(os.environ, {"SEARCH_X": " 12 "}):
            self.assertEqual(_search_limit("SEARCH_X", 7), 12)
        for bad in ("0", "-3", "dieci", "2.5"):
            with patch.dict(os.environ, {"SEARCH_X": bad}), self.assertRaises(ImproperlyConfigured):
                _search_limit("SEARCH_X", 7)
