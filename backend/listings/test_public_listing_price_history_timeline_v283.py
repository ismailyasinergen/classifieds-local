from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.listing_public_price_history_v283 import (
    PUBLIC_LISTING_PRICE_HISTORY_TIMELINE_V283,
    PUBLIC_PRICE_HISTORY_LIMIT_V283,
    get_public_price_history_v283,
)
from listings.models import Listing, ListingPriceHistory


class PublicListingPriceHistoryTimelineV283Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="v283-seller",
            email="v283-seller@example.com",
            password="v283-password",
        )
        self.category = Category.objects.create(
            name="V283 Timeline Category",
            slug="v283-timeline-category",
        )
        self.listing = self.create_listing(
            title="V283 Public Timeline Listing",
        )

    def create_listing(
        self,
        *,
        title,
        status=Listing.Status.APPROVED,
        price="100.00",
        expires_at=None,
    ):
        return Listing.objects.create(
            owner=self.user,
            category=self.category,
            title=title,
            description="Public price-history timeline test listing.",
            price=Decimal(price),
            location="Berlin",
            status=status,
            expires_at=expires_at,
        )

    def add_transition(
        self,
        *,
        listing=None,
        previous="100.00",
        new="80.00",
        changed_at=None,
    ):
        return ListingPriceHistory.objects.create(
            listing=listing or self.listing,
            previous_price=Decimal(previous),
            new_price=Decimal(new),
            changed_at=changed_at or timezone.now(),
        )

    def set_current_price(self, listing, price):
        Listing.objects.filter(pk=listing.pk).update(
            price=Decimal(price)
        )
        listing.refresh_from_db()

    def detail_url(self, listing=None):
        return reverse(
            "listings:listing_detail",
            kwargs={"pk": (listing or self.listing).pk},
        )

    def test_v283_public_reduction_renders_complete_semantic_timeline(self):
        self.set_current_price(self.listing, "100.00")
        self.add_transition(previous="150.00", new="100.00")

        response = self.client.get(self.detail_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Price history")
        self.assertContains(
            response,
            'data-version="PUBLIC_LISTING_PRICE_HISTORY_TIMELINE_V283"',
        )
        self.assertContains(response, "<h2", html=False)
        self.assertContains(response, "<ol", html=False)
        self.assertContains(response, "<li", html=False)
        self.assertContains(response, "<time", html=False)
        self.assertContains(response, "datetime=", html=False)
        self.assertContains(response, "Price reduced:")
        self.assertContains(response, 'class="price-history-drop-v275"')
        self.assertContains(response, "Previous price: 150.00 TL")
        self.assertContains(response, "New price: 100.00 TL")
        self.assertContains(response, "Amount saved: 50.00 TL")
        self.assertContains(response, "Percentage change: 33.3333%")
        self.assertContains(response, "Current price")
        self.assertContains(
            response,
            '<div class="classified-price">100.00 TL</div>',
            html=True,
        )
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.price, Decimal("100.00"))

    def test_v283_baseline_and_equal_price_rows_hide_the_section(self):
        baseline_response = self.client.get(self.detail_url())

        self.assertEqual(baseline_response.status_code, 200)
        self.assertNotContains(
            baseline_response,
            'data-version="PUBLIC_LISTING_PRICE_HISTORY_TIMELINE_V283"',
        )

        self.add_transition(previous="100.00", new="100.00")
        noop_response = self.client.get(self.detail_url())

        self.assertEqual(noop_response.status_code, 200)
        self.assertNotContains(
            noop_response,
            'data-version="PUBLIC_LISTING_PRICE_HISTORY_TIMELINE_V283"',
        )
        self.assertEqual(
            noop_response.context["public_price_history_v283"],
            [],
        )

    def test_v283_increase_values_and_percentage_are_correct(self):
        self.set_current_price(self.listing, "125.00")
        self.add_transition(previous="100.00", new="125.00")

        response = self.client.get(self.detail_url())

        self.assertContains(response, "Price increased:")
        self.assertContains(response, 'class="price-history-increase-v275"')
        self.assertContains(response, "Previous price: 100.00 TL")
        self.assertContains(response, "New price: 125.00 TL")
        self.assertContains(response, "Increase amount: 25.00 TL")
        self.assertContains(response, "Percentage change: 25%")
        self.assertNotContains(response, "Percentage change: 25.0000%")

    def test_v283_decimal_percentage_keeps_precision_without_trailing_zeros(self):
        self.set_current_price(self.listing, "2.00")
        self.add_transition(previous="3.00", new="2.00")

        response = self.client.get(self.detail_url())
        entry = response.context["public_price_history_v283"][0]

        self.assertEqual(entry.absolute_change, Decimal("1.00"))
        self.assertEqual(entry.percentage_display, "33.3333")
        self.assertContains(response, "Percentage change: 33.3333%")
        self.assertNotContains(response, "33.33330000%")

    def test_v283_zero_previous_price_uses_neutral_percentage_fallback(self):
        self.set_current_price(self.listing, "10.00")
        self.add_transition(previous="0.00", new="10.00")

        response = self.client.get(self.detail_url())
        entry = response.context["public_price_history_v283"][0]

        self.assertEqual(response.status_code, 200)
        self.assertEqual(entry.absolute_change, Decimal("10.00"))
        self.assertIsNone(entry.percentage_change)
        self.assertEqual(entry.percentage_display, "")
        self.assertContains(response, "Percentage unavailable")
        self.assertNotContains(response, "Percentage change:")

    def test_v283_ordering_is_changed_at_then_primary_key_descending(self):
        base_time = timezone.now() - timedelta(days=2)
        oldest = self.add_transition(
            previous="130.00",
            new="120.00",
            changed_at=base_time,
        )
        same_time = base_time + timedelta(hours=1)
        first_tied = self.add_transition(
            previous="120.00",
            new="110.00",
            changed_at=same_time,
        )
        second_tied = self.add_transition(
            previous="110.00",
            new="100.00",
            changed_at=same_time,
        )

        entries = get_public_price_history_v283(self.listing)

        self.assertEqual(
            [entry.previous_price for entry in entries],
            [Decimal("110.00"), Decimal("120.00"), Decimal("130.00")],
        )
        self.assertGreater(second_tied.pk, first_tied.pk)
        self.assertLess(oldest.changed_at, first_tied.changed_at)
        self.assertTrue(all(timezone.is_aware(entry.changed_at) for entry in entries))

    def test_v283_query_applies_database_limit_and_excludes_the_21st(self):
        base_time = timezone.now() - timedelta(days=3)
        for index in range(21):
            self.add_transition(
                previous=str(100 + index),
                new=str(99 + index),
                changed_at=base_time + timedelta(minutes=index),
            )

        with CaptureQueriesContext(connection) as captured:
            entries = get_public_price_history_v283(self.listing)

        self.assertEqual(PUBLIC_PRICE_HISTORY_LIMIT_V283, 20)
        self.assertEqual(len(entries), 20)
        self.assertEqual(len(captured), 1)
        self.assertIn("LIMIT 20", captured[0]["sql"].upper())
        self.assertEqual(entries[0].previous_price, Decimal("120.00"))
        self.assertEqual(entries[-1].previous_price, Decimal("101.00"))
        self.assertNotIn(
            Decimal("100.00"),
            [entry.previous_price for entry in entries],
        )

    def test_v283_current_marker_requires_the_newest_transition_to_match(self):
        self.set_current_price(self.listing, "80.00")
        base_time = timezone.now() - timedelta(days=1)
        self.add_transition(
            previous="100.00",
            new="80.00",
            changed_at=base_time,
        )
        self.add_transition(
            previous="80.00",
            new="70.00",
            changed_at=base_time + timedelta(hours=1),
        )

        entries = get_public_price_history_v283(self.listing)

        self.assertFalse(entries[0].is_current)
        self.assertFalse(entries[1].is_current)

    def test_v283_keeps_historical_increases_and_reductions(self):
        self.set_current_price(self.listing, "70.00")
        base_time = timezone.now() - timedelta(days=1)
        self.add_transition(
            previous="100.00",
            new="80.00",
            changed_at=base_time,
        )
        self.add_transition(
            previous="80.00",
            new="90.00",
            changed_at=base_time + timedelta(hours=1),
        )
        self.add_transition(
            previous="90.00",
            new="70.00",
            changed_at=base_time + timedelta(hours=2),
        )

        entries = get_public_price_history_v283(self.listing)

        self.assertEqual(
            [entry.direction for entry in entries],
            ["reduction", "increase", "reduction"],
        )
        self.assertTrue(entries[0].is_current)
        self.assertFalse(entries[1].is_current)
        self.assertFalse(entries[2].is_current)

    def test_v283_detail_history_query_count_does_not_grow_per_entry(self):
        one_entry_listing = self.create_listing(
            title="V283 One Timeline Entry",
            price="80.00",
        )
        self.add_transition(
            listing=one_entry_listing,
            previous="100.00",
            new="80.00",
        )
        twenty_entry_listing = self.create_listing(
            title="V283 Twenty Timeline Entries",
            price="80.00",
        )
        base_time = timezone.now() - timedelta(days=1)
        for index in range(20):
            self.add_transition(
                listing=twenty_entry_listing,
                previous=str(120 + index),
                new=str(119 + index),
                changed_at=base_time + timedelta(minutes=index),
            )

        with CaptureQueriesContext(connection) as one_captured:
            one_response = Client().get(self.detail_url(one_entry_listing))
        with CaptureQueriesContext(connection) as twenty_captured:
            twenty_response = Client().get(self.detail_url(twenty_entry_listing))

        self.assertEqual(one_response.status_code, 200)
        self.assertEqual(twenty_response.status_code, 200)
        self.assertEqual(len(one_captured), len(twenty_captured))
        for captured in (one_captured, twenty_captured):
            timeline_queries = [
                query["sql"]
                for query in captured
                if "listings_listingpricehistory" in query["sql"].lower()
                and "LIMIT 20" in query["sql"].upper()
            ]
            self.assertEqual(len(timeline_queries), 1)

    def test_v283_existing_detail_visibility_rules_are_unchanged(self):
        approved_response = self.client.get(self.detail_url())
        self.assertEqual(approved_response.status_code, 200)

        hidden_listings = [
            self.create_listing(
                title=f"V283 Hidden {status}",
                status=status,
            )
            for status in (
                Listing.Status.PENDING,
                Listing.Status.REJECTED,
                Listing.Status.SUSPENDED,
                Listing.Status.ARCHIVED,
            )
        ]
        expired = self.create_listing(
            title="V283 Expired Approved",
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        for listing in [*hidden_listings, expired]:
            with self.subTest(anonymous_listing=listing.title):
                self.assertEqual(
                    self.client.get(self.detail_url(listing)).status_code,
                    404,
                )

        self.client.force_login(self.user)
        for listing in [*hidden_listings, expired]:
            with self.subTest(owner_listing=listing.title):
                self.assertEqual(
                    self.client.get(self.detail_url(listing)).status_code,
                    200,
                )

        staff = get_user_model().objects.create_user(
            username="v283-staff",
            email="v283-staff@example.com",
            password="v283-password",
            is_staff=True,
        )
        self.client.force_login(staff)
        self.assertEqual(
            self.client.get(self.detail_url(hidden_listings[0])).status_code,
            200,
        )
        self.client.logout()
        self.assertEqual(
            self.client.get(
                reverse("listings:listing_detail", kwargs={"pk": 999999})
            ).status_code,
            404,
        )

    def test_v283_public_context_and_template_do_not_expose_internal_metadata(self):
        self.add_transition(previous="100.00", new="80.00")

        response = self.client.get(self.detail_url())
        entry = response.context["public_price_history_v283"][0]
        template_path = (
            Path(__file__).resolve().parent
            / "templates"
            / "listings"
            / "listing_detail.html"
        )
        template_source = template_path.read_text(encoding="utf-8")
        timeline_source = template_source.split(
            "{% if price_history_v275.has_changes %}",
            1,
        )[1].split("{% if related_listings %}", 1)[0]

        self.assertFalse(hasattr(entry, "pk"))
        self.assertFalse(hasattr(entry, "listing_id"))
        self.assertNotContains(response, "ListingPriceHistory")
        for forbidden in (
            "entry.pk",
            "entry.listing",
            "user_id",
            "staff_id",
            "actor",
            "ip_address",
            "moderation",
            "private",
            "admin_url",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, timeline_source.lower())

    def test_v283_adds_no_public_endpoint_and_preserves_access_path(self):
        urls_source = (
            Path(__file__).resolve().parent
            / "urls.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn("price-history/", urls_source)
        self.assertEqual(
            self.detail_url(),
            f"/listings/{self.listing.pk}/",
        )

    def test_v283_source_markers_documentation_and_migration_status(self):
        template_source = (
            Path(__file__).resolve().parent
            / "templates"
            / "listings"
            / "listing_detail.html"
        ).read_text(encoding="utf-8")
        migration_directory = Path(__file__).resolve().parent / "migrations"

        self.assertTrue(PUBLIC_LISTING_PRICE_HISTORY_TIMELINE_V283)
        self.assertIn(
            "PUBLIC_LISTING_PRICE_HISTORY_TIMELINE_V283",
            template_source,
        )
        self.assertEqual(list(migration_directory.glob("*v283*")), [])
