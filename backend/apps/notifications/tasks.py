import logging
import zoneinfo
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as dj_timezone
from django.utils import translation
from django.utils.translation import gettext_lazy

from apps.jobs.models import Job

from .services import send_web_push

User = get_user_model()
logger = logging.getLogger(__name__)

# Soglia di inattività (01-specifiche-funzionali-v4.md §4.12): 7 giorni senza
# alcuna "candidatura fatta" (User.last_activity_reset).
INACTIVITY_THRESHOLD = timedelta(days=7)

# Testi tradotti nella lingua dell'interfaccia dell'utente al momento
# dell'invio (Sprint 71): il task gira fuori da una richiesta, la lingua non
# arriva da Accept-Language ma da `User.interface_language`.
MORNING_NOTIFICATION_PAYLOAD = {
    "title": gettext_lazy("Nuovi job pronti"),
    "body": gettext_lazy("Ci sono nuove offerte da valutare nella tua lista."),
}
INACTIVITY_NOTIFICATION_PAYLOAD = {
    "title": gettext_lazy("Non ti candidi da un po'"),
    "body": gettext_lazy("Entra nell'app e valuta le offerte in attesa."),
}


def notification_payload(payload, user):
    with translation.override(user.interface_language):
        return {key: str(value) for key, value in payload.items()}


def _send_to_all_subscriptions(user, payload):
    """Un errore su una sottoscrizione (push service lento o in errore) non
    deve fermare l'invio alle altre né il giro degli altri utenti
    (Sprint 66). Nel log solo l'id, mai l'endpoint completo."""
    payload = notification_payload(payload, user)
    for subscription in list(user.push_subscriptions.all()):
        try:
            send_web_push(subscription, payload)
        except Exception as exc:
            logger.warning("Push fallito per la sottoscrizione %s: %s", subscription.pk, type(exc).__name__)


def _for_each_user(task_name, function):
    # Solo chi ha le notifiche attive (preferenza di Impostazioni, Sprint 67).
    for user in User.objects.filter(is_active=True, notifications_enabled=True):
        try:
            function(user)
        except Exception:
            logger.exception("%s: errore per l'utente %s, si prosegue", task_name, user.pk)


def _local_now(user):
    return dj_timezone.now().astimezone(zoneinfo.ZoneInfo(user.timezone))


def _is_around_ten_local(user):
    # "Circa le 10:00 locali" (§5.5 tecniche): lo scheduler gira ogni ~15
    # minuti, una finestura di un'ora intera è tollerante a questa cadenza;
    # il vero anti-doppio-invio è il confronto con `last_notified_at`, non
    # l'ampiezza della finestra.
    return _local_now(user).hour == 10


def send_morning_notification_for_user(user):
    """Notifica mattutina (§5.5 tecniche): se sono circa le 10:00 locali
    dell'utente ed esistono Job raccolti dopo l'ultima notifica, invia e
    aggiorna `last_notified_at`. Nessun caso speciale per fusi orari: la
    definizione "raccolti dopo l'ultima notifica" copre anche gli utenti a
    est dell'Europa la cui giornata locale inizia prima del batch 02:00
    Europe/Rome."""
    if not user.notifications_enabled or not _is_around_ten_local(user):
        return False

    has_new_jobs = Job.objects.filter(
        user=user, date_collected__gt=user.last_notified_at
    ).exists()
    if not has_new_jobs:
        return False

    now = dj_timezone.now()
    _send_to_all_subscriptions(user, MORNING_NOTIFICATION_PAYLOAD)

    User.objects.filter(pk=user.pk).update(last_notified_at=now)
    return True


@shared_task
def send_morning_notifications():
    _for_each_user("send_morning_notifications", send_morning_notification_for_user)


def send_inactivity_notification_for_user(user):
    """Promemoria di inattività (§4.12 funzionali): scatta 7 giorni dopo
    l'ultima "candidatura fatta" (o dalla registrazione, se mai marcata),
    anche per chi non ha mai avuto un CV pronto. `last_inactivity_notified_at`
    evita che il task, ripetuto ogni ~15 minuti, rinvii la stessa notifica
    per tutta la durata dell'inattività: una volta inviata, non riparte
    finché `last_activity_reset` non cambia (nuova candidatura)."""
    if not user.notifications_enabled:
        return False
    if dj_timezone.now() - user.last_activity_reset < INACTIVITY_THRESHOLD:
        return False
    if (
        user.last_inactivity_notified_at is not None
        and user.last_inactivity_notified_at >= user.last_activity_reset
    ):
        return False

    _send_to_all_subscriptions(user, INACTIVITY_NOTIFICATION_PAYLOAD)

    User.objects.filter(pk=user.pk).update(last_inactivity_notified_at=dj_timezone.now())
    return True


@shared_task
def send_inactivity_notifications():
    _for_each_user("send_inactivity_notifications", send_inactivity_notification_for_user)
