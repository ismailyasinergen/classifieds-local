"""
RELATED_LISTINGS_RECOMMENDATIONS_V271

Product-roadmap re-entry tests for user-visible related listings on the
listing-detail page.
"""

from __future__ import annotations

import ast
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import (
    resolve,
    reverse,
)
from django.utils import timezone

from accounts.models import (
    SellerStore,
    UserProfile,
)
from categories.models import Category

from listings import (
    listing_browse_detail_views,
    views as listing_views,
)
from listings.listing_recommendations import (
    RELATED_LISTINGS_DEFAULT_LIMIT_V271,
    RELATED_LISTINGS_MAX_LIMIT_V271,
    RELATED_LISTINGS_RECOMMENDATIONS_V271,
    get_related_listings_v271,
    normalize_related_listings_limit_v271,
)
from listings.listing_detail_asset_contract_v325 import (
    read_listing_detail_contract_source_v325,
)
from listings.models import Listing


V271_PRODUCT_ROADMAP_REENTRY = True
V271_SELECTED_FEATURE = "related listings recommendations"
V271_USER_OUTCOME = (
    "buyers can continue browsing relevant active listings "
    "without returning to search results"
)

V271_ALLOWED_SCOPE = (
    "backend/listings/listing_recommendations.py",
    "backend/listings/listing_browse_detail_views.py",
    (
        "backend/listings/templates/listings/"
        "listing_detail.html"
    ),
    (
        "backend/listings/"
        "test_related_listings_recommendations_v271.py"
    ),
    "docs/related_listings_recommendations_v271.md",
)


class RelatedListingsRecommendationsV271Tests(
    TestCase
):
    maxDiff = None

    def setUp(self):
        self.User = get_user_model()

        self.seller = self.User.objects.create_user(
            username="v271-seller",
            email="v271-seller@classifieds.local",
            password="StrongPass123!",
        )

        self.other_seller = self.User.objects.create_user(
            username="v271-other-seller",
            email="v271-other@classifieds.local",
            password="StrongPass123!",
        )

        for user in (
            self.seller,
            self.other_seller,
        ):
            UserProfile.objects.get_or_create(
                user=user,
            )
            SellerStore.objects.get_or_create(
                owner=user,
            )

        self.category = Category.objects.create(
            name="V271 Furniture",
            slug="v271-furniture",
        )

        self.other_category = Category.objects.create(
            name="V271 Electronics",
            slug="v271-electronics",
        )

        self.current = self._create_listing(
            title="V271 Current Listing",
            owner=self.seller,
            category=self.category,
            location="Berlin",
        )

    def _create_listing(
        self,
        *,
        title,
        owner,
        category,
        location="Berlin",
        status=Listing.Status.APPROVED,
        expires_at=None,
        top_listing_priority=0,
        is_featured=False,
    ):
        return Listing.objects.create(
            title=title,
            description=(
                f"Description for {title}"
            ),
            price=Decimal("125.00"),
            location=location,
            category=category,
            owner=owner,
            status=status,
            expires_at=expires_at,
            top_listing_priority=(
                top_listing_priority
            ),
            is_featured=is_featured,
        )

    def test_v271_scope_and_product_selection_are_explicit(self):
        self.assertTrue(
            V271_PRODUCT_ROADMAP_REENTRY
        )

        self.assertEqual(
            V271_SELECTED_FEATURE,
            "related listings recommendations",
        )

        self.assertEqual(
            len(V271_ALLOWED_SCOPE),
            5,
        )

        self.assertIn(
            "buyers can continue browsing",
            V271_USER_OUTCOME,
        )

    def test_v271_limit_normalization_is_bounded(self):
        self.assertEqual(
            RELATED_LISTINGS_DEFAULT_LIMIT_V271,
            4,
        )

        self.assertEqual(
            RELATED_LISTINGS_MAX_LIMIT_V271,
            8,
        )

        self.assertEqual(
            normalize_related_listings_limit_v271(
                "invalid"
            ),
            4,
        )

        self.assertEqual(
            normalize_related_listings_limit_v271(
                0
            ),
            1,
        )

        self.assertEqual(
            normalize_related_listings_limit_v271(
                100
            ),
            8,
        )

    def test_v271_service_returns_only_active_approved_same_category(self):
        valid = self._create_listing(
            title="V271 Valid Related",
            owner=self.other_seller,
            category=self.category,
        )

        self._create_listing(
            title="V271 Pending Related",
            owner=self.other_seller,
            category=self.category,
            status=Listing.Status.PENDING,
        )

        self._create_listing(
            title="V271 Expired Related",
            owner=self.other_seller,
            category=self.category,
            expires_at=(
                timezone.now()
                - timedelta(
                    minutes=1
                )
            ),
        )

        self._create_listing(
            title="V271 Other Category",
            owner=self.other_seller,
            category=self.other_category,
        )

        result = get_related_listings_v271(
            self.current
        )

        self.assertEqual(
            [listing.pk for listing in result],
            [valid.pk],
        )

    def test_v271_service_excludes_current_listing(self):
        self.assertNotIn(
            self.current.pk,
            [
                listing.pk
                for listing in (
                    get_related_listings_v271(
                        self.current
                    )
                )
            ],
        )

    def test_v271_service_is_limited_to_four_by_default(self):
        for index in range(6):
            self._create_listing(
                title=f"V271 Related {index}",
                owner=self.other_seller,
                category=self.category,
            )

        result = get_related_listings_v271(
            self.current
        )

        self.assertEqual(
            len(result),
            4,
        )

    def test_v271_exact_location_match_ranks_first(self):
        other_location = self._create_listing(
            title="V271 Munich Related",
            owner=self.other_seller,
            category=self.category,
            location="Munich",
            top_listing_priority=100,
        )

        berlin = self._create_listing(
            title="V271 Berlin Related",
            owner=self.other_seller,
            category=self.category,
            location="berlin",
            top_listing_priority=0,
        )

        result = get_related_listings_v271(
            self.current,
            limit=2,
        )

        self.assertEqual(
            result[0].pk,
            berlin.pk,
        )

        self.assertEqual(
            result[1].pk,
            other_location.pk,
        )

    def test_v271_marketplace_priority_orders_within_location(self):
        lower = self._create_listing(
            title="V271 Lower Priority",
            owner=self.other_seller,
            category=self.category,
            top_listing_priority=1,
        )

        higher = self._create_listing(
            title="V271 Higher Priority",
            owner=self.other_seller,
            category=self.category,
            top_listing_priority=10,
        )

        result = get_related_listings_v271(
            self.current,
            limit=2,
        )

        self.assertEqual(
            [listing.pk for listing in result],
            [
                higher.pk,
                lower.pk,
            ],
        )

    def test_v271_missing_listing_or_category_returns_empty(self):
        self.assertEqual(
            get_related_listings_v271(
                None
            ),
            [],
        )

        unsaved = Listing(
            title="Unsaved",
        )

        self.assertEqual(
            get_related_listings_v271(
                unsaved
            ),
            [],
        )

    def test_v271_detail_context_contains_related_listings(self):
        related = self._create_listing(
            title="V271 Visible Recommendation",
            owner=self.other_seller,
            category=self.category,
        )

        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.current.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertIn(
            "related_listings",
            response.context,
        )

        self.assertEqual(
            [
                listing.pk
                for listing
                in response.context[
                    "related_listings"
                ]
            ],
            [
                related.pk,
            ],
        )

    def test_v271_detail_renders_user_visible_similar_listings_section(self):
        self._create_listing(
            title="V271 Recommended Oak Cabinet",
            owner=self.other_seller,
            category=self.category,
        )

        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.current.pk,
                },
            )
        )

        self.assertContains(
            response,
            "Similar listings",
        )

        self.assertContains(
            response,
            "V271 Recommended Oak Cabinet",
        )

        self.assertContains(
            response,
            "RELATED_LISTINGS_RECOMMENDATIONS_V271",
        )

        self.assertContains(
            response,
            "View all in V271 Furniture",
        )

    def test_v271_section_is_hidden_when_no_related_listing_exists(self):
        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.current.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertNotContains(
            response,
            "Similar listings",
        )

        self.assertEqual(
            response.context[
                "related_listings"
            ],
            [],
        )

    def test_v271_pending_and_expired_titles_do_not_leak_into_page(self):
        self._create_listing(
            title="V271 Private Pending Title",
            owner=self.other_seller,
            category=self.category,
            status=Listing.Status.PENDING,
        )

        self._create_listing(
            title="V271 Private Expired Title",
            owner=self.other_seller,
            category=self.category,
            expires_at=(
                timezone.now()
                - timedelta(
                    seconds=1
                )
            ),
        )

        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.current.pk,
                },
            )
        )

        self.assertNotContains(
            response,
            "V271 Private Pending Title",
        )

        self.assertNotContains(
            response,
            "V271 Private Expired Title",
        )

    def test_v271_detail_url_still_resolves_to_dedicated_view(self):
        url = reverse(
            "listings:listing_detail",
            kwargs={
                "pk": self.current.pk,
            },
        )

        match = resolve(
            url
        )

        view_class = getattr(
            match.func,
            "view_class",
            None,
        )

        self.assertIs(
            view_class,
            listing_views.ListingDetailView,
        )

        self.assertIs(
            view_class,
            listing_browse_detail_views.ListingDetailView,
        )

    def test_v271_listing_detail_keeps_v157_line_count_contract(self):
        source = Path(
            "listings/"
            "listing_browse_detail_views.py"
        ).read_text(
            encoding="utf-8",
        )

        tree = ast.parse(
            source
        )

        classes = {
            node.name: node
            for node in tree.body
            if isinstance(
                node,
                ast.ClassDef,
            )
        }

        target = classes[
            "ListingDetailView"
        ]

        line_count = (
            (
                target.end_lineno
                or target.lineno
            )
            - target.lineno
            + 1
        )

        self.assertEqual(
            line_count,
            48,
        )

        self.assertIn(
            "RelatedListingsContextMixinV271",
            classes,
        )

    def test_v271_source_and_template_markers_are_present(self):
        service_source = Path(
            "listings/"
            "listing_recommendations.py"
        ).read_text(
            encoding="utf-8",
        )

        view_source = Path(
            "listings/"
            "listing_browse_detail_views.py"
        ).read_text(
            encoding="utf-8",
        )

        template_source = read_listing_detail_contract_source_v325(
            Path(__file__).resolve().parents[1],
        )

        for source in (
            service_source,
            view_source,
            template_source,
        ):
            self.assertIn(
                "RELATED_LISTINGS_RECOMMENDATIONS_V271",
                source,
            )

        self.assertIn(
            (
                '{% include "listings/_listing_card.html" '
                "with listing=related_listing"
            ),
            template_source,
        )

    def test_v271_service_is_read_only(self):
        self._create_listing(
            title="V271 Read Only Related",
            owner=self.other_seller,
            category=self.category,
        )

        before = list(
            Listing.objects.values_list(
                "pk",
                "status",
                "created_at",
            )
        )

        get_related_listings_v271(
            self.current
        )

        after = list(
            Listing.objects.values_list(
                "pk",
                "status",
                "created_at",
            )
        )

        self.assertEqual(
            before,
            after,
        )

    def test_v271_no_migration_0017_exists(self):
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

    def test_v271_public_service_marker_is_stable(self):
        self.assertTrue(
            RELATED_LISTINGS_RECOMMENDATIONS_V271
        )
