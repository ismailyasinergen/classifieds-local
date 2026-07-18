from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from listings.models import (
    Listing,
    ListingPriceHistory,
)
from listings.templatetags.listing_price_history_v275 import (
    LISTING_PRICE_HISTORY_V275,
    listing_price_history_summary_v275,
)


class ListingPriceHistoryV275Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="v275-seller",
            email="v275-seller@example.com",
            password="v275-password",
        )

        self.category = Category.objects.create(
            name="V275 Furniture",
            slug="v275-furniture",
        )

        self.listing = Listing.objects.create(
            owner=self.user,
            category=self.category,
            title="V275 Price History Desk",
            description="V275 price history test listing.",
            price=Decimal("100.00"),
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

    def history(self):
        return list(
            ListingPriceHistory.objects.filter(
                listing=self.listing,
            )
        )

    def detail_response(self):
        return self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing.pk,
                },
            )
        )

    def test_v275_marker_is_stable(self):
        self.assertEqual(
            LISTING_PRICE_HISTORY_V275,
            "LISTING_PRICE_HISTORY_V275",
        )

    def test_new_listing_receives_exactly_one_baseline(self):
        history = self.history()

        self.assertEqual(
            len(history),
            1,
        )
        self.assertTrue(
            history[0].is_baseline
        )
        self.assertIsNone(
            history[0].previous_price
        )
        self.assertEqual(
            history[0].new_price,
            Decimal("100.00"),
        )
        self.assertEqual(
            history[0].changed_at,
            self.listing.created_at,
        )

    def test_baseline_is_unique_per_listing(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ListingPriceHistory.objects.create(
                    listing=self.listing,
                    previous_price=None,
                    new_price=Decimal("100.00"),
                )

    def test_unchanged_full_save_creates_no_transition(self):
        self.listing.title = "Updated title"
        self.listing.save()

        self.assertEqual(
            len(self.history()),
            1,
        )

    def test_nonprice_update_fields_create_no_transition(self):
        self.listing.title = "Updated through update_fields"
        self.listing.save(
            update_fields=["title"],
        )

        self.assertEqual(
            len(self.history()),
            1,
        )

    def test_price_change_records_previous_and_new_price(self):
        self.listing.price = Decimal("80.00")
        self.listing.save(
            update_fields=["price"],
        )

        history = self.history()

        self.assertEqual(
            len(history),
            2,
        )
        self.assertEqual(
            history[0].previous_price,
            Decimal("100.00"),
        )
        self.assertEqual(
            history[0].new_price,
            Decimal("80.00"),
        )
        self.assertTrue(
            history[0].is_price_drop
        )
        self.assertEqual(
            history[0].change_amount,
            Decimal("20.00"),
        )
        self.assertEqual(
            history[0].change_percentage,
            Decimal("20.0"),
        )

    def test_repeated_identical_price_creates_no_duplicate(self):
        self.listing.price = Decimal("80.00")
        self.listing.save(
            update_fields=["price"],
        )

        self.listing.price = "80.00"
        self.listing.save(
            update_fields=["price"],
        )

        self.assertEqual(
            len(self.history()),
            2,
        )

    def test_multiple_price_changes_are_newest_first(self):
        for price in (
            Decimal("90.00"),
            Decimal("75.00"),
            Decimal("85.00"),
        ):
            self.listing.price = price
            self.listing.save(
                update_fields=["price"],
            )

        history = self.history()

        self.assertEqual(
            [
                event.new_price
                for event in history
            ],
            [
                Decimal("85.00"),
                Decimal("75.00"),
                Decimal("90.00"),
                Decimal("100.00"),
            ],
        )

    def test_price_drop_summary_uses_current_transition(self):
        self.listing.price = Decimal("75.00")
        self.listing.save(
            update_fields=["price"],
        )

        summary = (
            listing_price_history_summary_v275(
                self.listing,
            )
        )

        self.assertTrue(
            summary["has_changes"]
        )
        self.assertTrue(
            summary["is_drop"]
        )
        self.assertEqual(
            summary["previous_price"],
            Decimal("100.00"),
        )
        self.assertEqual(
            summary["drop_amount"],
            Decimal("25.00"),
        )
        self.assertEqual(
            summary["drop_percentage"],
            Decimal("25.0"),
        )

    def test_price_increase_does_not_show_drop_badge(self):
        self.listing.price = Decimal("125.00")
        self.listing.save(
            update_fields=["price"],
        )

        response = self.detail_response()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertNotContains(
            response,
            'data-price-drop-v275="true"',
        )
        self.assertNotContains(
            response,
            "Price dropped",
        )
        self.assertContains(
            response,
            "Price increased:",
        )

    def test_price_drop_is_visible_on_public_detail(self):
        self.listing.price = Decimal("75.00")
        self.listing.save(
            update_fields=["price"],
        )

        response = self.detail_response()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            'data-price-history-v275="true"',
        )
        self.assertContains(
            response,
            'data-price-drop-v275="true"',
        )
        self.assertContains(
            response,
            "Price dropped",
        )
        self.assertContains(
            response,
            "100.00 TL",
        )
        self.assertContains(
            response,
            "75.00 TL",
        )
        self.assertContains(
            response,
            "Save 25.00 TL",
        )
        self.assertContains(
            response,
            "25.0%",
        )
        self.assertContains(
            response,
            "Price history",
        )
        self.assertContains(
            response,
            'data-marker="LISTING_PRICE_HISTORY_V275"',
        )

    def test_baseline_only_listing_hides_timeline(self):
        response = self.detail_response()

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            'data-price-history-v275="true"',
        )
        self.assertNotContains(
            response,
            'data-marker="LISTING_PRICE_HISTORY_V275"',
        )
        self.assertNotContains(
            response,
            "Price dropped",
        )

    def test_general_seller_update_cannot_bypass_price_confirmation(self):
        self.client.force_login(
            self.user
        )

        response = self.client.post(
            reverse(
                "listings:listing_update",
                kwargs={
                    "pk": self.listing.pk,
                },
            ),
            {
                "title": self.listing.title,
                "description": self.listing.description,
                "price": "70.00",
                "category": str(self.category.pk),
                "location": self.listing.location,
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.listing.refresh_from_db()

        self.assertEqual(self.listing.price, Decimal("100.00"))
        self.assertEqual(
            self.listing.status,
            Listing.Status.PENDING,
        )

        self.assertEqual(len(self.history()), 1)

    def test_zero_previous_price_does_not_divide_by_zero(self):
        zero_listing = Listing.objects.create(
            owner=self.user,
            category=self.category,
            title="V275 Free Item",
            description="Zero-price percentage guard.",
            price=Decimal("0.00"),
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

        zero_listing.price = Decimal("10.00")
        zero_listing.save(
            update_fields=["price"],
        )

        latest = zero_listing.price_history.first()

        self.assertTrue(
            latest.is_price_increase
        )
        self.assertIsNone(
            latest.change_percentage
        )

    def test_history_is_removed_with_listing(self):
        listing_pk = self.listing.pk

        self.listing.delete()

        self.assertFalse(
            ListingPriceHistory.objects.filter(
                listing_id=listing_pk,
            ).exists()
        )

    def test_listing_admin_registration_remains_present(self):
        self.assertIn(
            Listing,
            admin.site._registry,
        )

    def test_migration_0017_remains_absent_and_0018_exists(self):
        migration_directory = (
            Path(__file__).resolve().parent
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )

        self.assertEqual(
            [
                path.name
                for path in migration_directory.glob(
                    "0018*"
                )
            ],
            [
                "0018_listingpricehistory.py",
            ],
        )

    def test_migration_contains_baseline_backfill(self):
        migration_source = (
            Path(__file__).resolve().parent
            / "migrations"
            / "0018_listingpricehistory.py"
        ).read_text(
            encoding="utf-8",
        )

        for required in (
            "backfill_listing_price_history_v275",
            "previous_price=None",
            "new_price=listing.price",
            "changed_at=listing.created_at",
            "migrations.RunPython",
        ):
            with self.subTest(
                required=required,
            ):
                self.assertIn(
                    required,
                    migration_source,
                )

    def test_v271_through_v275_template_markers_coexist(self):
        template_source = (
            Path(__file__).resolve().parent
            / "templates"
            / "listings"
            / "listing_detail.html"
        ).read_text(
            encoding="utf-8",
        )

        for marker in (
            "RELATED_LISTINGS_RECOMMENDATIONS_V271",
            "RECENTLY_VIEWED_LISTINGS_V272",
            "LISTING_COMPARISON_V274",
            "LISTING_PRICE_HISTORY_V275",
        ):
            with self.subTest(
                marker=marker,
            ):
                self.assertIn(
                    marker,
                    template_source,
                )

    def test_v275_price_ui_preserves_v274_compare_control(self):
        template_source = (
            Path(__file__).resolve().parent
            / "templates"
            / "listings"
            / "listing_detail.html"
        ).read_text(
            encoding="utf-8",
        )

        price_hook = (
            'data-price-history-v275="true"'
        )
        comparison_hook = (
            "listing-comparison-detail-v274"
        )

        self.assertEqual(
            template_source.count(price_hook),
            1,
        )

        self.assertEqual(
            template_source.count(comparison_hook),
            1,
        )

        self.assertIn(
            "listing_compare_toggle",
            template_source,
        )

        self.assertIn(
            'value="{{ request.path }}"',
            template_source,
        )

        self.assertLess(
            template_source.index(price_hook),
            template_source.index(comparison_hook),
        )

    def test_v275_timeline_is_independent_of_related_listings(self):
        template_source = (
            Path(__file__).resolve().parent
            / "templates"
            / "listings"
            / "listing_detail.html"
        ).read_text(
            encoding="utf-8",
        )

        timeline_position = template_source.index(
            "{% if price_history_v275.has_changes %}"
        )

        related_if_position = template_source.index(
            "{% if related_listings %}"
        )

        related_marker_position = template_source.index(
            'data-marker="RELATED_LISTINGS_RECOMMENDATIONS_V271"'
        )

        self.assertLess(
            timeline_position,
            related_if_position,
        )

        self.assertLess(
            related_if_position,
            related_marker_position,
        )
