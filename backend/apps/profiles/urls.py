from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("profiles", views.ProfileViewSet, basename="profile")
router.register("experiences", views.ExperienceViewSet, basename="experience")
router.register("educations", views.EducationViewSet, basename="education")
router.register("skills", views.SkillViewSet, basename="skill")
router.register("certifications", views.CertificationViewSet, basename="certification")
router.register("languages", views.LanguageViewSet, basename="language")

urlpatterns = router.urls
