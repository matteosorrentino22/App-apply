from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APITestCase

User = get_user_model()


def _fake_nominatim_response(items):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=items)
    return response


class CityAutocompleteApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username="geo@example.com", email="geo@example.com", password="pw-Geo-12345!"
        )
        self.client.force_authenticate(self.user)

    def test_returns_city_and_country_from_nominatim(self):
        items = [
            {
                "address": {
                    "city": "Zürich",
                    "country": "Switzerland",
                    "country_code": "ch",
                }
            },
            {
                "address": {
                    "state": "Zürich",  # nessun city/town/village: da scartare
                    "country": "Switzerland",
                    "country_code": "ch",
                }
            },
        ]
        with patch("apps.searches.geo.requests.get") as mock_get:
            mock_get.return_value = _fake_nominatim_response(items)
            response = self.client.get("/api/searches-city-autocomplete/", {"q": "Zuri"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data,
            [{"city": "Zürich", "country": "Switzerland", "country_code": "CH"}],
        )

    def test_short_query_returns_empty_without_calling_nominatim(self):
        with patch("apps.searches.geo.requests.get") as mock_get:
            response = self.client.get("/api/searches-city-autocomplete/", {"q": "Z"})

        mock_get.assert_not_called()
        self.assertEqual(response.data, [])

    def test_repeated_query_is_served_from_cache(self):
        items = [{"address": {"city": "Roma", "country": "Italia"}}]
        with patch("apps.searches.geo.requests.get") as mock_get:
            mock_get.return_value = _fake_nominatim_response(items)
            self.client.get("/api/searches-city-autocomplete/", {"q": "Rom"})
            self.client.get("/api/searches-city-autocomplete/", {"q": "Rom"})

        self.assertEqual(mock_get.call_count, 1)

    def test_unauthenticated_request_is_rejected(self):
        self.client.force_authenticate(None)
        response = self.client.get("/api/searches-city-autocomplete/", {"q": "Roma"})
        self.assertEqual(response.status_code, 401)
