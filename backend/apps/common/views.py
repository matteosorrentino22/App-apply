import mimetypes
import os

from django.http import FileResponse, Http404
from rest_framework import permissions
from rest_framework.views import APIView

from apps.cv.models import CoverLetterDocument, CVDocument
from apps.jobs.serializers import cover_letter_download_filename, cv_download_filename
from apps.profiles.models import Profile

from .files import unsign


def _file_response(field_file, *, as_attachment, filename):
    try:
        handle = field_file.open("rb")
    except (FileNotFoundError, ValueError) as exc:
        raise Http404 from exc
    content_type = mimetypes.guess_type(field_file.name)[0] or "application/octet-stream"
    response = FileResponse(
        handle, as_attachment=as_attachment, filename=filename, content_type=content_type
    )
    response["Cache-Control"] = "private, no-store"
    return response


class _SignedFileView(APIView):
    """Nessuna autenticazione: l'accesso è dato dalla firma (?s=), legata a
    utente e documento e valida SIGNED_URL_MAX_AGE. Qualunque errore (firma
    assente, scaduta, manomessa, documento di un altro utente o file
    mancante) risponde 404, mai 403: non conferma che il documento esista."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]


class _SignedDocumentView(_SignedFileView):
    kind = None
    model = None

    def download_filename(self, document):
        raise NotImplementedError

    def get(self, request, doc_id):
        value = unsign(self.kind, request.query_params.get("s"))
        user_id, _, signed_doc_id = (value or "").partition(":")
        if not value or signed_doc_id != str(doc_id) or not user_id.isdigit():
            raise Http404
        document = (
            self.model.objects.select_related("job", "user")
            .filter(pk=doc_id, user_id=int(user_id), user__is_active=True)
            .first()
        )
        if document is None or not document.pdf_file:
            raise Http404
        return _file_response(
            document.pdf_file, as_attachment=True, filename=self.download_filename(document)
        )


class CvFileView(_SignedDocumentView):
    kind = "cv"
    model = CVDocument

    def download_filename(self, document):
        return cv_download_filename(document.job)


class CoverLetterFileView(_SignedDocumentView):
    kind = "cover-letter"
    model = CoverLetterDocument

    def download_filename(self, document):
        return cover_letter_download_filename(document.job)


class PhotoFileView(_SignedFileView):
    def get(self, request):
        user_id = unsign("photo", request.query_params.get("s"))
        if not user_id or not user_id.isdigit():
            raise Http404
        profile = Profile.objects.filter(user_id=int(user_id), user__is_active=True).first()
        if profile is None or not profile.photo:
            raise Http404
        extension = os.path.splitext(profile.photo.name)[1]
        return _file_response(profile.photo, as_attachment=False, filename=f"foto{extension}")
