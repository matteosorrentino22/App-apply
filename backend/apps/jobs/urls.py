from django.urls import path

from .views import (
    ArchiveJobView,
    EnrichAndGenerateCvView,
    GenerateCvView,
    ImportJobView,
    JobListView,
    UnarchiveJobView,
)

urlpatterns = [
    path("jobs/", JobListView.as_view(), name="job-list"),
    path("jobs/import/", ImportJobView.as_view(), name="job-import"),
    path("jobs/<int:pk>/generate-cv/", GenerateCvView.as_view(), name="job-generate-cv"),
    path(
        "jobs/<int:pk>/enrich-and-generate-cv/",
        EnrichAndGenerateCvView.as_view(),
        name="job-enrich-and-generate-cv",
    ),
    path("jobs/<int:pk>/archive/", ArchiveJobView.as_view(), name="job-archive"),
    path("jobs/<int:pk>/unarchive/", UnarchiveJobView.as_view(), name="job-unarchive"),
]
