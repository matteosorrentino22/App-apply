from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "password"]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Un utente con questa email esiste già.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"]).first()
        authenticated = (
            authenticate(username=user.username, password=attrs["password"]) if user else None
        )
        if authenticated is None:
            raise serializers.ValidationError("Credenziali non valide.")
        attrs["user"] = authenticated
        return attrs


class UserOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "plan",
            "timezone",
            "interface_language",
            "cv_language_mode",
            "cv_include_photo",
            "objective_statement",
        ]
        read_only_fields = ["id", "email", "plan"]
