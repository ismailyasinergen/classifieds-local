from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.locking import lock_users
from accounts.rate_limits import enforce_action_limit
from listings.models import Listing
from listings.policies import require_active_actor, require_owner
from .models import Conversation, Message, Participant, UserBlock
from .policies import require_can_reply, require_can_start, require_participant


def _actor_id(actor):
    # Only input identity/shape is checked here. Authority is rechecked after locks.
    if (not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False)
            or not getattr(actor, "pk", None)):
        raise PermissionDenied("Etkin bir hesapla giriş yapın.")
    return actor.pk


def _message_input(*, body, client_token):
    if not isinstance(body, str) or len(body) > 8000:
        raise ValidationError({"body": "Geçerli, en çok 4000 karakterlik mesaj girin."})
    try:
        body.encode("utf-8", errors="strict")
    except UnicodeError:
        raise ValidationError({"body": "Geçerli Unicode metni girin."})
    body = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not body or "\x00" in body or len(body) > 4000:
        raise ValidationError({"body": "Boş olmayan, en çok 4000 karakterlik mesaj girin."})
    try:
        if not isinstance(client_token, (UUID, str)):
            raise ValueError
        token = client_token if isinstance(client_token, UUID) else UUID(client_token)
    except (ValueError, AttributeError):
        raise ValidationError({"client_token": "Geçerli bir gönderim kimliği girin."})
    return body, token


def _replay(*, conversation, actor_id, body, token):
    message = Message.objects.filter(
        conversation=conversation, sender_id=actor_id, client_token=token).first()
    if message is not None and message.body != body:
        raise ValidationError("Bu gönderim kimliği farklı bir mesaj için kullanılmış.", code="token_conflict")
    return message


def _lock_conversation(*, actor, conversation_id):
    actor_id = _actor_id(actor)
    identities = Conversation.objects.values_list("initiator_id", "recipient_id").get(pk=conversation_id)
    users = lock_users(user_ids=[actor_id, *identities])
    conversation = Conversation.objects.select_for_update().get(pk=conversation_id)
    if (conversation.initiator_id, conversation.recipient_id) != identities:
        raise ValidationError("Görüşmenin tarafları değişti.", code="identity_changed")
    require_participant(actor=actor, conversation=conversation)
    return conversation, users[actor_id]


def _lock_participants(conversation):
    return {
        row.user_id: row for row in Participant.objects.select_for_update()
        .filter(conversation=conversation).order_by("pk")
    }


def _append_message(*, conversation, actor, body, token, participants, at):
    enforce_action_limit(events=Message.objects.filter(sender=actor), action="message", at=at)
    sequence = conversation.last_sequence + 1
    message = Message.objects.create(
        conversation=conversation, sender=actor, sequence=sequence,
        body=body, client_token=token, created_at=at)
    conversation.last_sequence = sequence
    conversation.last_message_at = at
    conversation.save(update_fields=["last_sequence", "last_message_at"])
    other_id = (conversation.recipient_id if actor.pk == conversation.initiator_id
                else conversation.initiator_id)
    recipient_state = participants[other_id]
    if recipient_state.archived_at is not None:
        recipient_state.archived_at = None
        recipient_state.save(update_fields=["archived_at"])
    # Own sends do not move the read watermark or alter the sender's archive.
    return message


def start_conversation(*, actor, listing_id, body, client_token):
    actor_id = _actor_id(actor)
    body, token = _message_input(body=body, client_token=client_token)
    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(pk=listing_id)
        users = lock_users(user_ids=[actor_id, listing.owner_id])
        require_active_actor(actor=actor)
        conversation = Conversation.objects.select_for_update().filter(
            listing=listing, initiator_id=actor_id).first()
        if conversation is not None:
            if conversation.recipient_id != listing.owner_id:
                raise ValidationError("İlanın sahibi değişti.", code="identity_changed")
            require_participant(actor=actor, conversation=conversation)
            replay = _replay(conversation=conversation, actor_id=actor_id, body=body, token=token)
            if replay is not None:
                return replay
            participants = _lock_participants(conversation)
            now = timezone.now()
            require_can_reply(actor=users[actor_id], conversation=conversation, at=now)
        else:
            now = timezone.now()
            require_can_start(actor=users[actor_id], listing=listing, at=now)
            enforce_action_limit(events=Conversation.objects.filter(initiator_id=actor_id),
                                 action="new_contact", at=now)
            conversation = Conversation.objects.create(
                listing=listing, initiator=users[actor_id], recipient=users[listing.owner_id],
                subject=listing.public_revision.title[:200], last_message_at=now)
            Participant.objects.bulk_create([
                Participant(conversation=conversation, user_id=user_id)
                for user_id in sorted([actor_id, listing.owner_id])
            ])
            participants = _lock_participants(conversation)
        return _append_message(conversation=conversation, actor=users[actor_id],
                               body=body, token=token, participants=participants, at=now)


def send_message(*, actor, conversation_id, body, client_token):
    _actor_id(actor)
    body, token = _message_input(body=body, client_token=client_token)
    with transaction.atomic():
        conversation, current = _lock_conversation(actor=actor, conversation_id=conversation_id)
        replay = _replay(conversation=conversation, actor_id=current.pk, body=body, token=token)
        if replay is not None:
            return replay
        participants = _lock_participants(conversation)
        now = timezone.now()
        require_can_reply(actor=current, conversation=conversation, at=now)
        return _append_message(conversation=conversation, actor=current,
                               body=body, token=token, participants=participants, at=now)


def mark_read(*, actor, conversation_id, through_message_id):
    with transaction.atomic():
        conversation, current = _lock_conversation(actor=actor, conversation_id=conversation_id)
        participants = _lock_participants(conversation)
        if type(through_message_id) is not int or through_message_id < 1:
            raise ValidationError({"through_message_id": "Görüntülenen bir mesaj seçin."})
        message = Message.objects.filter(pk=through_message_id, conversation=conversation).first()
        if message is None:
            raise ValidationError({"through_message_id": "Bu görüşmedeki bir mesaj seçin."})
        participant = participants[current.pk]
        if message.sequence > participant.last_read_sequence:
            participant.last_read_sequence = message.sequence
            participant.save(update_fields=["last_read_sequence"])
        return participant


def set_archived(*, actor, conversation_id, archived):
    if type(archived) is not bool:
        raise ValidationError({"archived": "Geçerli bir arşiv tercihi girin."})
    with transaction.atomic():
        conversation, current = _lock_conversation(actor=actor, conversation_id=conversation_id)
        participant = _lock_participants(conversation)[current.pk]
        if archived and participant.archived_at is None:
            participant.archived_at = timezone.now()
            participant.save(update_fields=["archived_at"])
        elif not archived and participant.archived_at is not None:
            participant.archived_at = None
            participant.save(update_fields=["archived_at"])
        return participant


def block_user(*, actor, other_user_id):
    actor_id = _actor_id(actor)
    if actor_id == other_user_id:
        raise ValidationError({"other_user_id": "Kendinizi engelleyemezsiniz."})
    with transaction.atomic():
        users = lock_users(user_ids=[actor_id, other_user_id])
        require_active_actor(actor=actor)
        block, _ = UserBlock.objects.get_or_create(blocker=users[actor_id], blocked=users[other_user_id])
        return block


def unblock_user(*, actor, other_user_id):
    actor_id = _actor_id(actor)
    if actor_id == other_user_id:
        raise ValidationError({"other_user_id": "Kendinizi engelleyemezsiniz."})
    with transaction.atomic():
        lock_users(user_ids=[actor_id, other_user_id])
        require_active_actor(actor=actor)
        UserBlock.objects.filter(blocker_id=actor_id, blocked_id=other_user_id).delete()


def set_contact_enabled(*, actor, listing_id, enabled):
    actor_id = _actor_id(actor)
    if type(enabled) is not bool:
        raise ValidationError({"enabled": "Geçerli bir iletişim tercihi girin."})
    with transaction.atomic():
        listing = Listing.objects.select_for_update().get(pk=listing_id)
        users = lock_users(user_ids=[actor_id, listing.owner_id])
        require_active_actor(actor=actor)
        require_owner(actor=users[actor_id], listing=listing)
        if listing.contact_enabled != enabled:
            listing.contact_enabled = enabled
            listing.save(update_fields=["contact_enabled"])
        return listing
