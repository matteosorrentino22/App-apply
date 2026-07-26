from django.urls import path

from .views import PushSubscriptionView

urlpatterns = [
    path(
        "notifications/push-subscriptions/",
        PushSubscriptionView.as_view(),
        name="push-subscription-register",
    ),
]
