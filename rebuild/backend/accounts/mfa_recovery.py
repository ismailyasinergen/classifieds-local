"""Coordinate pinned allauth recovery display writes with code consumption.

allauth 65.19.7 consumes a code under an Authenticator row lock, but its
first-display writer saves an unlocked, potentially stale JSON data value.
Keep generation/validation/presentation in allauth and lock before its read.
"""
from functools import wraps

from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes import views as recovery_views
from django.db import transaction

from .mfa_middleware import remediation
from .mfa_policy import RECENT_MFA_MAX_AGE, has_mfa_proof, primary_factor, verified_current_email
from .models import User


def serialize_recovery_display(view):
    @wraps(view)
    def protected(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view(request, *args, **kwargs)
        with transaction.atomic():
            # Match regeneration's User -> Authenticator order. NO KEY UPDATE
            # permits FK checks from audit/other account-owned row inserts.
            User.objects.select_for_update(no_key=True).only("pk").get(pk=request.user.pk)
            list(Authenticator.objects.select_for_update().filter(
                user_id=request.user.pk, type=Authenticator.Type.RECOVERY_CODES,
            ).values_list("pk", flat=True))
            # A concurrent replacement or a long lock wait must not let a stale
            # pre-view middleware proof authorize the newly current factor set.
            if not verified_current_email(request.user):
                return remediation(request, "accounts:verify_email")
            if not primary_factor(request.user):
                return remediation(request, "mfa_activate_totp")
            if not has_mfa_proof(request, max_age=RECENT_MFA_MAX_AGE):
                return remediation(request, "mfa_reauthenticate")
            # Allauth now reads current JSON under the same row lock used by
            # validate_code(); a later viewed_at save cannot restore used_mask.
            return view(request, *args, **kwargs)
    return protected


view_recovery_codes = serialize_recovery_display(recovery_views.view_recovery_codes)
download_recovery_codes = serialize_recovery_display(recovery_views.download_recovery_codes)
