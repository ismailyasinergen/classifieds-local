"""
DEAL_AWARE_LISTING_COMPARISON_V297

Focused product and compatibility tests for current-discount evidence on the
public listing comparison page.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from categories.models import Category

from listings.listing_comparison_discount_v297 import (
    DEAL_AWARE_LISTING_COMPARISON_V297,
    LISTING_COMPARISON_DISCOUNT_ATTRIBUTE_V297,
    attach_listing_comparison_discounts_v297,
)
from listings.listing_comparison_v274 import (
    LISTING_COMPARISON_SESSION_KEY_V274,
)
from listings.listing_price_integrity_v293 import (
    DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
)
from listings.models import (
    Listing,
    ListingPriceHistory,
)


User = get_user_model()


class DealAwareListingComparisonV297Tests(TestCase):
    maxDiff = None

    def setUp(self):
        self.seller = User.objects.create_user(
            username="v297-seller",
            email="v297-seller@classifieds.local",
            password="StrongPass123!",
        )

        self.category = Category.objects.create(
            name="V297 Comparison Deals",
            slug="v297-comparison-deals",
        )

        self.compare_url = reverse(
            "listings:listing_compare"
        )

    def _create_listing(
        self,
        title,
        *,
        price="1000.00",
        status=Listing.Status.APPROVED,
        expires_at=None,
    ):
        return Listing.objects.create(
            owner=self.seller,
            category=self.category,
            title=title,
            description=f"Description for {title}",
            price=Decimal(price),
            location="Berlin",
            status=status,
            expires_at=expires_at,
            attributes={},
        )

    @staticmethod
    def _change_price(
        listing,
        price,
    ):
        listing.price = Decimal(price)
        listing.save(
            update_fields=["price"],
        )
        listing.refresh_from_db()

        return (
            listing.price_history
            .filter(previous_price__isnull=False)
            .first()
        )

    def _select(
        self,
        *listings,
        client=None,
    ):
        active_client = client or self.client
        session = active_client.session

        session[
            LISTING_COMPARISON_SESSION_KEY_V274
        ] = [
            listing.pk
            for listing in listings
        ]

        session.save()

    def test_v297_helper_attaches_v284_presentation_in_one_query(self):
        reduced = self._create_listing(
            "V297 Reduced",
        )
        baseline = self._create_listing(
            "V297 Baseline",
        )

        self._change_price(
            reduced,
            "800.00",
        )

        with CaptureQueriesContext(
            connection
        ) as captured:
            attach_listing_comparison_discounts_v297(
                [
                    reduced,
                    baseline,
                ]
            )

        self.assertEqual(
            len(captured),
            1,
        )

        reduced_discount = getattr(
            reduced,
            LISTING_COMPARISON_DISCOUNT_ATTRIBUTE_V297,
        )

        baseline_discount = getattr(
            baseline,
            LISTING_COMPARISON_DISCOUNT_ATTRIBUTE_V297,
        )

        self.assertIsNotNone(
            reduced_discount
        )
        self.assertEqual(
            reduced_discount.previous_price,
            Decimal("1000.00"),
        )
        self.assertEqual(
            reduced_discount.current_price,
            Decimal("800.00"),
        )
        self.assertEqual(
            reduced_discount.saving_amount,
            Decimal("200.00"),
        )
        self.assertEqual(
            reduced_discount.saving_percentage_display,
            "20",
        )
        self.assertIsNone(
            baseline_discount
        )

    def test_v297_valid_reduction_renders_complete_buyer_evidence(self):
        reduced = self._create_listing(
            "V297 Genuine Deal",
        )
        regular = self._create_listing(
            "V297 Regular Listing",
            price="1200.00",
        )

        self._change_price(
            reduced,
            "900.00",
        )

        self._select(
            reduced,
            regular,
        )

        response = self.client.get(
            self.compare_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(
            response.context["page_title"],
            "Compare listings",
        )
        self.assertTrue(
            response.context[
                "deal_aware_listing_comparison_v297"
            ]
        )

        self.assertContains(
            response,
            'data-listing-comparison-discount-v297="true"',
        )
        self.assertContains(
            response,
            "Price dropped",
        )
        self.assertContains(
            response,
            "1000.00 TL",
        )
        self.assertContains(
            response,
            "900.00 TL",
        )
        self.assertContains(
            response,
            "You save 100.00 TL",
        )
        self.assertContains(
            response,
            'data-saving-amount-v297="100.00"',
        )
        self.assertContains(
            response,
            'data-saving-percentage-v297="10"',
        )
        self.assertContains(
            response,
            (
                'aria-label="Price dropped from '
                '1000.00 TL to 900.00 TL. '
                'You save 100.00 TL '
                '(10 percent)."'
            ),
        )
        self.assertContains(
            response,
            'aria-label="Previous price 1000.00 TL"',
        )
        self.assertContains(
            response,
            'aria-label="Current price 900.00 TL"',
        )
        self.assertContains(
            response,
            "1200.00 TL",
        )

    def test_v297_baseline_and_noop_use_normal_price_fallback(self):
        baseline = self._create_listing(
            "V297 Baseline Only",
            price="700.00",
        )

        noop = self._create_listing(
            "V297 No-op",
            price="650.00",
        )

        ListingPriceHistory.objects.create(
            listing=noop,
            previous_price=Decimal("650.00"),
            new_price=Decimal("650.00"),
        )

        self._select(
            baseline,
            noop,
        )

        response = self.client.get(
            self.compare_url
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertNotContains(
            response,
            'data-listing-comparison-discount-v297="true"',
        )
        self.assertNotContains(
            response,
            "Price dropped",
        )
        self.assertNotContains(
            response,
            "You save",
        )
        self.assertContains(
            response,
            "700.00 TL",
        )
        self.assertContains(
            response,
            "650.00 TL",
        )

    def test_v297_later_increase_and_stale_reduction_are_hidden(self):
        later_increase = self._create_listing(
            "V297 Later Increase",
        )
        self._change_price(
            later_increase,
            "800.00",
        )
        self._change_price(
            later_increase,
            "900.00",
        )

        stale = self._create_listing(
            "V297 Stale Reduction",
        )
        self._change_price(
            stale,
            "800.00",
        )

        Listing.objects.filter(
            pk=stale.pk
        ).update(
            price=Decimal("850.00"),
        )
        stale.refresh_from_db()

        self._select(
            later_increase,
            stale,
        )

        response = self.client.get(
            self.compare_url
        )

        self.assertNotContains(
            response,
            'data-listing-comparison-discount-v297="true"',
        )
        self.assertNotContains(
            response,
            "You save",
        )
        self.assertContains(
            response,
            "900.00 TL",
        )
        self.assertContains(
            response,
            "850.00 TL",
        )

    def test_v297_zero_previous_and_guarded_drop_are_hidden(self):
        zero_previous = self._create_listing(
            "V297 Zero Previous",
            price="0.00",
        )

        Listing.objects.filter(
            pk=zero_previous.pk
        ).update(
            price=Decimal("-1.00"),
        )

        ListingPriceHistory.objects.create(
            listing=zero_previous,
            previous_price=Decimal("0.00"),
            new_price=Decimal("-1.00"),
        )

        zero_previous.refresh_from_db()

        guarded = self._create_listing(
            "V297 Guarded Deal",
            price="100.00",
        )

        self._change_price(
            guarded,
            "200.00",
        )
        restricted = self._change_price(
            guarded,
            "150.00",
        )

        self.assertEqual(
            restricted.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )

        self._select(
            zero_previous,
            guarded,
        )

        response = self.client.get(
            self.compare_url
        )

        self.assertNotContains(
            response,
            'data-listing-comparison-discount-v297="true"',
        )
        self.assertNotContains(
            response,
            "You save",
        )
        self.assertContains(
            response,
            "-1.00 TL",
        )
        self.assertContains(
            response,
            "150.00 TL",
        )
        self.assertNotContains(
            response,
            "raise_then_drop",
        )
        self.assertNotContains(
            response,
            "discount_reference_price",
        )

    def test_v297_nonpublic_selected_ids_are_pruned_before_presentation(self):
        approved = self._create_listing(
            "V297 Approved",
        )

        pending = self._create_listing(
            "V297 Pending",
            status=Listing.Status.PENDING,
        )

        expired = self._create_listing(
            "V297 Expired",
            expires_at=(
                timezone.now()
                - timedelta(seconds=1)
            ),
        )

        self._select(
            pending,
            approved,
            expired,
        )

        response = self.client.get(
            self.compare_url
        )

        self.assertEqual(
            [
                listing.pk
                for listing
                in response.context[
                    "comparison_listings"
                ]
            ],
            [
                approved.pk,
            ],
        )

        self.assertNotContains(
            response,
            pending.title,
        )
        self.assertNotContains(
            response,
            expired.title,
        )

        self.assertEqual(
            self.client.session[
                LISTING_COMPARISON_SESSION_KEY_V274
            ],
            [
                approved.pk,
            ],
        )

    def test_v297_preserves_selection_order_and_v274_controls(self):
        first = self._create_listing(
            "V297 First Selected",
        )
        second = self._create_listing(
            "V297 Second Selected",
        )
        third = self._create_listing(
            "V297 Third Selected",
        )

        self._change_price(
            second,
            "900.00",
        )

        self._select(
            third,
            first,
            second,
        )

        response = self.client.get(
            self.compare_url
        )

        self.assertEqual(
            [
                listing.pk
                for listing
                in response.context[
                    "comparison_listings"
                ]
            ],
            [
                third.pk,
                first.pk,
                second.pk,
            ],
        )

        html = response.content.decode(
            response.charset or "utf-8"
        )

        self.assertLess(
            html.index(third.title),
            html.index(first.title),
        )
        self.assertLess(
            html.index(first.title),
            html.index(second.title),
        )

        self.assertContains(
            response,
            "3 of 4 listings selected.",
        )
        self.assertContains(
            response,
            "Clear comparison",
        )
        self.assertContains(
            response,
            "Remove",
            count=3,
        )

    def test_v297_empty_state_and_header_link_to_public_deals(self):
        response = self.client.get(
            self.compare_url
        )

        deals_url = reverse(
            "listings:public_deals_v296"
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "No listings selected yet",
        )
        self.assertContains(
            response,
            "Browse deals",
            count=2,
        )
        self.assertContains(
            response,
            f'href="{deals_url}"',
            count=3,
        )
        self.assertContains(
            response,
            'class="listing-comparison-empty-actions-v297"',
        )

    def test_v297_comparison_query_count_does_not_grow_per_listing(self):
        listings = []

        for index in range(4):
            listing = self._create_listing(
                f"V297 Query Deal {index}",
                price="1000.00",
            )
            self._change_price(
                listing,
                str(900 - index),
            )
            listings.append(
                listing
            )

        def render_query_count(
            selected,
        ):
            client = self.client_class()
            self._select(
                *selected,
                client=client,
            )

            with CaptureQueriesContext(
                connection
            ) as captured:
                response = client.get(
                    self.compare_url
                )

            self.assertEqual(
                response.status_code,
                200,
            )

            return len(
                captured
            )

        one_listing_queries = render_query_count(
            listings[:1]
        )
        four_listing_queries = render_query_count(
            listings
        )

        self.assertEqual(
            one_listing_queries,
            four_listing_queries,
        )

    def test_v297_contract_reuses_v276_v284_and_adds_no_migration(self):
        backend_root = (
            Path(__file__).resolve().parents[1]
        )

        helper_source = (
            backend_root
            / "listings"
            / "listing_comparison_discount_v297.py"
        ).read_text(
            encoding="utf-8",
        )

        view_source = (
            backend_root
            / "listings"
            / "listing_comparison_views_v274.py"
        ).read_text(
            encoding="utf-8",
        )

        template_source = (
            backend_root
            / "listings"
            / "templates"
            / "listings"
            / "listing_comparison_v274.html"
        ).read_text(
            encoding="utf-8",
        )

        self.assertTrue(
            DEAL_AWARE_LISTING_COMPARISON_V297
        )
        self.assertIn(
            "get_current_listing_price_drops_v276",
            helper_source,
        )
        self.assertIn(
            "build_listing_card_discount_presentation_v284",
            helper_source,
        )
        self.assertIn(
            "attach_listing_comparison_discounts_v297",
            view_source,
        )
        self.assertIn(
            "DEAL_AWARE_LISTING_COMPARISON_V297",
            template_source,
        )
        self.assertIn(
            "LISTING_COMPARISON_V274",
            template_source,
        )
        self.assertIn(
            "public_deals_v296",
            template_source,
        )
        self.assertNotIn(
            "ListingPriceHistory.objects",
            template_source,
        )

        migration_directory = (
            backend_root
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "*v297*"
                )
            ),
            [],
        )
