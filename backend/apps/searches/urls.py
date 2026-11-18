from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("searches", views.SavedSearchViewSet, basename="saved-search")

urlpatterns = router.urls + [
    path("searches-city-autocomplete/", views.city_autocomplete, name="city-autocomplete"),
    path("search-limits/", views.search_limits, name="search-limits"),
    path("job-wish/", views.job_wish, name="job-wish"),
]
