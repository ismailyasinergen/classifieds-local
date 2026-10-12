import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "django.contrib.sites", "django.contrib.postgres", "allauth", "allauth.account",
    "allauth.mfa", "accounts", "catalog", "listings", "media", "moderation", "events", "conversations", "notifications", "promotions",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "accounts.mfa_middleware.MFABoundaryMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
        "notifications.context_processors.unread_notifications",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ["POSTGRES_DB"], "USER": os.environ["POSTGRES_USER"],
    "PASSWORD": os.environ["POSTGRES_PASSWORD"],
    "HOST": os.environ.get("POSTGRES_HOST", "db"), "PORT": os.environ.get("POSTGRES_PORT", "5432"),
}}
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SITE_ID = 1
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
ACCOUNT_UNIQUE_EMAIL = True
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Classifieds Local <noreply@localhost>"
LOGIN_REDIRECT_URL = "/"
ACCOUNT_LOGOUT_REDIRECT_URL = "/"
LANGUAGE_CODE = "tr"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = Path("/var/lib/classifieds/static")
PRIVATE_MEDIA_ROOT = Path("/var/lib/classifieds/media")
MEDIA_MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MEDIA_MAX_PIXELS = 20_000_000
MEDIA_MAX_IMAGES_PER_REVISION = 10


def _pilot_capacity(name, default):
    # Preserve malformed input for named, nonsensitive startup/runtime validation.
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return value


PILOT_NEW_CONTACTS_PER_HOUR = _pilot_capacity("PILOT_NEW_CONTACTS_PER_HOUR", 10)
PILOT_MESSAGES_PER_HOUR = _pilot_capacity("PILOT_MESSAGES_PER_HOUR", 120)
PILOT_NEW_LISTINGS_PER_DAY = _pilot_capacity("PILOT_NEW_LISTINGS_PER_DAY", 10)
PILOT_REPORTS_PER_DAY = _pilot_capacity("PILOT_REPORTS_PER_DAY", 20)
PILOT_APPEALS_PER_DAY = _pilot_capacity("PILOT_APPEALS_PER_DAY", 10)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_TASK_IGNORE_RESULT = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_PUBLISH_RETRY = False
CELERY_BROKER_CONNECTION_TIMEOUT = 3
CELERY_BEAT_SCHEDULE = {
    "rescue-pending-images": {"task": "media.tasks.rescue_pending_images", "schedule": 60.0},
}
IN_APP_NOTIFICATIONS_ENABLED = os.environ.get('IN_APP_NOTIFICATIONS_ENABLED', '0') == '1'
if IN_APP_NOTIFICATIONS_ENABLED:
    CELERY_BEAT_SCHEDULE['consume-in-app-notifications'] = {
        'task': 'notifications.tasks.consume_in_app_notifications', 'schedule': 30.0,
    }

# Shared auth rate limits and atomic TOTP replay keys. Celery remains on DB 0.
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.redis.RedisCache",
    "LOCATION": "redis://redis:6379/1",
    "KEY_PREFIX": "classifieds-auth",
    "OPTIONS": {"socket_connect_timeout": 2, "socket_timeout": 2},
}}
TEST_RUNNER = "config.test_runner.IsolatedSecurityTestRunner"
LOGIN_URL = "account_login"
MFA_ADAPTER = "accounts.mfa_adapter.ClassifiedsMFAAdapter"
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]
MFA_ALLOW_UNVERIFIED_EMAIL = False
MFA_TRUST_ENABLED = False
MFA_PASSKEY_LOGIN_ENABLED = False
MFA_PASSKEY_SIGNUP_ENABLED = False
MFA_RECOVERY_CODE_COUNT = 10
MFA_RECOVERY_CODE_DIGITS = 8
MFA_RECOVERY_CODES_SHOW_ONCE = True
MFA_TOTP_PERIOD = 30
MFA_TOTP_DIGITS = 6
MFA_TOTP_TOLERANCE = 0
MFA_TOTP_ISSUER = "Classifieds Local"

PROMOTIONS_DEMO_ENABLED = os.environ.get('PROMOTIONS_DEMO_ENABLED', '0') == '1'
DEPLOYMENT_ENVIRONMENT = os.environ.get('DEPLOYMENT_ENVIRONMENT', '')
