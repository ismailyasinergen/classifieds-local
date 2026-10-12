from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from conversations.models import Conversation, Message, Participant, UserBlock
from conversations.policies import can_reply, require_can_start, require_participant
from conversations.queries import conversation_for_actor, conversation_messages, inbox_conversations, start_context
from conversations.services import (
    block_user, mark_read, send_message, set_archived, set_contact_enabled,
    start_conversation, unblock_user,
)
from listings.models import Listing, ListingRevision
from moderation.models import MessagingRestriction, Restriction
from moderation.policies import visible_listings
from .helpers import ConversationFixtures


class ConversationServiceTests(ConversationFixtures, TestCase):
    def assert_no_thread(self):
        self.assertEqual(Conversation.objects.count(), 0)
        self.assertEqual(Participant.objects.count(), 0)
        self.assertEqual(Message.objects.count(), 0)

    def test_atomic_creation_subject_and_idempotent_start(self):
        token = uuid4()
        first = self.start(body="  Merhaba\r\nDünya  ", token=token)
        replay = self.start(body="Merhaba\nDünya", token=token)
        self.assertEqual(replay.pk, first.pk)
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Participant.objects.filter(conversation=first.conversation).count(), 2)
        self.assertEqual(first.conversation.subject, "Onaylı başlık")
        self.assertEqual(first.body, "Merhaba\nDünya")
        self.assertEqual(first.conversation.recipient_id, self.seller.pk)
        self.start(body="İkinci", token=uuid4())
        self.assertEqual(list(Message.objects.order_by("sequence").values_list("sequence", flat=True)), [1, 2])

    def test_invalid_body_boundaries_leave_no_rows(self):
        for body in ["", " \r\n ", "bad\x00value", "x" * 4001, " " * 8001, None, b"text", "\ud800"]:
            with self.subTest(kind=repr(body)[:30]):
                with self.assertRaises(ValidationError) as caught:
                    self.start(body=body)
                self.assertIn("body", caught.exception.message_dict)
                self.assert_no_thread()
        first = self.start(body="ğ" * 4000)
        self.assertEqual(len(first.body), 4000)

    def test_raw_cap_precedes_normalization_and_cr_retry(self):
        first = self.start(body=" " * 3999 + "a" + " " * 4000)
        self.assertEqual(first.body, "a")
        token = uuid4()
        message = self.start(body=" a\rb\r\nc ", token=token)
        self.assertEqual(self.start(body="a\nb\nc", token=token).pk, message.pk)

    def test_invalid_client_token_is_validation_and_atomic(self):
        for token in ["", "not-uuid", 1, None]:
            with self.subTest(token=token):
                with self.assertRaises(ValidationError) as caught:
                    start_conversation(actor=self.buyer, listing_id=self.listing.pk,
                                       body="Valid", client_token=token)
                self.assertIn("client_token", caught.exception.message_dict)
                self.assert_no_thread()

    def test_same_token_changed_body_conflicts_without_state_change(self):
        token = uuid4()
        message = self.start(token=token)
        before = Conversation.objects.values().get()
        with self.assertRaises(ValidationError) as caught:
            self.start(body="Changed", token=token)
        self.assertEqual(caught.exception.error_list[0].code, "token_conflict")
        self.assertEqual(Conversation.objects.values().get(), before)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(message.sequence, 1)

    def test_self_anonymous_inactive_and_stale_actor_cannot_start(self):
        for actor in [self.seller, AnonymousUser()]:
            with self.assertRaises(PermissionDenied):
                self.start(actor=actor)
            self.assert_no_thread()
        User.objects.filter(pk=self.buyer.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.start()
        self.assert_no_thread()
        User.objects.filter(pk=self.buyer.pk).update(is_active=True)
        self.buyer.is_active = False
        with self.assertRaises(PermissionDenied):
            self.start()
        self.assert_no_thread()

    def test_inactive_recipient_cannot_receive_first_message(self):
        User.objects.filter(pk=self.seller.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.start()
        self.assert_no_thread()

    def test_nonpublic_lifecycle_and_exact_expiry_reject_new_thread(self):
        for state in [Listing.Lifecycle.DRAFT, Listing.Lifecycle.PAUSED, Listing.Lifecycle.CLOSED]:
            Listing.objects.filter(pk=self.listing.pk).update(lifecycle=state)
            with self.assertRaises(PermissionDenied):
                self.start()
            self.assert_no_thread()
        Listing.objects.filter(pk=self.listing.pk).update(lifecycle=Listing.Lifecycle.LIVE, expires_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.start()
        self.assert_no_thread()

    def test_wrong_missing_or_unapproved_public_revision_rejects_start(self):
        other = self.public_listing()
        for revision_id in [None, other.public_revision_id]:
            Listing.objects.filter(pk=self.listing.pk).update(public_revision_id=revision_id)
            with self.assertRaises(PermissionDenied):
                self.start()
            self.assert_no_thread()
        Listing.objects.filter(pk=self.listing.pk).update(public_revision_id=self.listing.public_revision_id)
        ListingRevision.objects.filter(pk=self.listing.public_revision_id).update(status="submitted")
        with self.assertRaises(PermissionDenied):
            self.start()
        self.assert_no_thread()

    def test_visibility_restrictions_and_contact_disable_reject_start(self):
        for target in [dict(listing=self.listing), dict(seller=self.seller)]:
            restriction = Restriction.objects.create(actor=self.outsider, reason="Private", **target)
            with self.assertRaises(PermissionDenied):
                self.start()
            self.assert_no_thread()
            restriction.delete()
        set_contact_enabled(actor=self.seller, listing_id=self.listing.pk, enabled=False)
        self.assertTrue(visible_listings().filter(pk=self.listing.pk).exists())
        with self.assertRaises(PermissionDenied):
            self.start()
        self.assert_no_thread()

    def test_both_block_directions_reject_new_thread(self):
        for blocker, blocked in [(self.buyer, self.seller), (self.seller, self.buyer)]:
            block_user(actor=blocker, other_user_id=blocked.pk)
            with self.assertRaises(PermissionDenied):
                self.start()
            self.assert_no_thread()
            unblock_user(actor=blocker, other_user_id=blocked.pk)

    def test_messaging_restriction_for_either_account_rejects_new_thread(self):
        for target in [self.buyer, self.seller]:
            restriction = MessagingRestriction.objects.create(user=target, actor=self.outsider, reason="Private")
            with self.assertRaises(PermissionDenied):
                self.start()
            self.assert_no_thread()
            restriction.delete()

    def test_replies_survive_all_listing_closure_gates(self):
        message = self.start()
        for state in ["paused", "closed", "draft"]:
            Listing.objects.filter(pk=self.listing.pk).update(lifecycle=state)
            self.send(message.conversation)
        Listing.objects.filter(pk=self.listing.pk).update(expires_at=timezone.now(), contact_enabled=False)
        Restriction.objects.create(listing=self.listing, actor=self.outsider, reason="Private")
        Restriction.objects.create(seller=self.seller, actor=self.outsider, reason="Private")
        self.send(message.conversation)
        # A second start is a reply to the canonical existing thread.
        self.start(body="Existing")
        self.assertEqual(Message.objects.count(), 6)
        self.assertTrue(can_reply(actor=self.buyer, conversation=message.conversation))

    def test_existing_start_checks_owner_identity_before_replay(self):
        token = uuid4()
        message = self.start(token=token)
        Listing.objects.filter(pk=self.listing.pk).update(owner=self.outsider)
        with self.assertRaises(ValidationError) as caught:
            self.start(token=token)
        self.assertEqual(caught.exception.error_list[0].code, "identity_changed")
        self.assertEqual(conversation_for_actor(actor=self.buyer, conversation_id=message.conversation_id).pk,
                         message.conversation_id)
        self.send(message.conversation)
        with self.assertRaises(Conversation.DoesNotExist):
            conversation_for_actor(actor=self.outsider, conversation_id=message.conversation_id)

    def test_injected_participant_staff_superuser_has_no_authority(self):
        message = self.start()
        Participant.objects.create(conversation=message.conversation, user=self.outsider)
        with self.assertRaises(PermissionDenied):
            require_participant(actor=self.outsider, conversation=message.conversation)
        with self.assertRaises(Conversation.DoesNotExist):
            conversation_for_actor(actor=self.outsider, conversation_id=message.conversation_id)
        with self.assertRaises(Conversation.DoesNotExist):
            conversation_messages(actor=self.outsider, conversation_id=message.conversation_id)
        self.assertEqual(inbox_conversations(actor=self.outsider).count(), 0)
        for call in [
            lambda: self.send(message.conversation, actor=self.outsider),
            lambda: mark_read(actor=self.outsider, conversation_id=message.conversation_id, through_message_id=message.pk),
            lambda: set_archived(actor=self.outsider, conversation_id=message.conversation_id, archived=True),
        ]:
            with self.assertRaises(PermissionDenied):
                call()

    def test_inactive_actor_cannot_read_write_or_replay(self):
        token = uuid4()
        message = self.start(token=token)
        User.objects.filter(pk=self.buyer.pk).update(is_active=False)
        for call in [
            lambda: self.start(token=token),
            lambda: conversation_for_actor(actor=self.buyer, conversation_id=message.conversation_id),
            lambda: inbox_conversations(actor=self.buyer).count(),
            lambda: mark_read(actor=self.buyer, conversation_id=message.conversation_id, through_message_id=message.pk),
            lambda: set_archived(actor=self.buyer, conversation_id=message.conversation_id, archived=True),
        ]:
            with self.assertRaises(PermissionDenied):
                call()

    def test_other_account_inactive_preserves_history_and_state_but_blocks_send(self):
        message = self.start()
        User.objects.filter(pk=self.seller.pk).update(is_active=False)
        self.assertEqual(conversation_for_actor(actor=self.buyer, conversation_id=message.conversation_id).pk,
                         message.conversation_id)
        mark_read(actor=self.buyer, conversation_id=message.conversation_id, through_message_id=message.pk)
        set_archived(actor=self.buyer, conversation_id=message.conversation_id, archived=True)
        self.assertFalse(can_reply(actor=self.buyer, conversation=message.conversation))
        with self.assertRaises(PermissionDenied):
            self.send(message.conversation, actor=self.buyer)

    def test_replay_after_block_and_restriction_does_not_change_any_state(self):
        token = uuid4()
        first = self.start(token=token)
        set_archived(actor=self.seller, conversation_id=first.conversation_id, archived=True)
        set_archived(actor=self.buyer, conversation_id=first.conversation_id, archived=True)
        block_user(actor=self.seller, other_user_id=self.buyer.pk)
        MessagingRestriction.objects.create(user=self.buyer, actor=self.outsider, reason="Private")
        before = (Conversation.objects.values().get(),
                  list(Participant.objects.order_by("pk").values()))
        replay = self.start(token=token)
        self.assertEqual(replay.pk, first.pk)
        self.assertEqual((Conversation.objects.values().get(),
                          list(Participant.objects.order_by("pk").values())), before)
        with self.assertRaises(PermissionDenied):
            self.start()
        self.assertEqual(list(conversation_messages(actor=self.buyer, conversation_id=first.conversation_id)), [first])

    def test_send_replay_and_conflict_uses_sender_specific_token(self):
        first = self.start()
        token = uuid4()
        reply = self.send(first.conversation, token=token)
        block_user(actor=self.buyer, other_user_id=self.seller.pk)
        self.assertEqual(self.send(first.conversation, token=token).pk, reply.pk)
        with self.assertRaises(ValidationError) as caught:
            self.send(first.conversation, body="Different", token=token)
        self.assertEqual(caught.exception.error_list[0].code, "token_conflict")

    def test_read_cursor_marks_only_displayed_sequence_and_is_monotonic(self):
        first = self.start()
        displayed = self.send(first.conversation)
        later = self.send(first.conversation, body="Later incoming")
        read = mark_read(actor=self.buyer, conversation_id=first.conversation_id, through_message_id=displayed.pk)
        self.assertEqual(read.last_read_sequence, displayed.sequence)
        self.assertTrue(inbox_conversations(actor=self.buyer).get().has_unread)
        older = mark_read(actor=self.buyer, conversation_id=first.conversation_id, through_message_id=first.pk)
        self.assertEqual(older.last_read_sequence, displayed.sequence)
        mark_read(actor=self.buyer, conversation_id=first.conversation_id, through_message_id=later.pk)
        self.assertFalse(inbox_conversations(actor=self.buyer).get().has_unread)

    def test_foreign_read_message_cannot_advance_watermark(self):
        first = self.start()
        foreign = self.start(listing=self.public_listing())
        with self.assertRaises(ValidationError):
            mark_read(actor=self.buyer, conversation_id=first.conversation_id, through_message_id=foreign.pk)
        self.assertEqual(Participant.objects.get(conversation=first.conversation, user=self.buyer).last_read_sequence, 0)

    def test_own_sends_do_not_create_unread_or_mark_unseen_incoming(self):
        first = self.start()
        self.assertFalse(inbox_conversations(actor=self.buyer).get().has_unread)
        self.send(first.conversation)
        self.send(first.conversation, actor=self.buyer)
        participant = Participant.objects.get(conversation=first.conversation, user=self.buyer)
        self.assertEqual(participant.last_read_sequence, 0)
        self.assertTrue(inbox_conversations(actor=self.buyer).get().has_unread)

    def test_archive_is_personal_idempotent_and_only_real_incoming_unarchives(self):
        first = self.start()
        archived = set_archived(actor=self.buyer, conversation_id=first.conversation_id, archived=True)
        again = set_archived(actor=self.buyer, conversation_id=first.conversation_id, archived=True)
        self.assertEqual(archived.archived_at, again.archived_at)
        set_archived(actor=self.seller, conversation_id=first.conversation_id, archived=True)
        self.send(first.conversation, actor=self.buyer)
        buyer = Participant.objects.get(conversation=first.conversation, user=self.buyer)
        seller = Participant.objects.get(conversation=first.conversation, user=self.seller)
        self.assertEqual(buyer.archived_at, archived.archived_at)
        self.assertIsNone(seller.archived_at)
        self.assertEqual(inbox_conversations(actor=self.buyer).count(), 0)
        self.assertEqual(inbox_conversations(actor=self.buyer, archived=True).count(), 1)
        self.send(first.conversation)
        buyer.refresh_from_db()
        self.assertIsNone(buyer.archived_at)
        cleared = set_archived(actor=self.buyer, conversation_id=first.conversation_id, archived=False)
        self.assertIsNone(cleared.archived_at)

    def test_block_is_directional_idempotent_and_owned(self):
        block = block_user(actor=self.buyer, other_user_id=self.seller.pk)
        self.assertEqual(block_user(actor=self.buyer, other_user_id=self.seller.pk).pk, block.pk)
        unblock_user(actor=self.seller, other_user_id=self.buyer.pk)
        self.assertTrue(UserBlock.objects.filter(pk=block.pk).exists())
        User.objects.filter(pk=self.seller.pk).update(is_active=False)
        unblock_user(actor=self.buyer, other_user_id=self.seller.pk)
        unblock_user(actor=self.buyer, other_user_id=self.seller.pk)
        self.assertFalse(UserBlock.objects.exists())
        block_user(actor=self.buyer, other_user_id=self.seller.pk)

    def test_block_self_missing_and_inactive_actor_rejected(self):
        with self.assertRaises(ValidationError):
            block_user(actor=self.buyer, other_user_id=self.buyer.pk)
        with self.assertRaises(User.DoesNotExist):
            block_user(actor=self.buyer, other_user_id=999999)
        User.objects.filter(pk=self.buyer.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            block_user(actor=self.buyer, other_user_id=self.seller.pk)

    def test_contact_preference_requires_active_fresh_owner_and_boolean(self):
        with self.assertRaises(PermissionDenied):
            set_contact_enabled(actor=self.buyer, listing_id=self.listing.pk, enabled=False)
        with self.assertRaises(ValidationError):
            set_contact_enabled(actor=self.seller, listing_id=self.listing.pk, enabled="false")
        User.objects.filter(pk=self.seller.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            set_contact_enabled(actor=self.seller, listing_id=self.listing.pk, enabled=False)

    def test_contact_column_has_persistent_true_database_default(self):
        # The preceding Search source omits this field on INSERT after a source rollback.
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_get_expr(d.adbin, d.adrelid) "
                "FROM pg_attribute a JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum "
                "WHERE a.attrelid = 'listings_listing'::regclass AND a.attname = 'contact_enabled'")
            row = cursor.fetchone()
        self.assertIsNotNone(row, "contact_enabled requires a persistent PostgreSQL default")
        self.assertEqual(row[0], "true")

    def test_db_constraints_prevent_self_and_duplicate_records(self):
        first = self.start()
        bad_rows = [
            lambda: Conversation.objects.create(listing=self.listing, initiator=self.buyer, recipient=self.buyer, subject="Bad"),
            lambda: Conversation.objects.create(listing=self.listing, initiator=self.buyer, recipient=self.seller, subject="Duplicate"),
            lambda: Participant.objects.create(conversation=first.conversation, user=self.buyer),
            lambda: Message.objects.create(conversation=first.conversation, sender=self.buyer, sequence=0, body="Bad", client_token=uuid4()),
            lambda: Message.objects.create(conversation=first.conversation, sender=self.buyer, sequence=1, body="Bad", client_token=uuid4()),
            lambda: Message.objects.create(conversation=first.conversation, sender=self.buyer, sequence=2, body="Bad", client_token=first.client_token),
            lambda: UserBlock.objects.create(blocker=self.buyer, blocked=self.buyer),
        ]
        for call in bad_rows:
            with self.assertRaises(IntegrityError), transaction.atomic():
                call()
