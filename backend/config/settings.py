from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "dev-only-secret-key-change-later",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "web"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "accounts.apps.AccountsConfig",
    "categories",
    "listings",
    "pages",
    "conversations.apps.ConversationsConfig",
    "promotions.apps.PromotionsConfig",
]

MIDDLEWARE = [
    "accounts.middleware.CustomMethodNotAllowedMiddleware",

    "accounts.middleware.SensitiveMediaBlockMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "config.csp_nonce_v332.CspNonceMiddlewareV332",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.SellerRestrictionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "config.context_processors.csp_nonce_v332",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "accounts.context_processors.seller_restriction_status",
                "accounts.context_processors.unread_moderation_notice_count",
                "categories.context_processors.sidebar_categories",
                "listings.context_processors.favorite_listing_ids",
                "conversations.context_processors.unread_message_count",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DB_NAME", "classifieds_db"),
        "USER": os.environ.get("DB_USER", "postgres"),
        "PASSWORD": os.environ.get("DB_PASSWORD", "postgres"),
        "HOST": os.environ.get("DB_HOST", "localhost"),
        "PORT": os.environ.get("DB_PORT", "5432"),
    }
}

# V303: refresh preserved PostgreSQL parallel test clones from the migrated
# base test database. Application and serial test database behavior is unchanged.
TEST_RUNNER = "config.test_runner.MigrationAwareParallelDiscoverRunner"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "listings:listing_list"
LOGOUT_REDIRECT_URL = "listings:listing_list"

CSRF_TRUSTED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
]


# Allow appeal uploads. Each file is validated separately at 40 MB in the view.
DATA_UPLOAD_MAX_MEMORY_SIZE = 230 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# PRODUCTION_READY_SETTINGS_V1
# Environment-driven production overrides.
#
# Local development remains easy:
#   DJANGO_DEBUG defaults to True
#
# Production should set:
#   DJANGO_DEBUG=0
#   DJANGO_SECRET_KEY=<long random secret>
#   DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
#   DJANGO_CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com

import os


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default=0):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_list(name, default=None):
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default or []
    return [item.strip() for item in value.split(",") if item.strip()]


DEBUG = _env_bool("DJANGO_DEBUG", DEBUG)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", SECRET_KEY)

ALLOWED_HOSTS = _env_list(
    "DJANGO_ALLOWED_HOSTS",
    ALLOWED_HOSTS if ALLOWED_HOSTS else ["localhost", "127.0.0.1"],
)

CSRF_TRUSTED_ORIGINS = _env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    globals().get("CSRF_TRUSTED_ORIGINS", []),
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
SESSION_COOKIE_SECURE = _env_bool("DJANGO_SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("DJANGO_CSRF_COOKIE_SECURE", not DEBUG)

SECURE_HSTS_SECONDS = _env_int("DJANGO_SECURE_HSTS_SECONDS", 0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG)
SECURE_HSTS_PRELOAD = _env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_REFERRER_POLICY = "same-origin"

DATA_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE", 230 * 1024 * 1024)
)
FILE_UPLOAD_MAX_MEMORY_SIZE = int(
    os.getenv("DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE", 10 * 1024 * 1024)
)

DEFAULT_AUTO_FIELD = globals().get("DEFAULT_AUTO_FIELD", "django.db.models.BigAutoField")

LOG_LEVEL = os.getenv("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{levelname}] {asctime} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# LOCAL_DEMO_EMAIL_OR_USERNAME_LOGIN_V1
AUTHENTICATION_BACKENDS = [
    "accounts.auth_backends.EmailOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# V242 saved-search notification production-delivery feature gate.
V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION = (
    "V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION"
)


def _saved_search_production_delivery_env_bool_v242(
    name,
    *,
    default=False,
):
    import os as _v242_os

    raw_value = _v242_os.environ.get(name)

    if raw_value is None:
        return bool(default)

    return raw_value.strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED = (
    _saved_search_production_delivery_env_bool_v242(
        "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED",
        default=False,
    )
)

# V305 operator-facing notification recipient-output policy.
# Delivery internals retain the actual destination address, while command,
# preview, observability and rollback output redact it by default.
NOTIFICATION_OPERATOR_RECIPIENT_OUTPUT_POLICY = (
    "redacted_by_default"
)

# V306 verified-recipient lifecycle foundation.
# V309 runtime enforcement remains default-off and must fail closed
# when explicitly enabled without a current verified address.
NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED = _env_bool(
    "NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED",
    default=False,
)
EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS = _env_int(
    "EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS",
    86400,
)

EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = _env_int(
    "EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS",
    300,
)

# V307 provider-neutral notification outcome webhook.
V307_NOTIFICATION_PROVIDER_OUTCOME_SETTINGS = True

NOTIFICATION_PROVIDER_NAME = os.getenv(
    "NOTIFICATION_PROVIDER_NAME",
    "",
).strip().casefold()

NOTIFICATION_PROVIDER_WEBHOOK_SECRET = os.getenv(
    "NOTIFICATION_PROVIDER_WEBHOOK_SECRET",
    "",
).strip()

NOTIFICATION_PROVIDER_WEBHOOK_MAX_AGE_SECONDS = _env_int(
    "NOTIFICATION_PROVIDER_WEBHOOK_MAX_AGE_SECONDS",
    300,
)


# V308 notification-delivery-event retention foundation.
# Cleanup defaults to read-only dry-run. Destructive tombstoning additionally
# requires an explicit command confirmation and this default-off feature gate.
def _notification_retention_env_bool_v308(
    name,
    default=False,
):
    raw_value = os.getenv(name)

    if raw_value is None or raw_value == "":
        return bool(default)

    return raw_value.strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


NOTIFICATION_DELIVERY_EVENT_RETENTION_DAYS = _env_int(
    "NOTIFICATION_DELIVERY_EVENT_RETENTION_DAYS",
    90,
)

NOTIFICATION_DELIVERY_RETENTION_BACKUP_POLICY = (
    os.getenv(
        "NOTIFICATION_DELIVERY_RETENTION_BACKUP_POLICY",
        "restore_requires_recleanup",
    )
    .strip()
    .casefold()
)

NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED = (
    _notification_retention_env_bool_v308(
        "NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED",
        default=False,
    )
)

NOTIFICATION_DELIVERY_RETENTION_DEFAULT_LIMIT = _env_int(
    "NOTIFICATION_DELIVERY_RETENTION_DEFAULT_LIMIT",
    100,
)
