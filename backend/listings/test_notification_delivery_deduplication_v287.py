from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import (
    Listing,
    ListingPriceAlert,
    NotificationDeliveryEvent,
    SavedSearch,
)
from listings.notification_delivery_deduplication_v287 import (
    NOTIFICATION_EVENT_MAX_ATTEMPTS_V287,
    NOTIFICATION_EVENT_STALE_AFTER_V287,
    NotificationEventSpecV287,
    build_listing_price_alert_event_specs_v287,
    build_notification_event_key_v287,
    build_saved_search_event_specs_v287,
    claim_notification_events_v287,
    mark_notification_events_failed_v287,
    mark_notification_events_sent_v287,
)
from listings.saved_search_notification_email_sender import (
    send_saved_search_notification_email,
)
from listings.saved_search_notifications import build_saved_search_match_preview


class NotificationDeliveryDeduplicationV287Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            username="v287-buyer",
            email="v287-buyer@classifieds.local",
            password="Testpass12345",
        )
        self.other_buyer = User.objects.create_user(
            username="v287-other-buyer",
            email="v287-other@classifieds.local",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            username="v287-seller",
            email="v287-seller@classifieds.local",
            password="Testpass12345",
        )
        self.category = Category.objects.create(name="V287", slug="v287")
        self.listing = self._listing("V287 listing")

    def _listing(self, title, *, price="100.00", created_days_ago=0):
        listing = Listing.objects.create(
            title=title,
            description="V287 notification event fixture.",
            price=Decimal(price),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )
        if created_days_ago:
            Listing.objects.filter(pk=listing.pk).update(
                created_at=timezone.now() - timedelta(days=created_days_ago)
            )
            listing.refresh_from_db()
        return listing

    def _reduce(self, listing, price):
        listing.price = Decimal(price)
        listing.save(update_fields=["price"])
        listing.refresh_from_db()

    def _alert(self, listing=None, user=None):
        listing = listing or self.listing
        return ListingPriceAlert.objects.create(
            user=user or self.buyer,
            listing=listing,
            baseline_price=listing.price,
        )

    def _saved_search(self, *, user=None, params=None, enabled=True):
        params = params or {"q": "V287"}
        return SavedSearch.objects.create(
            user=user or self.buyer,
            name="V287 saved search",
            path=reverse("listings:listing_list"),
            query_params=params,
            querystring="&".join(
                f"{key}={value}" for key, value in sorted(params.items())
            ),
            email_notifications_enabled=enabled,
            last_notification_checked_at=timezone.now() - timedelta(days=1),
        )

    def _alert_spec(self, alert):
        return build_listing_price_alert_event_specs_v287([alert])[0]

    def test_event_key_is_deterministic_and_scoped_to_logical_identity(self):
        values = {
            "notification_type": "saved_search_new_listing",
            "recipient_id": self.buyer.pk,
            "listing_id": self.listing.pk,
            "saved_search_id": 41,
        }
        first = build_notification_event_key_v287(**values)
        replay = build_notification_event_key_v287(**values)
        other = build_notification_event_key_v287(
            **{**values, "saved_search_id": 42}
        )

        self.assertEqual(first, replay)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, other)

    def test_database_uniqueness_and_two_claims_allow_one_sendable_event(self):
        alert = self._alert()
        self._reduce(self.listing, "80.00")
        spec = self._alert_spec(alert)

        first = claim_notification_events_v287([spec])
        second = claim_notification_events_v287([spec])

        self.assertEqual(len(first.claimed_keys), 1)
        self.assertEqual(len(second.claimed_keys), 0)
        self.assertEqual(len(second.busy_keys), 1)
        self.assertEqual(NotificationDeliveryEvent.objects.count(), 1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                NotificationDeliveryEvent.objects.create(
                    recipient=self.buyer,
                    listing=self.listing,
                    notification_type="listing_price_drop",
                    event_key=spec.event_key,
                )

    def test_sent_event_is_permanent_and_failed_event_retries_with_attempt_count(self):
        alert = self._alert()
        self._reduce(self.listing, "80.00")
        spec = self._alert_spec(alert)
        first = claim_notification_events_v287([spec])
        mark_notification_events_failed_v287(
            first,
            error_category="SMTP timeout details are not stored",
        )

        retry = claim_notification_events_v287([spec])
        self.assertEqual(len(retry.claimed_keys), 1)
        event = NotificationDeliveryEvent.objects.get()
        self.assertEqual(event.attempt_count, 2)
        self.assertEqual(event.last_error_category, "")

        mark_notification_events_sent_v287(retry)
        replay = claim_notification_events_v287([spec])
        event.refresh_from_db()
        self.assertEqual(event.status, NotificationDeliveryEvent.Status.SENT)
        self.assertEqual(len(replay.duplicate_keys), 1)
        self.assertEqual(event.attempt_count, 2)

    def test_retry_count_is_bounded(self):
        alert = self._alert()
        self._reduce(self.listing, "80.00")
        spec = self._alert_spec(alert)

        for _index in range(NOTIFICATION_EVENT_MAX_ATTEMPTS_V287):
            claim = claim_notification_events_v287([spec])
            self.assertEqual(len(claim.claimed_keys), 1)
            mark_notification_events_failed_v287(
                claim,
                error_category="BackendError",
            )

        exhausted = claim_notification_events_v287([spec])
        event = NotificationDeliveryEvent.objects.get()
        self.assertEqual(len(exhausted.exhausted_keys), 1)
        self.assertEqual(
            event.attempt_count,
            NOTIFICATION_EVENT_MAX_ATTEMPTS_V287,
        )
        self.assertEqual(event.last_error_category, "BackendError")

    def test_stale_processing_claim_is_recovered(self):
        alert = self._alert()
        self._reduce(self.listing, "80.00")
        spec = self._alert_spec(alert)
        old_now = timezone.now() - NOTIFICATION_EVENT_STALE_AFTER_V287 - timedelta(seconds=1)
        first = claim_notification_events_v287([spec], now=old_now)

        recovered = claim_notification_events_v287([spec], now=timezone.now())

        self.assertEqual(len(first.claimed_keys), 1)
        self.assertEqual(len(recovered.claimed_keys), 1)
        event = NotificationDeliveryEvent.objects.get()
        self.assertEqual(event.attempt_count, 2)
        self.assertEqual(event.claim_token, recovered.claim_token)

    def test_listing_alert_command_dry_run_creates_no_event(self):
        self._alert()
        self._reduce(self.listing, "80.00")

        call_command("check_listing_price_alerts", stdout=StringIO())

        self.assertFalse(NotificationDeliveryEvent.objects.exists())

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="alerts@classifieds.local",
    )
    def test_listing_alert_duplicate_is_suppressed_and_later_reduction_sends(self):
        alert = self._alert()
        self._reduce(self.listing, "80.00")

        call_command("check_listing_price_alerts", "--send", stdout=StringIO())
        alert.last_notified_price = None
        alert.save(update_fields=["last_notified_price"])
        duplicate_output = StringIO()
        call_command(
            "check_listing_price_alerts",
            "--send",
            stdout=duplicate_output,
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(NotificationDeliveryEvent.objects.count(), 1)
        self.assertIn("1 duplicates suppressed", duplicate_output.getvalue())

        self._reduce(self.listing, "70.00")
        call_command("check_listing_price_alerts", "--send", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            NotificationDeliveryEvent.objects.filter(status="sent").count(),
            2,
        )

    def test_latest_increase_creates_no_listing_price_drop_event(self):
        self._alert()
        self._reduce(self.listing, "70.00")
        self._reduce(self.listing, "80.00")

        call_command("check_listing_price_alerts", "--send", stdout=StringIO())

        self.assertFalse(NotificationDeliveryEvent.objects.exists())

    def test_missing_recipient_is_skipped_without_sent_state_or_retry(self):
        self.buyer.email = ""
        self.buyer.save(update_fields=["email"])
        alert = self._alert()
        self._reduce(self.listing, "80.00")

        call_command("check_listing_price_alerts", "--send", stdout=StringIO())
        call_command("check_listing_price_alerts", "--send", stdout=StringIO())

        event = NotificationDeliveryEvent.objects.get()
        alert.refresh_from_db()
        self.assertEqual(event.status, NotificationDeliveryEvent.Status.SKIPPED)
        self.assertEqual(event.last_error_category, "missing_recipient")
        self.assertIsNone(event.sent_at)
        self.assertIsNone(alert.last_notified_price)
        self.assertEqual(event.attempt_count, 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="alerts@classifieds.local",
    )
    def test_saved_search_new_listing_and_price_drop_events_are_independently_deduped(self):
        ordinary = self._saved_search()
        price_listing = self._listing(
            "V287 price candidate",
            price="100.00",
            created_days_ago=10,
        )
        price_search = self._saved_search(params={"price_drops": "1"})
        self._reduce(price_listing, "80.00")

        call_command("check_saved_search_notifications", "--send", stdout=StringIO())
        first_count = len(mail.outbox)
        Listing.objects.filter(pk=self.listing.pk).update(
            created_at=timezone.now()
        )
        ordinary.last_notification_checked_at = timezone.now() - timedelta(days=1)
        ordinary.save(update_fields=["last_notification_checked_at"])
        price_search.last_notification_checked_at = timezone.now() - timedelta(days=1)
        price_search.save(update_fields=["last_notification_checked_at"])
        call_command("check_saved_search_notifications", "--send", stdout=StringIO())

        self.assertEqual(first_count, 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(
            set(NotificationDeliveryEvent.objects.values_list("notification_type", flat=True)),
            {"saved_search_new_listing", "saved_search_price_drop"},
        )

    def test_multiple_searches_and_users_get_distinct_event_identities(self):
        first = self._saved_search()
        second = self._saved_search()
        other = self._saved_search(user=self.other_buyer)
        previews = [
            build_saved_search_match_preview(search)
            for search in (first, second, other)
        ]

        keys = {
            build_saved_search_event_specs_v287(preview)[0].event_key
            for preview in previews
        }

        self.assertEqual(len(keys), 3)

    def test_one_listing_alert_failure_does_not_block_another(self):
        first = self._alert()
        self._reduce(self.listing, "80.00")
        other_listing = self._listing("V287 succeeds")
        self._alert(other_listing)
        self._reduce(other_listing, "70.00")

        def send_one(alert, **_kwargs):
            if alert.pk == first.pk:
                raise RuntimeError("simulated")
            return 1

        with patch(
            "listings.management.commands.check_listing_price_alerts.send_listing_price_alert_v285",
            side_effect=send_one,
        ):
            call_command("check_listing_price_alerts", "--send", stdout=StringIO())

        self.assertEqual(
            set(NotificationDeliveryEvent.objects.values_list("status", flat=True)),
            {NotificationDeliveryEvent.Status.FAILED, NotificationDeliveryEvent.Status.SENT},
        )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_mature_saved_search_sender_suppresses_replayed_listing(self):
        saved_search = self._saved_search()
        preview = build_saved_search_match_preview(saved_search)

        first = send_saved_search_notification_email(
            saved_search,
            match_count=preview.match_count,
            matching_listings=preview.listings,
            execute_send=True,
        )
        second = send_saved_search_notification_email(
            saved_search,
            match_count=preview.match_count,
            matching_listings=preview.listings,
            execute_send=True,
        )

        self.assertEqual(first["delivered_count"], 1)
        self.assertEqual(second["delivered_count"], 0)
        self.assertEqual(second["duplicates_suppressed"], 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_batch_claim_query_count_is_constant(self):
        alerts = []
        for index in range(5):
            listing = self._listing(f"V287 query {index}")
            alerts.append(self._alert(listing))
            self._reduce(listing, "50.00")
        specs = build_listing_price_alert_event_specs_v287(alerts)

        with CaptureQueriesContext(connection) as captured:
            claim = claim_notification_events_v287(specs)

        self.assertEqual(len(claim.claimed_keys), 5)
        self.assertLessEqual(len(captured), 4)

    def test_admin_is_staff_only_and_no_public_event_url_exists(self):
        changelist = reverse("admin:listings_notificationdeliveryevent_changelist")
        response = self.client.get(changelist)
        self.assertEqual(response.status_code, 302)

        self.client.force_login(self.buyer)
        response = self.client.get(changelist)
        self.assertEqual(response.status_code, 302)

        staff = get_user_model().objects.create_superuser(
            username="v287-staff",
            email="v287-staff@classifieds.local",
            password="Testpass12345",
        )
        self.client.force_login(staff)
        self.assertEqual(self.client.get(changelist).status_code, 200)

        urls_text = open("/app/listings/urls.py", encoding="utf-8").read()
        self.assertNotIn("NotificationDeliveryEvent", urls_text)

    def test_command_output_does_not_print_recipient_address(self):
        saved_search = self._saved_search()
        output = StringIO()

        call_command(
            "check_saved_search_notifications",
            "--saved-search-id",
            str(saved_search.pk),
            stdout=output,
        )

        self.assertNotIn(self.buyer.email, output.getvalue())


class NotificationDeliveryClaimConcurrencyV287Tests(TransactionTestCase):
    reset_sequences = True

    def test_concurrent_workers_claim_one_logical_event_once(self):
        User = get_user_model()
        buyer = User.objects.create_user(username="v287-race-buyer")
        seller = User.objects.create_user(username="v287-race-seller")
        category = Category.objects.create(name="V287 race", slug="v287-race")
        listing = Listing.objects.create(
            title="V287 race listing",
            description="Concurrent claim fixture.",
            price=Decimal("80.00"),
            category=category,
            owner=seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
        )
        key = build_notification_event_key_v287(
            notification_type="saved_search_new_listing",
            recipient_id=buyer.pk,
            listing_id=listing.pk,
            saved_search_id=91,
        )
        spec = NotificationEventSpecV287(
            notification_type="saved_search_new_listing",
            recipient_id=buyer.pk,
            listing_id=listing.pk,
            saved_search_id=None,
            event_key=key,
        )
        barrier = Barrier(2)

        def claim_once():
            close_old_connections()
            barrier.wait()
            result = claim_notification_events_v287([spec])
            close_old_connections()
            return len(result.claimed_keys)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _index: claim_once(), range(2)))

        self.assertEqual(sum(results), 1)
        event = NotificationDeliveryEvent.objects.get(event_key=key)
        self.assertEqual(event.attempt_count, 1)
        self.assertEqual(event.status, NotificationDeliveryEvent.Status.PROCESSING)
