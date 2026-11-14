from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.accounts.admin_login import throttled_admin_login
from apps.accounts.views import LegalInfoView

urlpatterns = [
    # Prima di admin.site.urls: sostituisce la sola view di login dell'admin.
    path(f"{settings.DJANGO_ADMIN_PATH}login/", throttled_admin_login),
    path(settings.DJANGO_ADMIN_PATH, admin.site.urls),
    path("api/accounts/", include("apps.accounts.urls")),
    path("api/legal/", LegalInfoView.as_view(), name="legal-info"),
    path("api/", include("apps.common.urls")),
    path("api/", include("apps.profiles.urls")),
    path("api/", include("apps.searches.urls")),
    path("api/", include("apps.jobs.urls")),
    path("api/", include("apps.notifications.urls")),
    path("accounts/", include("allauth.urls")),
]
