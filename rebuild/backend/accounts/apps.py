from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        from . import rate_limits  # Register named pilot capacity system checks.
        from . import mfa_signals  # Only real allauth verified signals issue proof.
