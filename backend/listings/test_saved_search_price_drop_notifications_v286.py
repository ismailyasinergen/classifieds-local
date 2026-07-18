from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing, ListingPriceHistory, SavedSearch
from listings.saved_search_notifications import (
    build_saved_search_match_preview,
    get_saved_search_matching_queryset,
)


class SavedSearchPriceDropNotificationsV286Tests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            username="v286-buyer",
            email="v286-buyer@classifieds.local",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            username="v286-seller",
            email="v286-seller@classifieds.local",
            password="Testpass12345",
        )
        self.category = Category.objects.create(
            name="V286 cars",
            slug="cars",
        )
        self.checked_since = timezone.now() - timedelta(hours=2)

    def _listing(
        self,
        title="V286 Toyota price drop",
        *,
        price="100.00",
        created_days_ago=10,
        location="Berlin Mitte",
        status=Listing.Status.APPROVED,
    ):
        listing = Listing.objects.create(
            title=title,
            description="Toyota notification fixture.",
            price=Decimal(price),
            category=self.category,
            owner=self.seller,
            location=location,
            status=status,
            expires_at=timezone.now() + timedelta(days=30),
            attributes={"marka": "Toyota"},
        )
        Listing.objects.filter(pk=listing.pk).update(
            created_at=timezone.now() - timedelta(days=created_days_ago)
        )
        listing.refresh_from_db()
        return listing

    def _saved_search(self, params, *, checked_since=None):
        return SavedSearch.objects.create(
            user=self.buyer,
            name="V286 price drop search",
            path=reverse("listings:listing_list"),
            query_params=params,
            querystring="&".join(
                f"{key}={value}" for key, value in sorted(params.items())
            ),
            email_notifications_enabled=True,
            last_notification_checked_at=checked_since or self.checked_since,
        )

    def _reduce(self, listing, new_price="80.00"):
        listing.price = Decimal(new_price)
        listing.save(update_fields=["price"])
        listing.refresh_from_db()

    def test_old_listing_with_new_current_reduction_matches_price_drop_search(self):
        listing = self._listing()
        saved_search = self._saved_search({"price_drops": "1"})
        self._reduce(listing)

        preview = build_saved_search_match_preview(saved_search)

        self.assertEqual(preview.listings, [listing])
        self.assertEqual(preview.match_count, 1)
        self.assertTrue(preview.includes_price_drops)

    def test_ordinary_search_remains_creation_based(self):
        listing = self._listing()
        ordinary = self._saved_search({"q": "Toyota", "sort": "price_low"})
        self._reduce(listing)

        preview = build_saved_search_match_preview(ordinary)

        self.assertEqual(preview.match_count, 0)
        self.assertFalse(preview.includes_price_drops)

    def test_each_canonical_price_drop_parameter_activates_reduction_activity(self):
        listing = self._listing()
        self._reduce(listing)
        cases = [
            {"price_drops": "1"},
            {"price_drop_period": "24h"},
            {"price_drop_period": "7d"},
            {"price_drop_period": "30d"},
            {"min_price_drop_amount": "20"},
            {"min_price_drop_percent": "20"},
            {"sort": "recent_price_drop"},
            {"sort": "biggest_price_drop"},
        ]

        for index, params in enumerate(cases):
            with self.subTest(params=params):
                saved_search = self._saved_search(params)
                matches = list(get_saved_search_matching_queryset(saved_search))
                self.assertEqual(matches, [listing], msg=f"case {index}")

    def test_watermark_period_and_invalid_values_are_enforced(self):
        listing = self._listing()
        self._reduce(listing)
        transition = ListingPriceHistory.objects.filter(
            listing=listing,
            previous_price__isnull=False,
        ).latest("pk")
        old_time = timezone.now() - timedelta(days=8)
        ListingPriceHistory.objects.filter(pk=transition.pk).update(
            changed_at=old_time
        )

        before_watermark = self._saved_search(
            {"price_drops": "1"},
            checked_since=old_time,
        )
        period = self._saved_search(
            {"price_drop_period": "7d"},
            checked_since=timezone.now() - timedelta(days=30),
        )
        invalid = self._saved_search(
            {
                "price_drop_period": "forever",
                "min_price_drop_amount": "NaN",
                "sort": "price_low",
            },
            checked_since=timezone.now() - timedelta(days=9),
        )

        self.assertEqual(
            build_saved_search_match_preview(before_watermark).match_count,
            0,
        )
        self.assertEqual(build_saved_search_match_preview(period).match_count, 0)
        invalid_preview = build_saved_search_match_preview(invalid)
        self.assertEqual(invalid_preview.match_count, 0)
        self.assertFalse(invalid_preview.includes_price_drops)

    def test_stale_mismatch_later_increase_and_nonpublic_state_are_excluded(self):
        stale = self._listing("V286 stale Toyota")
        self._reduce(stale, "80.00")
        Listing.objects.filter(pk=stale.pk).update(price=Decimal("70.00"))

        increased = self._listing("V286 increased Toyota")
        self._reduce(increased, "70.00")
        self._reduce(increased, "80.00")

        pending = self._listing("V286 pending Toyota")
        self._reduce(pending, "60.00")
        Listing.objects.filter(pk=pending.pk).update(status=Listing.Status.PENDING)

        saved_search = self._saved_search({"price_drops": "1"})

        self.assertEqual(
            list(get_saved_search_matching_queryset(saved_search)),
            [],
        )

    def test_shared_base_attribute_threshold_and_sort_filters_combine(self):
        match = self._listing(price="120.00")
        self._reduce(match, "80.00")
        wrong_location = self._listing(
            "V286 Toyota wrong location",
            price="120.00",
            location="Hamburg",
        )
        self._reduce(wrong_location, "80.00")

        saved_search = self._saved_search(
            {
                "q": "Toyota",
                "location": "Berlin",
                "category": self.category.slug,
                "min_price": "70",
                "max_price": "90",
                "attr_marka": "Toyota",
                "min_price_drop_amount": "40",
                "min_price_drop_percent": "30",
                "sort": "biggest_price_drop",
            }
        )

        self.assertEqual(
            list(get_saved_search_matching_queryset(saved_search)),
            [match],
        )

    def test_price_drop_email_copy_and_successful_watermark_prevent_repeat(self):
        listing = self._listing()
        saved_search = self._saved_search({"price_drops": "1"})
        self._reduce(listing)

        preview = build_saved_search_match_preview(saved_search)
        self.assertTrue(preview.includes_price_drops)

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

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("new or newly reduced listing", mail.outbox[0].subject)
        self.assertIn("new or newly reduced listing", mail.outbox[0].body)
        self.assertIn("new or newly reduced", output.getvalue())

        saved_search.refresh_from_db()
        self.assertIsNotNone(saved_search.last_notification_checked_at)
        self.assertEqual(
            build_saved_search_match_preview(saved_search).match_count,
            0,
        )

    def test_new_listing_matching_price_drop_search_is_not_duplicated(self):
        listing = self._listing(created_days_ago=0, price="120.00")
        Listing.objects.filter(pk=listing.pk).update(
            created_at=timezone.now(),
        )
        listing.refresh_from_db()
        saved_search = self._saved_search({"price_drops": "1"})
        self._reduce(listing, "80.00")

        preview = build_saved_search_match_preview(saved_search)

        self.assertEqual(preview.match_count, 1)
        self.assertEqual(preview.listings, [listing])

    def test_matcher_query_count_does_not_grow_with_price_history_rows(self):
        listing = self._listing(price="150.00")
        saved_search = self._saved_search({"price_drops": "1"})
        for price in ("140.00", "130.00", "120.00", "110.00", "100.00"):
            self._reduce(listing, price)

        with CaptureQueriesContext(connection) as captured:
            matches = list(get_saved_search_matching_queryset(saved_search))
            titles = [match.title for match in matches]

        self.assertEqual(titles, [listing.title])
        self.assertEqual(len(captured), 1)
