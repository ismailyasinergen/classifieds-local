# SAVED_SEARCH_NOTIFICATION_OBSERVABILITY_V85_TESTS
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing, SavedSearch


class SavedSearchNotificationObservabilityTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="v85-observability-buyer@classifieds.local",
            username="v85_observability_buyer",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            email="v85-observability-seller@classifieds.local",
            username="v85_observability_seller",
            password="Testpass12345",
        )
        self.vehicles = Category.objects.create(name="Vehicles", slug="vehicles")
        self.cars = Category.objects.create(name="Cars", slug="cars", parent=self.vehicles)

    def _saved_search(self, name):
        return SavedSearch.objects.create(
            user=self.buyer,
            name=name,
            path=reverse("listings:listing_list"),
            query_params={
                "category": "cars",
                "q": "Toyota",
                "min_price": "900000",
                "max_price": "1000000",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
            querystring=(
                "attr_km_max=50000&attr_marka=Toyota&attr_yil_min=2019"
                "&category=cars&max_price=1000000&min_price=900000&q=Toyota"
            ),
            email_notifications_enabled=True,
            last_notification_checked_at=timezone.now() - timedelta(days=1),
        )

    def _listing(self, title):
        return Listing.objects.create(
            title=title,
            description="Temporary v85 observability test listing.",
            price=Decimal("950000.00"),
            category=self.cars,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes={
                "marka": "Toyota",
                "model": "Corolla",
                "yil": "2020",
                "km": "45000",
            },
        )

    def test_send_failure_is_reported_and_does_not_mark_failed_search_sent(self):
        failed_search = self._saved_search("V85 failed send")
        self._listing("V85 Toyota failure-only match")

        original_checked_at = failed_search.last_notification_checked_at

        def failing_send(preview, from_email=None, site_base_url=None):
            raise RuntimeError("SMTP temporarily unavailable")

        output = StringIO()
        with patch(
            "listings.management.commands.check_saved_search_notifications.send_saved_search_match_email",
            side_effect=failing_send,
        ):
            call_command(
                "check_saved_search_notifications",
                "--saved-search-id",
                str(failed_search.pk),
                "--send",
                stdout=output,
            )

        failed_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("Email send failed for saved search", text)
        self.assertIn("RuntimeError: SMTP temporarily unavailable", text)
        self.assertIn("Timestamps were not updated for this saved search", text)
        self.assertIn("0 email(s) sent", text)
        self.assertIn("1 email failure(s)", text)
        self.assertIn(f"Failed saved search ID(s): {failed_search.pk}", text)
        self.assertEqual(failed_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(failed_search.last_notification_sent_at)

    def test_one_failed_send_does_not_stop_later_saved_searches(self):
        failed_search = self._saved_search("V85 failed send in batch")
        successful_search = self._saved_search("V85 successful send in batch")
        self._listing("V85 Toyota batch failure isolation match")

        failed_original_checked_at = failed_search.last_notification_checked_at
        successful_original_checked_at = successful_search.last_notification_checked_at

        send_calls = []

        def mixed_send(preview, from_email=None, site_base_url=None):
            send_calls.append(preview.saved_search.pk)
            if preview.saved_search.pk == failed_search.pk:
                raise RuntimeError("First send failed")
            return 1

        output = StringIO()
        with patch(
            "listings.management.commands.check_saved_search_notifications.send_saved_search_match_email",
            side_effect=mixed_send,
        ):
            call_command(
                "check_saved_search_notifications",
                "--saved-search-id",
                str(failed_search.pk),
                "--saved-search-id",
                str(successful_search.pk),
                "--send",
                stdout=output,
            )

        failed_search.refresh_from_db()
        successful_search.refresh_from_db()
        text = output.getvalue()

        self.assertEqual(send_calls, [failed_search.pk, successful_search.pk])
        self.assertIn("Processed 2 enabled saved search(es)", text)
        self.assertIn("1 email(s) sent", text)
        self.assertIn("1 email failure(s)", text)
        self.assertIn(f"Failed saved search ID(s): {failed_search.pk}", text)
        self.assertEqual(failed_search.last_notification_checked_at, failed_original_checked_at)
        self.assertIsNone(failed_search.last_notification_sent_at)
        self.assertGreater(successful_search.last_notification_checked_at, successful_original_checked_at)
        self.assertIsNotNone(successful_search.last_notification_sent_at)
