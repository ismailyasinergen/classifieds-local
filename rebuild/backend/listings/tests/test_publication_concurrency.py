from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connection, connections
from django.test import TransactionTestCase

from listings.models import Listing, ListingRevision
from listings.services import InvalidRevisionState
from listings.tests.test_publication import PublicationFixtures


class PublicationConcurrencyTests(PublicationFixtures, TransactionTestCase):
    def race(self, *callbacks):
        barrier = Barrier(len(callbacks))

        def worker(callback):
            connections.close_all()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                    cursor.execute("SET statement_timeout = '10s'")
                    cursor.execute("SELECT pg_backend_pid()")
                    pid = cursor.fetchone()[0]
                barrier.wait(timeout=5)
                return pid, callback()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(callbacks)) as pool:
            futures = [pool.submit(worker, callback) for callback in callbacks]
            results = [future.result(timeout=15) for future in futures]
        self.assertEqual(len({pid for pid, result in results}), len(callbacks))
        return [result for pid, result in results]

    def test_concurrent_approvals_do_not_double_publish(self):
        from events.models import OutboxEvent
        from moderation.models import ModerationDecision
        self.assertEqual(connection.vendor, "postgresql")
        revision = self.submit()
        results = self.race(lambda: self.approve(revision).pk, lambda: self.approve(revision).pk)
        self.assertEqual(results, [revision.pk, revision.pk])
        self.assertEqual(OutboxEvent.objects.count(), 1)
        self.assertEqual(ModerationDecision.objects.count(), 1)
        revision.listing.refresh_from_db()
        self.assertEqual(revision.listing.public_revision_id, revision.pk)

    def test_concurrent_stale_screen_and_correct_approval(self):
        from listings.publication import StalePublicRevision
        public = self.publish()
        revision = self.submit(self.edit(public, price="900"))

        def stale():
            try:
                return self.approve(revision).pk
            except StalePublicRevision:
                return "stale"

        results = self.race(stale, lambda: self.approve(revision, expected=public.pk).pk)
        self.assertIn(results[0], ("stale", revision.pk))
        self.assertEqual(results[1], revision.pk)
        from events.models import OutboxEvent
        self.assertEqual(OutboxEvent.objects.filter(revision=revision).count(), 2)

    def test_concurrent_withdrawal_and_approval_have_one_terminal_decision(self):
        from moderation.models import ModerationDecision
        revision = self.submit()

        def approve():
            try:
                return self.approve(revision).status
            except InvalidRevisionState:
                return "blocked"

        def withdraw():
            try:
                return self.call("withdraw_revision", actor=self.owner, revision_id=revision.pk).status
            except InvalidRevisionState:
                return "blocked"

        results = self.race(approve, withdraw)
        revision.refresh_from_db()
        self.assertIn(revision.status, ("approved", "withdrawn"))
        self.assertEqual(results.count("blocked"), 1)
        self.assertEqual(ModerationDecision.objects.count(), int(revision.status == "approved"))
        revision.listing.refresh_from_db()
        self.assertEqual(revision.listing.public_revision_id, revision.pk if revision.status == "approved" else None)

    def test_concurrent_old_replay_cannot_roll_back_future_publication(self):
        public = self.publish()
        revision = self.submit(self.edit(public, title="Yeni"))

        def old_replay():
            try:
                return self.approve(public).pk
            except InvalidRevisionState:
                return "blocked"

        self.race(old_replay, lambda: self.approve(revision, expected=public.pk).pk)
        public.listing.refresh_from_db()
        self.assertEqual(public.listing.public_revision_id, revision.pk)
        from events.models import OutboxEvent
        self.assertEqual(OutboxEvent.objects.filter(event_type="listing.revision_published").count(), 2)
