from django.urls import path

from .views import CoverLetterFileView, CvFileView, PhotoFileView

urlpatterns = [
    path("files/cv/<int:doc_id>/", CvFileView.as_view(), name="file-cv"),
    path("files/cover-letter/<int:doc_id>/", CoverLetterFileView.as_view(), name="file-cover-letter"),
    path("files/photo/", PhotoFileView.as_view(), name="file-photo"),
]
