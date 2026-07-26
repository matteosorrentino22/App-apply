import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
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

# Europe/Rome governa il batch notturno e il reset delle quote giornaliere
# (02-specifiche-tecniche-v3.md §7): fuso di sistema unico per Django/Celery Beat.
LANGUAGE_CODE = "it-it"
TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Foto profilo e PDF dei CV generati (apps.profiles.Profile.photo, apps.cv.CVDocument.pdf_file).
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
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
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
# Pianificazione persistita in DB (gestibile da Django Admin), non nel codice:
# coerente con l'amministrazione via Admin già scelta per piani/credito/voucher
# (02-specifiche-tecniche-v3.md §9) e verificabile senza un deploy.
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# API Anthropic (Claude) — scoring, generazione CV, parsing del CV caricato
# (02-specifiche-tecniche-v3.md §3.5). Modello per lo step di strutturazione
# del parsing CV configurabile a parte: dominio a basso volume, non richiede
# necessariamente lo stesso modello usato per scoring/generazione CV.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_CV_PARSING_MODEL = os.environ.get("ANTHROPIC_CV_PARSING_MODEL", "claude-opus-5")
# Scoring gira ogni notte su tutti i job raccolti di tutti gli utenti (alto
# volume): famiglia di modello più economica di default, come indicato
# esplicitamente da 02-specifiche-tecniche-v3.md §3.5 ("una famiglia più
# economica per lo scoring ad alto volume, una più capace per il CV") — resta
# comunque un parametro di configurazione, non un vincolo architetturale.
ANTHROPIC_SCORING_MODEL = os.environ.get("ANTHROPIC_SCORING_MODEL", "claude-haiku-4-5")
# Generazione contenuti CV: dominio a basso volume (max 15 job/utente/notte
# tenuti dal cap, più le generazioni manuali) rispetto allo scoring — famiglia
# più capace di default, come indicato da 02-specifiche-tecniche-v3.md §3.5.
ANTHROPIC_CV_GENERATION_MODEL = os.environ.get("ANTHROPIC_CV_GENERATION_MODEL", "claude-opus-5")

# Fonte offerte Apify/LinkedIn (02-specifiche-tecniche-v3.md §5.3): token in
# configurazione sicura, mai cablato nell'URL come nel prototipo.
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

# Listino prezzi unitari per le azioni oltre massimale, scalate da
# User.extra_credit (02-specifiche-tecniche-v3.md §4.6, §11: "valori da
# definire" — placeholder di configurazione, da fissare prima del rilascio).
PRICE_MANUAL_CV_EXTRA = Decimal(os.environ.get("PRICE_MANUAL_CV_EXTRA", "1.50"))
