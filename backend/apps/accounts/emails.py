# Email di servizio (Sprint 67): testo semplice, in italiano o in inglese
# secondo `User.interface_language`. Mai dati del profilo nel corpo: solo
# il link o la conferma dell'operazione.
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils.encoding import force_bytes
from django.utils.http import urlencode, urlsafe_base64_encode

from .tasks import send_service_email

logger = logging.getLogger(__name__)

VERIFY_EMAIL_SALT = "apps.accounts.verify-email"

_SIGNATURE = {
    "it": "\n\n— App-apply\nEmail automatica: non rispondere a questo messaggio.",
    "en": "\n\n— App-apply\nAutomated email: please do not reply to this message.",
}

MESSAGES = {
    "verify": {
        "it": (
            "Conferma il tuo indirizzo email",
            "Ciao,\n\nper completare la registrazione ad App-apply conferma il tuo indirizzo "
            "aprendo questo link (valido 3 giorni):\n\n{link}\n\n"
            "Se non sei stato tu a registrarti, ignora questa email: senza conferma l'account non è utilizzabile.",
        ),
        "en": (
            "Confirm your email address",
            "Hi,\n\nto complete your App-apply registration please confirm your address "
            "by opening this link (valid for 3 days):\n\n{link}\n\n"
            "If you did not sign up, ignore this email: the account cannot be used without confirmation.",
        ),
    },
    "already_registered": {
        "it": (
            "Tentativo di registrazione con il tuo indirizzo",
            "Ciao,\n\nqualcuno ha provato a registrarsi ad App-apply con questo indirizzo email, "
            "che ha già un account.\n\nSe sei stato tu, accedi da {login_link} oppure, se non ricordi "
            "la password, recuperala da {forgot_link}.\n\nSe non sei stato tu, puoi ignorare questa "
            "email: il tuo account non è stato modificato.",
        ),
        "en": (
            "Sign-up attempt with your address",
            "Hi,\n\nsomeone tried to sign up to App-apply with this email address, which already "
            "has an account.\n\nIf it was you, log in at {login_link} or, if you forgot your "
            "password, reset it at {forgot_link}.\n\nIf it wasn't you, you can ignore this email: "
            "your account has not been changed.",
        ),
    },
    "password_reset": {
        "it": (
            "Recupero della password",
            "Ciao,\n\nabbiamo ricevuto una richiesta di recupero della password del tuo account "
            "App-apply. Per sceglierne una nuova apri questo link (valido 3 giorni, utilizzabile "
            "una sola volta):\n\n{link}\n\nDopo il cambio sarai disconnesso da tutti i dispositivi.\n\n"
            "Se non hai chiesto tu il recupero, ignora questa email: la password resta invariata.",
        ),
        "en": (
            "Password reset",
            "Hi,\n\nwe received a request to reset the password of your App-apply account. "
            "To choose a new one open this link (valid for 3 days, single use):\n\n{link}\n\n"
            "After the change you will be logged out of all devices.\n\n"
            "If you did not request it, ignore this email: your password stays the same.",
        ),
    },
    "account_deleted": {
        "it": (
            "Il tuo account è stato eliminato",
            "Ciao,\n\nti confermiamo che il tuo account App-apply e tutti i dati collegati "
            "(profilo, offerte, documenti, bozze, chat, file) sono stati eliminati. Le copie di "
            "backup che li contengono vengono cancellate automaticamente entro 7 giorni.\n\n"
            "Se non hai chiesto tu la cancellazione, rispondi al titolare indicato nell'informativa privacy.",
        ),
        "en": (
            "Your account has been deleted",
            "Hi,\n\nwe confirm that your App-apply account and all related data (profile, jobs, "
            "documents, drafts, chats, files) have been deleted. Backup copies containing them "
            "are automatically erased within 7 days.\n\n"
            "If you did not request the deletion, contact the controller listed in the privacy policy.",
        ),
    },
}


def email_enabled():
    """Invio email configurato (Gmail SMTP con password per le app). Se non
    lo è: verifica dell'indirizzo spenta, recupero password non disponibile."""
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def _lang(language):
    return "en" if language == "en" else "it"


def send_templated_email(kind, to, language, **params):
    lang = _lang(language)
    subject, body = MESSAGES[kind][lang]
    try:
        send_service_email.delay(to, f"App-apply — {subject}", body.format(**params) + _SIGNATURE[lang])
    except Exception:
        # Broker non raggiungibile: l'operazione dell'utente non deve fallire
        # per un'email non accodata (nel log solo il tipo, mai l'indirizzo).
        logger.exception("Email '%s' non accodata", kind)


def _url(path, **query):
    return f"{settings.PUBLIC_BASE_URL}{path}?{urlencode(query)}" if query else f"{settings.PUBLIC_BASE_URL}{path}"


def make_verification_token(user):
    return signing.TimestampSigner(salt=VERIFY_EMAIL_SALT).sign(f"{user.pk}:{user.email.lower()}")


def read_verification_token(token):
    """(user_id, email) dal token, o solleva signing.SignatureExpired /
    signing.BadSignature."""
    value = signing.TimestampSigner(salt=VERIFY_EMAIL_SALT).unsign(
        token, max_age=settings.EMAIL_VERIFICATION_MAX_AGE
    )
    user_id, _, email = value.partition(":")
    if not user_id.isdigit() or not email:
        raise signing.BadSignature("payload non valido")
    return int(user_id), email


def send_verification_email(user):
    send_templated_email(
        "verify", user.email, user.interface_language,
        link=_url("/verify-email", t=make_verification_token(user)),
    )


def send_already_registered_email(user):
    send_templated_email(
        "already_registered", user.email, user.interface_language,
        login_link=_url("/login"), forgot_link=_url("/forgot-password"),
    )


def send_password_reset_email(user):
    send_templated_email(
        "password_reset", user.email, user.interface_language,
        link=_url(
            "/reset-password",
            uid=urlsafe_base64_encode(force_bytes(user.pk)),
            token=default_token_generator.make_token(user),
        ),
    )


def send_account_deleted_email(email, language):
    send_templated_email("account_deleted", email, language)
