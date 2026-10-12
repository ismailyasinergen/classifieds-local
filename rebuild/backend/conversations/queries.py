from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Q, Subquery
from django.db.models.functions import Substr

from listings.models import Listing
from listings.policies import require_active_actor
from .models import Conversation, Message, Participant
from .policies import require_can_start


def _canonical(actor):
    return Q(initiator_id=actor.pk) | Q(recipient_id=actor.pk)


def inbox_conversations(*, actor, archived=False):
    require_active_actor(actor=actor)
    states = Participant.objects.filter(conversation_id=OuterRef("pk"), user_id=actor.pk)
    latest = Message.objects.filter(conversation_id=OuterRef("pk")).order_by("-sequence")
    incoming = Message.objects.filter(
        conversation_id=OuterRef("pk"),
        sequence__gt=OuterRef("viewer_last_read_sequence")).exclude(sender_id=actor.pk)
    rows = Conversation.objects.filter(_canonical(actor)).select_related("listing").annotate(
        viewer_last_read_sequence=Subquery(states.values("last_read_sequence")[:1]),
        viewer_archived_at=Subquery(states.values("archived_at")[:1]),
        last_message_preview=Subquery(latest.annotate(preview=Substr("body", 1, 160)).values("preview")[:1]),
        has_unread=Exists(incoming),
    ).filter(viewer_last_read_sequence__isnull=False)
    return rows.filter(viewer_archived_at__isnull=not archived).order_by("-last_message_at", "-pk")


def conversation_for_actor(*, actor, conversation_id):
    require_active_actor(actor=actor)
    return Conversation.objects.filter(_canonical(actor)).select_related("listing").get(pk=conversation_id)


def conversation_messages(*, actor, conversation_id):
    conversation = conversation_for_actor(actor=actor, conversation_id=conversation_id)
    return Message.objects.filter(conversation=conversation).order_by("-sequence")


def start_context(*, actor, listing_id):
    require_active_actor(actor=actor)
    listing = Listing.objects.get(pk=listing_id)
    conversation = Conversation.objects.filter(listing=listing, initiator_id=actor.pk).first()
    if conversation is not None:
        if conversation.recipient_id != listing.owner_id:
            raise ValidationError("İlanın sahibi değişti.", code="identity_changed")
        return listing, conversation
    require_can_start(actor=actor, listing=listing)
    return listing, None
