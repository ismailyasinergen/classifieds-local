"""Authenticated MFA encryption; the existing Django key remains private."""
import base64

from allauth.core import context
from allauth.mfa.adapter import DefaultMFAAdapter
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

from .mfa_policy import RECENT_MFA_MAX_AGE, has_mfa_proof

CIPHERTEXT_PREFIX = "classifieds-mfa:v1:"


class MFAStorageError(Exception):
    """Generic storage failure; never attach encrypted or plaintext input."""


def _cipher(secret_key):
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None,
               info=b"classifieds/mfa-at-rest/v1").derive(secret_key.encode("utf-8"))
    return Fernet(base64.urlsafe_b64encode(key))


class ClassifiedsMFAAdapter(DefaultMFAAdapter):
    error_messages = {
        **DefaultMFAAdapter.error_messages,
        "incorrect_code": "Doğrulama başarısız. Kodu kontrol edip tekrar deneyin.",
        "unverified_email": "Önce hesabınızın güncel e-posta adresini doğrulayın.",
        "cannot_delete_authenticator": "Cihaz değişimi için önce iki adımlı doğrulama yapın.",
        "cannot_generate_recovery_codes": "Önce iki adımlı doğrulamayı etkinleştirin.",
    }

    def encrypt(self, text):
        return CIPHERTEXT_PREFIX + _cipher(settings.SECRET_KEY).encrypt(text.encode("utf-8")).decode("ascii")

    def decrypt(self, encrypted_text):
        if not isinstance(encrypted_text, str) or not encrypted_text.startswith(CIPHERTEXT_PREFIX):
            raise MFAStorageError("Doğrulama şu anda kullanılamıyor.")
        token = encrypted_text[len(CIPHERTEXT_PREFIX):]
        for key in [settings.SECRET_KEY, *settings.SECRET_KEY_FALLBACKS]:
            try:
                return _cipher(key).decrypt(token.encode("ascii")).decode("utf-8")
            except (InvalidToken, UnicodeError, ValueError):
                continue
        raise MFAStorageError("Doğrulama şu anda kullanılamıyor.")

    def can_delete_authenticator(self, authenticator):
        request = context.request
        return bool(request and request.user.is_authenticated
                    and request.user.pk == authenticator.user_id
                    and has_mfa_proof(request, max_age=RECENT_MFA_MAX_AGE))
