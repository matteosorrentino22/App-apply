from apps.accounts.models import User

from .models import SavedSearch

# Limiti di piano (01-specifiche-funzionali-v4.md §4.2): due pool indipendenti,
# ricerche salvate totali e ricerche attive contemporaneamente.
PLAN_LIMITS = {
    User.Plan.FREE: {"max_saved": 10, "max_active": 1},
    User.Plan.PRO: {"max_saved": 100, "max_active": 50},
}


class PlanLimitExceeded(Exception):
    pass


def get_limits(user):
    return PLAN_LIMITS[user.plan]


def check_can_create(user):
    limits = get_limits(user)
    if SavedSearch.objects.filter(user=user).count() >= limits["max_saved"]:
        raise PlanLimitExceeded(
            "Hai raggiunto il numero massimo di ricerche salvate per il tuo piano."
        )


def activate_search(search):
    """Attiva una ricerca secondo le regole di piano.

    Free (1 attiva max): disattiva automaticamente l'eventuale ricerca già
    attiva — mai un errore. Pro (50 attive max): rifiuta oltre il massimale.
    Ritorna la ricerca disattivata automaticamente, o None.
    """
    limits = get_limits(search.user)
    active_qs = SavedSearch.objects.filter(user=search.user, is_active=True).exclude(pk=search.pk)

    deactivated = None
    if limits["max_active"] == 1:
        deactivated = active_qs.first()
        if deactivated is not None:
            active_qs.update(is_active=False)
    elif active_qs.count() >= limits["max_active"]:
        raise PlanLimitExceeded(
            "Hai raggiunto il numero massimo di ricerche attive per il tuo piano."
        )

    search.is_active = True
    search.save(update_fields=["is_active"])
    return deactivated


def deactivate_search(search):
    search.is_active = False
    search.save(update_fields=["is_active"])


def get_active_searches(user):
    """Ricerche attive di un utente, consumato dal modulo di raccolta (Sprint 07)."""
    return SavedSearch.objects.filter(user=user, is_active=True)
