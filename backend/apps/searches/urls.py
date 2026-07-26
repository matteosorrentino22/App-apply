from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("searches", views.SavedSearchViewSet, basename="saved-search")

urlpatterns = router.urls
