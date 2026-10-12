"""Synthetic fixtures; obtain proof only through stock HTTP verification."""
import time

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, format_hotp_value, generate_totp_secret, hotp_value
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

PASSWORD = "Synthetic-MFA-test-password-57"


def totp_code(secret):
    return format_hotp_value(hotp_value(secret, int(time.time()) // 30))


def add_factors(user):
    primary = Authenticator.objects.filter(user=user, type=Authenticator.Type.TOTP).first()
    if primary is None:
        primary = TOTP.activate(user, generate_totp_secret()).instance
    RecoveryCodes.activate(user)
    return primary


def authenticate_client(client, user):
    """Acceptance-test setup: verified fixture, then real recovery reauthentication.

    Recovery validation uses the stock PostgreSQL single-use lock and emits
    authenticator_used. No application proof is fabricated.
    """
    EmailAddress.objects.get_or_create(user=user, email=user.email,
                                      defaults={"verified": True, "primary": True})
    add_factors(user)
    client.force_login(user)
    recovery = Authenticator.objects.get(user=user, type=Authenticator.Type.RECOVERY_CODES).wrap()
    codes = recovery.get_unused_codes()
    if not codes:
        raise AssertionError("Synthetic MFA fixture exhausted recovery codes.")
    response = client.post(reverse("mfa_reauthenticate"),
                           {"code": codes[0], "next": reverse("accounts:security")})
    if response.status_code != 302:
        raise AssertionError("Real synthetic MFA verification did not finish.")


class MFATestIsolationMixin:
    def setUp(self):
        super().setUp()
        # The default runner already overrides CACHES. Defend direct/custom
        # runner invocations too, before any clear operation.
        self.cache_settings = override_settings(CACHES={"default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": f"mfa-test-{self.id()}",
        }}, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
        self.cache_settings.enable()
        self.addCleanup(self.cache_settings.disable)
        cache.clear()
