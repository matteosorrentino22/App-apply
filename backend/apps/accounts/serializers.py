import hmac
import zoneinfo

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone as dj_timezone
from rest_framework import serializers

from apps.profiles.models import Profile

from .emails import email_enabled
from .legal import MIN_AGE, missing_acceptances
from .models import User


INVALID_INVITE_MESSAGE = "Registrazione non consentita: codice di invito mancante o non valido."
EMAIL_TAKEN_MESSAGE = "Un utente con questa email esiste già."


def is_valid_timezone(value):
    return bool(value) and value in zoneinfo.available_timezones()


class LegalConsentFields(serializers.Serializer):
    """Le tre spunte obbligatorie (Sprint 67): mai pre-selezionate nella PWA,
    validate anche qui — un valore diverso da true è rifiutato."""

    accept_privacy = serializers.BooleanField(write_only=True)
    accept_terms = serializers.BooleanField(write_only=True)
    confirm_age = serializers.BooleanField(write_only=True)

    def validate_accept_privacy(self, value):
        if value is not True:
            raise serializers.ValidationError("Devi dichiarare di aver letto l'informativa privacy.")
        return value

    def validate_accept_terms(self, value):
        if value is not True:
            raise serializers.ValidationError("Devi accettare i termini di servizio.")
        return value

    def validate_confirm_age(self, value):
        if value is not True:
            raise serializers.ValidationError(f"Per usare l'app devi avere almeno {MIN_AGE} anni.")
        return value


class RegisterSerializer(LegalConsentFields, serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=128, validators=[validate_password])
    invite_code = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200)
    interface_language = serializers.ChoiceField(
        choices=User.InterfaceLanguage.choices, required=False, write_only=True
    )
    # Fuso rilevato dal browser (Sprint 70): un nome non riconosciuto non
    # blocca la registrazione, resta il default (Europe/Rome).
    timezone = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=50)

    class Meta:
        model = User
        fields = [
            "email", "password", "invite_code", "interface_language", "timezone",
            "accept_privacy", "accept_terms", "confirm_age",
        ]
        # Il controllo di unicità è in validate(), dopo il codice di invito:
        # senza codice valido non si scopre se un'email è già registrata.
        extra_kwargs = {"email": {"validators": []}}

    def validate(self, attrs):
        expected = settings.REGISTRATION_INVITE_CODE
        if expected and not hmac.compare_digest(
            attrs.get("invite_code", "").encode(), expected.encode()
        ):
            raise serializers.ValidationError({"invite_code": [INVALID_INVITE_MESSAGE]})
        attrs["existing_user"] = User.objects.filter(email__iexact=attrs["email"]).first()
        # Con l'invio email attivo un'email già registrata non si rivela
        # (la view risponde come a una registrazione riuscita e avvisa per
        # email il titolare dell'indirizzo); senza email, comportamento di prima.
        if attrs["existing_user"] is not None and not email_enabled():
            raise serializers.ValidationError({"email": [EMAIL_TAKEN_MESSAGE]})
        return attrs

    def validate_timezone(self, value):
        return value if is_valid_timezone(value) else ""

    def create(self, validated_data):
        extra = {"timezone": validated_data["timezone"]} if validated_data.get("timezone") else {}
        return User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            interface_language=validated_data.get("interface_language", User.InterfaceLanguage.IT),
            email_verified=not email_enabled(),
            **extra,
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
            "email_verified",
            "notifications_enabled",
            "legal_acceptance_required",
            "legal_missing",
            "legal_acceptances",
            "profile_status",
        ]
        # extra_credit è gestito solo da amministratore (Django Admin, §3
        # funzionali "Gestione account": nessun checkout/pagamento in UI) —
        # esposto qui in lettura per la schermata account (Sprint 20).
        read_only_fields = ["id", "email", "plan", "extra_credit", "email_verified"]
        extra_kwargs = {"objective_statement": {"max_length": 2000}}

    legal_acceptance_required = serializers.SerializerMethodField()
    legal_missing = serializers.SerializerMethodField()
    legal_acceptances = serializers.SerializerMethodField()
    profile_status = serializers.SerializerMethodField()

    def get_profile_status(self, user):
        # Sprint 70: "complete" con la stessa regola della generazione CV
        # (`Profile.is_complete`, almeno un titolo di studio); "empty" se
        # non c'è ancora nulla (onboarding mai fatto), altrimenti "incomplete".
        profile = Profile.objects.filter(user=user).first()
        if profile is None:
            return "empty"
        if profile.is_complete:
            return "complete"
        if profile.experiences.exists() or profile.summary:
            return "incomplete"
        return "empty"

    def get_legal_missing(self, user):
        return missing_acceptances(user)

    def get_legal_acceptance_required(self, user):
        return bool(missing_acceptances(user))

    def get_legal_acceptances(self, user):
        # Ultima accettazione per documento (lo storico completo è nell'export).
        latest = {}
        for acceptance in user.legal_acceptances.all():
            latest[acceptance.document] = {
                "version": acceptance.version,
                "accepted_at": acceptance.accepted_at,
            }
        return latest

    def validate_timezone(self, value):
        if not is_valid_timezone(value):
            raise serializers.ValidationError("Fuso orario non valido.")
        return value

    def update(self, instance, validated_data):
        # Notifiche riaccese (Sprint 70): `last_notified_at` riparte da ora,
        # così la prima notifica mattutina non conta i job del periodo di
        # silenzio.
        if validated_data.get("notifications_enabled") is True and not instance.notifications_enabled:
            validated_data["last_notified_at"] = dj_timezone.now()
        # Solo i campi modificati (Sprint 66): `instance` è request.user,
        # letto all'autenticazione — un save() completo riscriverebbe anche
        # `extra_credit` con il valore di allora, annullando un addebito o
        # una ricarica avvenuti nel frattempo.
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save(update_fields=list(validated_data))
        if validated_data.get("notifications_enabled") is False:
            # Notifiche spente (Sprint 67): via anche le sottoscrizioni push
            # di tutti i dispositivi, non solo il flag.
            instance.push_subscriptions.all().delete()
        return instance


class PasswordCheckMixin:
    def validate_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password non corretta.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, max_length=128)
    new_password = serializers.CharField(write_only=True, max_length=128)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Password attuale non corretta.")
        return value

    def validate(self, attrs):
        validate_password(attrs["new_password"], self.context["request"].user)
        return attrs


class DeleteAccountSerializer(PasswordCheckMixin, serializers.Serializer):
    password = serializers.CharField(write_only=True, max_length=128)
    confirm = serializers.BooleanField(write_only=True)

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError("Conferma esplicita richiesta.")
        return value


class EmailChangeSerializer(PasswordCheckMixin, serializers.Serializer):
    password = serializers.CharField(write_only=True, max_length=128)
    new_email = serializers.EmailField(max_length=254)

    def validate_new_email(self, value):
        if value.strip().lower() == self.context["request"].user.email.lower():
            raise serializers.ValidationError("È già la tua email di accesso.")
        return value.strip()


class EmailChangeConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=1000)


class LegalAcceptanceSerializer(LegalConsentFields):
    pass


class EmailOnlySerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=500)


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=50)
    token = serializers.CharField(max_length=100)
    new_password = serializers.CharField(write_only=True, max_length=128)
