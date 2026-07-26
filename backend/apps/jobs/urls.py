from django.urls import path

from .views import EnrichAndGenerateCvView, GenerateCvView, ImportJobView

urlpatterns = [
    path("jobs/<int:pk>/generate-cv/", GenerateCvView.as_view(), name="job-generate-cv"),
    path(
        "jobs/<int:pk>/enrich-and-generate-cv/",
        EnrichAndGenerateCvView.as_view(),
        name="job-enrich-and-generate-cv",
    ),
    path("jobs/import/", ImportJobView.as_view(), name="job-import"),
]
