from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.template import RequestContext, Template
from django.test import RequestFactory, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from categories.models import Category
from listings.listing_card_discount_presentation_v284 import (
    ENHANCED_LISTING_CARD_DISCOUNT_V284,
    build_listing_card_discount_presentation_v284,
)
from listings.listing_price_drop_discovery_v276 import (
    get_current_listing_price_drops_v276,
)
from listings.models import Listing, ListingPriceHistory


class EnhancedListingCardDiscountV284Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="v284-seller",
            email="v284-seller@example.com",
            password="v284-password",
        )
        self.category = Category.objects.create(
            name="V284 Discount Cards",
            slug="v284-discount-cards",
        )

    def create_listing(self, title, *, price="1000.00"):
        return Listing.objects.create(
            owner=self.user,
            category=self.category,
            title=title,
            description="Enhanced listing-card discount presentation test.",
            price=Decimal(price),
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

    def change_price(self, listing, price):
        listing.price = Decimal(price)
        listing.save(update_fields=["price"])
        listing.refresh_from_db()
        return listing

    def card_template_source(self):
        return (
            Path(__file__).resolve().parent
            / "templates"
            / "listings"
            / "_listing_card.html"
        ).read_text(encoding="utf-8")

    def test_v284_valid_reduction_renders_complete_buyer_evidence(self):
        listing = self.create_listing("V284 Valid Reduction")
        self.change_price(listing, "900.00")

        response = self.client.get(reverse("listings:listing_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-price-drop-card-v284="true"')
        self.assertContains(response, "Price dropped")
        self.assertContains(response, "1000.00 TL")
        self.assertContains(response, "900.00 TL")
        self.assertContains(response, "You save 100.00 TL (10%)")
        self.assertContains(response, 'data-saving-percentage-v284="10"')
        self.assertContains(response, 'aria-label="Current price 900.00 TL"')
        self.assertContains(
            response,
            (
                'aria-label="Price dropped from 1000.00 TL to 900.00 TL. '
                'You save 100.00 TL (10 percent)."'
            ),
        )

    def test_v284_previous_price_uses_semantic_strikethrough(self):
        listing = self.create_listing("V284 Semantic Previous Price")
        self.change_price(listing, "900.00")

        response = self.client.get(reverse("listings:listing_list"))

        self.assertContains(response, "<del", html=False)
        self.assertContains(
            response,
            'aria-label="Previous price 1000.00 TL"',
        )
        self.assertContains(response, "Now")

    def test_v284_decimal_percentage_keeps_precision_and_trims_zeros(self):
        listing = self.create_listing(
            "V284 Decimal Percentage",
            price="120.00",
        )
        self.change_price(listing, "100.00")

        response = self.client.get(reverse("listings:listing_list"))

        self.assertContains(response, "You save 20.00 TL (16.67%)")
        self.assertContains(
            response,
            'data-saving-percentage-v284="16.67"',
        )
        self.assertNotContains(response, "16.6700%")

    def test_v284_baseline_and_noop_rows_use_normal_price_presentation(self):
        baseline = self.create_listing("V284 Baseline Only")
        noop = self.create_listing("V284 No-op History")
        ListingPriceHistory.objects.create(
            listing=noop,
            previous_price=Decimal("1000.00"),
            new_price=Decimal("1000.00"),
        )

        response = self.client.get(reverse("listings:listing_list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-price-drop-card-v284="true"')
        self.assertNotContains(response, "You save")
        self.assertContains(response, f'href="{baseline.get_absolute_url()}"')

    def test_v284_later_increase_hides_an_earlier_reduction(self):
        listing = self.create_listing("V284 Later Increase")
        self.change_price(listing, "800.00")
        self.change_price(listing, "900.00")

        response = self.client.get(reverse("listings:listing_list"))

        self.assertNotContains(response, 'data-price-drop-card-v284="true"')
        self.assertNotContains(response, "You save")
        self.assertContains(response, "900.00 TL")

    def test_v284_stale_current_price_mismatch_hides_discount(self):
        listing = self.create_listing("V284 Stale Reduction")
        self.change_price(listing, "800.00")
        Listing.objects.filter(pk=listing.pk).update(price=Decimal("900.00"))

        response = self.client.get(reverse("listings:listing_list"))

        self.assertNotContains(response, 'data-price-drop-card-v284="true"')
        self.assertNotContains(response, "You save")
        self.assertContains(response, "900.00 TL")

    def test_v284_zero_previous_price_is_rejected_by_presentation(self):
        listing = self.create_listing(
            "V284 Zero Previous Price",
            price="0.00",
        )
        Listing.objects.filter(pk=listing.pk).update(price=Decimal("-1.00"))
        ListingPriceHistory.objects.create(
            listing=listing,
            previous_price=Decimal("0.00"),
            new_price=Decimal("-1.00"),
        )

        discovery = get_current_listing_price_drops_v276(
            [listing.pk]
        )[listing.pk]
        presentation = build_listing_card_discount_presentation_v284(
            discovery
        )
        response = self.client.get(reverse("listings:listing_list"))

        self.assertIsNone(presentation)
        self.assertNotContains(response, 'data-price-drop-card-v284="true"')
        self.assertNotContains(response, "You save")
        self.assertContains(response, "-1.00 TL")

    def test_v284_tag_adds_no_query_growth(self):
        listings = []
        for index in range(12):
            listing = self.create_listing(
                f"V284 Query Count {index:02d}"
            )
            self.change_price(listing, str(900 - index))
            listings.append(listing)

        template = Template(
            """
            {% load listing_price_drop_discovery_v276 %}
            {% load listing_card_discount_presentation_v284 %}
            {% for listing in listings %}
                {% listing_card_price_drop_v276 listing as discovery %}
                {% listing_card_discount_presentation_v284 discovery as discount %}
                {% if discount %}{{ discount.saving_percentage_display }}{% endif %}
            {% endfor %}
            """
        )

        def render_query_count(card_list):
            request = RequestFactory().get("/listings/")
            request.user = AnonymousUser()
            context = RequestContext(request, {"listings": card_list})
            with CaptureQueriesContext(connection) as captured:
                template.render(context)
            return len(captured)

        self.assertEqual(render_query_count(listings[:1]), 1)
        self.assertEqual(render_query_count(listings), 1)

    def test_v284_template_preserves_card_contracts_and_accessibility(self):
        source = self.card_template_source()

        for required in (
            "ENHANCED_LISTING_CARD_DISCOUNT_V284",
            "V276_LISTING_CARD_PRICE_DROP_DISCOVERY",
            "V277_LISTING_CARD_PRICE_DROP_UX_ACCESSIBILITY_POLISH",
            "LISTING_COMPARISON_V274",
            "<del",
            "Price dropped",
            "You save",
            "accessible_explanation",
            "listing-card-location",
            "listing-card-category",
            "listing_favorite_toggle",
            "listing_compare_toggle",
        ):
            with self.subTest(required=required):
                self.assertIn(required, source)

    def test_v284_documentation_marker_and_no_migration(self):
        project_root = Path(__file__).resolve().parents[1]
        migration_directory = Path(__file__).resolve().parent / "migrations"

        self.assertTrue(ENHANCED_LISTING_CARD_DISCOUNT_V284)
        self.assertEqual(list(migration_directory.glob("*v284*")), [])
        self.assertIn(
            "enhanced_listing_card_discount_v284.md",
            str(
                project_root
                / "docs"
                / "enhanced_listing_card_discount_v284.md"
            ),
        )
