# Pulizia alla cancellazione (Sprint 67), qualunque sia la strada (Impostazioni
# → Elimina account, Django Admin, shell, cascata da un job): le FileField non
# cancellano il file su disco insieme alla riga, e i RunLog sopravvivono
# all'utente (SET_NULL) con un messaggio che può contenere testo derivato
# dalle sue richieste.
import logging
import os

from django.db import transaction
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from apps.cv.models import CoverLetterDocument, CVDocument
from apps.jobs.models import RunLog
from apps.profiles.models import Profile

from .models import User

logger = logging.getLogger(__name__)


def _delete_file_after_commit(field_file):
    if not field_file:
        return
    storage, name = field_file.storage, field_file.name

    def delete():
        try:
            storage.delete(name)
        except OSError:
            logger.warning("File non eliminabile dopo la cancellazione (%s)", os.path.basename(name))

    transaction.on_commit(delete)


@receiver(post_delete, sender=CVDocument)
@receiver(post_delete, sender=CoverLetterDocument)
def delete_document_pdf(sender, instance, **kwargs):
    _delete_file_after_commit(instance.pdf_file)


@receiver(post_delete, sender=Profile)
def delete_profile_photo(sender, instance, **kwargs):
    _delete_file_after_commit(instance.photo)


@receiver(pre_delete, sender=User)
def anonymize_run_logs(sender, instance, **kwargs):
    RunLog.objects.filter(user=instance).update(message="")
    RunLog.objects.filter(job__user=instance).update(message="")
