import zoneinfo
from datetime import timedelta

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone as dj_timezone

from apps.jobs.models import Job

from .services import send_web_push

User = get_user_model()

# Soglia di inattività (01-specifiche-funzionali-v4.md §4.12): 7 giorni senza
# alcuna "candidatura fatta" (User.last_activity_reset).
INACTIVITY_THRESHOLD = timedelta(days=7)

MORNING_NOTIFICATION_PAYLOAD = {
    "title": "Nuovi job pronti",
    "body": "Ci sono nuove offerte da valutare nella tua lista.",
}
INACTIVITY_NOTIFICATION_PAYLOAD = {
    "title": "Non ti candidi da un po'",
    "body": "Entra nell'app e valuta le offerte in attesa.",
}


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
    if not _is_around_ten_local(user):
        return False

    has_new_jobs = Job.objects.filter(
        user=user, date_collected__gt=user.last_notified_at
    ).exists()
    if not has_new_jobs:
        return False

    now = dj_timezone.now()
    for subscription in user.push_subscriptions.all():
        send_web_push(subscription, MORNING_NOTIFICATION_PAYLOAD)

    User.objects.filter(pk=user.pk).update(last_notified_at=now)
    return True


@shared_task
def send_morning_notifications():
    for user in User.objects.all():
        send_morning_notification_for_user(user)


def send_inactivity_notification_for_user(user):
    """Promemoria di inattività (§4.12 funzionali): scatta 7 giorni dopo
    l'ultima "candidatura fatta" (o dalla registrazione, se mai marcata),
    anche per chi non ha mai avuto un CV pronto. `last_inactivity_notified_at`
    evita che il task, ripetuto ogni ~15 minuti, rinvii la stessa notifica
    per tutta la durata dell'inattività: una volta inviata, non riparte
    finché `last_activity_reset` non cambia (nuova candidatura)."""
    if dj_timezone.now() - user.last_activity_reset < INACTIVITY_THRESHOLD:
        return False
    if (
        user.last_inactivity_notified_at is not None
        and user.last_inactivity_notified_at >= user.last_activity_reset
    ):
        return False

    for subscription in user.push_subscriptions.all():
        send_web_push(subscription, INACTIVITY_NOTIFICATION_PAYLOAD)

    User.objects.filter(pk=user.pk).update(last_inactivity_notified_at=dj_timezone.now())
    return True


@shared_task
def send_inactivity_notifications():
    for user in User.objects.all():
        send_inactivity_notification_for_user(user)
