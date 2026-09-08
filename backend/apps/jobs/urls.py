from django.urls import path

from .views import (
    ArchiveJobView,
    CollectJobsView,
    CoverLetterInstructionsView,
    CreateManualJobView,
    EnrichAndGenerateCvView,
    GenerateCoverLetterView,
    GenerateCvView,
    HomeStatsView,
    ImportJobView,
    JobDetailView,
    JobListView,
    MarkApplicationDoneView,
    UnarchiveJobView,
)

urlpatterns = [
    path("jobs/", JobListView.as_view(), name="job-list"),
    path("jobs/collect/", CollectJobsView.as_view(), name="job-collect"),
    path("jobs/import/", ImportJobView.as_view(), name="job-import"),
    path("jobs/manual/", CreateManualJobView.as_view(), name="job-manual-create"),
    path("jobs/stats/", HomeStatsView.as_view(), name="job-stats"),
    path("jobs/<int:pk>/", JobDetailView.as_view(), name="job-detail"),
    path("jobs/<int:pk>/generate-cv/", GenerateCvView.as_view(), name="job-generate-cv"),
    path(
        "jobs/<int:pk>/enrich-and-generate-cv/",
        EnrichAndGenerateCvView.as_view(),
        name="job-enrich-and-generate-cv",
    ),
    path(
        "jobs/<int:pk>/generate-cover-letter/",
        GenerateCoverLetterView.as_view(),
        name="job-generate-cover-letter",
    ),
    path(
        "cover-letter-instructions/",
        CoverLetterInstructionsView.as_view(),
        name="cover-letter-instructions",
    ),
    path("jobs/<int:pk>/archive/", ArchiveJobView.as_view(), name="job-archive"),
    path("jobs/<int:pk>/unarchive/", UnarchiveJobView.as_view(), name="job-unarchive"),
    path(
        "jobs/<int:pk>/mark-application-done/",
        MarkApplicationDoneView.as_view(),
        name="job-mark-application-done",
    ),
]
