from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

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


class CVImportView(APIView):
    """Pre-popola il profilo da un CV caricato (PDF/.docx), senza salvarlo (§5.4 tecniche)."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

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
            return Response(
                {"detail": "non siamo riusciti a leggere il CV, compila il profilo manualmente"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        if not cv_import.has_sufficient_text(raw_text):
            return Response(
                {"detail": "non siamo riusciti a leggere il CV, compila il profilo manualmente"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        structured_profile = cv_import.structure_with_claude(raw_text)
        return Response(structured_profile, status=status.HTTP_200_OK)
