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

from django.test import SimpleTestCase
from listings.saved_search_notification_observability import (
    format_saved_search_notification_observability_lines,
    V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY,
)

class FormatSavedSearchNotificationObservabilityLinesTests(SimpleTestCase):
    def test_format_without_samples(self):
        snapshot = {
            "owner_scoped": True,
            "total_count": 10,
            "enabled_count": 5,
            "disabled_count": 5,
            "enabled_with_email_count": 3,
            "missing_recipient_email_count": 2,
            "checked_timestamp_count": 8,
            "sent_timestamp_count": 4,
            "sample_count": 0,
            "samples": []
        }
        lines = format_saved_search_notification_observability_lines(snapshot)
        self.assertEqual(len(lines), 1)
        expected_header = (
            f"{V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY} "
            f"mode=observability read_only=True delivery_enabled=False "
            f"mutation_allowed=False owner_scoped=True "
            f"total=10 enabled=5 "
            f"disabled=5 "
            f"enabled_with_email=3 "
            f"missing_recipient_email=2 "
            f"checked_timestamps=8 "
            f"sent_timestamps=4 "
            f"samples=0"
        )
        self.assertEqual(lines[0], expected_header)

    def test_format_with_samples_and_fallbacks(self):
        snapshot = {
            "owner_scoped": False,
            "total_count": 1,
            "enabled_count": 1,
            "disabled_count": 0,
            "enabled_with_email_count": 1,
            "missing_recipient_email_count": 0,
            "checked_timestamp_count": 0,
            "sent_timestamp_count": 0,
            "sample_count": 1,
            "samples": [
                {
                    "saved_search_id": 42,
                    "owner_id": 101,
                    "email_notifications_enabled": True,
                    "recipient_email": "test@example.com",
                    "last_notification_checked_at": None,
                    "last_notification_sent_at": None,
                    "label": "test_label"
                }
            ]
        }
        lines = format_saved_search_notification_observability_lines(snapshot)
        self.assertEqual(len(lines), 2)
        # Verify redact_notification_recipient_for_operator_v305 is applied by checking for the redacted form
        # We don't know the exact redaction logic, but it should contain part of the email or a redacted version.
        # It's better to just mock it or check that it's processed correctly. Actually, let's just assert the line is formatted.
        from listings.notification_recipient_output_redaction_v305 import redact_notification_recipient_for_operator_v305
        recipient_output = redact_notification_recipient_for_operator_v305("test@example.com")

        expected_sample_line = (
            "OBSERVABILITY saved_search "
            f"id=42 "
            f"owner_id=101 "
            f"enabled=True "
            f"recipient={recipient_output} "
            f"checked_at=<none> "
            f"sent_at=<none> "
            f"label=test_label"
        )
        self.assertEqual(lines[1], expected_sample_line)

    def test_format_with_samples_and_timestamps(self):
        snapshot = {
            "owner_scoped": False,
            "total_count": 1,
            "enabled_count": 1,
            "disabled_count": 0,
            "enabled_with_email_count": 1,
            "missing_recipient_email_count": 0,
            "checked_timestamp_count": 1,
            "sent_timestamp_count": 1,
            "sample_count": 1,
            "samples": [
                {
                    "saved_search_id": 43,
                    "owner_id": 102,
                    "email_notifications_enabled": False,
                    "recipient_email": "hello@world.com",
                    "last_notification_checked_at": "2023-10-01T12:00:00Z",
                    "last_notification_sent_at": "2023-10-02T12:00:00Z",
                    "label": "another_label"
                }
            ]
        }
        lines = format_saved_search_notification_observability_lines(snapshot)
        self.assertEqual(len(lines), 2)
        from listings.notification_recipient_output_redaction_v305 import redact_notification_recipient_for_operator_v305
        recipient_output = redact_notification_recipient_for_operator_v305("hello@world.com")

        expected_sample_line = (
            "OBSERVABILITY saved_search "
            f"id=43 "
            f"owner_id=102 "
            f"enabled=False "
            f"recipient={recipient_output} "
            f"checked_at=2023-10-01T12:00:00Z "
            f"sent_at=2023-10-02T12:00:00Z "
            f"label=another_label"
        )
        self.assertEqual(lines[1], expected_sample_line)
