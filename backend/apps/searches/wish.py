import zoneinfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.accounts.models import User
from apps.common.ai import call_claude_structured

from . import services
from .models import MAX_CITIES_PER_SEARCH, MAX_WISH_CHANGES_PER_DAY, MAX_WISH_DESCRIPTION_LENGTH, JobWish, SavedSearch

# Lavoro dei desideri (Sprint 84, SPEC-DELTA A19). Il giorno del massimale
# delle modifiche è quello di Europe/Rome, come gli altri massimali.
ROME = zoneinfo.ZoneInfo("Europe/Rome")

WISH_KEYWORDS_SCHEMA = {
    "type": "object",
    "properties": {
        "keywords": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
    },
    "required": ["keywords"],
    "additionalProperties": False,
}

WISH_KEYWORDS_PROMPT = (
    "Ricevi la descrizione, scritta da un candidato, del lavoro che vorrebbe fare. "
    "Ricava da 1 a 2 parole chiave di ricerca per LinkedIn Jobs, MOLTO mirate: "
    "meglio pochi annunci ma pertinenti che molti generici. Ogni parola chiave è "
    "un titolo di ruolo o un'espressione breve (2-4 parole), nella lingua in cui "
    "gli annunci di quel ruolo sono di solito pubblicati (spesso inglese). Niente "
    "località, niente nomi di aziende, niente parole generiche come \"lavoro\" o \"job\"."
)


class WishError(Exception):
    pass


def derive_wish_keywords(description):
    result = call_claude_structured(
        model=settings.BEDROCK_SCORING_MODEL,
        system=WISH_KEYWORDS_PROMPT,
        user_content=f"DESCRIZIONE DEL LAVORO DESIDERATO:\n{description}",
        schema=WISH_KEYWORDS_SCHEMA,
        max_tokens=300,
    )
    keywords = []
    for keyword in result.get("keywords") or []:
        keyword = " ".join(str(keyword).split())[:255]
        if keyword and keyword.casefold() not in {k.casefold() for k in keywords}:
            keywords.append(keyword)
    return keywords[:2]


def changes_left_today(wish):
    today = timezone.now().astimezone(ROME).date()
    used = wish.changes_count if wish and wish.changes_date == today else 0
    return max(0, MAX_WISH_CHANGES_PER_DAY - used)


def save_wish(user, description, country, cities, is_active):
    """Crea o aggiorna il lavoro dei desideri. Solo Pro. Se la descrizione
    cambia (al massimo 5 volte al giorno) l'AI ricava di nuovo le keyword;
    altrimenti si aggiornano solo paese, città e stato. Le città contano come
    ricerche attive (Pro 50). Errori: `WishError` (messaggio per l'utente) e
    `services.PlanLimitExceeded`."""
    if user.plan != User.Plan.PRO:
        raise WishError(_("Il lavoro dei desideri è incluso nel piano Pro."))
    description = (description or "").strip()
    if not description:
        raise WishError(_("Descrivi il lavoro che vorresti."))
    if len(description) > MAX_WISH_DESCRIPTION_LENGTH:
        raise WishError(_("La descrizione può avere al massimo %(max)s caratteri.") % {"max": MAX_WISH_DESCRIPTION_LENGTH})
    if not country:
        raise WishError(_("Scegli il paese."))
    if not cities or len(cities) > MAX_CITIES_PER_SEARCH["pro"]:
        raise WishError(_("Scegli da 1 a %(max)s città.") % {"max": MAX_CITIES_PER_SEARCH["pro"]})

    wish = JobWish.objects.filter(user=user).first()
    description_changed = wish is None or wish.description != description
    if description_changed and changes_left_today(wish) == 0:
        raise WishError(_("Hai raggiunto il limite di modifiche della descrizione per oggi."))

    if is_active:
        normal = services.active_city_count(user) - (len(wish.cities) if wish and wish.is_active else 0)
        if normal + len(cities) > services.max_active_cities(user):
            raise services.PlanLimitExceeded(
                _("Hai raggiunto il numero massimo di città attive per il tuo piano (%(max)s).")
                % {"max": services.max_active_cities(user)}
            )

    # Chiamata AI fuori dalla transazione: se fallisce non cambia nulla.
    keywords = derive_wish_keywords(description) if description_changed else wish.keywords
    if not keywords:
        raise WishError(_("Non siamo riusciti a ricavare la ricerca dalla descrizione: riprova riformulandola."))

    with transaction.atomic():
        if wish is None:
            wish = JobWish(user=user)
        if description_changed:
            today = timezone.now().astimezone(ROME).date()
            wish.changes_count = (wish.changes_count if wish.changes_date == today else 0) + 1
            wish.changes_date = today
        wish.description = description
        wish.country = country
        wish.cities = list(cities)
        wish.is_active = bool(is_active)
        wish.keywords = keywords
        wish.save()
        services.sync_wish_searches(wish)
    return wish


def deactivate_wish(user):
    JobWish.objects.filter(user=user).update(is_active=False)
    SavedSearch.objects.filter(user=user, is_wish=True).update(is_active=False)


def active_wish_description(user):
    """Descrizione da passare allo scoring: solo per i Pro con il desiderio attivo."""
    if user.plan != User.Plan.PRO:
        return None
    wish = JobWish.objects.filter(user=user, is_active=True).only("description").first()
    return wish.description if wish else None
