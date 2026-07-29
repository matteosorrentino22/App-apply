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


def _fake_guest_posting_html(title="Business Analyst", company="Acme", location="Zurich, Switzerland"):
    return f"""
    <h2 class="top-card-layout__title topcard__title">{title}</h2>
    <a class="topcard__org-name-link" href="#">{company}</a>
    <span class="topcard__flavor topcard__flavor--bullet">{location}</span>
    <div class="show-more-less-html__markup">
      <strong>About</strong><br><br>Descrizione del ruolo.<ul><li>Requisito A</li></ul>
    </div>
    """


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


class ApifyLinkedInSourceFetchByUrlTests(TestCase):
    """fetch_by_url (import manuale) chiama LinkedIn direttamente, non Apify
    (Sprint 24): nessuna delle chiamate qui deve toccare requests.post."""

    URL = "https://www.linkedin.com/jobs/view/business-analyst-4123456789/"

    def test_fetch_by_url_parses_title_company_location_description(self):
        source = ApifyLinkedInSource()
        fake_response = MagicMock(status_code=200, text=_fake_guest_posting_html())
        with patch("apps.jobs.sources.apify_linkedin.requests.get") as mock_get:
            mock_get.return_value = fake_response
            offer = source.fetch_by_url(self.URL)

        self.assertEqual(offer["external_id"], "4123456789")
        self.assertEqual(offer["title"], "Business Analyst")
        self.assertEqual(offer["company"], "Acme")
        self.assertEqual(offer["location"], "Zurich, Switzerland")
        self.assertIn("Descrizione del ruolo.", offer["description"])
        self.assertIn("Requisito A", offer["description"])
        self.assertEqual(offer["apply_url"], self.URL)

    def test_fetch_by_url_requests_the_guest_endpoint_not_apify(self):
        source = ApifyLinkedInSource()
        fake_response = MagicMock(status_code=200, text=_fake_guest_posting_html())
        with patch("apps.jobs.sources.apify_linkedin.requests.get") as mock_get, patch(
            "apps.jobs.sources.apify_linkedin.requests.post"
        ) as mock_post:
            mock_get.return_value = fake_response
            source.fetch_by_url(self.URL)

        mock_post.assert_not_called()
        requested_url = mock_get.call_args.args[0]
        self.assertEqual(
            requested_url,
            "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/4123456789",
        )

    def test_fetch_by_url_returns_none_on_404(self):
        source = ApifyLinkedInSource()
        with patch("apps.jobs.sources.apify_linkedin.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=404, text="")
            offer = source.fetch_by_url(self.URL)

        self.assertIsNone(offer)

    def test_fetch_by_url_returns_none_on_network_error(self):
        source = ApifyLinkedInSource()
        with patch("apps.jobs.sources.apify_linkedin.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ReadTimeout("timed out")
            offer = source.fetch_by_url(self.URL)

        self.assertIsNone(offer)

    def test_fetch_by_url_returns_none_for_unrecognized_url(self):
        source = ApifyLinkedInSource()
        with patch("apps.jobs.sources.apify_linkedin.requests.get") as mock_get:
            offer = source.fetch_by_url("https://example.com/not-a-linkedin-job")

        mock_get.assert_not_called()
        self.assertIsNone(offer)

    def test_fetch_by_url_returns_none_when_title_missing(self):
        source = ApifyLinkedInSource()
        incomplete_html = '<div class="show-more-less-html__markup">Descrizione.</div>'
        with patch("apps.jobs.sources.apify_linkedin.requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200, text=incomplete_html)
            offer = source.fetch_by_url(self.URL)

        self.assertIsNone(offer)
