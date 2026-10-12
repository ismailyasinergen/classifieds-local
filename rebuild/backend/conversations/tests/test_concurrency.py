from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic
from uuid import uuid4

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db import connection, connections, transaction
from django.db.transaction import TransactionManagementError
from django.test import TransactionTestCase

from accounts.locking import lock_users
from accounts.models import User
from conversations.models import Conversation, Message, Participant, UserBlock
from conversations.queries import inbox_conversations
from conversations.services import block_user, mark_read
from moderation.messaging import restrict_messaging
from moderation.models import MessagingRestriction
from .helpers import ConversationFixtures


class ConversationConcurrencyTests(ConversationFixtures, TransactionTestCase):
    def worker(self, callback, barrier=None):
        connections.close_all()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout = '5s'")
                cursor.execute("SET statement_timeout = '10s'")
                cursor.execute("SELECT pg_backend_pid()")
                pid = cursor.fetchone()[0]
            if barrier is not None:
                barrier.wait(timeout=5)
            return pid, callback(pid)
        finally:
            connections.close_all()

    def race(self, *callbacks):
        self.assertEqual(connection.vendor, "postgresql")
        barrier = Barrier(len(callbacks))
        with ThreadPoolExecutor(max_workers=len(callbacks)) as pool:
            futures = [
                pool.submit(self.worker, lambda pid, callback=callback: callback(), barrier)
                for callback in callbacks
            ]
            results = [future.result(timeout=20) for future in futures]
        self.assertEqual(len({pid for pid, result in results}), len(callbacks))
        return [result for pid, result in results]

    def ordered(self, first, second, user_ids):
        """Hold the first transaction until PostgreSQL proves the second is lock-waiting."""
        first_done, second_ready, release = Event(), Event(), Event()
        second_pid = []

        def holding(pid):
            with transaction.atomic():
                lock_users(user_ids=user_ids)
                result = first()
                first_done.set()
                if not release.wait(timeout=8):
                    raise AssertionError("First transaction release timed out")
            return result

        def waiting(pid):
            if not first_done.wait(timeout=8):
                raise AssertionError("First operation did not reach its held commit")
            second_pid.append(pid)
            second_ready.set()
            return second()

        with ThreadPoolExecutor(max_workers=2) as pool:
            held = pool.submit(self.worker, holding)
            waited = pool.submit(self.worker, waiting)
            try:
                self.assertTrue(first_done.wait(timeout=5))
                self.assertTrue(second_ready.wait(timeout=5))
                deadline = monotonic() + 3
                observed_wait = False
                while monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", [second_pid[0]])
                        row = cursor.fetchone()
                    if row and row[0] == "Lock":
                        observed_wait = True
                        break
                self.assertTrue(observed_wait, "Second connection never waited on a PostgreSQL lock")
            finally:
                release.set()
            results = [held.result(timeout=15), waited.result(timeout=15)]
        self.assertNotEqual(results[0][0], results[1][0])
        return [result for pid, result in results]

    def allowed_send(self, conversation, actor=None):
        try:
            return self.send(conversation, actor=actor).pk
        except PermissionDenied:
            return "denied"

    def assert_atomic_thread(self, messages):
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.get()
        self.assertEqual(Participant.objects.filter(conversation=conversation).count(), 2)
        self.assertEqual(Message.objects.count(), messages)
        self.assertEqual(conversation.last_sequence, messages)
        self.assertEqual(list(Message.objects.order_by("sequence").values_list("sequence", flat=True)),
                         list(range(1, messages + 1)))

    def test_simultaneous_first_send_same_token_has_one_message(self):
        token = uuid4()
        results = self.race(lambda: self.start(token=token).pk, lambda: self.start(token=token).pk)
        self.assertEqual(results[0], results[1])
        self.assert_atomic_thread(1)

    def test_simultaneous_first_send_different_tokens_allocates_unique_sequences(self):
        results = self.race(lambda: self.start().pk, lambda: self.start().pk)
        self.assertNotEqual(results[0], results[1])
        self.assert_atomic_thread(2)

    def test_simultaneous_replies_reversed_actor_order_has_unique_sequences(self):
        first = self.start()
        self.race(lambda: self.send(first.conversation, actor=self.buyer).pk,
                  lambda: self.send(first.conversation, actor=self.seller).pk)
        self.assert_atomic_thread(3)

    def test_simultaneous_reply_replay_is_one_message(self):
        first = self.start()
        token = uuid4()
        results = self.race(lambda: self.send(first.conversation, token=token).pk,
                            lambda: self.send(first.conversation, token=token).pk)
        self.assertEqual(results[0], results[1])
        self.assert_atomic_thread(2)

    def test_unordered_send_and_block_have_serializable_persisted_outcome(self):
        first = self.start()
        results = self.race(lambda: self.allowed_send(first.conversation),
                            lambda: block_user(actor=self.buyer, other_user_id=self.seller.pk).pk)
        self.assert_atomic_thread(1 if results[0] == "denied" else 2)
        self.assertEqual(UserBlock.objects.count(), 1)
        self.assertEqual(self.allowed_send(first.conversation), "denied")

    def test_block_commits_before_waiting_send_rejects_message(self):
        first = self.start()
        results = self.ordered(
            lambda: block_user(actor=self.buyer, other_user_id=self.seller.pk).pk,
            lambda: self.allowed_send(first.conversation),
            [self.buyer.pk, self.seller.pk])
        self.assertEqual(results[1], "denied")
        self.assert_atomic_thread(1)
        self.assertEqual(UserBlock.objects.count(), 1)

    def test_send_commits_before_waiting_block_preserves_successful_message(self):
        first = self.start()
        results = self.ordered(
            lambda: self.allowed_send(first.conversation),
            lambda: block_user(actor=self.buyer, other_user_id=self.seller.pk).pk,
            [self.buyer.pk, self.seller.pk])
        self.assertNotEqual(results[0], "denied")
        self.assert_atomic_thread(2)
        self.assertEqual(self.allowed_send(first.conversation), "denied")

    def grant_restriction_permission(self):
        self.buyer.user_permissions.add(Permission.objects.get(
            content_type__app_label="moderation", codename="restrict_messaging"))

    def test_restriction_commits_before_waiting_send_rejects_message(self):
        self.grant_restriction_permission()
        first = self.start()
        results = self.ordered(
            lambda: restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason="Private").pk,
            lambda: self.allowed_send(first.conversation),
            [self.buyer.pk, self.seller.pk])
        self.assertEqual(results[1], "denied")
        self.assert_atomic_thread(1)
        self.assertEqual(MessagingRestriction.objects.count(), 1)

    def test_send_commits_before_waiting_restriction_preserves_message(self):
        self.grant_restriction_permission()
        first = self.start()
        results = self.ordered(
            lambda: self.allowed_send(first.conversation),
            lambda: restrict_messaging(actor=self.buyer, user_id=self.seller.pk, reason="Private").pk,
            [self.buyer.pk, self.seller.pk])
        self.assertNotEqual(results[0], "denied")
        self.assert_atomic_thread(2)
        self.assertEqual(self.allowed_send(first.conversation), "denied")

    def test_deactivation_commits_before_waiting_send_rejects_message(self):
        first = self.start()
        results = self.ordered(
            lambda: User.objects.filter(pk=self.buyer.pk).update(is_active=False),
            lambda: self.allowed_send(first.conversation),
            [self.buyer.pk, self.seller.pk])
        self.assertEqual(results[1], "denied")
        self.assert_atomic_thread(1)
        self.assertFalse(User.objects.get(pk=self.buyer.pk).is_active)

    def test_send_commits_before_waiting_deactivation_preserves_message(self):
        first = self.start()

        def deactivate():
            with transaction.atomic():
                lock_users(user_ids=[self.buyer.pk])
                return User.objects.filter(pk=self.buyer.pk).update(is_active=False)

        results = self.ordered(
            lambda: self.allowed_send(first.conversation), deactivate,
            [self.buyer.pk, self.seller.pk])
        self.assertNotEqual(results[0], "denied")
        self.assert_atomic_thread(2)
        self.assertEqual(self.allowed_send(first.conversation), "denied")

    def test_reversed_block_actor_order_does_not_deadlock(self):
        results = self.race(
            lambda: block_user(actor=self.buyer, other_user_id=self.seller.pk).pk,
            lambda: block_user(actor=self.seller, other_user_id=self.buyer.pk).pk)
        self.assertNotEqual(results[0], results[1])
        self.assertEqual(UserBlock.objects.count(), 2)

    def test_overlapping_user_pairs_do_not_deadlock(self):
        results = self.race(
            lambda: block_user(actor=self.buyer, other_user_id=self.seller.pk).pk,
            lambda: block_user(actor=self.seller, other_user_id=self.outsider.pk).pk,
            lambda: block_user(actor=self.outsider, other_user_id=self.buyer.pk).pk)
        self.assertEqual(len(set(results)), 3)
        self.assertEqual(UserBlock.objects.count(), 3)

    def test_read_and_incoming_send_leave_later_message_unread(self):
        first = self.start()
        displayed = self.send(first.conversation)
        results = self.race(
            lambda: mark_read(actor=self.buyer, conversation_id=first.conversation_id,
                              through_message_id=displayed.pk).last_read_sequence,
            lambda: self.send(first.conversation).sequence)
        self.assertEqual(results, [displayed.sequence, displayed.sequence + 1])
        self.assertEqual(Participant.objects.get(conversation=first.conversation, user=self.buyer).last_read_sequence,
                         displayed.sequence)
        self.assertTrue(inbox_conversations(actor=self.buyer).get().has_unread)
        self.assert_atomic_thread(3)

    def test_account_lock_helper_requires_transaction_sorted_complete_anchors(self):
        with self.assertRaises(TransactionManagementError):
            lock_users(user_ids=[self.buyer.pk])
        with self.assertRaises(TransactionManagementError):
            lock_users(user_ids=[])
        with transaction.atomic():
            locked = lock_users(user_ids=[self.buyer.pk, self.seller.pk, self.buyer.pk])
            self.assertEqual(list(locked), sorted([self.buyer.pk, self.seller.pk]))
            with self.assertRaises(User.DoesNotExist):
                lock_users(user_ids=[999999])
