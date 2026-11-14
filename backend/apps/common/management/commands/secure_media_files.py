import os
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.common.files import (
    InvalidPhoto,
    cover_letter_document_upload_to,
    cv_document_upload_to,
    profile_photo_upload_to,
    sanitize_photo,
)
from apps.cv.models import CoverLetterDocument, CVDocument
from apps.profiles.models import Profile

_RANDOM_NAME = re.compile(r"^[a-z_]+/[0-9a-f]{32}(\.[a-z]+)?$")

TARGETS = [
    (CVDocument, "pdf_file", cv_document_upload_to),
    (CoverLetterDocument, "pdf_file", cover_letter_document_upload_to),
    (Profile, "photo", profile_photo_upload_to),
]


class Command(BaseCommand):
    help = (
        "Sprint 66: rinomina con nomi casuali i file media esistenti (CV, cover "
        "letter, foto profilo — le foto vengono anche ripulite dai metadati EXIF) "
        "aggiornando il DB; con --delete-orphans elimina i file in MEDIA_ROOT non "
        "più referenziati da nessun record. Idempotente."
    )

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Mostra cosa farebbe, senza modificare nulla.")
        parser.add_argument("--delete-orphans", action="store_true", help="Elimina i file non referenziati.")

    def handle(self, *args, dry_run=False, delete_orphans=False, **options):
        media_root = os.fspath(settings.MEDIA_ROOT)
        renamed = missing = 0
        for model, field_name, upload_to in TARGETS:
            for obj in model.objects.exclude(**{field_name: ""}).exclude(**{f"{field_name}__isnull": True}):
                old_name = getattr(obj, field_name).name
                if _RANDOM_NAME.match(old_name):
                    continue
                old_path = os.path.join(media_root, old_name)
                if not os.path.isfile(old_path):
                    missing += 1
                    self.stdout.write(f"MANCANTE {model.__name__} {obj.pk}: {old_name}")
                    continue
                content = None
                if field_name == "photo":
                    content = self._sanitized_photo(old_path)
                new_name = upload_to(obj, content.name if content else old_name)
                renamed += 1
                self.stdout.write(f"RINOMINA {model.__name__} {obj.pk}: {old_name} -> {new_name}")
                if dry_run:
                    continue
                self._replace(model, obj.pk, field_name, old_path, os.path.join(media_root, new_name), new_name, content)

        deleted = 0
        if delete_orphans:
            referenced = set()
            for model, field_name, _upload_to in TARGETS:
                referenced.update(
                    model.objects.exclude(**{field_name: ""})
                    .exclude(**{f"{field_name}__isnull": True})
                    .values_list(field_name, flat=True)
                )
            for directory, _subdirs, files in os.walk(media_root):
                for filename in files:
                    path = os.path.join(directory, filename)
                    relative = os.path.relpath(path, media_root).replace(os.sep, "/")
                    if relative in referenced:
                        continue
                    deleted += 1
                    self.stdout.write(f"ORFANO {relative}")
                    if not dry_run:
                        os.remove(path)

        prefix = "[dry-run] " if dry_run else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}Rinominati: {renamed} · mancanti su disco: {missing} · orfani eliminati: {deleted}"
            )
        )

    def _sanitized_photo(self, path):
        with open(path, "rb") as handle:
            try:
                return sanitize_photo(handle)
            except InvalidPhoto:
                # Foto non ricodificabile (formato non più ammesso): si
                # rinomina soltanto, il contenuto resta quello originale.
                return None

    def _replace(self, model, pk, field_name, old_path, new_path, new_name, content):
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        if content is not None:
            with open(new_path, "wb") as handle:
                handle.write(content.read())
        else:
            os.rename(old_path, new_path)
        try:
            model.objects.filter(pk=pk).update(**{field_name: new_name})
        except Exception:
            if content is not None:
                os.remove(new_path)
            else:
                os.rename(new_path, old_path)
            raise
        if content is not None:
            os.remove(old_path)
