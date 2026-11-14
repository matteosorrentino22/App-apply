# Email di servizio (Sprint 67): testo semplice, in italiano o in inglese
# secondo `User.interface_language`. Mai dati del profilo nel corpo: solo
# il link o la conferma dell'operazione. Dallo Sprint 71 i testi sono
# tradotti con gettext come il resto del backend (msgid in italiano,
# inglese in locale/en/LC_MESSAGES/django.po).
import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils.encoding import force_bytes
from django.utils import translation
from django.utils.http import urlencode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy

from .tasks import send_service_email

logger = logging.getLogger(__name__)

VERIFY_EMAIL_SALT = "apps.accounts.verify-email"
CHANGE_EMAIL_SALT = "apps.accounts.change-email"

_SIGNATURE = gettext_lazy(
    "— App-apply\n"
    "Email automatica: non rispondere a questo messaggio."
)

MESSAGES = {
    "verify": (
        gettext_lazy("Conferma il tuo indirizzo email"),
        gettext_lazy(
            "Ciao,\n\n"
            "per completare la registrazione ad App-apply conferma il tuo indirizzo aprendo questo "
            "link (valido 3 giorni):\n\n"
            "{link}\n\n"
            "Se non sei stato tu a registrarti, ignora questa email: senza conferma l'account non è "
            "utilizzabile."
        ),
    ),
    "already_registered": (
        gettext_lazy("Tentativo di registrazione con il tuo indirizzo"),
        gettext_lazy(
            "Ciao,\n\n"
            "qualcuno ha provato a registrarsi ad App-apply con questo indirizzo email, che ha già "
            "un account.\n\n"
            "Se sei stato tu, accedi da {login_link} oppure, se non ricordi la password, recuperala "
            "da {forgot_link}.\n\n"
            "Se non sei stato tu, puoi ignorare questa email: il tuo account non è stato modificato."
        ),
    ),
    "password_reset": (
        gettext_lazy("Recupero della password"),
        gettext_lazy(
            "Ciao,\n\n"
            "abbiamo ricevuto una richiesta di recupero della password del tuo account App-apply. "
            "Per sceglierne una nuova apri questo link (valido 3 giorni, utilizzabile una sola "
            "volta):\n\n"
            "{link}\n\n"
            "Dopo il cambio sarai disconnesso da tutti i dispositivi.\n\n"
            "Se non hai chiesto tu il recupero, ignora questa email: la password resta invariata."
        ),
    ),
    "email_change_confirm": (
        gettext_lazy("Conferma il nuovo indirizzo email"),
        gettext_lazy(
            "Ciao,\n\n"
            "è stato chiesto di usare questo indirizzo come nuova email di accesso di un account "
            "App-apply. Per confermare apri questo link (valido 3 giorni):\n\n"
            "{link}\n\n"
            "Finché non confermi, l'email di accesso resta quella di prima. Se non sei stato tu, "
            "ignora questa email."
        ),
    ),
    "email_change_notice": (
        gettext_lazy("Richiesta di cambio dell'email di accesso"),
        gettext_lazy(
            "Ciao,\n\n"
            "è stato chiesto di cambiare l'email di accesso del tuo account App-apply. Abbiamo "
            "inviato un link di conferma al nuovo indirizzo: l'email di accesso cambia solo dopo la "
            "conferma, fino ad allora resta questa.\n\n"
            "Se non sei stato tu, qualcuno conosce la tua password: cambiala subito dalle "
            "Impostazioni dell'app ({settings_link})."
        ),
    ),
    "account_deleted": (
        gettext_lazy("Il tuo account è stato eliminato"),
        gettext_lazy(
            "Ciao,\n\n"
            "ti confermiamo che il tuo account App-apply e tutti i dati collegati (profilo, offerte, "
            "documenti, bozze, chat, file) sono stati eliminati. Le copie di backup che li "
            "contengono vengono cancellate automaticamente entro 7 giorni.\n\n"
            "Se non hai chiesto tu la cancellazione, rispondi al titolare indicato nell'informativa "
            "privacy."
        ),
    ),
}


def email_enabled():
    """Invio email configurato (Gmail SMTP con password per le app). Se non
    lo è: verifica dell'indirizzo spenta, recupero password non disponibile."""
    return bool(settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def _lang(language):
    return "en" if language == "en" else "it"


def send_templated_email(kind, to, language, **params):
    subject, body = MESSAGES[kind]
    with translation.override(_lang(language)):
        subject, body = str(subject), str(body).format(**params) + "\n\n" + str(_SIGNATURE)
    try:
        send_service_email.delay(to, f"App-apply — {subject}", body)
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
    user_id, _sep, email = value.partition(":")
    if not user_id.isdigit() or not email:
        raise signing.BadSignature("payload non valido")
    return int(user_id), email


def make_email_change_token(user, new_email):
    # Contiene anche l'email attuale: dopo il cambio il link non vale più
    # (stesso schema della verifica, nessuna tabella in più).
    return signing.TimestampSigner(salt=CHANGE_EMAIL_SALT).sign_object(
        {"id": user.pk, "old": user.email.lower(), "new": new_email.lower()}
    )


def read_email_change_token(token):
    """(user_id, email attuale, nuova email) dal token, o solleva
    signing.SignatureExpired / signing.BadSignature."""
    value = signing.TimestampSigner(salt=CHANGE_EMAIL_SALT).unsign_object(
        token, max_age=settings.EMAIL_VERIFICATION_MAX_AGE
    )
    if (
        not isinstance(value, dict)
        or not isinstance(value.get("id"), int)
        or not all(isinstance(value.get(key), str) and value[key] for key in ("old", "new"))
    ):
        raise signing.BadSignature("payload non valido")
    return value["id"], value["old"], value["new"]


def send_email_change_emails(user, new_email):
    send_templated_email(
        "email_change_confirm", new_email, user.interface_language,
        link=_url("/confirm-email-change", t=make_email_change_token(user, new_email)),
    )
    send_templated_email(
        "email_change_notice", user.email, user.interface_language, settings_link=_url("/settings"),
    )


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
