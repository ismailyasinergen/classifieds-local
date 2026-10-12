from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from time import monotonic
from uuid import uuid4

from django.db import connection, connections, transaction
from django.test import TransactionTestCase, override_settings

from accounts.locking import lock_users
from accounts.models import User
from accounts.rate_limits import ActionRateLimited
from conversations.models import Conversation, Message, Participant
from .helpers import ConversationFixtures


class PostgresLimitWorkers:
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

    def ordered(self, first, second, user_ids, *, rollback=False):
        """Release the holder only after observing the other backend's real Lock wait."""
        self.assertEqual(connection.vendor, "postgresql")
        first_done, second_ready, release = Event(), Event(), Event()
        second_pid = []

        def holding(pid):
            with transaction.atomic():
                lock_users(user_ids=user_ids)
                result = first()
                if rollback:
                    transaction.set_rollback(True)
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
                        cursor.execute("SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s",
                                       [second_pid[0]])
                        row = cursor.fetchone()
                    if row and row[0] == "Lock":
                        observed_wait = True
                        break
                self.assertTrue(observed_wait, "Second backend never waited on a PostgreSQL lock")
            finally:
                release.set()
            results = [held.result(timeout=15), waited.result(timeout=15)]
        self.assertNotEqual(results[0][0], results[1][0])
        return [result for pid, result in results]

    def limited_operation(self, operation):
        try:
            return operation().pk
        except ActionRateLimited as error:
            return error.action


@override_settings(PILOT_NEW_CONTACTS_PER_HOUR=2, PILOT_MESSAGES_PER_HOUR=120)
class RateLimitConcurrencyTests(PostgresLimitWorkers, ConversationFixtures, TransactionTestCase):
    def test_final_contact_slot_across_distinct_sellers_and_listings(self):
        self.start()
        second = self.public_listing()
        third = self.public_listing(owner=self.outsider)
        results = self.race(
            lambda: self.limited_operation(lambda: self.start(listing=second)),
            lambda: self.limited_operation(lambda: self.start(listing=third)),
        )
        self.assertEqual(results.count("new_contact"), 1)
        self.assertEqual(Conversation.objects.filter(initiator=self.buyer).count(), 2)
        self.assertEqual(Message.objects.filter(sender=self.buyer).count(), 2)
        self.assertEqual(Participant.objects.count(), 4)

    @override_settings(PILOT_MESSAGES_PER_HOUR=3)
    def test_final_message_slot_across_distinct_threads_and_recipients(self):
        first = self.start()
        second = self.start(listing=self.public_listing(owner=self.outsider))
        results = self.race(
            lambda: self.limited_operation(lambda: self.send(first.conversation, actor=self.buyer)),
            lambda: self.limited_operation(lambda: self.send(second.conversation, actor=self.buyer)),
        )
        self.assertEqual(results.count("message"), 1)
        self.assertEqual(Message.objects.filter(sender=self.buyer).count(), 3)
        self.assertEqual(sorted(Conversation.objects.values_list("last_sequence", flat=True)), [1, 2])

    @override_settings(PILOT_MESSAGES_PER_HOUR=2)
    def test_same_token_race_at_final_message_slot_replays_one_insert(self):
        first = self.start()
        token = uuid4()
        results = self.race(
            lambda: self.send(first.conversation, actor=self.buyer, token=token).pk,
            lambda: self.send(first.conversation, actor=self.buyer, token=token).pk,
        )
        self.assertEqual(results[0], results[1])
        self.assertEqual(Message.objects.count(), 2)
        first.conversation.refresh_from_db()
        self.assertEqual(first.conversation.last_sequence, 2)

    @override_settings(PILOT_NEW_CONTACTS_PER_HOUR=1, PILOT_MESSAGES_PER_HOUR=1)
    def test_same_token_first_contact_race_at_final_slots_replays_one_insert(self):
        token = uuid4()
        results = self.race(lambda: self.start(token=token).pk, lambda: self.start(token=token).pk)
        self.assertEqual(results[0], results[1])
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Message.objects.count(), 1)

    @override_settings(PILOT_NEW_CONTACTS_PER_HOUR=1)
    def test_contact_commit_is_visible_to_waiting_distinct_listing(self):
        other = self.public_listing(owner=self.outsider)
        results = self.ordered(
            lambda: self.start().pk,
            lambda: self.limited_operation(lambda: self.start(listing=other)),
            [self.buyer.pk],
        )
        self.assertEqual(results[1], "new_contact")
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(Participant.objects.count(), 2)

    @override_settings(PILOT_NEW_CONTACTS_PER_HOUR=1)
    def test_contact_rollback_leaves_waiting_distinct_listing_slot_free(self):
        other = self.public_listing(owner=self.outsider)
        results = self.ordered(
            lambda: self.start().pk,
            lambda: self.limited_operation(lambda: self.start(listing=other)),
            [self.buyer.pk], rollback=True,
        )
        self.assertNotEqual(results[1], "new_contact")
        self.assertEqual(Conversation.objects.get().listing_id, other.pk)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Participant.objects.count(), 2)

    @override_settings(PILOT_MESSAGES_PER_HOUR=3)
    def test_message_commit_is_visible_to_waiting_other_thread(self):
        first = self.start()
        other = self.start(listing=self.public_listing(owner=self.outsider))
        results = self.ordered(
            lambda: self.send(first.conversation, actor=self.buyer).pk,
            lambda: self.limited_operation(lambda: self.send(other.conversation, actor=self.buyer)),
            [self.buyer.pk],
        )
        self.assertEqual(results[1], "message")
        self.assertEqual(Message.objects.count(), 3)
        other.conversation.refresh_from_db()
        self.assertEqual(other.conversation.last_sequence, 1)

    @override_settings(PILOT_MESSAGES_PER_HOUR=3)
    def test_message_rollback_keeps_waiting_other_thread_slot_free(self):
        first = self.start()
        other = self.start(listing=self.public_listing(owner=self.outsider))
        results = self.ordered(
            lambda: self.send(first.conversation, actor=self.buyer).pk,
            lambda: self.limited_operation(lambda: self.send(other.conversation, actor=self.buyer)),
            [self.buyer.pk], rollback=True,
        )
        self.assertNotEqual(results[1], "message")
        self.assertEqual(Message.objects.count(), 3)
        first.conversation.refresh_from_db()
        other.conversation.refresh_from_db()
        self.assertEqual(first.conversation.last_sequence, 1)
        self.assertEqual(other.conversation.last_sequence, 2)
