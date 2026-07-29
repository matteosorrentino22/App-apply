from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.searches.models import SavedSearch

from .apify_linkedin import ApifyLinkedInSource

User = get_user_model()


def _fake_response(items):
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json = MagicMock(return_value=items)
    return response


class ApifyLinkedInSourceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="apify@example.com", email="apify@example.com", password="pw-Apify-12345!"
        )
        self.search = SavedSearch.objects.create(
            user=self.user, keywords="Business analyst", city="Zurich", country="Switzerland"
        )

    def test_fetch_builds_location_from_city_and_country(self):
        source = ApifyLinkedInSource()
        with patch("apps.jobs.sources.apify_linkedin.requests.post") as mock_post:
            mock_post.return_value = _fake_response([])
            source.fetch([self.search], window_hours=24, limit=50)

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["location"], "Zurich, Switzerland")

    def test_normalize_item_extracts_matched_search_from_search_string(self):
        source = ApifyLinkedInSource()
        item = {
            "id": "123",
            "title": "Business Analyst",
            "companyName": "Acme",
            "location": "Zurich, Switzerland",
            "description": "Descrizione.",
            "jobUrl": "https://linkedin.com/jobs/view/123",
            "searchString": "Business analyst - Zurich, Switzerland",
        }

        normalized = source._normalize_item(item)

        self.assertEqual(
            normalized["matched_search"], "Business analyst - Zurich, Switzerland"
        )

    def test_normalize_item_without_search_string_defaults_to_empty(self):
        source = ApifyLinkedInSource()
        item = {"id": "123", "title": "X", "companyName": "Y", "jobUrl": "https://x"}

        normalized = source._normalize_item(item)

        self.assertEqual(normalized["matched_search"], "")

    def test_fetch_retries_once_after_a_timeout_then_succeeds(self):
        source = ApifyLinkedInSource()
        with patch("apps.jobs.sources.apify_linkedin.requests.post") as mock_post:
            mock_post.side_effect = [
                requests.exceptions.ReadTimeout("timed out"),
                _fake_response([]),
            ]
            source.fetch([self.search], window_hours=24, limit=50)

        self.assertEqual(mock_post.call_count, 2)

    def test_fetch_raises_after_exhausting_retries(self):
        source = ApifyLinkedInSource()
        with patch("apps.jobs.sources.apify_linkedin.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ReadTimeout("timed out")
            with self.assertRaises(requests.exceptions.ReadTimeout):
                source.fetch([self.search], window_hours=24, limit=50)

        self.assertEqual(mock_post.call_count, 2)
