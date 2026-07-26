from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.accounts.models import User

from .models import SavedSearch


@receiver(pre_save, sender=User)
def _track_previous_plan(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._previous_plan = User.objects.only("plan").get(pk=instance.pk).plan
        except User.DoesNotExist:
            instance._previous_plan = None
    else:
        instance._previous_plan = None


@receiver(post_save, sender=User)
def _deactivate_searches_on_pro_to_free_downgrade(sender, instance, created, **kwargs):
    # Downgrade Pro→Free disattiva tutte le ricerche, senza selezione automatica
    # di una nuova attiva (01-specifiche-funzionali-v4.md §4.2).
    if created:
        return
    previous_plan = getattr(instance, "_previous_plan", None)
    if previous_plan == User.Plan.PRO and instance.plan == User.Plan.FREE:
        SavedSearch.objects.filter(user=instance, is_active=True).update(is_active=False)
