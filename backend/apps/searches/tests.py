from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from . import services
from .models import SavedSearch

User = get_user_model()


class SavedSearchPlanLimitsApiTests(APITestCase):
    def setUp(self):
        self.free_user = User.objects.create_user(
            username="free@example.com", email="free@example.com", password="pw-Free-12345!"
        )
        self.pro_user = User.objects.create_user(
            username="pro@example.com",
            email="pro@example.com",
            password="pw-Pro-12345!",
            plan=User.Plan.PRO,
        )

    def _create(self, index=0):
        return self.client.post(
            "/api/searches/",
            {"keywords": "Project Manager", "city": "Roma", "country": "Italia"},
            format="json",
        )

    def test_free_user_cannot_exceed_ten_saved_searches(self):
        self.client.force_authenticate(self.free_user)
        for i in range(10):
            response = self._create(i)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self._create(10)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SavedSearch.objects.filter(user=self.free_user).count(), 10)

    def test_activating_a_search_on_free_plan_deactivates_the_previous_one(self):
        self.client.force_authenticate(self.free_user)
        search_a = SavedSearch.objects.create(
            user=self.free_user, keywords="PM", city="Roma", country="Italia", is_active=True
        )
        search_b = SavedSearch.objects.create(
            user=self.free_user, keywords="PM", city="Milano", country="Italia"
        )

        response = self.client.post(f"/api/searches/{search_b.pk}/activate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("deactivated_previous", response.data)
        self.assertEqual(response.data["deactivated_previous"]["id"], search_a.pk)

        search_a.refresh_from_db()
        search_b.refresh_from_db()
        self.assertFalse(search_a.is_active)
        self.assertTrue(search_b.is_active)

    def test_pro_user_can_activate_up_to_fifty_searches(self):
        searches = [
            SavedSearch.objects.create(
                user=self.pro_user, keywords="PM", city="Roma", country="Italia"
            )
            for i in range(51)
        ]
        for search in searches[:50]:
            deactivated = services.activate_search(search)
            self.assertIsNone(deactivated)

        with self.assertRaises(services.PlanLimitExceeded):
            services.activate_search(searches[50])

        self.assertEqual(
            SavedSearch.objects.filter(user=self.pro_user, is_active=True).count(), 50
        )

    def test_downgrade_from_pro_to_free_deactivates_all_searches(self):
        for i in range(15):
            SavedSearch.objects.create(
                user=self.pro_user,
                keywords="PM",
                city="Roma",
                country="Italia",
                is_active=(i < 5),
            )
        self.assertEqual(
            SavedSearch.objects.filter(user=self.pro_user, is_active=True).count(), 5
        )

        self.pro_user.plan = User.Plan.FREE
        self.pro_user.save()

        self.assertEqual(
            SavedSearch.objects.filter(user=self.pro_user, is_active=True).count(), 0
        )

        self.client.force_authenticate(self.pro_user)
        response = self._create(99)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(SavedSearch.objects.filter(user=self.pro_user).count(), 15)

    def test_get_active_searches_returns_only_active_ones(self):
        active = SavedSearch.objects.create(
            user=self.free_user, keywords="PM", city="Roma", country="Italia", is_active=True
        )
        SavedSearch.objects.create(
            user=self.free_user, keywords="PM", city="Roma", country="Italia", is_active=False
        )

        active_searches = services.get_active_searches(self.free_user)
        self.assertEqual(list(active_searches), [active])

    def test_user_can_update_keywords_and_city_country_of_a_saved_search(self):
        self.client.force_authenticate(self.free_user)
        search = SavedSearch.objects.create(
            user=self.free_user, keywords="PM", city="Roma", country="Italia"
        )

        response = self.client.patch(
            f"/api/searches/{search.pk}/",
            {"keywords": "Business Analyst", "city": "Milano", "country": "Italia"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search.refresh_from_db()
        self.assertEqual(search.keywords, "Business Analyst")
        self.assertEqual(search.city, "Milano")

    def test_user_cannot_update_another_users_saved_search(self):
        self.client.force_authenticate(self.pro_user)
        other_search = SavedSearch.objects.create(
            user=self.free_user, keywords="PM", city="Roma", country="Italia"
        )

        response = self.client.patch(
            f"/api/searches/{other_search.pk}/", {"keywords": "Hacked"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
