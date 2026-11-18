import json
import zipfile
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APITestCase

from apps.accounts.account_data import build_export
from apps.jobs.list_service import list_jobs
from apps.jobs.models import Job
from apps.jobs.scoring import score_job
from apps.jobs.sources.apify_linkedin import ApifyLinkedInSource

from . import services
from .models import JobWish, SavedSearch

User = get_user_model()

# Sprint 84 (SPEC-DELTA A17–A19): ricerche con paese e più città, modalità
# di lavoro (solo Pro), lavoro dei desideri (solo Pro, keyword nascoste),
# etichetta Desiderio e modalità del job dallo scoring, filtri della lista.


def _user(email, plan="free"):
    return User.objects.create_user(username=email, email=email, password="pw-S84-12345!", plan=plan)


def _search(user, cities, **fields):
    return SavedSearch.objects.create(
        user=user, keywords=fields.pop("keywords", "Project Manager"), country=fields.pop("country", "Italy"),
        cities=cities, **fields,
    )


class MultiCitySearchApiTests(APITestCase):
    def test_free_search_has_one_city_and_no_work_mode(self):
        self.client.force_authenticate(_user("free@example.com"))
        ok = self.client.post("/api/searches/", {"keywords": "PM", "country": "Italy", "cities": ["Milan"]}, format="json")
        self.assertEqual(ok.status_code, 201)
        self.assertEqual((ok.data["cities"], ok.data["city"]), (["Milan"], "Milan"))
        two = self.client.post("/api/searches/", {"keywords": "PM", "country": "Italy", "cities": ["Milan", "Turin"]}, format="json")
        self.assertEqual(two.status_code, 400)
        mode = self.client.post(
            "/api/searches/", {"keywords": "PM", "country": "Italy", "cities": ["Milan"], "work_mode": "remote"}, format="json"
        )
        self.assertEqual(mode.status_code, 400)

    def test_pro_search_up_to_five_cities_with_work_mode(self):
        self.client.force_authenticate(_user("pro@example.com", "pro"))
        five = ["Milan", "Turin", "Rome", "Bologna", "Florence"]
        ok = self.client.post(
            "/api/searches/", {"keywords": "PM", "country": "Italy", "cities": five, "work_mode": "hybrid"}, format="json"
        )
        self.assertEqual(ok.status_code, 201)
        self.assertEqual((ok.data["cities"], ok.data["work_mode"]), (five, "hybrid"))
        six = self.client.post("/api/searches/", {"keywords": "PM", "country": "Italy", "cities": five + ["Naples"]}, format="json")
        self.assertEqual(six.status_code, 400)

    def test_legacy_city_field_and_duplicate_cities(self):
        self.client.force_authenticate(_user("legacy@example.com", "pro"))
        legacy = self.client.post("/api/searches/", {"keywords": "PM", "city": "Rome", "country": "Italy"}, format="json")
        self.assertEqual(legacy.data["cities"], ["Rome"])
        dup = self.client.post("/api/searches/", {"keywords": "PM", "country": "Italy", "cities": ["Rome", "rome", " "]}, format="json")
        self.assertEqual(dup.data["cities"], ["Rome"])

    def test_every_active_city_counts_toward_the_pro_limit(self):
        user = _user("limit@example.com", "pro")
        self.client.force_authenticate(user)
        for i in range(9):
            _search(user, [f"C{i}a", f"C{i}b", f"C{i}c", f"C{i}d", f"C{i}e"], is_active=True)  # 45 città
        last = _search(user, ["X1", "X2", "X3", "X4", "X5", "X6"][:5])
        self.assertEqual(self.client.post(f"/api/searches/{last.pk}/activate/").status_code, 200)  # 50
        extra = _search(user, ["Y1"])
        response = self.client.post(f"/api/searches/{extra.pk}/activate/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(services.active_city_count(user), 50)
        self.assertEqual(self.client.get("/api/search-limits/").data["active_cities"], 50)

    def test_adding_cities_to_an_active_search_rechecks_the_limit(self):
        user = _user("edit@example.com", "pro")
        self.client.force_authenticate(user)
        for i in range(10):
            _search(user, [f"A{i}", f"B{i}", f"C{i}", f"D{i}", f"E{i}"][:5] if i < 9 else ["Z1", "Z2", "Z3", "Z4"], is_active=True)
        search = SavedSearch.objects.filter(user=user, cities=["Z1", "Z2", "Z3", "Z4"]).get()
        ok = self.client.patch(f"/api/searches/{search.pk}/", {"cities": ["Z1", "Z2", "Z3", "Z4", "Z5"]}, format="json")
        self.assertEqual(ok.status_code, 200)
        other = SavedSearch.objects.filter(user=user, cities__contains=["A0"]).get()
        response = self.client.patch(f"/api/searches/{other.pk}/", {"cities": ["A0", "B0", "C0", "D0"]}, format="json")
        self.assertEqual(response.status_code, 200)  # togliere città è sempre possibile

    def test_multi_city_search_cannot_be_activated_after_downgrade(self):
        user = _user("down@example.com", "pro")
        search = _search(user, ["Milan", "Turin"], is_active=True)
        user.plan = User.Plan.FREE
        user.save()
        search.refresh_from_db()
        self.assertFalse(search.is_active)
        self.client.force_authenticate(user)
        self.assertEqual(self.client.post(f"/api/searches/{search.pk}/activate/").status_code, 400)

    def test_city_autocomplete_passes_the_country_code(self):
        self.client.force_authenticate(_user("geo@example.com"))
        with patch("apps.searches.geo.requests.get") as mock_get:
            mock_get.return_value = MagicMock(json=lambda: [], raise_for_status=lambda: None)
            self.client.get("/api/searches-city-autocomplete/?q=Mil&country_code=IT")
        self.assertEqual(mock_get.call_args.kwargs["params"]["countrycodes"], "it")


class CollectionGroupsTests(TestCase):
    def setUp(self):
        self.user = _user("groups@example.com", "pro")
        self.source = ApifyLinkedInSource()

    def test_one_group_per_city_and_work_mode_with_radius(self):
        a = _search(self.user, ["Milan", "Turin"], keywords="PM")
        b = _search(self.user, ["Milan"], keywords="Sales")
        c = _search(self.user, ["Milan"], keywords="Data", work_mode="remote")
        groups = self.source._group_by_type_and_location([a, b, c])
        keys = sorted((g["city"], g["work_mode"], sorted(s.keywords for s in g["searches"])) for g in groups)
        self.assertEqual(keys, [("Milan", "", ["PM", "Sales"]), ("Milan", "remote", ["Data"]), ("Turin", "", ["PM"])])

        response = MagicMock(json=lambda: [])
        with patch.object(self.source, "_post_with_retry", return_value=response) as post:
            remote_group = next(g for g in groups if g["work_mode"] == "remote")
            self.source._fetch_group(remote_group, 24)
        payload = post.call_args.args[0]
        self.assertEqual((payload["location"], payload["distance"], payload["workType"]), ("Milan, Italy", "25", ["remote"]))

    def test_offer_attributed_to_the_search_of_its_city_and_wish_label_hidden(self):
        normal = _search(self.user, ["Rome", "Milan"], keywords="PM")
        wish = _search(self.user, ["Milan"], keywords="Segreto", is_wish=True)
        group = next(g for g in self.source._group_by_type_and_location([normal, wish]) if g["city"] == "Milan")
        items = [
            {"id": "1", "title": "T", "companyName": "C", "jobUrl": "https://x", "searchString": "PM - Milan, Italy"},
            {"id": "2", "title": "T", "companyName": "C", "jobUrl": "https://x", "searchString": "Segreto - Milan, Italy"},
        ]
        with patch.object(self.source, "_post_with_retry", return_value=MagicMock(json=lambda: items)):
            offers = self.source._fetch_group(group, 24)
        self.assertEqual(offers[0]["saved_search_id"], normal.pk)
        self.assertEqual(offers[0]["matched_search"], "PM - Milan, Italy")
        self.assertEqual(offers[1]["saved_search_id"], wish.pk)
        self.assertEqual(offers[1]["matched_search"], "")


def _wish_ai(keywords):
    return patch("apps.searches.wish.call_claude_structured", return_value={"keywords": keywords})


class JobWishApiTests(APITestCase):
    def setUp(self):
        self.pro = _user("wish@example.com", "pro")
        self.client.force_authenticate(self.pro)
        self.payload = {"description": "Vorrei lavorare nella sostenibilità energetica", "country": "Italy", "cities": ["Milan", "Turin"], "is_active": True}

    def test_free_cannot_save_a_wish(self):
        self.client.force_authenticate(_user("freewish@example.com"))
        with _wish_ai(["X"]) as ai:
            response = self.client.put("/api/job-wish/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)
        ai.assert_not_called()

    def test_pro_wish_creates_hidden_searches_and_never_returns_keywords(self):
        with _wish_ai(["Energy Transition Manager", "Sustainability Lead"]):
            response = self.client.put("/api/job-wish/", self.payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("keywords", response.data)
        self.assertNotIn("Energy", json.dumps(response.data))
        hidden = SavedSearch.objects.filter(user=self.pro, is_wish=True)
        self.assertEqual(sorted(hidden.values_list("keywords", flat=True)), ["Energy Transition Manager", "Sustainability Lead"])
        self.assertTrue(all(s.is_active and s.cities == ["Milan", "Turin"] for s in hidden))
        self.assertEqual(self.client.get("/api/searches/").data, [])
        self.assertEqual(services.active_city_count(self.pro), 2)  # città contate una volta
        self.assertNotIn("Energy", json.dumps(self.client.get("/api/job-wish/").data))

    def test_keywords_are_derived_again_only_when_the_description_changes(self):
        with _wish_ai(["A"]):
            self.client.put("/api/job-wish/", self.payload, format="json")
        with _wish_ai(["B"]) as ai:
            self.client.put("/api/job-wish/", {**self.payload, "cities": ["Rome"], "is_active": False}, format="json")
        ai.assert_not_called()
        self.assertEqual(list(SavedSearch.objects.filter(user=self.pro, is_wish=True).values_list("keywords", "is_active")), [("A", False)])

    def test_at_most_five_description_changes_per_day(self):
        for i in range(5):
            with _wish_ai([f"K{i}"]):
                self.assertEqual(self.client.put("/api/job-wish/", {**self.payload, "description": f"Desc {i}"}, format="json").status_code, 200)
        with _wish_ai(["K6"]) as ai:
            response = self.client.put("/api/job-wish/", {**self.payload, "description": "Desc 6"}, format="json")
        self.assertEqual(response.status_code, 400)
        ai.assert_not_called()
        self.assertEqual(self.client.get("/api/job-wish/").data["changes_left_today"], 0)

    def test_wish_cities_count_toward_the_limit(self):
        for i in range(10):
            _search(self.pro, [f"A{i}", f"B{i}", f"C{i}", f"D{i}", f"E{i}"], is_active=True)  # 50
        with _wish_ai(["A"]):
            response = self.client.put("/api/job-wish/", self.payload, format="json")
        self.assertEqual(response.status_code, 400)
        with _wish_ai(["A"]):
            off = self.client.put("/api/job-wish/", {**self.payload, "is_active": False}, format="json")
        self.assertEqual(off.status_code, 200)

    def test_ai_failure_changes_nothing(self):
        with patch("apps.searches.wish.call_claude_structured", side_effect=RuntimeError("bedrock")):
            response = self.client.put("/api/job-wish/", self.payload, format="json")
        self.assertEqual(response.status_code, 502)
        self.assertFalse(JobWish.objects.filter(user=self.pro).exists())

    def test_downgrade_turns_the_wish_off_and_export_contains_it(self):
        with _wish_ai(["A"]):
            self.client.put("/api/job-wish/", self.payload, format="json")
        self.pro.plan = User.Plan.FREE
        self.pro.save()
        self.assertFalse(JobWish.objects.get(user=self.pro).is_active)
        self.assertFalse(SavedSearch.objects.filter(user=self.pro, is_active=True).exists())
        with zipfile.ZipFile(build_export(self.pro)) as archive:
            data = json.loads(archive.read("dati.json"))
        self.assertEqual(data["job_wish"][0]["description"], self.payload["description"])


class ScoringWorkModeAndWishTests(TestCase):
    def setUp(self):
        self.user = _user("score@example.com", "pro")

    def _job(self, search=None):
        return Job.objects.create(
            user=self.user, source=Job.Source.LINKEDIN, external_id="j1", title="T", company="C", location="Milan",
            description="D", apply_url="https://x", matched_saved_search=search,
        )

    def _result(self, **extra):
        return {"score": 7, "score_match": [], "score_gaps": [], "score_reasoning": "ok",
                "language_check": {"required": False, "language": "", "international_exception": False}, **extra}

    def test_work_mode_from_ai_and_fallback_to_the_search(self):
        job = self._job(_search(self.user, ["Milan"], work_mode="hybrid"))
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=self._result(work_mode="not_indicated")):
            score_job(job)
        job.refresh_from_db()
        self.assertEqual(job.work_mode, "hybrid")
        other = Job.objects.create(user=self.user, source=Job.Source.LINKEDIN, external_id="j2", title="T", company="C",
                                   location="Milan", description="D", apply_url="https://x")
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=self._result(work_mode="remote")):
            score_job(other)
        other.refresh_from_db()
        self.assertEqual(other.work_mode, "remote")

    def test_wish_description_only_when_active_and_label_saved(self):
        job = self._job()
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=self._result(work_mode="remote")) as call:
            score_job(job)
        self.assertEqual(call.call_args.kwargs, {})
        JobWish.objects.create(user=self.user, description="Energia", country="Italy", cities=["Milan"], is_active=True, keywords=["A"])
        with patch("apps.jobs.scoring.score_job_with_claude", return_value=self._result(work_mode="remote", wish_match=True)) as call:
            score_job(job)
        self.assertEqual(call.call_args.kwargs, {"wish_description": "Energia"})
        job.refresh_from_db()
        self.assertTrue(job.is_wish_match)


class ListFiltersTests(APITestCase):
    def setUp(self):
        self.user = _user("lf@example.com", "pro")
        self.client.force_authenticate(self.user)
        make = lambda ext, **f: Job.objects.create(user=self.user, source=Job.Source.LINKEDIN, external_id=ext, title="T",
                                                   company="C", location="L", description="", apply_url="https://x", **f)
        self.remote = make("r", work_mode="remote", is_wish_match=True)
        self.hybrid = make("h", work_mode="hybrid")
        self.none = make("n", work_mode="not_indicated")
        self.old = make("o")

    def test_work_mode_filter_and_old_jobs_left_out(self):
        ids = {j.pk for j in list_jobs(self.user, "main", work_modes=["remote", "not_indicated"])}
        self.assertEqual(ids, {self.remote.pk, self.none.pk})
        response = self.client.get("/api/jobs/?mode=hybrid")
        self.assertEqual([j["id"] for j in response.data], [self.hybrid.pk])
        self.assertEqual(response.data[0]["work_mode"], "hybrid")
        self.assertEqual(self.client.get("/api/jobs/?mode=anywhere").status_code, 400)

    def test_wish_chip_filters_the_label(self):
        response = self.client.get("/api/jobs/?search=wish")
        self.assertEqual([j["id"] for j in response.data], [self.remote.pk])
        self.assertTrue(response.data[0]["is_wish_match"])
        self.assertTrue(self.client.get("/api/accounts/me/").data["wish_filter_available"])

    def test_preset_saves_work_modes_and_wish(self):
        response = self.client.post("/api/job-filter-presets/", {"name": "R", "work_modes": ["remote"], "search_ids": ["wish"]}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual((response.data["work_modes"], response.data["search_ids"]), (["remote"], ["wish"]))
        self.assertEqual(self.client.post("/api/job-filter-presets/", {"name": "X", "work_modes": ["x"]}, format="json").status_code, 400)
