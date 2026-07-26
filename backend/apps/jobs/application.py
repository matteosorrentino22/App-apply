from django.db import transaction
from django.utils import timezone

from .models import Job


class ApplicationMarkRejected(Exception):
    """Il Job non ha (ancora) un CV generato: la marcatura "candidatura
    fatta" richiede che lo stato sia già `cv_generated` (01-specifiche
    -funzionali-v4.md §4.10)."""


@transaction.atomic
def mark_application_done(job):
    """Marca un Job come "candidatura fatta": possibile solo se esiste già
    un CV per quel job (automatico o manuale, cioè `status='cv_generated'`).
    Valorizza `date_application_done` e azzera `User.last_activity_reset`
    (§4.12 funzionali: il timer di inattività riparte a ogni candidatura)."""
    locked_job = Job.objects.select_for_update().get(pk=job.pk)
    if locked_job.status != Job.Status.CV_GENERATED:
        raise ApplicationMarkRejected(
            "Puoi marcare come candidatura fatta solo un job per cui è già stato generato un CV."
        )

    now = timezone.now()
    locked_job.status = Job.Status.APPLICATION_DONE
    locked_job.date_application_done = now
    locked_job.save(update_fields=["status", "date_application_done"])

    type(locked_job.user).objects.filter(pk=locked_job.user.pk).update(last_activity_reset=now)
    return locked_job
