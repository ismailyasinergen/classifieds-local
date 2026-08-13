from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from .listing_price_drop_period_filter_v280 import (
    annotate_current_price_drop_time_v280,
    get_price_drop_period_label_v280,
)
from .models import Category, Listing, ListingPriceHistory
from django.contrib.auth.models import User

class TestAnnotateCurrentPriceDropTimeV280(TestCase):
    def setUp(self):
        self.user = User.objects.create(username="testuser")
        self.category = Category.objects.create(name="Test Category", slug="test-category")
        self.listing = Listing.objects.create(
            title="Test Listing",
            description="Test Description",
            price=Decimal("100.00"),
            category=self.category,
            owner=self.user,
        )

    def test_no_price_history(self):
        # Listing has no price history
        ListingPriceHistory.objects.filter(listing=self.listing).delete()
        queryset = Listing.objects.filter(pk=self.listing.pk)
        annotated = annotate_current_price_drop_time_v280(queryset)
        self.assertIsNone(annotated.first().price_drop_changed_at_v280)

    def test_price_history_no_previous_price(self):
        # Listing has price history but no previous price (e.g. initial listing creation)
        # Note: Listing automatically creates a history without previous_price on creation
        ListingPriceHistory.objects.filter(listing=self.listing).update(changed_at=timezone.now())

        queryset = Listing.objects.filter(pk=self.listing.pk)
        annotated = annotate_current_price_drop_time_v280(queryset)
        self.assertIsNone(annotated.first().price_drop_changed_at_v280)

    def test_price_history_with_previous_price(self):
        # Listing has a price history with a previous price
        now = timezone.now()
        ListingPriceHistory.objects.create(
            listing=self.listing,
            previous_price=Decimal("110.00"),
            new_price=Decimal("100.00"),
            changed_at=now,
        )

        queryset = Listing.objects.filter(pk=self.listing.pk)
        annotated = annotate_current_price_drop_time_v280(queryset)
        self.assertEqual(annotated.first().price_drop_changed_at_v280, now)

    def test_multiple_price_histories(self):
        # Listing has multiple price histories. It should pick the latest one based on changed_at
        now = timezone.now()
        yesterday = now - timedelta(days=1)

        # Older transition
        ListingPriceHistory.objects.create(
            listing=self.listing,
            previous_price=Decimal("120.00"),
            new_price=Decimal("110.00"),
            changed_at=yesterday,
        )

        # Newer transition
        ListingPriceHistory.objects.create(
            listing=self.listing,
            previous_price=Decimal("110.00"),
            new_price=Decimal("100.00"),
            changed_at=now,
        )

        queryset = Listing.objects.filter(pk=self.listing.pk)
        annotated = annotate_current_price_drop_time_v280(queryset)
        self.assertEqual(annotated.first().price_drop_changed_at_v280, now)

    def test_custom_annotation_name(self):
        # Use a custom annotation name
        now = timezone.now()
        ListingPriceHistory.objects.create(
            listing=self.listing,
            previous_price=Decimal("110.00"),
            new_price=Decimal("100.00"),
            changed_at=now,
        )

        queryset = Listing.objects.filter(pk=self.listing.pk)
        annotated = annotate_current_price_drop_time_v280(
            queryset, changed_at_annotation="custom_changed_at"
        )
        self.assertEqual(annotated.first().custom_changed_at, now)
        with self.assertRaises(AttributeError):
            _ = annotated.first().price_drop_changed_at_v280



class TestPriceDropPeriodLabelV280(TestCase):
    def test_get_price_drop_period_label_v280(self):
        # Valid values
        self.assertEqual(get_price_drop_period_label_v280("24h"), "Last 24 hours")
        self.assertEqual(get_price_drop_period_label_v280("7d"), "Last 7 days")
        self.assertEqual(get_price_drop_period_label_v280("30d"), "Last 30 days")

        # Valid values with whitespace padding
        self.assertEqual(get_price_drop_period_label_v280(" 24h "), "Last 24 hours")
        self.assertEqual(get_price_drop_period_label_v280("7d "), "Last 7 days")

        # Invalid values
        self.assertEqual(get_price_drop_period_label_v280(""), "")
        self.assertEqual(get_price_drop_period_label_v280("invalid"), "")
        self.assertEqual(get_price_drop_period_label_v280("60d"), "")
        self.assertEqual(get_price_drop_period_label_v280(None), "")
