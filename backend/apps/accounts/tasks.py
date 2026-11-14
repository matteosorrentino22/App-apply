import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


@shared_task(autoretry_for=(OSError,), retry_backoff=60, max_retries=3)
def send_service_email(to, subject, body):
    """Invio di un'email di servizio già composta (Sprint 67): il task non
    legge il database, così può partire anche per un utente appena
    cancellato e non dipende dal commit della transazione che lo accoda."""
    if not (settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD):
        logger.warning("Email non configurata (EMAIL_HOST_USER/EMAIL_HOST_PASSWORD): messaggio non inviato.")
        return False
    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to])
    return True
