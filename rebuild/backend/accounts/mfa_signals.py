"""Privacy-limited allauth post-commit audit and verified success handling."""
from allauth.mfa import signals
from allauth.mfa.models import Authenticator
from django.dispatch import receiver

from .mfa_policy import PROOF_SESSION_KEY, establish_mfa_proof
from .models import SecurityEvent


def _event(user, action, authenticator):
    SecurityEvent.objects.create(actor_id=user.pk, action=action, method=authenticator.type)


@receiver(signals.authenticator_used, dispatch_uid="classifieds.mfa.used")
def authenticator_used(sender, request, user, authenticator, **kwargs):
    establish_mfa_proof(request, user=user, authenticator=authenticator)
    _event(user, "used", authenticator)


@receiver(signals.authenticator_added, dispatch_uid="classifieds.mfa.added")
def authenticator_added(sender, request, user, authenticator, **kwargs):
    if (authenticator.type == Authenticator.Type.TOTP and request
            and request.user.is_authenticated and request.user.pk == user.pk):
        establish_mfa_proof(request, user=user, authenticator=authenticator)
    _event(user, "activated", authenticator)


@receiver(signals.authentication_failed, dispatch_uid="classifieds.mfa.failed")
def authentication_failed(sender, request, user, authenticator, **kwargs):
    _event(user, "failed", authenticator)


@receiver(signals.authenticator_removed, dispatch_uid="classifieds.mfa.removed")
def authenticator_removed(sender, request, user, authenticator, **kwargs):
    if authenticator.type == Authenticator.Type.TOTP and request:
        request.session.pop(PROOF_SESSION_KEY, None)
    _event(user, "removed", authenticator)


@receiver(signals.authenticator_reset, dispatch_uid="classifieds.mfa.reset")
def authenticator_reset(sender, request, user, authenticator, **kwargs):
    _event(user, "recovery_regenerated", authenticator)
