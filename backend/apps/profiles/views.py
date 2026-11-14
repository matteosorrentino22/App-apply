import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
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
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(self.get_serializer(profile).data)


class ProfileSectionViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(profile__user=self.request.user)

    def perform_create(self, serializer):
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        serializer.save(profile=profile)


class ExperienceViewSet(ProfileSectionViewSet):
    queryset = Experience.objects.all()
    serializer_class = ExperienceSerializer


class EducationViewSet(ProfileSectionViewSet):
    queryset = Education.objects.all()
    serializer_class = EducationSerializer


class SkillViewSet(ProfileSectionViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer


class CertificationViewSet(ProfileSectionViewSet):
    queryset = Certification.objects.all()
    serializer_class = CertificationSerializer


class LanguageViewSet(ProfileSectionViewSet):
    queryset = Language.objects.all()
    serializer_class = LanguageSerializer


logger = logging.getLogger(__name__)

# Import CV al giorno per utente (Sprint 66), uguale per tutti i piani e
# senza credito: ogni import è una chiamata al modello più costoso.
CV_IMPORT_DAILY_LIMIT = 5

UNREADABLE_CV_MESSAGE = "non siamo riusciti a leggere il CV, compila il profilo manualmente"


@transaction.atomic
def _reserve_cv_import(user):
    quota, _ = DailyQuota.objects.get_or_create(
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

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]
    post_throttle_scope = "cv_import"

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response(
                {"detail": "Nessun file caricato."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            raw_text = cv_import.extract_text(uploaded_file)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except cv_import.CVUnreadableError:
            return Response({"detail": UNREADABLE_CV_MESSAGE}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if not cv_import.has_sufficient_text(raw_text):
            return Response({"detail": UNREADABLE_CV_MESSAGE}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        quota = _reserve_cv_import(request.user)
        if quota is None:
            return Response(
                {"detail": f"Hai raggiunto il limite di {CV_IMPORT_DAILY_LIMIT} import del CV per oggi."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            structured_profile = cv_import.structure_with_claude(raw_text)
        except Exception:
            logger.exception("Import CV: strutturazione AI fallita")
            DailyQuota.objects.filter(pk=quota.pk).update(cv_import_count=F("cv_import_count") - 1)
            return Response({"detail": UNREADABLE_CV_MESSAGE}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(structured_profile, status=status.HTTP_200_OK)
