from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile
from categories.models import Category
from listings.listing_price_drop_discovery_v276 import (
    V276_LISTING_CARD_PRICE_DROP_DISCOVERY,
)
from listings.models import Listing


V277_LISTING_CARD_PRICE_DROP_UX_ACCESSIBILITY_POLISH = True

V277_TEMPLATE_MARKER = (
    "V277_LISTING_CARD_PRICE_DROP_UX_ACCESSIBILITY_POLISH"
)


class ListingCardPriceDropUxPolishV277Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.seller = User.objects.create_user(
            username="v277-price-drop-seller",
            email="v277-price-drop-seller@example.test",
            password="StrongPass123!",
        )

        UserProfile.objects.get_or_create(
            user=cls.seller,
        )

        cls.category = Category.objects.create(
            name="V277 Furniture",
            slug="v277-furniture",
        )

    def create_listing(
        self,
        title: str,
        *,
        price: str = "1000.00",
    ) -> Listing:
        return Listing.objects.create(
            title=title,
            description=(
                f"{title} v277 listing-card price-drop "
                "UX accessibility test."
            ),
            price=Decimal(price),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

    def change_price(
        self,
        listing: Listing,
        price: str,
    ) -> Listing:
        listing.price = Decimal(price)
        listing.save(
            update_fields=[
                "price",
            ],
        )
        listing.refresh_from_db()
        return listing

    def card_template_source(self) -> str:
        return (
            Path(settings.BASE_DIR)
            / "listings"
            / "templates"
            / "listings"
            / "_listing_card.html"
        ).read_text(
            encoding="utf-8",
        )

    def test_v277_contract_marker_and_v276_dependency_are_present(
        self,
    ):
        self.assertTrue(
            V277_LISTING_CARD_PRICE_DROP_UX_ACCESSIBILITY_POLISH
        )

        self.assertTrue(
            V276_LISTING_CARD_PRICE_DROP_DISCOVERY
        )

        source = self.card_template_source()

        self.assertIn(
            V277_TEMPLATE_MARKER,
            source,
        )

        self.assertIn(
            "V276_LISTING_CARD_PRICE_DROP_DISCOVERY",
            source,
        )

    def test_reduced_listing_card_exposes_accessible_price_evidence(
        self,
    ):
        listing = self.create_listing(
            "Accessible Reduced Listing",
        )

        self.change_price(
            listing,
            "900.00",
        )

        response = self.client.get(
            reverse(
                "listings:listing_list",
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            'data-price-drop-card-v277="true"',
        )

        self.assertContains(
            response,
            'data-price-drop-badge-v277="true"',
        )

        self.assertContains(
            response,
            'data-previous-price-v277="1000.00"',
        )

        self.assertContains(
            response,
            'data-current-price-v277="900.00"',
        )

        self.assertContains(
            response,
            'data-saving-amount-v277="100.00"',
        )

        self.assertContains(
            response,
            (
                'data-price-drop-saving-copy-v276='
                '"Save 100.00 TL"'
            ),
        )

        self.assertContains(
            response,
            'data-saving-percentage-v277="10.00"',
        )

        self.assertContains(
            response,
            (
                'aria-label="Price dropped from '
                '1000.00 TL to 900.00 TL. '
                'You save 100.00 TL (10 percent)."'
            ),
        )

        self.assertContains(
            response,
            'aria-label="Current price 900.00 TL"',
        )

        self.assertContains(
            response,
            "You save 100.00 TL (10%)",
        )

        self.assertContains(
            response,
            "Now",
        )

    def test_baseline_only_listing_does_not_show_v277_drop_markup(
        self,
    ):
        self.create_listing(
            "Baseline Only V277 Listing",
        )

        response = self.client.get(
            reverse(
                "listings:listing_list",
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            'data-price-drop-card-v277="true"',
        )

        self.assertNotContains(
            response,
            'data-price-drop-badge-v277="true"',
        )

        self.assertNotContains(
            response,
            "You save",
        )

    def test_latest_increase_hides_an_earlier_price_drop(
        self,
    ):
        listing = self.create_listing(
            "V277 Drop Then Increase",
        )

        self.change_price(
            listing,
            "900.00",
        )

        self.change_price(
            listing,
            "950.00",
        )

        response = self.client.get(
            reverse(
                "listings:listing_list",
            ),
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            'data-price-drop-card-v277="true"',
        )

        self.assertNotContains(
            response,
            "You save",
        )

    def test_v277_markup_is_only_inside_v276_drop_condition(
        self,
    ):
        source = self.card_template_source()

        condition_start = source.index(
            "{% if listing_price_drop_v276 %}"
        )

        condition_end = source.index(
            "{% endif %}",
            condition_start,
        )

        v277_summary = source.index(
            'data-price-drop-card-v277="true"'
        )

        self.assertGreater(
            v277_summary,
            condition_start,
        )

        self.assertLess(
            v277_summary,
            condition_end,
        )

    def test_v277_preserves_comparison_and_v276_card_contracts(
        self,
    ):
        source = self.card_template_source()

        required_fragments = (
            "{% load listing_comparison_v274 %}",
            "LISTING_COMPARISON_V274",
            "listing_compare_toggle",
            "{% load listing_price_drop_discovery_v276 %}",
            "data-price-drop-card-v276",
            "listing_card_price_drop_v276",
        )

        for fragment in required_fragments:
            with self.subTest(
                fragment=fragment,
            ):
                self.assertIn(
                    fragment,
                    source,
                )

    def test_v277_replaces_generic_accessibility_copy(
        self,
    ):
        source = self.card_template_source()

        self.assertNotIn(
            'aria-label="Price reduction"',
            source,
        )

        self.assertIn(
            (
                'aria-label="{{ '
                "listing_price_drop_v276.accessible_explanation }}"
                '"'
            ),
            source,
        )

        self.assertIn(
            (
                'aria-label="You save '
                "{{ listing_price_drop_v276.saving_amount }} TL"
            ),
            source,
        )
