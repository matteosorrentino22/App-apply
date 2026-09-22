from django.db import transaction
from django.utils import timezone

from .models import Job


class ApplicationMarkRejected(Exception):
    """Il Job è già stato marcato come candidatura fatta: la marcatura non è
    ripetibile (deviazione voluta da 01-specifiche-funzionali-v4.md §4.10,
    che richiedeva anche un CV già generato — l'utente può ora candidarsi
    anche solo con il link diretto all'annuncio, senza aver generato nulla)."""


@transaction.atomic
def mark_application_done(job):
    """Marca un Job come "candidatura fatta", con o senza un CV generato per
    quel job. Valorizza `date_application_done` e azzera
    `User.last_activity_reset` (§4.12 funzionali: il timer di inattività
    riparte a ogni candidatura)."""
    locked_job = Job.objects.select_for_update().get(pk=job.pk)
    if locked_job.status == Job.Status.APPLICATION_DONE:
        raise ApplicationMarkRejected("Questo job è già stato marcato come candidatura fatta.")

    now = timezone.now()
    locked_job.status = Job.Status.APPLICATION_DONE
    locked_job.date_application_done = now
    locked_job.save(update_fields=["status", "date_application_done"])

    type(locked_job.user).objects.filter(pk=locked_job.user.pk).update(last_activity_reset=now)
    return locked_job
