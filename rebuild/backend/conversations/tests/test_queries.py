from datetime import timedelta
from uuid import uuid4

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from conversations.models import Conversation, Message, Participant
from conversations.queries import (
    conversation_for_actor, conversation_messages, inbox_conversations, start_context,
)
from conversations.services import set_archived
from listings.models import Listing, ListingRevision
from .helpers import ConversationFixtures


class ConversationQueryTests(ConversationFixtures, TestCase):
    def test_start_context_get_is_side_effect_free_and_existing_closed_history_redirects(self):
        listing, existing = start_context(actor=self.buyer, listing_id=self.listing.pk)
        self.assertEqual(listing.pk, self.listing.pk)
        self.assertIsNone(existing)
        self.assertEqual(Conversation.objects.count(), 0)
        first = self.start()
        Listing.objects.filter(pk=self.listing.pk).update(lifecycle="closed", contact_enabled=False)
        before = list(Participant.objects.values())
        listing, existing = start_context(actor=self.buyer, listing_id=self.listing.pk)
        self.assertEqual(existing.pk, first.conversation_id)
        self.assertEqual(list(Participant.objects.values()), before)
        with self.assertRaises(PermissionDenied):
            start_context(actor=self.outsider, listing_id=self.listing.pk)

    def test_owner_change_existing_start_context_fails_identity_changed(self):
        first = self.start()
        Listing.objects.filter(pk=self.listing.pk).update(owner=self.outsider)
        with self.assertRaises(ValidationError) as caught:
            start_context(actor=self.buyer, listing_id=self.listing.pk)
        self.assertEqual(caught.exception.error_list[0].code, "identity_changed")
        self.assertEqual(conversation_for_actor(actor=self.seller, conversation_id=first.conversation_id).pk,
                         first.conversation_id)

    def test_frozen_public_subject_does_not_take_unapproved_revision(self):
        first = self.start()
        approved = self.listing.public_revision
        ListingRevision.objects.create(
            listing=self.listing, category=self.category, attribute_schema=self.schema,
            schema_version=1, title="PRIVATE DRAFT", status="draft")
        self.assertEqual(conversation_for_actor(actor=self.buyer, conversation_id=first.conversation_id).subject,
                         approved.title)
        self.assertEqual(inbox_conversations(actor=self.buyer).get().subject, approved.title)

    def test_queries_do_not_mutate_watermark_archive_time_or_message_count(self):
        first = self.start()
        self.send(first.conversation)
        set_archived(actor=self.buyer, conversation_id=first.conversation_id, archived=True)
        before = (list(Participant.objects.order_by("pk").values()), Conversation.objects.values().get())
        list(inbox_conversations(actor=self.buyer, archived=True))
        list(conversation_messages(actor=self.buyer, conversation_id=first.conversation_id))
        conversation_for_actor(actor=self.buyer, conversation_id=first.conversation_id)
        self.assertEqual((list(Participant.objects.order_by("pk").values()), Conversation.objects.values().get()), before)
        self.assertEqual(Message.objects.count(), 2)

    @override_settings(PILOT_NEW_CONTACTS_PER_HOUR=15)
    def test_inbox_sql_pagination_and_bounded_queries_on_fifteen_threads(self):
        conversations = []
        for i in range(15):
            first = self.start(listing=self.public_listing(title=f"Public {i}"), body="x" * 200)
            conversations.append(first.conversation)
        tied_at = timezone.now()
        Conversation.objects.update(last_message_at=tied_at)
        expected = sorted([thread.pk for thread in conversations], reverse=True)[:12]
        with CaptureQueriesContext(connection) as captured:
            page = list(inbox_conversations(actor=self.buyer)[:12])
            # Listing is included, but no private User object is loaded as display data.
            for thread in page:
                self.assertIsNotNone(thread.listing.pk)
                self.assertNotIn("initiator", thread._state.fields_cache)
                self.assertNotIn("recipient", thread._state.fields_cache)
        self.assertEqual([row.pk for row in page], expected)
        self.assertLessEqual(len(captured), 3)
        self.assertEqual(len(page), 12)
        self.assertTrue(any("LIMIT 12" in query["sql"] for query in captured))
        self.assertFalse(any("email" in query["sql"].lower().split(" from ")[0] for query in captured))
        for row in page:
            self.assertEqual(len(row.last_message_preview), 160)
            self.assertEqual(row.viewer_last_read_sequence, 0)
            self.assertIsNone(row.viewer_archived_at)
            self.assertFalse(row.has_unread)
            self.assertFalse(getattr(row, "_prefetched_objects_cache", {}))

    def test_thread_thirty_message_slice_is_sql_and_latest_first(self):
        first = self.start()
        for i in range(35):
            self.send(first.conversation, actor=self.buyer, body=f"Message {i}")
        with CaptureQueriesContext(connection) as captured:
            rows = list(conversation_messages(actor=self.buyer, conversation_id=first.conversation_id)[:30])
        self.assertEqual([row.sequence for row in rows], list(range(36, 6, -1)))
        self.assertLessEqual(len(captured), 4)
        self.assertTrue(any("LIMIT 30" in query["sql"] for query in captured))
        self.assertFalse(any("email" in query["sql"].lower().split(" from ")[0] for query in captured))
        for row in rows:
            self.assertNotIn("sender", row._state.fields_cache)

    def test_missing_and_outsider_have_same_absence_and_canonical_filter(self):
        first = self.start()
        for pk in [first.conversation_id, uuid4()]:
            with self.assertRaises(Conversation.DoesNotExist):
                conversation_for_actor(actor=self.outsider, conversation_id=pk)
        self.assertEqual(inbox_conversations(actor=self.outsider).count(), 0)

    def test_unread_is_incoming_only_even_when_latest_message_is_own(self):
        first = self.start()
        self.assertTrue(inbox_conversations(actor=self.seller).get().has_unread)
        self.assertFalse(inbox_conversations(actor=self.buyer).get().has_unread)
        self.send(first.conversation)
        self.send(first.conversation, actor=self.buyer)
        self.assertTrue(inbox_conversations(actor=self.buyer).get().has_unread)
        self.assertTrue(inbox_conversations(actor=self.seller).get().has_unread)
