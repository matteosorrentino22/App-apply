import hmac
import zoneinfo

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


INVALID_INVITE_MESSAGE = "Registrazione non consentita: codice di invito mancante o non valido."


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=128, validators=[validate_password])
    invite_code = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200)

    class Meta:
        model = User
        fields = ["email", "password", "invite_code"]
        # Il controllo di unicità è in validate(), dopo il codice di invito:
        # senza codice valido non si scopre se un'email è già registrata.
        extra_kwargs = {"email": {"validators": []}}

    def validate(self, attrs):
        expected = settings.REGISTRATION_INVITE_CODE
        if expected and not hmac.compare_digest(
            attrs.get("invite_code", "").encode(), expected.encode()
        ):
            raise serializers.ValidationError({"invite_code": [INVALID_INVITE_MESSAGE]})
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": ["Un utente con questa email esiste già."]})
        return attrs

    def create(self, validated_data):
        validated_data.pop("invite_code", None)
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, max_length=128)

    def validate(self, attrs):
        user = User.objects.filter(email__iexact=attrs["email"]).first()
        # Anche con email inesistente si passa da authenticate(): ModelBackend
        # calcola comunque un hash, i tempi di risposta non rivelano se
        # l'account esiste.
        authenticated = authenticate(
            username=user.username if user else attrs["email"], password=attrs["password"]
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
            "first_name",
            "last_name",
            "plan",
            "extra_credit",
            "timezone",
            "interface_language",
            "cv_language_mode",
            "cv_include_photo",
            "objective_statement",
        ]
        # extra_credit è gestito solo da amministratore (Django Admin, §3
        # funzionali "Gestione account": nessun checkout/pagamento in UI) —
        # esposto qui in lettura per la schermata account (Sprint 20).
        read_only_fields = ["id", "email", "plan", "extra_credit"]
        extra_kwargs = {"objective_statement": {"max_length": 2000}}

    def validate_timezone(self, value):
        if value not in zoneinfo.available_timezones():
            raise serializers.ValidationError("Fuso orario non valido.")
        return value

    def update(self, instance, validated_data):
        # Solo i campi modificati (Sprint 66): `instance` è request.user,
        # letto all'autenticazione — un save() completo riscriverebbe anche
        # `extra_credit` con il valore di allora, annullando un addebito o
        # una ricarica avvenuti nel frattempo.
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data))
        return instance
