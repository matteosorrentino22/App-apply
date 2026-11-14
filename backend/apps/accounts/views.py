from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError
from django.http import FileResponse, Http404
from django.utils.encoding import force_str
from django.utils.http import urlencode, urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle
from rest_framework.views import APIView

from .account_data import build_export, delete_account
from .emails import (
    email_enabled,
    read_email_change_token,
    read_verification_token,
    send_account_deleted_email,
    send_email_change_emails,
    send_already_registered_email,
    send_password_reset_email,
    send_verification_email,
)
from .legal import missing_acceptances, public_legal_info, record_acceptances
from .models import User
from .serializers import (
    ChangePasswordSerializer,
    DeleteAccountSerializer,
    EmailChangeConfirmSerializer,
    EmailChangeSerializer,
    EmailOnlySerializer,
    LegalAcceptanceSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    UserOnboardingSerializer,
    VerifyEmailSerializer,
)
from .throttling import EmailAddressRateThrottle, LoginEmailRateThrottle
from .tokens import create_token, revoke_all_tokens
from .usage import usage_for_user

EXPORT_SALT = "apps.accounts.export"
EXPORT_URL_MAX_AGE = 10 * 60


def _user_agent(request):
    return request.META.get("HTTP_USER_AGENT", "")


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    throttle_scope = "register"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Con l'invio email attivo (Sprint 67) la risposta è identica sia
        # per un'email nuova sia per una già registrata: nessun token, il
        # login arriva dopo la conferma dell'indirizzo.
        if email_enabled():
            existing = serializer.validated_data["existing_user"]
            if existing is not None:
                send_already_registered_email(existing)
            else:
                user = serializer.save()
                record_acceptances(user)
                send_verification_email(user)
            return Response({"verification_required": True}, status=status.HTTP_201_CREATED)

        user = serializer.save()
        record_acceptances(user)
        return Response(
            {"token": create_token(user, _user_agent(request)), "verification_required": False},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle, ScopedRateThrottle, LoginEmailRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        # Solo dopo la password corretta: il messaggio non rivela nulla a
        # chi non conosce già le credenziali.
        if email_enabled() and not user.email_verified:
            return Response(
                {
                    "code": "email_not_verified",
                    "detail": "Conferma il tuo indirizzo email con il link che ti abbiamo inviato.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        token = create_token(user, _user_agent(request))
        return Response({"token": token})


class LogoutView(APIView):
    """Revoca il solo token della richiesta (questo dispositivo)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Sprint 70: la PWA manda l'endpoint push del browser in uso, che
        # smette di ricevere notifiche per questo account (gli altri
        # dispositivi restano registrati).
        endpoint = request.data.get("push_endpoint") if hasattr(request.data, "get") else None
        if isinstance(endpoint, str) and endpoint:
            request.user.push_subscriptions.filter(endpoint=endpoint[:1000]).delete()
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserOnboardingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UsageView(APIView):
    """Contatori di oggi, massimali del piano e prezzi (Sprint 70). Permessi
    di default: dietro il gate delle accettazioni come le azioni a cui si
    riferisce."""

    def get(self, request):
        return Response(usage_for_user(request.user))


class LegalInfoView(APIView):
    """Versioni e date dei testi legali, dati del titolare (da env) e flag
    per la PWA (Sprint 67). Pubblico: le pagine /privacy e /terms si leggono
    senza account."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        data = public_legal_info()
        data["google_login_enabled"] = bool(
            settings.SOCIALACCOUNT_PROVIDERS["google"]["APPS"][0]["client_id"]
        )
        data["email_enabled"] = email_enabled()
        return Response(data)


class LegalAcceptanceView(APIView):
    """Accettazione delle versioni correnti (gate degli utenti esistenti o di
    una nuova versione dei testi)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        LegalAcceptanceSerializer(data=request.data).is_valid(raise_exception=True)
        missing = missing_acceptances(request.user)
        if missing:
            record_acceptances(request.user, missing)
        return Response(UserOnboardingSerializer(request.user).data)


class VerifyEmailView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_id, email = read_verification_token(serializer.validated_data["token"])
        except signing.SignatureExpired:
            return Response({"code": "expired", "detail": "Link scaduto."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return Response({"code": "invalid", "detail": "Link non valido."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(pk=user_id, email__iexact=email, is_active=True).first()
        if user is None:
            return Response({"code": "invalid", "detail": "Link non valido."}, status=status.HTTP_400_BAD_REQUEST)
        if not user.email_verified:
            User.objects.filter(pk=user.pk).update(email_verified=True)
        return Response({"status": "verified"})


class _EmailRequestView(APIView):
    """Richieste che inviano un'email a un indirizzo (reinvio verifica,
    recupero password): risposta sempre identica, che l'indirizzo sia
    registrato o no; limite per IP e per indirizzo."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle, EmailAddressRateThrottle]
    throttle_scope = "email_request"

    def send(self, user):
        raise NotImplementedError

    def post(self, request):
        if not email_enabled():
            return Response(
                {"code": "email_unavailable", "detail": "L'invio di email non è disponibile."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        serializer = EmailOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True).first()
        if user is not None:
            self.send(user)
        return Response({"status": "sent_if_registered"})


class ResendVerificationView(_EmailRequestView):
    def send(self, user):
        if not user.email_verified:
            send_verification_email(user)


class PasswordResetRequestView(_EmailRequestView):
    def send(self, user):
        if user.has_usable_password():
            send_password_reset_email(user)


class PasswordResetConfirmView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "email_request"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user_id = int(force_str(urlsafe_base64_decode(data["uid"])))
        except (TypeError, ValueError, OverflowError):
            user_id = None
        user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
        if user is None or not default_token_generator.check_token(user, data["token"]):
            return Response(
                {"code": "invalid_link", "detail": "Link non valido o scaduto."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            validate_password(data["new_password"], user)
        except ValidationError as exc:
            return Response({"new_password": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(data["new_password"])
        # Il link è arrivato all'indirizzo: vale anche come verifica.
        user.email_verified = True
        user.save(update_fields=["password", "email_verified"])
        revoke_all_tokens(user)
        return Response({"status": "password_reset"})


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "password_check"

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        # Disconnette tutti i dispositivi, poi un token nuovo per questo.
        revoke_all_tokens(user)
        return Response({"token": create_token(user, _user_agent(request))})


EMAIL_UNAVAILABLE_RESPONSE = {"code": "email_unavailable", "detail": "L'invio di email non è disponibile."}


class EmailChangeRequestView(APIView):
    """Cambio dell'email di accesso (Sprint 70, diritto di rettifica):
    password + nuovo indirizzo → link di conferma al nuovo indirizzo e avviso
    a quello attuale. L'email cambia solo alla conferma. Risposta identica
    anche se il nuovo indirizzo ha già un account (in quel caso nessuna
    email): non rivela quali indirizzi sono registrati."""

    throttle_scope = "password_check"

    def post(self, request):
        if not email_enabled():
            return Response(EMAIL_UNAVAILABLE_RESPONSE, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        serializer = EmailChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        new_email = serializer.validated_data["new_email"]
        if not User.objects.filter(email__iexact=new_email).exists():
            send_email_change_emails(request.user, new_email)
        return Response({"status": "confirmation_sent"})


class EmailChangeConfirmView(APIView):
    """Conferma dal link (pubblico come la verifica dell'email: il link può
    essere aperto su un dispositivo dove l'utente non è collegato)."""

    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    throttle_scope = "email_request"

    def post(self, request):
        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user_id, old_email, new_email = read_email_change_token(serializer.validated_data["token"])
        except signing.SignatureExpired:
            return Response({"code": "expired", "detail": "Link scaduto."}, status=status.HTTP_400_BAD_REQUEST)
        except signing.BadSignature:
            return Response({"code": "invalid", "detail": "Link non valido."}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(pk=user_id, email__iexact=old_email, is_active=True).first()
        if user is None:
            return Response({"code": "invalid", "detail": "Link non valido."}, status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            return Response(
                {"code": "email_taken", "detail": "Questo indirizzo è già usato da un altro account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Lo username resta uguale all'email (§4.1 tecniche): il login lo usa.
        user.email = new_email
        user.username = new_email
        user.email_verified = True
        user.save(update_fields=["email", "username", "email_verified"])
        return Response({"status": "email_changed", "email": new_email})


class DeleteAccountView(APIView):
    """Cancellazione immediata dell'account (Sprint 67, art. 17 GDPR)."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "password_check"

    def post(self, request):
        serializer = DeleteAccountSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        email, language = user.email, user.interface_language
        delete_account(user)
        send_account_deleted_email(email, language)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DataExportView(APIView):
    """Restituisce un URL firmato (10 minuti) da cui scaricare lo ZIP
    dell'export: come per i PDF (Sprint 66) un semplice link funziona anche
    nella PWA iOS, che non può aggiungere l'header Authorization. Il limite
    (3 al giorno) vale qui, sulla richiesta autenticata."""

    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = "data_export"

    def post(self, request):
        signature = signing.TimestampSigner(salt=EXPORT_SALT).sign(str(request.user.pk))
        return Response({"url": f"/api/accounts/export/download/?{urlencode({'s': signature})}"})


class DataExportDownloadView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            user_id = signing.TimestampSigner(salt=EXPORT_SALT).unsign(
                request.query_params.get("s", ""), max_age=EXPORT_URL_MAX_AGE
            )
        except signing.BadSignature as exc:
            raise Http404 from exc
        user = User.objects.filter(pk=int(user_id), is_active=True).first()
        if user is None:
            raise Http404
        response = FileResponse(
            build_export(user),
            as_attachment=True,
            filename=f"app-apply-dati-{user.pk}.zip",
            content_type="application/zip",
        )
        response["Cache-Control"] = "private, no-store"
        return response
