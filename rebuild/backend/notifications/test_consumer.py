from allauth.account.models import EmailAddress
from django.http import QueryDict
from django.test import TestCase, override_settings
from listings.tests.test_publication import PublicationFixtures
from listings.search.parsing import parse_search_spec, search_spec_to_dict
from notifications.services import save_search, set_notifications
from notifications.models import NotificationDelivery
from notifications.models import SavedSearch, NotificationMatch
from notifications.consumer import consume_pending, CONSUMER
from events.models import EventConsumption, OutboxEvent, PublicationBoundary
from notifications.services import delete_search, rename_search, mark_notification
from accounts.models import User
from listings.models import Listing
from django.db import transaction, OperationalError, connections, connection
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch
from django.test import TransactionTestCase
from conversations.tests.test_rate_limit_concurrency import PostgresLimitWorkers


@override_settings(IN_APP_NOTIFICATIONS_ENABLED=True)
class ConsumerTests(PublicationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        for user in (self.owner, self.other):
            EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)

    def subscribe(self, user=None, query='q=Araba'):
        row, _ = save_search(actor=user or self.other, name='Özel arama', payload=search_spec_to_dict(parse_search_spec(QueryDict(query))))
        return set_notifications(actor=user or self.other, search_id=row.pk, enabled=True)

    def test_first_publication_produces_one_private_delivery(self):
        self.subscribe()
        self.publish()
        try:
            from notifications.consumer import consume_pending
        except ImportError:
            self.fail('Kalıcı bildirim tüketicisi henüz uygulanmadı')
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.assertEqual(NotificationDelivery.objects.get().recipient, self.other)
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_default_off_and_duplicate_save_does_not_subscribe(self):
        row, _ = save_search(actor=self.other, name='x', payload=search_spec_to_dict(parse_search_spec(QueryDict('q=Araba'))))
        self.assertFalse(row.notifications_enabled)
        self.publish()
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_overlapping_searches_one_delivery_and_two_contributions(self):
        self.subscribe()
        self.subscribe(query='currency=EUR')
        self.publish()
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.assertEqual(NotificationMatch.objects.count(), 2)

    def test_old_and_disabled_window_events_not_backfilled(self):
        self.publish()
        row = self.subscribe()
        set_notifications(actor=self.other, search_id=row.pk, enabled=False)
        self.publish()
        row2 = set_notifications(actor=self.other, search_id=row.pk, enabled=True)
        self.assertGreater(row2.notification_boundary, row.notification_boundary)
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())
        self.publish()
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_rename_keeps_period_and_stop_keeps_history(self):
        row = self.subscribe()
        rename_search(actor=self.other, search_id=row.pk, name='Yeni')
        row.refresh_from_db()
        boundary = row.notification_boundary
        self.publish()
        consume_pending()
        set_notifications(actor=self.other, search_id=row.pk, enabled=False)
        set_notifications(actor=self.other, search_id=row.pk, enabled=False)
        row.refresh_from_db()
        self.assertEqual(row.notification_boundary, boundary)
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_delete_before_delivery_and_after_delivery(self):
        row = self.subscribe()
        self.publish()
        delete_search(actor=self.other, search_id=row.pk)
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())
        row = self.subscribe()
        self.publish()
        consume_pending()
        delete_search(actor=self.other, search_id=row.pk)
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.assertIsNone(NotificationMatch.objects.get().search_id)

    def test_subsequent_revision_and_price_event_skipped(self):
        self.subscribe()
        old = self.publish()
        self.approve(self.submit(self.edit(old, price='800')), expected=old.pk)
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())
        self.assertEqual(set(EventConsumption.objects.values_list('reason', flat=True)),
                         {'superseded', 'not_first_publication', 'event_type_out_of_scope'})

    def test_legacy_and_poison_do_not_block_other_event_or_set_global_processed(self):
        self.subscribe()
        for payload in ({}, {'notification_version': 99}):
            rev = self.publish()
            OutboxEvent.objects.filter(revision=rev).update(payload=payload)
        self.publish()
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.assertEqual(EventConsumption.objects.filter(status='failed').count(), 1)
        self.assertFalse(OutboxEvent.objects.exclude(processed_at=None).exists())

    def test_noncanonical_spec_does_not_broaden_and_other_search_progresses(self):
        row = self.subscribe(query='q=wrong')
        SavedSearch.objects.filter(pk=row.pk).update(spec={'version': 999})
        self.subscribe()
        self.publish()
        consume_pending()
        row.refresh_from_db()
        self.assertEqual(row.notification_error, 'invalid_spec')
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_inactive_unverified_and_self_excluded(self):
        self.subscribe(user=self.owner)
        self.subscribe()
        self.publish()
        User.objects.filter(pk=self.other.pk).update(is_active=False)
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())
        User.objects.filter(pk=self.other.pk).update(is_active=True)
        EmailAddress.objects.filter(user=self.other).update(verified=False)
        self.publish()
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_hidden_expired_and_closed_events_are_not_delivered(self):
        self.subscribe()
        for field, value in [('lifecycle', 'paused'), ('lifecycle', 'closed'), ('expires_at', timezone.now()-timedelta(seconds=1))]:
            revision = self.publish()
            Listing.objects.filter(pk=revision.listing_id).update(**{field: value})
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_archive_survives_replay(self):
        self.subscribe()
        self.publish()
        consume_pending()
        row = NotificationDelivery.objects.get()
        mark_notification(actor=self.other, delivery_id=row.pk, archive=True)
        archived = NotificationDelivery.objects.get().archived_at
        EventConsumption.objects.update(status='pending', recipient_cursor=0)
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.get().archived_at, archived)

    def test_failure_after_insert_rolls_back_delivery_and_progress_then_retries(self):
        self.subscribe()
        self.publish()
        from notifications import consumer
        real = consumer._deliver
        def failing(*args):
            real(*args)
            raise OperationalError('PRIVATE_CANARY')
        with patch.object(consumer, '_deliver', side_effect=failing):
            consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())
        job = EventConsumption.objects.get()
        self.assertEqual((job.status, job.recipient_cursor, job.attempts, job.reason), ('retry', 0, 1, 'database_transient'))
        EventConsumption.objects.update(next_attempt_at=timezone.now()-timedelta(seconds=1))
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_bounded_retry_and_other_events_continue(self):
        self.subscribe()
        self.publish()
        for attempt in range(5):
            with patch('notifications.consumer._deliver', side_effect=OperationalError('PRIVATE_CANARY')):
                consume_pending()
            EventConsumption.objects.update(next_attempt_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(EventConsumption.objects.get().status, 'failed')
        self.assertEqual(EventConsumption.objects.get().attempts, 5)
        self.publish()
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_chunks_resume_without_marking_event_complete(self):
        self.subscribe()
        self.subscribe(user=self.owner)
        self.publish()
        with patch('notifications.consumer.RECIPIENT_BATCH', 1), patch('notifications.consumer.JOB_BATCH', 1):
            consume_pending()
            self.assertEqual(EventConsumption.objects.get().status, 'pending')
            consume_pending()
            consume_pending()
        self.assertEqual(EventConsumption.objects.get().status, 'completed')
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    @override_settings(IN_APP_NOTIFICATIONS_ENABLED=False)
    def test_disabled_task_and_consumer_do_not_write(self):
        from notifications.tasks import consume_in_app_notifications
        self.publish()
        self.assertEqual(consume_pending()['status'], 'disabled')
        self.assertEqual(consume_in_app_notifications()['status'], 'disabled')
        self.assertFalse(EventConsumption.objects.exists())

    def test_lost_broker_wakeup_is_recovered_by_scanner(self):
        self.subscribe()
        with patch('celery.app.task.Task.apply_async', side_effect=ConnectionError('not available')):
            self.publish()
        self.assertEqual(OutboxEvent.objects.count(), 1)
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_new_supported_event_is_not_delayed_by_legacy_backlog(self):
        self.subscribe()
        for _ in range(2):
            OutboxEvent.objects.create(revision=self.approved(), event_type=OutboxEvent.Type.REVISION_PUBLISHED)
        self.publish()
        with patch('notifications.consumer.JOB_BATCH', 1):
            consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_frozen_schema_turkish_decimal_currency_matching(self):
        from catalog.models import AttributeSchema
        self.subscribe(query=f'category={self.category.pk}&schema={self.schema.pk}&schema_version=1&a.area.min=82.5&currency=EUR&price_max=1234.50&q=araba')
        self.publish()
        AttributeSchema.objects.create(category=self.category, version=2, definition=self.schema.definition)
        self.publish()
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.assertEqual(SavedSearch.objects.get().spec['resolved_schemas'][0]['id'], self.schema.pk)


@override_settings(IN_APP_NOTIFICATIONS_ENABLED=True)
class ConsumerConcurrencyTests(PostgresLimitWorkers, PublicationFixtures, TransactionTestCase):
    def setUp(self):
        super().setUp()
        EmailAddress.objects.create(user=self.other, email=self.other.email, verified=True, primary=True)
        self.search, _ = save_search(actor=self.other, name='x', payload=search_spec_to_dict(parse_search_spec(QueryDict('q=Araba'))))
        set_notifications(actor=self.other, search_id=self.search.pk, enabled=True)

    def test_parallel_workers_deliver_once(self):
        self.publish()
        self.race(consume_pending, consume_pending)
        self.assertEqual(NotificationDelivery.objects.count(), 1)

    def test_reenable_serializes_after_uncommitted_publication(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from time import monotonic
        set_notifications(actor=self.other, search_id=self.search.pk, enabled=False)
        ready = Event()
        pid = []
        def enabling(backend):
            pid.append(backend)
            ready.set()
            return set_notifications(actor=self.other, search_id=self.search.pk, enabled=True).notification_boundary
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                revision = self.publish()
                event = OutboxEvent.objects.get(revision=revision)
                future = pool.submit(self.worker, enabling)
                self.assertTrue(ready.wait(5))
                waiting = False
                deadline = monotonic() + 3
                while monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute('SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s', [pid[0]])
                        row = cursor.fetchone()
                    if row and row[0] == 'Lock':
                        waiting = True
                        break
                self.assertTrue(waiting)
            _, boundary = future.result(10)
        self.assertGreater(boundary, event.payload['publication_boundary'])
        consume_pending()
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_committed_stop_wins_waiting_delivery(self):
        self.publish()
        self.ordered(lambda: set_notifications(actor=self.other, search_id=self.search.pk, enabled=False), consume_pending, [self.other.pk])
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_committed_delete_wins_waiting_delivery(self):
        self.publish()
        self.ordered(lambda: delete_search(actor=self.other, search_id=self.search.pk), consume_pending, [self.other.pk])
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_late_commit_lower_event_id_is_discovered(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        ready, release = Event(), Event()
        low = []
        def delayed(pid):
            with transaction.atomic():
                rev = self.publish()
                low.append(OutboxEvent.objects.get(revision=rev).pk)
                ready.set()
                self.assertTrue(release.wait(10))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.worker, delayed)
            self.assertTrue(ready.wait(10))
            # Legacy price event needs no publication boundary lock, commits at a higher ID.
            other = self.approved()
            high = OutboxEvent.objects.create(revision=other, event_type=OutboxEvent.Type.PRICE_CHANGED)
            self.assertGreater(high.pk, low[0])
            consume_pending()
            self.assertFalse(NotificationDelivery.objects.exists())
            release.set()
            future.result(15)
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)
        self.assertEqual(NotificationDelivery.objects.get().recipient, self.other)
        consume_pending()
        self.assertEqual(NotificationDelivery.objects.count(), 1)
