from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("searches", views.SavedSearchViewSet, basename="saved-search")

urlpatterns = router.urls + [
    path("searches-city-autocomplete/", views.city_autocomplete, name="city-autocomplete"),
]
