from django.urls import path

from .views import GenerateCvView

urlpatterns = [
    path("jobs/<int:pk>/generate-cv/", GenerateCvView.as_view(), name="job-generate-cv"),
]
