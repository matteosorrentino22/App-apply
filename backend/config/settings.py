import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


_DEV_SECRET_KEY = "insecure-dev-key-change-me"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", _DEV_SECRET_KEY)
# Default sicuri (Sprint 66): una variabile mancante nel .env non deve mai
# accendere DEBUG né lasciare in uso una chiave nota (firma di sessioni,
# reset password e URL firmati dei download).
DEBUG = env_bool("DJANGO_DEBUG", False)
# "insecure" copre sia questo default sia quello di .env.example.
if not DEBUG and (not SECRET_KEY or "insecure" in SECRET_KEY):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY obbligatoria (e non quella di sviluppo) con DJANGO_DEBUG=false.")
TESTING = sys.argv[1:2] == ["test"]
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

# Dietro Caddy in produzione, Django deve fidarsi dell'header impostato dal
# reverse proxy per sapere che la richiesta originale era HTTPS (altrimenti
# SECURE_SSL_REDIRECT genera un loop di redirect) — 02-specifiche-tecniche-v3.md
# §8.3. Disattivato in dev, dove non c'è TLS.
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Caddy imposta già lo stesso valore su tutte le risposte (Caddyfile.prod):
    # qui serve a `check --deploy` e a non dipendere solo dal proxy.
    SECURE_HSTS_SECONDS = 31536000
    # HSTS senza includeSubDomains/preload, per scelta (Sprint 66): il
    # dominio può avere sottodomini non serviti da questa app.
    SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

# Stesso valore impostato da Caddy su tutte le risposte (Caddyfile.prod).
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_celery_beat",
    "apps.accounts",
    "apps.common",
    "apps.profiles",
    "apps.searches",
    "apps.jobs",
    "apps.cv",
    "apps.notifications",
]

SITE_ID = 1

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Dopo le sessioni e prima di CommonMiddleware, come LocaleMiddleware
    # (Sprint 71): lingua dei messaggi dell'API da Accept-Language.
    "apps.common.middleware.ApiLocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "app_apply"),
        "USER": os.environ.get("POSTGRES_USER", "app_apply"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "app_apply"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Europe/Rome governa il reset delle quote giornaliere
# (02-specifiche-tecniche-v3.md §7): fuso di sistema unico per Django/Celery Beat.
TIME_ZONE = "Europe/Rome"
# Testi rivolti all'utente (Sprint 71): sorgenti in italiano con gettext,
# traduzione inglese in locale/en/LC_MESSAGES/django.po (.mo compilato e
# committato, comandi in DEPLOY.md §4.9). Nelle richieste API la lingua
# arriva da Accept-Language (apps.common.middleware.ApiLocaleMiddleware);
# nei task (notifiche, scoring) da User.interface_language. Qualunque altra
# lingua ricade sull'italiano, come il Django Admin.
LANGUAGE_CODE = "it"
LANGUAGES = [("it", "Italiano"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Foto profilo e PDF dei CV generati (apps.profiles.Profile.photo, apps.cv.CVDocument.pdf_file).
# Mai serviti direttamente (Caddy risponde 404 su /media/*, Sprint 66): si
# scaricano solo dagli URL firmati di apps.common.files.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"
if TESTING:
    # I test lanciati nel container di produzione (`compose run web`) non
    # devono mai scrivere nel volume media_data montato su /app/mediafiles.
    MEDIA_ROOT = Path(tempfile.mkdtemp(prefix="test-media-"))

# Upload (Sprint 66): il file più grande accettato è il CV da importare
# (5 MB, apps.profiles.cv_import), la foto profilo ha lo stesso tetto. Il
# corpo non-file (JSON delle bozze, testi) resta sotto i 2,5 MB di default.
DATA_UPLOAD_MAX_MEMORY_SIZE = 2_621_440
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Path del Django Admin configurabile (Sprint 66): va tenuto allineato con
# Caddy, che inoltra a Django solo /api/*, /accounts/* e questo path (stessa
# variabile d'ambiente passata al container caddy in docker-compose.prod.yml).
DJANGO_ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "admin/").strip("/") + "/"

# Cache condivisa tra i worker gunicorn (Sprint 66): serve a throttling DRF e
# al limite dei tentativi di login dell'admin, che con la LocMemCache di
# default sarebbero contati per processo. Nei test una DummyCache: nessuna
# dipendenza da Redis e nessun contatore che si accumula tra un test e
# l'altro (i test del throttling usano override_settings con una LocMemCache).
if TESTING:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.environ.get("REDIS_CACHE_URL", "redis://redis:6379/2"),
        }
    }

# Token di accesso dell'API (Sprint 66, apps.accounts.authentication):
# scadono dopo questo numero di giorni senza alcuna richiesta.
AUTH_TOKEN_IDLE_DAYS = 30

# Registrazione su invito (Sprint 66): se valorizzato, POST /api/accounts/
# register/ richiede `invite_code` uguale; vuoto = registrazione aperta.
REGISTRATION_INVITE_CODE = os.environ.get("REGISTRATION_INVITE_CODE", "")
if TESTING:
    # Come per l'email: il codice reale del .env non deve cambiare l'esito
    # dei test (quelli dell'invito lo impostano con override_settings).
    REGISTRATION_INVITE_CODE = ""

# Accettazione di informativa privacy, termini ed età minima (Sprint 67,
# apps.accounts.legal): chi non ha accettato le versioni correnti riceve 403
# `legal_acceptance_required` su quasi tutta l'API. Spento nei test, dove la
# gran parte degli utenti è creata senza accettazioni: i test del gate lo
# riaccendono con override_settings.
LEGAL_GATE_ENABLED = not TESTING
# Titolare del trattamento, mostrato nelle pagine legali (GET /api/legal/):
# mai nel repository, che è pubblico. Se mancano nome o email le pagine
# mostrano un avviso "dati del titolare da completare".
LEGAL_CONTROLLER_NAME = os.environ.get("LEGAL_CONTROLLER_NAME", "").strip()
LEGAL_CONTROLLER_ADDRESS = os.environ.get("LEGAL_CONTROLLER_ADDRESS", "").strip()
LEGAL_CONTROLLER_EMAIL = os.environ.get("LEGAL_CONTROLLER_EMAIL", "").strip()

# URL pubblico della PWA, usato nei link delle email (verifica dell'indirizzo,
# recupero password). Default: https://$DOMAIN (già nel .env di produzione
# per Caddy); in sviluppo il server Vite.
DOMAIN = os.environ.get("DOMAIN", "").strip()
PUBLIC_BASE_URL = (
    os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
    or (f"https://{DOMAIN}" if DOMAIN else "http://localhost:5173")
)

# Email di servizio (Sprint 67) via SMTP, pensato per Gmail con una password
# per le app. Senza EMAIL_HOST_USER/EMAIL_HOST_PASSWORD l'app funziona lo
# stesso: nessuna email (warning nei log), verifica dell'indirizzo spenta
# (nuovi account già verificati), recupero password non disponibile
# (apps.accounts.emails.email_enabled).
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND") or "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.environ.get("EMAIL_HOST") or "smtp.gmail.com"
EMAIL_PORT = int(os.environ.get("EMAIL_PORT") or 587)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "").strip()
# Google mostra la password per le app in gruppi separati da spazi: gli
# spazi non fanno parte della password.
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "").replace(" ", "").strip()
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "").strip() or EMAIL_HOST_USER or "webmaster@localhost"
EMAIL_TIMEOUT = 20
if TESTING:
    # I test lanciati nel container di produzione leggono il .env reale: mai
    # credenziali SMTP vere (i test dell'invio email le simulano con
    # override_settings).
    EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    EMAIL_HOST_USER = EMAIL_HOST_PASSWORD = ""
# Link di verifica dell'email validi 3 giorni, come quelli di recupero
# password (PASSWORD_RESET_TIMEOUT, default di Django).
EMAIL_VERIFICATION_MAX_AGE = 3 * 24 * 60 * 60
PASSWORD_RESET_TIMEOUT = 3 * 24 * 60 * 60

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.authentication.ExpiringTokenAuthentication",
    ],
    # Il gate delle accettazioni legali (Sprint 67) vale per ogni view che
    # non dichiara `permission_classes`: le poche eccezioni (me, logout,
    # accettazione, export, cancellazione account, cambio password) le
    # dichiarano esplicitamente con il solo IsAuthenticated.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "apps.accounts.permissions.LegalAcceptanceRequired",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ]
    + (["rest_framework.renderers.BrowsableAPIRenderer"] if DEBUG else []),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
        "login": "10/min",
        "login_email": "10/hour",
        "register": "5/hour",
        "cv_import": "10/hour",
        "chat": "20/min",
        "draft_preview": "60/min",
        # Sprint 67: email inviate su richiesta (reinvio verifica, recupero
        # password) per IP e per indirizzo; cambio password e cancellazione
        # account (tentativi di password); export dei dati.
        "email_request": "10/hour",
        "email_address": "3/hour",
        "password_check": "10/hour",
        "data_export": "3/day",
    },
    # Messaggio del 429 tradotto (Sprint 71), il resto come l'handler di DRF.
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    # Caddy è l'unico proxy davanti a Django e sostituisce X-Forwarded-For
    # con l'IP del client: l'identificativo usato dal throttling è quello.
    "NUM_PROXIES": 1,
}

# Log su stdout (Sprint 66): con DEBUG=false Django non scrive gli errori
# da nessuna parte (ADMINS vuoto). Finiscono in `docker logs`, ruotati da
# docker-compose.prod.yml. Mai token, header o query string nei messaggi.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        # Solo gli errori 5xx: i 4xx (404, 401, 429) sono già nell'access log di Caddy.
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "apps": {"handlers": ["console"], "level": "WARNING" if TESTING else "INFO", "propagate": False},
    },
}

# Login via email+password (nativo Django) — nessun username scelto dall'utente
# (02-specifiche-tecniche-v3.md §3.7, §4.1: l'identificativo è l'email).
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_UNIQUE_EMAIL = True

# Credenziali OAuth Google lette da env, mai hardcoded (CLAUDE.md "Config/segreti");
# vuote in dev finché non si caricano credenziali di test in .env (Sprint 03).
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APPS": [
            {
                "client_id": os.environ.get("GOOGLE_OAUTH_CLIENT_ID", ""),
                "secret": os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", ""),
                "key": "",
            }
        ],
        "SCOPE": ["profile", "email"],
    }
}

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# Nei test i task (invio email, Sprint 67) girano in linea, senza Redis.
CELERY_TASK_ALWAYS_EAGER = TESTING
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Pianificazione persistita in DB (gestibile da Django Admin), non nel codice:
# coerente con l'amministrazione via Admin già scelta per piani/credito/voucher
# (02-specifiche-tecniche-v3.md §9) e verificabile senza un deploy.
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Claude via AWS Bedrock — scoring, generazione CV, parsing del CV caricato
# (02-specifiche-tecniche-v3.md §3.5). Non l'API Anthropic diretta: le
# credenziali AWS (AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY) sono lette
# automaticamente da boto3 dall'ambiente, nessuna lettura esplicita qui.
# Modello per lo step di strutturazione del parsing CV configurabile a
# parte: dominio a basso volume, non richiede necessariamente lo stesso
# modello usato per scoring/generazione CV.
# Default UE (Sprint 67, come dichiarato nell'informativa privacy): regione
# di Francoforte e profili di inferenza "eu.", che instradano le richieste
# solo verso regioni AWS dell'Unione Europea.
AWS_BEDROCK_REGION = os.environ.get("AWS_BEDROCK_REGION", "eu-central-1")
BEDROCK_CV_PARSING_MODEL = os.environ.get("BEDROCK_CV_PARSING_MODEL", "eu.anthropic.claude-opus-5")
# Scoring gira ogni notte su tutti i job raccolti di tutti gli utenti (alto
# volume): famiglia di modello più economica di default, come indicato
# esplicitamente da 02-specifiche-tecniche-v3.md §3.5 ("una famiglia più
# economica per lo scoring ad alto volume, una più capace per il CV") — resta
# comunque un parametro di configurazione, non un vincolo architetturale.
BEDROCK_SCORING_MODEL = os.environ.get(
    "BEDROCK_SCORING_MODEL", "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
)
# Generazione contenuti CV: dominio a basso volume (max 15 job/utente/notte
# tenuti dal cap, più le generazioni manuali) rispetto allo scoring — famiglia
# più capace di default, come indicato da 02-specifiche-tecniche-v3.md §3.5.
BEDROCK_CV_GENERATION_MODEL = os.environ.get(
    "BEDROCK_CV_GENERATION_MODEL", "eu.anthropic.claude-opus-5"
)

# Fonte offerte Apify/LinkedIn (02-specifiche-tecniche-v3.md §5.3): token in
# configurazione sicura, mai cablato nell'URL come nel prototipo.
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

# Listino prezzi unitari per le azioni oltre massimale, scalate da
# User.extra_credit (02-specifiche-tecniche-v3.md §4.6, §11: "valori da
# definire" — placeholder di configurazione, da fissare prima del rilascio).
PRICE_MANUAL_CV_EXTRA = Decimal(os.environ.get("PRICE_MANUAL_CV_EXTRA", "1.50"))
PRICE_IMPORT_EXTRA = Decimal(os.environ.get("PRICE_IMPORT_EXTRA", "0.50"))
# Massimale giornaliero separato da quello del CV, stessi tetti Free/Pro
# (Sprint 42): budget indipendente, prezzo a credito configurabile a parte.
PRICE_COVER_LETTER_EXTRA = Decimal(os.environ.get("PRICE_COVER_LETTER_EXTRA", "1.50"))
# Massimale giornaliero separato da quello dell'import LinkedIn, stesso
# valore/prezzo di default ma budget indipendente (Sprint 43).
PRICE_MANUAL_JOB_EXTRA = Decimal(os.environ.get("PRICE_MANUAL_JOB_EXTRA", "0.50"))
# Massimale giornaliero separato da CV/cover letter, stessi tetti Free/Pro
# (Sprint 50): budget indipendente, prezzo a credito configurabile a parte.
PRICE_REFERRAL_MESSAGE_EXTRA = Decimal(os.environ.get("PRICE_REFERRAL_MESSAGE_EXTRA", "1.00"))
# Chat dell'editor CV (Sprint 59): niente massimale giornaliero come le
# altre azioni — ogni messaggio scala sempre il credito extra, come scelto
# dal committente (un turno di chat costa meno di una generazione intera).
PRICE_CV_DRAFT_CHAT_MESSAGE = Decimal(os.environ.get("PRICE_CV_DRAFT_CHAT_MESSAGE", "0.20"))
# Stesso principio di PRICE_CV_DRAFT_CHAT_MESSAGE, budget indipendente
# (Sprint 63): editor/chat della cover letter.
PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE = Decimal(
    os.environ.get("PRICE_COVER_LETTER_DRAFT_CHAT_MESSAGE", "0.20")
)

# Notifiche Web Push (02-specifiche-tecniche-v3.md §3.8): chiavi VAPID per
# l'autenticazione standard del protocollo, nessun servizio a pagamento.
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@example.com")

# Backup giornaliero del database su storage a oggetti esterno al VPS
# (02-specifiche-tecniche-v3.md §8.4): compatibile con qualunque provider che
# parli l'API S3 (es. Hetzner Object Storage, Backblaze B2), nessun servizio
# proprietario. Backup saltato (con warning nei log) se il bucket non è
# configurato, per non far fallire il ciclo Celery Beat in dev.
BACKUP_S3_ENDPOINT_URL = os.environ.get("BACKUP_S3_ENDPOINT_URL", "")
BACKUP_S3_BUCKET = os.environ.get("BACKUP_S3_BUCKET", "")
BACKUP_S3_ACCESS_KEY = os.environ.get("BACKUP_S3_ACCESS_KEY", "")
BACKUP_S3_SECRET_KEY = os.environ.get("BACKUP_S3_SECRET_KEY", "")
BACKUP_S3_REGION = os.environ.get("BACKUP_S3_REGION", "auto")
# Backup locale ruotato (Sprint 67), usato quando il bucket S3 non è
# configurato: dump del DB + archivio media nel volume `local_backups`,
# conservati BACKUP_LOCAL_KEEP_DAYS giorni (come dichiarato nell'informativa).
BACKUP_LOCAL_DIR = Path(os.environ.get("BACKUP_LOCAL_DIR") or BASE_DIR / "backups")
BACKUP_LOCAL_KEEP_DAYS = 7
