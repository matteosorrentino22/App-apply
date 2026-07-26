from rest_framework import serializers

from .models import Certification, Education, Experience, Language, Profile, Skill


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = [
            "id",
            "company",
            "role",
            "location",
            "start_date",
            "end_date",
            "bullets",
            "technologies",
        ]


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ["id", "institution", "title", "location", "dates", "notes"]


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

    class Meta:
        model = Profile
        fields = [
            "id",
            "summary",
            "photo",
            "key_achievements",
            "phone",
            "city",
            "linkedin_url",
            "experiences",
            "educations",
            "skills",
            "certifications",
            "languages",
        ]
