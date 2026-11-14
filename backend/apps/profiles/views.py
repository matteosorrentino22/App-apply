import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.throttling import PostOnlyScopeMixin
from apps.jobs.models import DailyQuota

from . import cv_import
from .models import Certification, Education, Experience, Language, Profile, Skill
from .serializers import (
    CertificationSerializer,
    EducationSerializer,
    ExperienceSerializer,
    LanguageSerializer,
    ProfileSerializer,
    SkillSerializer,
)


class ProfileViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = ProfileSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        profile, _created = Profile.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(profile).data)

    @action(detail=False, methods=["delete"], url_path="me/photo")
    def remove_photo(self, request):
        # Rimozione della foto (Sprint 70): anche il file si cancella dal
        # disco, a commit avvenuto, per non lasciarlo orfano nel volume media.
        profile = Profile.objects.filter(user=request.user).first()
        if profile is not None and profile.photo:
            name, storage = profile.photo.name, profile.photo.storage
            profile.photo = None
            profile.save(update_fields=["photo"])
            transaction.on_commit(lambda: storage.delete(name))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileSectionViewSet(viewsets.ModelViewSet):
    # Numero massimo di voci per sezione (Sprint 70): tutte finiscono nel
    # prompt della generazione CV. Vale solo per le nuove voci.
    max_items = None

    def get_queryset(self):
        return self.queryset.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        profile, _created = Profile.objects.get_or_create(user=self.request.user)
        if self.max_items is not None and self.get_queryset().count() >= self.max_items:
            raise serializers.ValidationError(
                {"detail": _("Hai raggiunto il numero massimo di voci per questa sezione (%(max)s).") % {"max": self.max_items}}
            )
        serializer.save(profile=profile)


class ExperienceViewSet(ProfileSectionViewSet):
    max_items = 30
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer


class EducationViewSet(ProfileSectionViewSet):
    max_items = 15
    queryset = Education.objects.all()
    serializer_class = EducationSerializer


class SkillViewSet(ProfileSectionViewSet):
    max_items = 100
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class CertificationViewSet(ProfileSectionViewSet):
    max_items = 50
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer


class LanguageViewSet(ProfileSectionViewSet):
    max_items = 36
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


logger = logging.getLogger(__name__)

# Import CV al giorno per utente (Sprint 66), uguale per tutti i piani e
# senza credito: ogni import è una chiamata al modello più costoso.
CV_IMPORT_DAILY_LIMIT = 5

UNREADABLE_CV_MESSAGE = gettext_lazy("non siamo riusciti a leggere il CV, compila il profilo manualmente")


@transaction.atomic
def _reserve_cv_import(user):
    quota, _created = DailyQuota.objects.get_or_create(
        user=user, date=timezone.localtime(timezone.now()).date()
    )
    quota = DailyQuota.objects.select_for_update().get(pk=quota.pk)
    if quota.cv_import_count >= CV_IMPORT_DAILY_LIMIT:
        return None
    quota.cv_import_count += 1
    quota.save(update_fields=["cv_import_count"])
    return quota


class CVImportView(PostOnlyScopeMixin, APIView):
    """Pre-popola il profilo da un CV caricato (PDF/.docx), senza salvarlo (§5.4 tecniche)."""

    parser_classes = [MultiPartParser]
    post_throttle_scope = "cv_import"

    # Ogni errore ha un `code` stabile (Sprint 70): la PWA mostra un
    # messaggio specifico nella lingua dell'interfaccia; `detail` è nella
    # lingua della richiesta (Accept-Language, Sprint 71).
    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"code": "file_missing", "detail": _("Nessun file caricato.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            raw_text = cv_import.extract_text(uploaded_file)
        except cv_import.CVFileRejected as exc:
            return Response({"code": exc.code, "detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except cv_import.CVUnreadableError:
            return Response(
                {"code": "unreadable", "detail": UNREADABLE_CV_MESSAGE},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if not cv_import.has_sufficient_text(raw_text):
            return Response(
                {"code": "unreadable", "detail": UNREADABLE_CV_MESSAGE},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        quota = _reserve_cv_import(request.user)
        if quota is None:
            return Response(
                {
                    "code": "quota_exceeded",
                    "detail": _("Hai raggiunto il limite di %(max)s import del CV per oggi.") % {"max": CV_IMPORT_DAILY_LIMIT},
                    "limit": CV_IMPORT_DAILY_LIMIT,
                },
                status=status.HTTP_409_CONFLICT,
            )
        try:
            structured_profile = cv_import.structure_with_claude(raw_text)
        except Exception:
            logger.exception("Import CV: strutturazione AI fallita")
            DailyQuota.objects.filter(pk=quota.pk).update(cv_import_count=F("cv_import_count") - 1)
            return Response(
                {
                    "code": "ai_unavailable",
                    "detail": _("Il servizio di lettura del CV non è disponibile in questo momento: riprova più tardi."),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(structured_profile, status=status.HTTP_200_OK)
