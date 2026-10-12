"""Current database role state and signal-issued, primary-bound browser proof."""
import math
import time

from allauth.account.models import EmailAddress
from allauth.mfa.models import Authenticator
from django.db.models import Q

from .models import User

PROOF_SESSION_KEY = "classifieds_mfa_proof"
PROOF_MAX_AGE = 28800
RECENT_MFA_MAX_AGE = 300


def requires_mfa(user):
    if not getattr(user, "is_authenticated", False) or not user.pk:
        return False
    current = User.objects.filter(pk=user.pk, is_active=True).first()
    if current is None:
        return False
    return current.is_staff or current.is_superuser or User.objects.filter(
        pk=current.pk,
    ).filter(
        Q(user_permissions__content_type__app_label="listings",
          user_permissions__codename="review_listingrevision")
        | Q(groups__permissions__content_type__app_label="listings",
            groups__permissions__codename="review_listingrevision")
        | Q(user_permissions__content_type__app_label="moderation",
            user_permissions__codename__in=["review_reports", "review_appeals"])
        | Q(groups__permissions__content_type__app_label="moderation",
            groups__permissions__codename__in=["review_reports", "review_appeals"]),
    ).exists()


def primary_factor(user):
    if not getattr(user, "is_authenticated", False):
        return None
    return Authenticator.objects.filter(user_id=user.pk, type=Authenticator.Type.TOTP).first()


def verified_current_email(user):
    current = User.objects.filter(pk=user.pk, is_active=True).first()
    return bool(current and EmailAddress.objects.filter(
        user_id=current.pk, email__iexact=current.email, verified=True,
    ).exists())


def has_mfa_proof(request, *, max_age=PROOF_MAX_AGE):
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return False
    proof = request.session.get(PROOF_SESSION_KEY)
    if not isinstance(proof, dict) or set(proof) != {"user_id", "primary_id", "method", "verified_at"}:
        return False
    if type(proof["user_id"]) is not int or type(proof["primary_id"]) is not int:
        return False
    if (proof["user_id"] != user.pk or type(proof["method"]) is not str
            or proof["method"] not in {"totp", "recovery_codes"}):
        return False
    verified_at = proof["verified_at"]
    if type(verified_at) not in {float, int} or not math.isfinite(verified_at):
        return False
    age = time.time() - verified_at
    if age < 0 or age >= max_age:
        return False
    primary = primary_factor(user)
    return bool(primary and primary.pk == proof["primary_id"]
                and User.objects.filter(pk=user.pk, is_active=True).exists())


def establish_mfa_proof(request, *, user, authenticator):
    """Only the real allauth success signal handlers call this function.

    During the anonymous login stage request.user is not signed in yet. The
    allauth signal supplies the verified owner; the marker is unusable until
    the same owner completes login.
    """
    if request is None or authenticator.type not in {
        Authenticator.Type.TOTP, Authenticator.Type.RECOVERY_CODES,
    }:
        return
    if getattr(request.user, "is_authenticated", False) and request.user.pk != user.pk:
        return
    if authenticator.user_id != user.pk or not Authenticator.objects.filter(
        pk=authenticator.pk, user_id=user.pk, type=authenticator.type,
    ).exists():
        return
    primary = primary_factor(user)
    if primary is None or not User.objects.filter(pk=user.pk, is_active=True).exists():
        return
    request.session[PROOF_SESSION_KEY] = {
        "user_id": user.pk, "primary_id": primary.pk,
        "method": authenticator.type, "verified_at": time.time(),
    }
