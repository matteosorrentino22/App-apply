from django.urls import path

from .views import PushSubscriptionView, VapidPublicKeyView

urlpatterns = [
    path(
        "notifications/push-subscriptions/",
        PushSubscriptionView.as_view(),
        name="push-subscription-register",
    ),
    path(
        "notifications/vapid-public-key/",
        VapidPublicKeyView.as_view(),
        name="vapid-public-key",
    ),
]
