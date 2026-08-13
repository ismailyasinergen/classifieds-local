from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing, SavedSearch
from listings.saved_search_notifications import (
    build_saved_search_match_preview,
    get_saved_search_matching_queryset,
    _listing_url_for_email,
)


class SavedSearchNotificationMatcherTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="saved-search-matcher-buyer-v81@classifieds.local",
            username="saved_search_matcher_buyer_v81",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            email="saved-search-matcher-seller-v81@classifieds.local",
            username="saved_search_matcher_seller_v81",
            password="Testpass12345",
        )
        self.vehicles = Category.objects.create(name="Vehicles", slug="vehicles")
        self.cars = Category.objects.create(name="Cars", slug="cars", parent=self.vehicles)

    def _listing(
        self,
        title,
        *,
        brand="Toyota",
        year="2020",
        km="45000",
        price="950000.00",
        status=Listing.Status.APPROVED,
        created_delta=timedelta(minutes=0),
        expires_delta=timedelta(days=30),
    ):
        listing = Listing.objects.create(
            title=title,
            description="Temporary v81 matcher listing.",
            price=Decimal(price),
            category=self.cars,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=status,
            expires_at=timezone.now() + expires_delta,
            attributes={
                "marka": brand,
                "model": "Corolla" if brand == "Toyota" else "Civic",
                "yil": year,
                "km": km,
            },
        )
        Listing.objects.filter(pk=listing.pk).update(created_at=timezone.now() + created_delta)
        listing.refresh_from_db()
        return listing

    def _saved_search(self, *, checked_delta=timedelta(days=-1), enabled=True):
        return SavedSearch.objects.create(
            user=self.buyer,
            name="V81 Toyota matcher",
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
            email_notifications_enabled=enabled,
            last_notification_checked_at=timezone.now() + checked_delta,
        )

    def test_saved_search_matcher_finds_only_new_approved_matching_listings(self):
        saved_search = self._saved_search()

        match = self._listing("V81 Toyota Corolla match")
        self._listing("V81 Honda Civic wrong brand", brand="Honda")
        self._listing("V81 Toyota too old", created_delta=timedelta(days=-2))
        self._listing("V81 Toyota pending", status=Listing.Status.PENDING)
        self._listing("V81 Toyota expired", expires_delta=timedelta(days=-1))
        self._listing("V81 Toyota too expensive", price="1200000.00")
        self._listing("V81 Toyota too much km", km="80000")

        matches = list(get_saved_search_matching_queryset(saved_search))

        self.assertEqual(matches, [match])

    def test_match_preview_reports_count_and_limited_listing_list(self):
        saved_search = self._saved_search()
        self._listing("V81 Toyota match one")
        self._listing("V81 Toyota match two")

        preview = build_saved_search_match_preview(saved_search, limit=1)

        self.assertEqual(preview.match_count, 2)
        self.assertEqual(len(preview.listings), 1)
        self.assertEqual(preview.saved_search, saved_search)

    def test_management_command_previews_without_sending_or_marking_checked_by_default(self):
        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at
        self._listing("V81 Toyota command match")

        output = StringIO()
        call_command("check_saved_search_notifications", stdout=output)

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("V81 Toyota command match", text)
        self.assertIn("1 new matching approved listing", text)
        self.assertIn("No emails were sent", text)
        self.assertEqual(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_management_command_can_mark_search_checked(self):
        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at
        self._listing("V81 Toyota mark checked match")

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--saved-search-id",
            str(saved_search.pk),
            "--mark-checked",
            stdout=output,
        )

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("Marked checked", text)
        self.assertGreater(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_management_command_ignores_disabled_saved_searches(self):
        self._saved_search(enabled=False)
        self._listing("V81 Toyota disabled should not show")

        output = StringIO()
        call_command("check_saved_search_notifications", stdout=output)

        self.assertIn("No enabled saved searches found", output.getvalue())
        self.assertNotIn("V81 Toyota disabled should not show", output.getvalue())

# SAVED_SEARCH_EMAIL_DELIVERY_SKELETON_V82_TESTS
class SavedSearchEmailDeliverySkeletonTests(SavedSearchNotificationMatcherTests):
    def test_build_saved_search_email_message_contains_safe_delivery_details(self):
        from django.test import override_settings

        from listings.saved_search_notifications import build_saved_search_email_message

        saved_search = self._saved_search()
        self._listing("V82 Toyota email body match")

        preview = build_saved_search_match_preview(saved_search, limit=5)

        with override_settings(DEFAULT_FROM_EMAIL="alerts@classifieds.local"):
            message = build_saved_search_email_message(
                preview,
                site_base_url="https://classifieds.local",
            )

        self.assertEqual(message.to, [self.buyer.email])
        self.assertEqual(message.from_email, "alerts@classifieds.local")
        self.assertIn("1 new listing", message.subject)
        self.assertIn("V81 Toyota matcher", message.subject)
        self.assertIn("V82 Toyota email body match", message.body)
        self.assertIn("https://classifieds.local", message.body)
        self.assertIn("disable email alerts", message.body)

    def test_send_saved_search_match_email_uses_django_mail_backend(self):
        from django.core import mail
        from django.test import override_settings

        from listings.saved_search_notifications import send_saved_search_match_email

        saved_search = self._saved_search()
        self._listing("V82 Toyota send helper match")

        preview = build_saved_search_match_preview(saved_search, limit=5)

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="alerts@classifieds.local",
        ):
            sent_count = send_saved_search_match_email(
                preview,
                site_base_url="https://classifieds.local",
            )

        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.buyer.email])
        self.assertIn("V82 Toyota send helper match", mail.outbox[0].body)

    def test_management_command_dry_run_does_not_send_or_mark_sent(self):
        from django.core import mail
        from django.test import override_settings

        saved_search = self._saved_search()
        self._listing("V82 Toyota dry run command match")

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="alerts@classifieds.local",
        ):
            output = StringIO()
            call_command(
                "check_saved_search_notifications",
                "--saved-search-id",
                str(saved_search.pk),
                "--site-base-url",
                "https://classifieds.local",
                stdout=output,
            )

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("Dry run: email not sent", text)
        self.assertIn("No emails were sent. Pass --send to send", text)
        self.assertIn("Email subject:", text)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_management_command_send_sends_email_and_updates_notification_timestamps(self):
        from django.core import mail
        from django.test import override_settings

        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at
        self._listing("V82 Toyota send command match")

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="alerts@classifieds.local",
        ):
            output = StringIO()
            call_command(
                "check_saved_search_notifications",
                "--saved-search-id",
                str(saved_search.pk),
                "--send",
                "--site-base-url",
                "https://classifieds.local",
                stdout=output,
            )

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("Email sent and notification timestamps updated", text)
        self.assertIn("1 email(s) sent", text)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("V82 Toyota send command match", mail.outbox[0].body)
        self.assertGreater(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNotNone(saved_search.last_notification_sent_at)
        self.assertEqual(
            saved_search.last_notification_checked_at,
            saved_search.last_notification_sent_at,
        )

# SAVED_SEARCH_NOTIFICATION_OPERATIONAL_HARDENING_V83_TESTS
class SavedSearchNotificationOperationalHardeningTests(SavedSearchNotificationMatcherTests):
    def test_command_skips_zero_match_search_without_marking_checked(self):
        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--saved-search-id",
            str(saved_search.pk),
            "--mark-checked",
            stdout=output,
        )

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("0 new matching approved listing", text)
        self.assertIn("No new matches; email skipped and timestamps unchanged", text)
        self.assertIn("--mark-checked skipped because there were no matches", text)
        self.assertIn("1 zero-match search(es) skipped", text)
        self.assertEqual(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_send_skips_zero_match_search_without_email_or_timestamp_update(self):
        from django.core import mail
        from django.test import override_settings

        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="alerts@classifieds.local",
        ):
            output = StringIO()
            call_command(
                "check_saved_search_notifications",
                "--saved-search-id",
                str(saved_search.pk),
                "--send",
                stdout=output,
            )

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("No new matches; email skipped and timestamps unchanged", text)
        self.assertIn("0 email(s) sent", text)
        self.assertIn("1 zero-match search(es) skipped", text)
        self.assertEqual(len(getattr(mail, "outbox", [])), 0)
        self.assertEqual(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_command_reports_multiple_saved_searches_with_mixed_results(self):
        from django.core import mail
        from django.test import override_settings

        matching_search = self._saved_search()
        zero_match_search = SavedSearch.objects.create(
            user=self.buyer,
            name="V83 Honda zero matcher",
            path=reverse("listings:listing_list"),
            query_params={
                "category": "cars",
                "q": "Honda",
                "min_price": "900000",
                "max_price": "1000000",
                "attr_marka": "Honda",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
            querystring=(
                "attr_km_max=50000&attr_marka=Honda&attr_yil_min=2019"
                "&category=cars&max_price=1000000&min_price=900000&q=Honda"
            ),
            email_notifications_enabled=True,
            last_notification_checked_at=timezone.now() - timedelta(days=1),
        )
        zero_original_checked_at = zero_match_search.last_notification_checked_at

        self._listing("V83 Toyota mixed command match")

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="alerts@classifieds.local",
        ):
            if hasattr(mail, "outbox"):
                mail.outbox.clear()

            output = StringIO()
            call_command(
                "check_saved_search_notifications",
                "--saved-search-id",
                str(matching_search.pk),
                "--saved-search-id",
                str(zero_match_search.pk),
                "--send",
                stdout=output,
            )

        matching_search.refresh_from_db()
        zero_match_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("Processed 2 enabled saved search(es)", text)
        self.assertIn("1 total match(es)", text)
        self.assertIn("1 email(s) sent", text)
        self.assertIn("1 zero-match search(es) skipped", text)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIsNotNone(matching_search.last_notification_sent_at)
        self.assertEqual(zero_match_search.last_notification_checked_at, zero_original_checked_at)
        self.assertIsNone(zero_match_search.last_notification_sent_at)

    def test_no_recipient_saved_search_is_skipped_without_crashing(self):
        from django.core import mail
        from django.test import override_settings

        self.buyer.email = ""
        self.buyer.save(update_fields=["email"])

        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at
        self._listing("V83 Toyota no recipient command match")

        with override_settings(
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="alerts@classifieds.local",
        ):
            output = StringIO()
            call_command(
                "check_saved_search_notifications",
                "--saved-search-id",
                str(saved_search.pk),
                "--send",
                stdout=output,
            )

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("for (no email)", text)
        self.assertIn("Email skipped: saved search user has no email address", text)
        self.assertIn("1 no-recipient search(es) skipped", text)
        self.assertIn("0 email(s) sent", text)
        self.assertEqual(len(getattr(mail, "outbox", [])), 0)
        self.assertEqual(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_email_builder_rejects_missing_recipient(self):
        from listings.saved_search_notifications import build_saved_search_email_message

        self.buyer.email = ""
        self.buyer.save(update_fields=["email"])

        saved_search = self._saved_search()
        self._listing("V83 Toyota no recipient builder match")

        preview = build_saved_search_match_preview(saved_search, limit=5)

        with self.assertRaisesMessage(ValueError, "no email address"):
            build_saved_search_email_message(preview)

    def test_listing_url_for_email_handles_get_absolute_url_exception(self):
        from unittest.mock import patch

        listing = self._listing("V83 Toyota error handling test")

        with patch.object(Listing, 'get_absolute_url', side_effect=Exception("Simulated error")):
            url = _listing_url_for_email(listing, site_base_url="https://classifieds.local")
            self.assertEqual(url, f"https://classifieds.local/listings/{listing.pk}/")
