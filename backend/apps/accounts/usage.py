# Contatori e prezzi visibili all'utente (Sprint 70): per ogni azione a
# massimale, quante ne ha usate oggi, il massimale del suo piano e il prezzo
# oltre il massimale; più i prezzi a messaggio delle chat. Sola lettura: le
# regole vere restano nei servizi che riservano quota/credito, qui si
# leggono le stesse costanti.
from datetime import datetime, time, timedelta

from django.conf import settings
from django.utils import timezone

from apps.cv.cover_letter_manual_generation import COVER_LETTER_PLAN_LIMITS
from apps.cv.manual_generation import MANUAL_CV_PLAN_LIMITS
from apps.cv.referral_message_manual_generation import REFERRAL_MESSAGE_PLAN_LIMITS
from apps.jobs.import_service import IMPORT_DAILY_LIMIT
from apps.jobs.manual_job_service import MANUAL_JOB_DAILY_LIMIT
from apps.jobs.models import DailyQuota
from apps.jobs.tasks import COLLECTION_DAILY_LIMIT
from apps.profiles.views import CV_IMPORT_DAILY_LIMIT


def _actions(user):
    # (chiave, contatore di DailyQuota, massimale, prezzo oltre il massimale
    # o None se non c'è estensione a credito, disponibile sul piano)
    is_pro = user.plan == "pro"
    return [
        ("cv", "manual_cv_count", MANUAL_CV_PLAN_LIMITS[user.plan], settings.PRICE_MANUAL_CV_EXTRA, True),
        (
            "cover_letter", "cover_letter_count", COVER_LETTER_PLAN_LIMITS[user.plan],
            settings.PRICE_COVER_LETTER_EXTRA, True,
        ),
        (
            "referral_message", "referral_message_count", REFERRAL_MESSAGE_PLAN_LIMITS[user.plan],
            settings.PRICE_REFERRAL_MESSAGE_EXTRA, True,
        ),
        # L'import da link è solo Pro, nemmeno a credito sul Free (§4.11).
        ("import", "import_count", IMPORT_DAILY_LIMIT if is_pro else 0, settings.PRICE_IMPORT_EXTRA, is_pro),
        ("manual_job", "manual_job_count", MANUAL_JOB_DAILY_LIMIT, settings.PRICE_MANUAL_JOB_EXTRA, True),
        ("collection", "collection_count", COLLECTION_DAILY_LIMIT, None, True),
        ("cv_import", "cv_import_count", CV_IMPORT_DAILY_LIMIT, None, True),
    ]


def _next_charge(used, limit, price, available, credit):
    # Cosa succede alla prossima richiesta: inclusa nel massimale, a
    # credito, bloccata (massimale raggiunto senza credito sufficiente o
    # senza estensione), non disponibile sul piano.
    if not available:
        return "unavailable"
    if used < limit:
        return "included"
    if price is not None and credit >= price:
        return "credit"
    return "blocked"


def usage_for_user(user):
    now = timezone.localtime(timezone.now())
    quota = DailyQuota.objects.filter(user=user, date=now.date()).first()
    credit = type(user).objects.values_list("extra_credit", flat=True).get(pk=user.pk)
    actions = {}
    for key, counter, limit, price, available in _actions(user):
        used = getattr(quota, counter) if quota is not None else 0
        actions[key] = {
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
            "price": str(price) if price is not None else None,
            "next_charge": _next_charge(used, limit, price, available, credit),
        }
    # I massimali ripartono alla mezzanotte Europe/Rome (TIME_ZONE), non
    # nel fuso dell'utente (§7 tecniche).
    resets_at = timezone.make_aware(datetime.combine(now.date() + timedelta(days=1), time.min))
    return {
        "date": now.date().isoformat(),
        "resets_at": resets_at.isoformat(),
        "plan": user.plan,
        "extra_credit": str(credit),
        "actions": actions,
        "chat_prices": {
            "cv_draft_chat": str(settings.PRICE_CV_DRAFT_CHAT_MESSAGE),
            "cover_letter_draft_chat": str(settings.PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE),
        },
    }
