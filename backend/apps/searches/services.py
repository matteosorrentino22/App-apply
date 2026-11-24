from django.conf import settings
from django.utils.translation import gettext as _

from apps.accounts.models import User

from .models import JobWish, SavedSearch, max_cities_per_search

# Limiti di piano (01-specifiche-funzionali-v4.md §4.2, aggiornato sprint-39):
# ricerche salvate totali sempre come pool unico; ricerche attive invece
# separate per tipo su Free (1 job-role + 1 company) e come pool unico
# condiviso tra i due tipi su Pro (50 in totale, divisibili liberamente).
# Sprint 84 (A17): sul Pro il pool conta le **città** delle ricerche in uso
# (ogni città è una ricerca attiva), comprese quelle del lavoro dei desideri;
# sul Free una ricerca ha una sola città.
# Sprint 86: i valori sono in `settings.SEARCH_LIMITS` (dal `.env`, con i
# predefiniti 10 / 1 per tipo / 1 città per il Free e 100 / 50 città attive /
# 5 città per il Pro), letti a ogni chiamata.


class PlanLimitExceeded(Exception):
    pass


def get_limits(user):
    config = settings.SEARCH_LIMITS[user.plan]
    if user.plan == User.Plan.FREE:
        per_type = config["max_active_per_type"]
        return {
            "max_saved": config["max_saved"],
            "max_active_per_type": {search_type: per_type for search_type in SavedSearch.SearchType.values},
        }
    return {"max_saved": config["max_saved"], "max_active_total": config["max_active_cities"]}


def check_can_create(user):
    limits = get_limits(user)
    if SavedSearch.objects.filter(user=user).count() >= limits["max_saved"]:
        raise PlanLimitExceeded(
            _("Hai raggiunto il numero massimo di ricerche salvate per il tuo piano.")
        )


def activate_search(search):
    """Attiva una ricerca secondo le regole di piano.

    Free (1 attiva per tipo max): disattiva automaticamente l'eventuale
    ricerca già attiva dello stesso tipo — mai un errore. Pro (50 attive
    max, pool unico condiviso tra i tipi): rifiuta oltre il massimale.
    Ritorna la ricerca disattivata automaticamente, o None.
    """
    limits = get_limits(search.user)
    limit = max_cities_per_search(search.user.plan)
    if len(search.cities) > limit:
        # Ricerca con più città rimasta da un periodo Pro (Sprint 84).
        raise PlanLimitExceeded(
            _("Con il tuo piano una ricerca può avere al massimo %(max)s città: togli le altre per attivarla.")
            % {"max": limit}
        )

    deactivated = None
    if "max_active_per_type" in limits:
        max_for_type = limits["max_active_per_type"][search.search_type]
        active_qs = SavedSearch.objects.filter(
            user=search.user, is_active=True, search_type=search.search_type
        ).exclude(pk=search.pk)
        if max_for_type == 1:
            deactivated = active_qs.first()
            if deactivated is not None:
                active_qs.update(is_active=False)
        elif active_qs.count() >= max_for_type:
            raise PlanLimitExceeded(
                _("Hai raggiunto il numero massimo di ricerche attive per il tuo piano.")
            )
    else:
        if active_city_count(search.user, exclude_pk=search.pk) + len(search.cities) > limits["max_active_total"]:
            raise PlanLimitExceeded(
                _("Hai raggiunto il numero massimo di città attive per il tuo piano (%(max)s).")
                % {"max": limits["max_active_total"]}
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


def active_city_count(user, exclude_pk=None):
    """Città attive di un utente (Sprint 84): somma delle città delle ricerche
    in uso, più quelle del lavoro dei desideri se attivo (contate una volta,
    anche se le keyword ricavate sono due)."""
    qs = SavedSearch.objects.filter(user=user, is_active=True, is_wish=False)
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    total = sum(len(cities or []) for cities in qs.values_list("cities", flat=True))
    wish = JobWish.objects.filter(user=user, is_active=True).first()
    if wish is not None:
        total += len(wish.cities)
    return total


def max_active_cities(user):
    return get_limits(user).get("max_active_total")


def sync_wish_searches(wish):
    """Ricerche nascoste del lavoro dei desideri (Sprint 84, A19): una per
    keyword ricavata dall'AI, con paese e città del desiderio, attive solo se
    il desiderio è attivo. Le keyword non escono mai dal backend."""
    SavedSearch.objects.filter(user=wish.user, is_wish=True).delete()
    for keyword in wish.keywords:
        SavedSearch.objects.create(
            user=wish.user,
            search_type=SavedSearch.SearchType.JOB_ROLE,
            keywords=keyword[:255],
            country=wish.country,
            cities=list(wish.cities),
            is_wish=True,
            is_active=wish.is_active,
        )
