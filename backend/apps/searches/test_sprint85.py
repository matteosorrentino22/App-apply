from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import SavedSearch

User = get_user_model()


# Sprint 85: l'elenco delle SavedSearch nell'Admin mostra tutte le città,
# tipo, modalità e le ricerche nascoste del lavoro dei desideri.
class SavedSearchAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(username="admin85@example.com", email="admin85@example.com", password="pw-S85-12345!")
        owner = User.objects.create_user(username="owner85@example.com", email="owner85@example.com", password="pw-S85-12345!", plan="pro")
        SavedSearch.objects.create(user=owner, keywords="Agenzia", search_type="company", country="Switzerland", cities=["Zurich", "Geneva"])
        SavedSearch.objects.create(user=owner, keywords="Nascosta", country="Italy", cities=["Milan"], work_mode="hybrid", is_wish=True)
        self.client.force_login(self.admin)
        self.url = f"/{settings.DJANGO_ADMIN_PATH}searches/savedsearch/"

    def test_changelist_shows_all_cities_type_mode_and_hidden_flag(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        for text in ("Zurich, Geneva", "Città", "Modalità", "Nascosta (desiderio)", "Ibrido", "Company"):
            self.assertContains(response, text)

    def test_filters_by_hidden_wish_and_type(self):
        hidden = self.client.get(self.url, {"is_wish__exact": "1"})
        self.assertContains(hidden, "Nascosta")
        self.assertNotContains(hidden, "Agenzia")
        company = self.client.get(self.url, {"search_type__exact": "company"})
        self.assertContains(company, "Agenzia")
        self.assertNotContains(company, "Milan")
