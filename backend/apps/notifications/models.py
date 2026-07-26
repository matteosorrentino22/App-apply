from django.conf import settings
from django.db import models


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    endpoint = models.URLField(max_length=1000)
    p256dh_key = models.CharField(max_length=255)
    auth_key = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "endpoint"], name="unique_push_subscription_per_user_endpoint"
            )
        ]

    def __str__(self):
        return f"PushSubscription({self.user})"
