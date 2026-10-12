import uuid

from django.conf import settings
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey("listings.Listing", on_delete=models.PROTECT, related_name="conversations")
    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="initiated_conversations")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="received_conversations")
    subject = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(default=timezone.now)
    last_sequence = models.PositiveBigIntegerField(default=0)

    class Meta:
        ordering = ["-last_message_at", "-pk"]
        indexes = [models.Index(fields=["initiator", "-created_at", "-id"], name="contact_actor_recent_idx")]
        constraints = [
            models.UniqueConstraint(fields=["listing", "initiator"], name="conversations_listing_initiator_unique"),
            models.CheckConstraint(condition=~models.Q(initiator=models.F("recipient")),
                                   name="conversations_distinct_parties"),
        ]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="conversation_messages")
    sequence = models.PositiveBigIntegerField()
    body = models.TextField(validators=[MaxLengthValidator(4000)])
    created_at = models.DateTimeField(default=timezone.now)
    client_token = models.UUIDField()

    class Meta:
        ordering = ["-sequence"]
        indexes = [models.Index(fields=["sender", "-created_at", "-id"], name="message_actor_recent_idx")]
        constraints = [
            models.UniqueConstraint(fields=["conversation", "sequence"], name="conversations_message_sequence_unique"),
            models.UniqueConstraint(fields=["conversation", "sender", "client_token"],
                                    name="conversations_message_token_unique"),
            models.CheckConstraint(condition=models.Q(sequence__gte=1), name="conversations_message_positive_sequence"),
        ]


class Participant(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="conversation_participations")
    last_read_sequence = models.PositiveBigIntegerField(default=0)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="conversations_participant_unique"),
        ]


class UserBlock(models.Model):
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="placed_user_blocks")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="received_user_blocks")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="conversations_userblock_unique"),
            models.CheckConstraint(condition=~models.Q(blocker=models.F("blocked")),
                                   name="conversations_userblock_distinct_users"),
        ]
