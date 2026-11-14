# File degli utenti (Sprint 66): CV, cover letter e foto profilo non sono
# mai serviti direttamente da Caddy (/media/* risponde 404). Si scaricano
# solo da URL firmati a scadenza generati dall'API per il proprietario, così
# un semplice <a href> funziona anche nella PWA iOS (che non può aggiungere
# l'header Authorization). Nomi su disco casuali: anche un file finito per
# errore fuori da questo percorso non è indovinabile.
import os
import uuid
from io import BytesIO

from django.core import signing
from django.core.files.base import ContentFile
from django.utils.http import urlencode
from PIL import Image, ImageOps, UnidentifiedImageError

SIGNED_URL_MAX_AGE = 60 * 60

_SALTS = {
    "cv": "apps.common.files.cv",
    "cover-letter": "apps.common.files.cover-letter",
    "photo": "apps.common.files.photo",
}

PHOTO_MAX_BYTES = 5 * 1024 * 1024
PHOTO_MAX_DIMENSION = 4000
PHOTO_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _random_name(folder, extension):
    return f"{folder}/{uuid.uuid4().hex}{extension}"


def cv_document_upload_to(instance, filename):
    return _random_name("cv_documents", ".pdf")


def cover_letter_document_upload_to(instance, filename):
    return _random_name("cover_letter_documents", ".pdf")


def profile_photo_upload_to(instance, filename):
    extension = os.path.splitext(filename)[1].lower()
    return _random_name("profile_photos", extension if extension in PHOTO_FORMATS.values() else "")


class InvalidPhoto(ValueError):
    pass


def sanitize_photo(uploaded_file):
    """Ricodifica la foto da zero: niente EXIF/GPS/XMP (resta solo il
    profilo colore), orientamento applicato ai pixel. Solleva InvalidPhoto
    per formati, dimensioni o file non ammessi."""
    uploaded_file.seek(0, os.SEEK_END)
    if uploaded_file.tell() > PHOTO_MAX_BYTES:
        raise InvalidPhoto("La foto non può superare i 5 MB.")
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image_format = image.format
        if image_format not in PHOTO_FORMATS:
            raise InvalidPhoto("Formato non supportato: usa JPEG, PNG o WebP.")
        if image.width > PHOTO_MAX_DIMENSION or image.height > PHOTO_MAX_DIMENSION:
            raise InvalidPhoto(
                f"La foto non può superare {PHOTO_MAX_DIMENSION}×{PHOTO_MAX_DIMENSION} pixel."
            )
        image = ImageOps.exif_transpose(image)
        image.load()
    except InvalidPhoto:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as exc:
        raise InvalidPhoto("Immagine non valida.") from exc

    icc_profile = image.info.get("icc_profile")
    image.info = {}
    options = {"icc_profile": icc_profile} if icc_profile else {}
    if image_format == "JPEG":
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        options.update(quality=90)
    elif image_format == "WEBP":
        options.update(quality=90)

    output = BytesIO()
    image.save(output, image_format, **options)
    return ContentFile(output.getvalue(), name=f"photo{PHOTO_FORMATS[image_format]}")


def _sign(kind, value):
    return signing.TimestampSigner(salt=_SALTS[kind]).sign(value)


def unsign(kind, signature):
    """Valore firmato o None se firma mancante, manomessa o scaduta."""
    if not signature:
        return None
    try:
        return signing.TimestampSigner(salt=_SALTS[kind]).unsign(
            signature, max_age=SIGNED_URL_MAX_AGE
        )
    except signing.BadSignature:
        return None


def signed_document_url(kind, document):
    signature = _sign(kind, f"{document.user_id}:{document.pk}")
    return f"/api/files/{kind}/{document.pk}/?{urlencode({'s': signature})}"


def signed_photo_url(profile):
    if not profile.photo:
        return None
    return f"/api/files/photo/?{urlencode({'s': _sign('photo', str(profile.user_id))})}"
