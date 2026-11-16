from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.searches.models import SavedSearch

from .collection import collect_jobs_for_user
from .list_service import list_jobs
from .models import Job, JobFilterPreset
from .sources.apify_linkedin import ApifyLinkedInSource
from .tests import _fake_source, _offer

User = get_user_model()

# Sprint 82 (SPEC-DELTA A16): stipendio da `salaryInfo` (prima si leggeva
# `salary`, che la fonte non usa: lo stipendio restava sempre vuoto), tipo
# di contratto da `contractType`, filtri Contratto e Stipendio nella lista e
# nei filtri salvati.


def _item(**overrides):
    item = {"id": "123", "title": "X", "companyName": "Y", "jobUrl": "https://x"}
    item.update(overrides)
    return item


class SalaryAndContractNormalizationTests(TestCase):
    def setUp(self):
        self.source = ApifyLinkedInSource()

    def test_salary_info_range_becomes_a_readable_string(self):
        normalized = self.source._normalize_item(_item(salaryInfo=["$91000.00", "$136500.00"]))
        self.assertEqual(normalized["salary"], "$91.000 – $136.500")

    def test_single_value_keeps_real_decimals_with_a_comma(self):
        self.assertEqual(self.source._normalize_item(_item(salaryInfo=["$16.75"]))["salary"], "$16,75")

    def test_symbol_spacing_and_suffix_are_kept(self):
        self.assertEqual(
            self.source._normalize_item(_item(salaryInfo=["CHF 90000/yr", "CHF 110000/yr"]))["salary"],
            "CHF 90.000/yr – CHF 110.000/yr",
        )

    def test_thousands_separators_in_the_source_are_understood(self):
        self.assertEqual(self.source._normalize_item(_item(salaryInfo=["€45,000"]))["salary"], "€45.000")

    def test_unrecognized_text_is_kept_as_is(self):
        self.assertEqual(self.source._normalize_item(_item(salaryInfo=["Competitive"]))["salary"], "Competitive")

    def test_missing_or_empty_salary_info_gives_an_empty_salary(self):
        self.assertEqual(self.source._normalize_item(_item())["salary"], "")
        self.assertEqual(self.source._normalize_item(_item(salaryInfo=[]))["salary"], "")
        self.assertEqual(self.source._normalize_item(_item(salaryInfo=["", None]))["salary"], "")

    def test_salary_stays_within_the_field_length(self):
        normalized = self.source._normalize_item(_item(salaryInfo=["x" * 300, "y" * 300]))
        self.assertLessEqual(len(normalized["salary"]), 255)

    def test_contract_type_is_normalized(self):
        cases = {
            "Full-time": "full_time",
            "Part-time": "part_time",
            "Temporary": "temporary",
            "Contract": "contract",
            "Internship": "internship",
            "Volunteer": "volunteer",
            "Other": "other",
            "Something new": "",
            None: "",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self.source._normalize_item(_item(contractType=raw))["contract_type"], expected)


class CollectionSavesSalaryAndContractTests(TestCase):
    def test_collected_job_keeps_salary_and_contract_type(self):
        user = User.objects.create_user(username="s82@example.com", email="s82@example.com", password="pw-S82-12345!")
        SavedSearch.objects.create(user=user, keywords="Sales", city="Milano", country="Italia", is_active=True)
        offers = [_offer("ext-1", salary="$91.000 – $136.500", contract_type="part_time"), _offer("ext-2")]
        with patch("apps.jobs.collection.get_job_source") as mock_get_source:
            mock_get_source.return_value = _fake_source(offers)
            collect_jobs_for_user(user)
        first = Job.objects.get(user=user, external_id="ext-1")
        second = Job.objects.get(user=user, external_id="ext-2")
        self.assertEqual((first.salary, first.contract_type), ("$91.000 – $136.500", "part_time"))
        self.assertEqual((second.salary, second.contract_type), ("", ""))


class ContractAndSalaryFilterTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="f82@example.com", email="f82@example.com", password="pw-F82-12345!")
        self.client.force_authenticate(self.user)
        self.full = self._job("full", contract_type="full_time", salary="$91.000 – $136.500")
        self.part = self._job("part", contract_type="part_time")
        self.temp = self._job("temp", contract_type="temporary", salary="€30.000")
        self.old = self._job("old")  # raccolto prima dello Sprint 82: nessun dato

    def _job(self, external_id, **fields):
        return Job.objects.create(
            user=self.user, source=Job.Source.LINKEDIN, external_id=external_id, title="Sales Manager",
            company="Esempio", location="Milano", description="", apply_url="https://x", **fields,
        )

    def _ids(self, jobs):
        return {job.pk for job in jobs}

    def test_contract_filter_is_an_or_between_the_chosen_types(self):
        self.assertEqual(self._ids(list_jobs(self.user, "main", contract_types=["full_time", "part_time"])), {self.full.pk, self.part.pk})

    def test_jobs_without_contract_are_left_out_when_the_filter_is_active(self):
        self.assertNotIn(self.old.pk, self._ids(list_jobs(self.user, "main", contract_types=["full_time"])))
        self.assertIn(self.old.pk, self._ids(list_jobs(self.user, "main")))

    def test_salary_filter_with_and_without(self):
        self.assertEqual(self._ids(list_jobs(self.user, "main", has_salary=True)), {self.full.pk, self.temp.pk})
        self.assertEqual(self._ids(list_jobs(self.user, "main", has_salary=False)), {self.part.pk, self.old.pk})

    def test_contract_and_salary_combine_in_and(self):
        result = list_jobs(self.user, "main", contract_types=["full_time", "part_time"], has_salary=True)
        self.assertEqual(self._ids(result), {self.full.pk})

    def test_text_search_ignores_the_new_filters(self):
        result = list_jobs(self.user, "main", query="Sales", contract_types=["temporary"], has_salary=False)
        self.assertEqual(len(result), 4)

    def test_api_parameters_and_serializer(self):
        response = self.client.get("/api/jobs/?contract=part_time,temporary&salary=yes")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([job["id"] for job in response.data], [self.temp.pk])
        self.assertEqual(response.data[0]["contract_type"], "temporary")
        self.assertEqual(response.data[0]["salary"], "€30.000")
        self.assertEqual(self.client.get("/api/jobs/?salary=all").status_code, 200)

    def test_api_rejects_unknown_values(self):
        self.assertEqual(self.client.get("/api/jobs/?contract=freelance").status_code, 400)
        self.assertEqual(self.client.get("/api/jobs/?salary=maybe").status_code, 400)


class PresetWithContractAndSalaryTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="p82@example.com", email="p82@example.com", password="pw-P82-12345!")
        self.client.force_authenticate(self.user)

    def test_preset_saves_contract_types_and_salary(self):
        response = self.client.post(
            "/api/job-filter-presets/",
            {"name": "Part-time con stipendio", "contract_types": ["part_time", "full_time"], "has_salary": "yes"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        preset = JobFilterPreset.objects.get(user=self.user)
        self.assertEqual((preset.contract_types, preset.has_salary), (["part_time", "full_time"], "yes"))
        self.assertEqual(response.data["contract_types"], ["part_time", "full_time"])

    def test_existing_presets_default_to_no_contract_or_salary_filter(self):
        response = self.client.post("/api/job-filter-presets/", {"name": "Vecchio"}, format="json")
        self.assertEqual((response.data["contract_types"], response.data["has_salary"]), ([], ""))

    def test_preset_rejects_invalid_values(self):
        for payload in ({"contract_types": ["freelance"]}, {"contract_types": "full_time"}, {"has_salary": "maybe"}):
            with self.subTest(payload=payload):
                response = self.client.post("/api/job-filter-presets/", {"name": "X", **payload}, format="json")
                self.assertEqual(response.status_code, 400)
