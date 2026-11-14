from rest_framework import serializers

from apps.common.files import InvalidPhoto, sanitize_photo, signed_photo_url

from .models import Certification, Education, Experience, Language, Profile, Skill


# Testi del profilo che finiscono nei prompt AI e nei PDF (Sprint 66): stessi
# tetti del content_json delle bozze (apps.cv.draft_validation).
MAX_BULLETS = 30
MAX_BULLET_LENGTH = 2_000
MAX_TECHNOLOGIES = 50
MAX_TECHNOLOGY_LENGTH = 200


def _validate_string_list(value, max_items, max_length):
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise serializers.ValidationError("Deve essere una lista di testi.")
    if len(value) > max_items:
        raise serializers.ValidationError(f"Massimo {max_items} elementi.")
    if any(len(item) > max_length for item in value):
        raise serializers.ValidationError(f"Ogni elemento può avere al massimo {max_length} caratteri.")
    return value


class ExperienceSerializer(serializers.ModelSerializer):
    def validate_bullets(self, value):
        return _validate_string_list(value, MAX_BULLETS, MAX_BULLET_LENGTH)

    def validate_technologies(self, value):
        return _validate_string_list(value, MAX_TECHNOLOGIES, MAX_TECHNOLOGY_LENGTH)

    class Meta:
        model = Experience
        fields = [
            "id",
            "company",
            "role",
            "location",
            "location_country_code",
            "start_date",
            "end_date",
            "bullets",
            "technologies",
        ]


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = [
            "id",
            "institution",
            "title",
            "location",
            "location_country_code",
            "start_date",
            "end_date",
            "notes",
        ]
        extra_kwargs = {"notes": {"max_length": 3_000}}


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


class CertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certification
        fields = ["id", "name"]


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ["id", "language", "level"]


class ProfileSerializer(serializers.ModelSerializer):
    experiences = ExperienceSerializer(many=True, read_only=True)
    educations = EducationSerializer(many=True, read_only=True)
    skills = SkillSerializer(many=True, read_only=True)
    certifications = CertificationSerializer(many=True, read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    # La foto si carica qui ma non si rilegge mai dal path media (Sprint 66):
    # `photo_url` è un URL firmato a scadenza (apps.common.files).
    photo = serializers.ImageField(write_only=True, required=False)
    has_photo = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            "id",
            "summary",
            "photo",
            "has_photo",
            "photo_url",
            "phone",
            "email",
            "city",
            "country_code",
            "linkedin_url",
            "experiences",
            "educations",
            "skills",
            "certifications",
            "languages",
        ]
        extra_kwargs = {"summary": {"max_length": 5_000}}

    def get_has_photo(self, profile):
        return bool(profile.photo)

    def get_photo_url(self, profile):
        return signed_photo_url(profile)

    def validate_photo(self, value):
        try:
            return sanitize_photo(value)
        except InvalidPhoto as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def update(self, instance, validated_data):
        # La FileField non cancella il file sostituito (Sprint 67): senza
        # questo la foto precedente resterebbe su disco anche dopo la
        # cancellazione dell'account, non più collegata a nessun record.
        old_photo_name = instance.photo.name if instance.photo else ""
        instance = super().update(instance, validated_data)
        if "photo" in validated_data and old_photo_name and old_photo_name != instance.photo.name:
            instance.photo.storage.delete(old_photo_name)
        return instance
