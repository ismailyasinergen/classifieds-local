from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import resolve, reverse
from django.utils import timezone

from accounts.models import UserProfile
from categories.models import Category
from listings.listing_biggest_price_drop_sort_v281 import (
    BIGGEST_PRICE_DROP_SORT_V281,
)
from listings.listing_card_discount_presentation_v284 import (
    ENHANCED_LISTING_CARD_DISCOUNT_V284,
)
from listings.listing_price_integrity_v293 import (
    DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
)
from listings.models import Listing, ListingPriceHistory
from listings.public_deals_landing_page_v296 import (
    PUBLIC_DEALS_LANDING_PAGE_V296,
    PUBLIC_DEALS_PAGE_SIZE_V296,
    PublicDealsListViewV296,
)


class PublicDealsLandingPageV296Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.seller = User.objects.create_user(
            username="v296-deals-seller",
            email="v296-deals-seller@example.test",
            password="StrongPass123!",
        )
        UserProfile.objects.get_or_create(user=cls.seller)

        cls.category = Category.objects.create(
            name="V296 Deals",
            slug="v296-deals",
        )
        cls.now = timezone.now()

    def create_listing(
        self,
        title,
        *,
        price="1000.00",
        status=Listing.Status.APPROVED,
        expires_at=None,
    ):
        return Listing.objects.create(
            title=title,
            description=f"{title} public Deals test.",
            price=Decimal(str(price)),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=status,
            expires_at=expires_at,
        )

    def change_price(
        self,
        listing,
        new_price,
        *,
        changed_at=None,
    ):
        listing.price = Decimal(str(new_price))
        listing.save(update_fields=["price"])
        listing.refresh_from_db()

        transition = (
            ListingPriceHistory.objects
            .filter(
                listing=listing,
                previous_price__isnull=False,
            )
            .order_by("-changed_at", "-pk")
            .first()
        )

        if changed_at is not None:
            ListingPriceHistory.objects.filter(
                pk=transition.pk,
            ).update(changed_at=changed_at)
            transition.changed_at = changed_at

        return transition

    def deals(self, params=None):
        return self.client.get(
            reverse("listings:public_deals_v296"),
            params or {},
        )

    @staticmethod
    def response_titles(response):
        return [
            listing.title
            for listing in response.context["listings"]
        ]

    def test_anonymous_access_heading_url_and_public_navigation(self):
        deals_url = reverse("listings:public_deals_v296")
        match = resolve(deals_url)

        response = self.deals()
        browse = self.client.get(
            reverse("listings:listing_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(match.func.view_class, PublicDealsListViewV296)
        self.assertEqual(response.context["page_title"], "Deals")
        self.assertContains(
            response,
            '<h1 id="public-deals-heading-v296">Deals</h1>',
            html=True,
        )
        self.assertContains(
            response,
            f'href="{deals_url}">Deals</a>',
            html=False,
        )
        self.assertContains(
            browse,
            f'href="{deals_url}">Deals</a>',
            html=False,
        )

    def test_valid_reduction_reuses_complete_v284_card_presentation(self):
        listing = self.create_listing(
            "V296 Complete Deal",
            price="1200.00",
        )
        self.change_price(listing, "900.00")

        response = self.deals()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, listing.title)
        self.assertContains(
            response,
            'data-price-drop-card-v284="true"',
        )
        self.assertContains(response, "1200.00 TL")
        self.assertContains(response, "900.00 TL")
        self.assertContains(
            response,
            "You save 300.00 TL (25%)",
        )
        self.assertContains(
            response,
            'aria-label="Previous price 1200.00 TL"',
        )
        self.assertContains(
            response,
            'aria-label="Current price 900.00 TL"',
        )
        self.assertContains(
            response,
            (
                'aria-label="Price dropped from 1200.00 TL to '
                '900.00 TL. You save 300.00 TL (25 percent)."'
            ),
        )

    def test_percentage_precedes_absolute_amount(self):
        high_percentage = self.create_listing(
            "V296 High Percentage",
            price="100.00",
        )
        self.change_price(
            high_percentage,
            "50.00",
            changed_at=self.now - timedelta(hours=2),
        )

        high_amount = self.create_listing(
            "V296 High Amount",
            price="1000.00",
        )
        self.change_price(
            high_amount,
            "600.00",
            changed_at=self.now - timedelta(hours=1),
        )

        response = self.deals()

        self.assertEqual(
            self.response_titles(response),
            [
                "V296 High Percentage",
                "V296 High Amount",
            ],
        )

    def test_amount_time_and_primary_key_are_deterministic_tiebreakers(self):
        small_amount = self.create_listing(
            "V296 Equal Percent Small Amount",
            price="100.00",
        )
        self.change_price(
            small_amount,
            "50.00",
            changed_at=self.now,
        )

        large_amount = self.create_listing(
            "V296 Equal Percent Large Amount",
            price="1000.00",
        )
        self.change_price(
            large_amount,
            "500.00",
            changed_at=self.now - timedelta(hours=3),
        )

        older = self.create_listing("V296 Older Equal Deal")
        self.change_price(
            older,
            "500.00",
            changed_at=self.now - timedelta(hours=2),
        )

        newer = self.create_listing("V296 Newer Equal Deal")
        self.change_price(
            newer,
            "500.00",
            changed_at=self.now - timedelta(hours=1),
        )

        first_pk_tie = self.create_listing(
            "V296 First PK Tie"
        )
        self.change_price(
            first_pk_tie,
            "500.00",
            changed_at=self.now + timedelta(minutes=1),
        )

        second_pk_tie = self.create_listing(
            "V296 Second PK Tie"
        )
        self.change_price(
            second_pk_tie,
            "500.00",
            changed_at=self.now + timedelta(minutes=1),
        )

        response = self.deals()

        self.assertEqual(
            self.response_titles(response),
            [
                "V296 Second PK Tie",
                "V296 First PK Tie",
                "V296 Newer Equal Deal",
                "V296 Older Equal Deal",
                "V296 Equal Percent Large Amount",
                "V296 Equal Percent Small Amount",
            ],
        )

    def test_baseline_noop_stale_increase_and_current_mismatch_are_excluded(self):
        valid = self.create_listing("V296 Valid Control")
        self.change_price(valid, "800.00")

        self.create_listing("V296 Baseline Only")

        noop = self.create_listing("V296 Latest No-op")
        ListingPriceHistory.objects.create(
            listing=noop,
            previous_price=Decimal("1000.00"),
            new_price=Decimal("1000.00"),
            changed_at=self.now + timedelta(minutes=2),
        )

        stale = self.create_listing("V296 Stale Reduction")
        self.change_price(
            stale,
            "800.00",
            changed_at=self.now - timedelta(hours=2),
        )
        ListingPriceHistory.objects.create(
            listing=stale,
            previous_price=Decimal("800.00"),
            new_price=Decimal("800.00"),
            changed_at=self.now - timedelta(hours=1),
        )

        increased = self.create_listing("V296 Later Increase")
        self.change_price(
            increased,
            "700.00",
            changed_at=self.now - timedelta(hours=2),
        )
        self.change_price(
            increased,
            "900.00",
            changed_at=self.now - timedelta(hours=1),
        )

        mismatch = self.create_listing("V296 Current Mismatch")
        self.change_price(mismatch, "800.00")
        Listing.objects.filter(pk=mismatch.pk).update(
            price=Decimal("850.00")
        )

        response = self.deals()
        titles = self.response_titles(response)

        self.assertIn(valid.title, titles)
        for excluded in (
            "V296 Baseline Only",
            noop.title,
            stale.title,
            increased.title,
            mismatch.title,
        ):
            with self.subTest(excluded=excluded):
                self.assertNotIn(excluded, titles)

    def test_zero_or_missing_previous_price_is_excluded(self):
        missing = self.create_listing(
            "V296 Missing Previous Price"
        )

        zero = self.create_listing(
            "V296 Zero Previous Price",
            price="0.00",
        )
        Listing.objects.filter(pk=zero.pk).update(
            price=Decimal("-1.00")
        )
        ListingPriceHistory.objects.create(
            listing=zero,
            previous_price=Decimal("0.00"),
            new_price=Decimal("-1.00"),
            changed_at=self.now + timedelta(minutes=1),
        )

        response = self.deals()
        titles = self.response_titles(response)

        self.assertNotIn(missing.title, titles)
        self.assertNotIn(zero.title, titles)

    def test_v293_guardrail_excludes_raise_then_drop(self):
        guarded = self.create_listing(
            "V296 Guarded Deal",
            price="100.00",
        )
        self.change_price(guarded, "200.00")
        restricted = self.change_price(guarded, "150.00")
        restricted.refresh_from_db()

        clean = self.create_listing(
            "V296 Genuine Deal",
            price="200.00",
        )
        self.change_price(clean, "150.00")

        response = self.deals()
        titles = self.response_titles(response)

        self.assertEqual(
            restricted.discount_guardrail_status,
            DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        )
        self.assertNotIn(guarded.title, titles)
        self.assertIn(clean.title, titles)
        self.assertNotContains(
            response,
            "raise_then_drop",
        )
        self.assertNotContains(
            response,
            "discount_reference_price",
        )

    def test_public_visibility_expiry_and_deletion_rules(self):
        valid = self.create_listing(
            "V296 Public Deal",
            expires_at=self.now + timedelta(days=30),
        )
        self.change_price(valid, "800.00")

        hidden_listings = []
        for status in (
            Listing.Status.DRAFT,
            Listing.Status.PENDING,
            Listing.Status.REJECTED,
            Listing.Status.ARCHIVED,
            Listing.Status.SUSPENDED,
        ):
            listing = self.create_listing(
                f"V296 Hidden {status}",
                status=status,
            )
            self.change_price(listing, "800.00")
            hidden_listings.append(listing)

        expired = self.create_listing(
            "V296 Expired Deal",
            expires_at=self.now - timedelta(seconds=1),
        )
        self.change_price(expired, "800.00")
        hidden_listings.append(expired)

        deleted = self.create_listing(
            "V296 Deleted Deal"
        )
        self.change_price(deleted, "800.00")
        deleted_title = deleted.title
        deleted.delete()

        response = self.deals()
        titles = self.response_titles(response)

        self.assertIn(valid.title, titles)
        for hidden in hidden_listings:
            with self.subTest(hidden=hidden.title):
                self.assertNotIn(hidden.title, titles)
        self.assertNotIn(deleted_title, titles)

    def test_pagination_uses_twelve_deals_and_semantic_navigation(self):
        for index in range(13):
            listing = self.create_listing(
                f"V296 Paginated Deal {index:02d}"
            )
            self.change_price(
                listing,
                "500.00",
                changed_at=self.now - timedelta(minutes=index),
            )

        first_page = self.deals()
        second_page = self.deals({"page": "2"})

        self.assertEqual(
            first_page.context["page_obj"].paginator.count,
            13,
        )
        self.assertEqual(len(first_page.context["listings"]), 12)
        self.assertEqual(len(second_page.context["listings"]), 1)
        self.assertContains(
            first_page,
            'aria-label="Deals pages"',
        )
        self.assertContains(first_page, 'href="?page=2"')
        self.assertContains(second_page, "Page 2 of 2")

    def test_accessible_semantic_markup_and_shared_card_contracts(self):
        listing = self.create_listing(
            "V296 Accessible Deal"
        )
        self.change_price(listing, "800.00")

        response = self.deals()
        html = response.content.decode("utf-8")

        self.assertContains(
            response,
            'data-public-deals-page-v296="true"',
        )
        self.assertContains(
            response,
            'aria-labelledby="public-deals-heading-v296"',
        )
        self.assertContains(
            response,
            'aria-label="Deals results summary"',
        )
        self.assertContains(
            response,
            'aria-label="Available deals"',
        )
        self.assertContains(response, "<del", html=False)
        self.assertContains(
            response,
            'role="group"',
        )
        self.assertEqual(html.count("<main"), 1)
        self.assertEqual(html.count("</main>"), 1)

    def test_page_query_count_does_not_grow_per_card(self):
        first = self.create_listing(
            "V296 Query Deal 00"
        )
        self.change_price(first, "800.00")

        self.deals()

        with CaptureQueriesContext(connection) as one_capture:
            one_response = self.deals()
            self.assertEqual(one_response.status_code, 200)

        for index in range(1, 12):
            listing = self.create_listing(
                f"V296 Query Deal {index:02d}"
            )
            self.change_price(
                listing,
                str(800 - index),
            )

        with CaptureQueriesContext(connection) as many_capture:
            many_response = self.deals()
            self.assertEqual(many_response.status_code, 200)

        self.assertEqual(
            len(one_capture),
            len(many_capture),
        )

    def test_v278_v295_compatibility_contract_and_no_migration(self):
        migration_directory = (
            Path(settings.BASE_DIR)
            / "listings"
            / "migrations"
        )
        card_source = (
            Path(settings.BASE_DIR)
            / "listings"
            / "templates"
            / "listings"
            / "_listing_card.html"
        ).read_text(encoding="utf-8")
        self.assertTrue(PUBLIC_DEALS_LANDING_PAGE_V296)
        self.assertEqual(PUBLIC_DEALS_PAGE_SIZE_V296, 12)
        self.assertTrue(BIGGEST_PRICE_DROP_SORT_V281)
        self.assertTrue(ENHANCED_LISTING_CARD_DISCOUNT_V284)
        self.assertIn(
            "ENHANCED_LISTING_CARD_DISCOUNT_V284",
            card_source,
        )
        self.assertIn(
            "listing_compare_toggle",
            card_source,
        )
        self.assertIn(
            "listing_favorite_toggle",
            card_source,
        )
        self.assertEqual(
            list(migration_directory.glob("*v296*")),
            [],
        )
        self.assertEqual(
            len(
                list(
                    migration_directory.glob(
                        "0023_listingpricehistory_discount_guardrail_v293.py"
                    )
                )
            ),
            1,
        )
