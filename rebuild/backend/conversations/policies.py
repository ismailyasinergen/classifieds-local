from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from listings.policies import require_active_actor
from moderation.messaging import messaging_restrictions
from moderation.policies import visible_listings
from .models import UserBlock


def require_participant(*, actor, conversation):
    require_active_actor(actor=actor)
    if actor.pk not in (conversation.initiator_id, conversation.recipient_id):
        raise PermissionDenied("Bu görüşmeye erişim yetkiniz yok.")


def _require_accounts_can_message(*, first_id, second_id, at):
    if User.objects.filter(pk__in=[first_id, second_id], is_active=True).count() != 2:
        raise PermissionDenied("Bu görüşmede şu anda mesaj gönderilemiyor.")
    if messaging_restrictions(at=at).filter(user_id__in=[first_id, second_id]).exists():
        raise PermissionDenied("Bu görüşmede şu anda mesaj gönderilemiyor.")
    if UserBlock.objects.filter(
            Q(blocker_id=first_id, blocked_id=second_id) |
            Q(blocker_id=second_id, blocked_id=first_id)).exists():
        raise PermissionDenied("Bu görüşmede şu anda mesaj gönderilemiyor.")


def require_can_start(*, actor, listing, at=None):
    require_active_actor(actor=actor)
    at = timezone.now() if at is None else at
    if actor.pk == listing.owner_id:
        raise PermissionDenied("Kendi ilanınıza görüşme başlatamazsınız.")
    if not listing.contact_enabled or not visible_listings(at=at).filter(pk=listing.pk).exists():
        raise PermissionDenied("Bu ilan için yeni görüşme başlatılamıyor.")
    _require_accounts_can_message(first_id=actor.pk, second_id=listing.owner_id, at=at)


def require_can_reply(*, actor, conversation, at=None):
    require_participant(actor=actor, conversation=conversation)
    at = timezone.now() if at is None else at
    _require_accounts_can_message(
        first_id=conversation.initiator_id, second_id=conversation.recipient_id, at=at)


def can_reply(*, actor, conversation):
    """Advisory UI check; mutation services repeat the policy under account locks."""
    try:
        require_can_reply(actor=actor, conversation=conversation)
    except PermissionDenied:
        return False
    return True
