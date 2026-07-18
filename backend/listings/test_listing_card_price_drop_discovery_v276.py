from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import (
    get_user_model,
)
from django.contrib.auth.models import AnonymousUser
from django.db import connection
from django.template import RequestContext, Template
from django.test import (
    RequestFactory,
    TestCase,
)
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import (
    SellerStore,
    UserProfile,
)
from categories.models import Category
from listings.listing_price_drop_discovery_v276 import (
    LISTING_CARD_PRICE_DROP_CONTEXT_LIMIT_V276,
    V276_LISTING_CARD_PRICE_DROP_DISCOVERY,
    collect_listing_ids_from_template_context_v276,
    get_current_listing_price_drops_v276,
)
from listings.models import (
    Listing,
    ListingPriceHistory,
)


V276_MARKER = (
    "V276_LISTING_CARD_PRICE_DROP_DISCOVERY"
)


class ListingCardPriceDropDiscoveryV276Tests(
    TestCase
):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.seller = User.objects.create_user(
            username="v276-price-drop-seller",
            email="v276-seller@example.test",
            password="StrongPass123!",
        )

        UserProfile.objects.get_or_create(
            user=cls.seller,
        )

        cls.category = Category.objects.create(
            name="V276 Furniture",
            slug="v276-furniture",
        )

        cls.other_category = Category.objects.create(
            name="V276 Vehicles",
            slug="v276-vehicles",
        )

    def create_listing(
        self,
        title,
        *,
        price="1000.00",
        category=None,
        status=Listing.Status.APPROVED,
        expires_at=None,
    ):
        return Listing.objects.create(
            title=title,
            description=(
                f"{title} listing-card price-drop "
                "discovery test."
            ),
            price=Decimal(str(price)),
            category=category or self.category,
            owner=self.seller,
            location="Berlin",
            status=status,
            expires_at=expires_at,
        )

    def reduce_price(
        self,
        listing,
        new_price="900.00",
    ):
        listing.price = Decimal(str(new_price))
        listing.save(update_fields=["price"])
        listing.refresh_from_db()
        return listing

    def card_template_source(self):
        return (
            Path(settings.BASE_DIR)
            / "listings"
            / "templates"
            / "listings"
            / "_listing_card.html"
        ).read_text(
            encoding="utf-8",
        )

    def test_v276_contract_constants_are_declared(self):
        self.assertTrue(
            V276_LISTING_CARD_PRICE_DROP_DISCOVERY
        )

        self.assertEqual(
            LISTING_CARD_PRICE_DROP_CONTEXT_LIMIT_V276,
            1000,
        )

    def test_baseline_only_listing_has_no_drop(self):
        listing = self.create_listing(
            "Baseline Only Card"
        )

        result = (
            get_current_listing_price_drops_v276(
                [listing.pk]
            )
        )

        self.assertEqual(result, {})

    def test_latest_real_reduction_returns_card_summary(self):
        listing = self.create_listing(
            "Reduced Card Listing"
        )

        self.reduce_price(
            listing,
            "900.00",
        )

        discovery = (
            get_current_listing_price_drops_v276(
                [listing.pk]
            )[listing.pk]
        )

        self.assertEqual(
            discovery.previous_price,
            Decimal("1000.00"),
        )

        self.assertEqual(
            discovery.current_price,
            Decimal("900.00"),
        )

        self.assertEqual(
            discovery.saving_amount,
            Decimal("100.00"),
        )

        self.assertEqual(
            discovery.saving_percentage,
            Decimal("10.00"),
        )

        self.assertTrue(
            discovery.has_percentage
        )

    def test_latest_increase_hides_earlier_drop(self):
        listing = self.create_listing(
            "Drop Then Increase"
        )

        self.reduce_price(
            listing,
            "900.00",
        )

        listing.price = Decimal("950.00")
        listing.save(update_fields=["price"])

        result = (
            get_current_listing_price_drops_v276(
                [listing.pk]
            )
        )

        self.assertNotIn(
            listing.pk,
            result,
        )

    def test_stale_transition_does_not_leak_drop(self):
        listing = self.create_listing(
            "Stale Transition Listing"
        )

        self.reduce_price(
            listing,
            "900.00",
        )

        Listing.objects.filter(
            pk=listing.pk,
        ).update(
            price=Decimal("950.00"),
        )

        result = (
            get_current_listing_price_drops_v276(
                [listing.pk]
            )
        )

        self.assertNotIn(
            listing.pk,
            result,
        )

    def test_pending_and_expired_listings_are_hidden(self):
        pending = self.create_listing(
            "Pending Reduced Listing",
            status=Listing.Status.PENDING,
        )

        expired = self.create_listing(
            "Expired Reduced Listing",
            expires_at=(
                timezone.now()
                - timezone.timedelta(days=1)
            ),
        )

        self.reduce_price(
            pending,
            "900.00",
        )

        self.reduce_price(
            expired,
            "900.00",
        )

        result = (
            get_current_listing_price_drops_v276(
                [
                    pending.pk,
                    expired.pk,
                ]
            )
        )

        self.assertEqual(result, {})

    def test_zero_previous_price_omits_percentage(self):
        listing = self.create_listing(
            "Zero Previous Price",
            price="0.00",
        )

        Listing.objects.filter(
            pk=listing.pk,
        ).update(
            price=Decimal("-1.00"),
        )

        ListingPriceHistory.objects.create(
            listing=listing,
            previous_price=Decimal("0.00"),
            new_price=Decimal("-1.00"),
        )

        discovery = (
            get_current_listing_price_drops_v276(
                [listing.pk]
            )[listing.pk]
        )

        self.assertEqual(
            discovery.saving_amount,
            Decimal("1.00"),
        )

        self.assertIsNone(
            discovery.saving_percentage
        )

        self.assertFalse(
            discovery.has_percentage
        )

    def test_unchanged_save_does_not_duplicate_history(self):
        listing = self.create_listing(
            "Unchanged Reduced Listing"
        )

        self.reduce_price(
            listing,
            "900.00",
        )

        count_before = (
            ListingPriceHistory.objects
            .filter(listing=listing)
            .count()
        )

        listing.price = Decimal("900.00")
        listing.save(update_fields=["price"])

        count_after = (
            ListingPriceHistory.objects
            .filter(listing=listing)
            .count()
        )

        self.assertEqual(
            count_after,
            count_before,
        )

    def test_template_context_collects_all_card_surfaces(self):
        listing_one = self.create_listing(
            "Context Listing One"
        )

        listing_two = self.create_listing(
            "Context Listing Two"
        )

        listing_three = self.create_listing(
            "Context Listing Three"
        )

        context = {
            "listings": [listing_one],
            "related_listings": [listing_two],
            "category_sections": [
                {
                    "category": self.category,
                    "listings": [listing_three],
                }
            ],
        }

        result = (
            collect_listing_ids_from_template_context_v276(
                context,
            )
        )

        self.assertEqual(
            set(result),
            {
                listing_one.pk,
                listing_two.pk,
                listing_three.pk,
            },
        )

    def test_batch_tag_query_count_does_not_grow_with_cards(
        self,
    ):
        listings = []

        for index in range(12):
            listing = self.create_listing(
                f"Query Count Reduced {index:02d}"
            )

            self.reduce_price(
                listing,
                str(900 - index),
            )

            listings.append(listing)

        template = Template(
            """
            {% load listing_price_drop_discovery_v276 %}
            {% for listing in listings %}
                {% listing_card_price_drop_v276 listing as drop %}
                {% if drop %}{{ drop.listing_id }}{% endif %}
            {% endfor %}
            """
        )

        def render_count(card_list):
            request = RequestFactory().get(
                "/listings/"
            )

            request.user = AnonymousUser()

            context = RequestContext(
                request,
                {
                    "listings": card_list,
                },
            )

            with CaptureQueriesContext(
                connection
            ) as captured:
                template.render(context)

            return len(captured)

        one_card_queries = render_count(
            listings[:1]
        )

        twelve_card_queries = render_count(
            listings
        )

        self.assertEqual(
            one_card_queries,
            1,
        )

        self.assertEqual(
            twelve_card_queries,
            1,
        )

    def test_shared_card_template_preserves_v274_contract(self):
        source = self.card_template_source()

        self.assertIn(
            V276_MARKER,
            source,
        )

        self.assertIn(
            "{% load listing_comparison_v274 %}",
            source,
        )

        self.assertIn(
            "LISTING_COMPARISON_V274",
            source,
        )

        self.assertIn(
            "listing-comparison-action-v274",
            source,
        )

        self.assertIn(
            "listing_compare_toggle",
            source,
        )

        self.assertIn(
            'value="{{ request.path }}"',
            source,
        )

        self.assertIn(
            "{{ listing.price }} TL",
            source,
        )

        self.assertIn(
            "listing-price-drop-badge-v276",
            source,
        )

        self.assertIn(
            "listing-card-previous-price-v276",
            source,
        )

        self.assertIn(
            "listing-card-saving-v276",
            source,
        )

    def test_public_browse_card_renders_drop(self):
        listing = self.create_listing(
            "Browse Reduced Listing"
        )

        self.reduce_price(
            listing,
            "900.00",
        )

        response = self.client.get(
            reverse("listings:listing_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            listing.title,
        )

        self.assertContains(
            response,
            'data-price-drop-card-v276="true"',
        )

        self.assertContains(
            response,
            "Price dropped",
        )

        self.assertContains(
            response,
            "Save 100.00 TL",
        )

    def test_seller_store_cards_render_drop(self):
        store, _created = (
            SellerStore.objects.get_or_create(
                owner=self.seller,
                defaults={
                    "name": "V276 Seller Store",
                    "headline": (
                        "Price-drop discovery store."
                    ),
                    "location": "Berlin",
                    "is_active": True,
                },
            )
        )

        store.name = "V276 Seller Store"
        store.is_active = True
        store.save()

        listing = self.create_listing(
            "Seller Store Reduced Listing"
        )

        self.reduce_price(
            listing,
            "900.00",
        )

        response = self.client.get(
            reverse(
                "accounts:seller_store_public",
                kwargs={
                    "slug": store.slug,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertContains(
            response,
            listing.title,
        )

        self.assertContains(
            response,
            'data-price-drop-card-v276="true"',
        )

    def test_related_listing_card_renders_drop(self):
        current = self.create_listing(
            "Current Related Detail"
        )

        related = self.create_listing(
            "Related Reduced Listing"
        )

        self.reduce_price(
            related,
            "900.00",
        )

        response = self.client.get(
            current.get_absolute_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        related_ids = [
            item.pk
            for item in response.context_data[
                "related_listings"
            ]
        ]

        self.assertIn(
            related.pk,
            related_ids,
        )

        content = response.content.decode()

        related_anchor = (
            'data-marker='
            '"RELATED_LISTINGS_RECOMMENDATIONS_V271"'
        )

        recent_anchor = (
            'data-marker='
            '"RECENTLY_VIEWED_LISTINGS_V272"'
        )

        self.assertIn(
            related_anchor,
            content,
        )

        start = content.index(
            related_anchor
        )

        end = content.find(
            recent_anchor,
            start,
        )

        segment = (
            content[start:end]
            if end >= 0
            else content[start:]
        )

        self.assertIn(
            related.title,
            segment,
        )

        self.assertIn(
            'data-price-drop-card-v276="true"',
            segment,
        )

    def test_recently_viewed_card_renders_drop(self):
        recent = self.create_listing(
            "Recently Viewed Reduced Listing",
            category=self.other_category,
        )

        current = self.create_listing(
            "Current Recently Viewed Detail",
            category=self.category,
        )

        self.reduce_price(
            recent,
            "900.00",
        )

        first_response = self.client.get(
            recent.get_absolute_url()
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )

        response = self.client.get(
            current.get_absolute_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        content = response.content.decode()

        start = content.index(
            "RECENTLY_VIEWED_LISTINGS_V272"
        )

        segment = content[start:]

        self.assertIn(
            recent.title,
            segment,
        )

        self.assertIn(
            'data-price-drop-card-v276="true"',
            segment,
        )

    def test_v275_detail_price_drop_remains_intact(self):
        listing = self.create_listing(
            "V275 Detail Compatibility"
        )

        self.reduce_price(
            listing,
            "900.00",
        )

        response = self.client.get(
            listing.get_absolute_url()
        )

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
            "Price history",
        )

    def test_v276_adds_no_migration(self):
        migration_root = (
            Path(settings.BASE_DIR)
            / "listings"
            / "migrations"
        )

        self.assertFalse(
            list(
                migration_root.glob("0017*")
            )
        )

        self.assertFalse(
            list(
                migration_root.glob("0019*")
            )
        )

        self.assertEqual(
            len(
                list(
                    migration_root.glob("0018*")
                )
            ),
            1,
        )
