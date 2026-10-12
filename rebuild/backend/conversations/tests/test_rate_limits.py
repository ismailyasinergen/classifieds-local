from datetime import timedelta
from uuid import uuid4
from unittest.mock import patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import User

from conversations.models import Conversation, Message, Participant
from conversations.services import block_user, mark_read, set_archived
from listings.models import Listing
from .helpers import ConversationFixtures


@override_settings(PILOT_NEW_CONTACTS_PER_HOUR=1, PILOT_MESSAGES_PER_HOUR=2)
class ConversationLimitTests(ConversationFixtures, TestCase):
    def test_new_contact_budget_spans_sellers_and_listings(self):
        self.start()
        second = self.public_listing(owner=self.outsider)
        with self.assertRaises(ValidationError) as caught:
            self.start(listing=second)
        self.assertEqual(caught.exception.action, "new_contact")
        self.assertGreaterEqual(caught.exception.retry_after, 1)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Participant.objects.count(), 2)

    def test_message_budget_spans_threads_and_recipient_accounts(self):
        with override_settings(PILOT_NEW_CONTACTS_PER_HOUR=10):
            first = self.start()
            second = self.start(listing=self.public_listing(owner=self.outsider))
        with self.assertRaises(ValidationError) as caught:
            self.send(second.conversation, actor=self.buyer)
        self.assertEqual(caught.exception.action, "message")
        self.assertEqual(Message.objects.filter(sender=self.buyer).count(), 2)
        self.send(first.conversation, actor=self.seller)
        self.assertEqual(Message.objects.filter(sender=self.seller).count(), 1)

    @override_settings(PILOT_MESSAGES_PER_HOUR=1)
    def test_initial_send_consumes_message_budget_and_rejection_changes_no_state(self):
        first = self.start()
        mark_read(actor=self.buyer, conversation_id=first.conversation_id, through_message_id=first.pk)
        set_archived(actor=self.seller, conversation_id=first.conversation_id, archived=True)
        set_archived(actor=self.buyer, conversation_id=first.conversation_id, archived=True)
        before = (Conversation.objects.values().get(), list(Participant.objects.order_by("pk").values()))
        with self.assertRaises(ValidationError) as caught:
            self.send(first.conversation, actor=self.buyer)
        self.assertEqual(caught.exception.action, "message")
        self.assertEqual((Conversation.objects.values().get(), list(Participant.objects.order_by("pk").values())), before)
        self.assertEqual(Message.objects.count(), 1)

    @override_settings(PILOT_MESSAGES_PER_HOUR=1)
    def test_exhausted_replay_succeeds_but_changed_body_conflicts(self):
        token = uuid4()
        first = self.start(token=token)
        self.assertEqual(self.start(token=token).pk, first.pk)
        self.assertEqual(self.send(first.conversation, actor=self.buyer, body=first.body, token=token).pk, first.pk)
        with self.assertRaises(ValidationError) as caught:
            self.start(token=token, body="Changed")
        self.assertEqual(caught.exception.error_list[0].code, "token_conflict")
        self.assertEqual(Message.objects.count(), 1)

    @override_settings(PILOT_NEW_CONTACTS_PER_HOUR=10, PILOT_MESSAGES_PER_HOUR=1)
    def test_initial_message_limit_rolls_back_provisional_thread_and_participants(self):
        self.start()
        with self.assertRaises(ValidationError):
            self.start(listing=self.public_listing())
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Participant.objects.count(), 2)
        self.assertEqual(Message.objects.count(), 1)

    def test_failed_message_insert_and_outer_rollback_consume_neither_budget(self):
        with patch("conversations.services.Message.objects.create", side_effect=ValidationError("save failed")):
            with self.assertRaises(ValidationError):
                self.start()
        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(Participant.objects.count(), 0)
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.start()
                raise RuntimeError("rollback")
        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)
        self.start()

    @override_settings(PILOT_MESSAGES_PER_HOUR=1)
    def test_policy_and_identity_checks_precede_exhausted_limits(self):
        first = self.start()
        block_user(actor=self.seller, other_user_id=self.buyer.pk)
        with self.assertRaises(PermissionDenied):
            self.send(first.conversation, actor=self.buyer)
        with self.assertRaises(PermissionDenied):
            self.send(first.conversation, actor=self.outsider)
        with self.assertRaises(PermissionDenied):
            self.start(listing=self.public_listing())
        Listing.objects.filter(pk=self.listing.pk).update(owner=self.outsider)
        with self.assertRaises(ValidationError) as caught:
            self.start(token=first.client_token)
        self.assertEqual(caught.exception.error_list[0].code, "identity_changed")

    @override_settings(PILOT_MESSAGES_PER_HOUR=1)
    def test_inactive_current_actor_precedes_exhausted_budget_and_replay(self):
        first = self.start()
        User.objects.filter(pk=self.buyer.pk).update(is_active=False)
        for operation in (
            lambda: self.send(first.conversation, actor=self.buyer),
            lambda: self.start(token=first.client_token),
            lambda: self.start(listing=self.public_listing(owner=self.outsider)),
        ):
            with self.assertRaises(PermissionDenied):
                operation()
        self.assertEqual(Message.objects.count(), 1)

    @override_settings(PILOT_MESSAGES_PER_HOUR=1)
    def test_contact_and_message_cutoffs_are_exclusive_at_service_boundary(self):
        at = timezone.now()
        first = self.start()
        cutoff = at - timedelta(hours=1)
        Conversation.objects.filter(pk=first.conversation_id).update(created_at=cutoff)
        Message.objects.filter(pk=first.pk).update(created_at=cutoff)
        with patch("conversations.services.timezone.now", return_value=at):
            second = self.start(listing=self.public_listing(owner=self.outsider))
        self.assertEqual(Conversation.objects.count(), 2)
        Conversation.objects.filter(pk=second.conversation_id).update(
            created_at=cutoff + timedelta(microseconds=1))
        Message.objects.filter(pk=second.pk).update(
            created_at=cutoff + timedelta(microseconds=1))
        with patch("conversations.services.timezone.now", return_value=at):
            with self.assertRaises(ValidationError) as contact:
                self.start(listing=self.public_listing())
            with self.assertRaises(ValidationError) as message:
                self.send(first.conversation, actor=self.buyer)
        self.assertEqual(contact.exception.action, "new_contact")
        self.assertEqual(message.exception.action, "message")
        self.assertEqual(contact.exception.retry_after, 1)
        self.assertEqual(message.exception.retry_after, 1)
        self.assertEqual(Message.objects.count(), 2)

    def test_staff_and_superuser_have_the_same_budget(self):
        self.start(actor=self.outsider)
        with self.assertRaises(ValidationError) as caught:
            self.start(actor=self.outsider, listing=self.public_listing())
        self.assertEqual(caught.exception.action, "new_contact")
