"""
RECENTLY_VIEWED_LISTINGS_V272

Tests for session-based recently-viewed listings on listing detail pages.
"""

from __future__ import annotations

import ast
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import (
    RequestFactory,
    TestCase,
)
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
from listings.listing_recently_viewed import (
    RECENTLY_VIEWED_DISPLAY_LIMIT_V272,
    RECENTLY_VIEWED_HISTORY_LIMIT_V272,
    RECENTLY_VIEWED_LISTINGS_V272,
    RECENTLY_VIEWED_MAX_DISPLAY_LIMIT_V272,
    RECENTLY_VIEWED_SESSION_KEY_V272,
    get_recently_viewed_listings_v272,
    listing_is_publicly_viewable_v272,
    normalize_recently_viewed_display_limit_v272,
    normalize_recently_viewed_listing_ids_v272,
    record_recently_viewed_listing_v272,
)
from listings.listing_detail_asset_contract_v325 import (
    read_listing_detail_contract_source_v325,
)
from listings.models import Listing


V271_COMPATIBILITY_MARKER = "RELATED_LISTINGS_RECOMMENDATIONS_V271"
V272_PRODUCT_FEATURE = "recently viewed listings"
V272_STORAGE_BOUNDARY = "Django session only"
V272_ALLOWED_SCOPE = (
    "backend/listings/listing_recently_viewed.py",
    "backend/listings/listing_browse_detail_views.py",
    (
        "backend/listings/templates/listings/"
        "listing_detail.html"
    ),
    (
        "backend/listings/"
        "test_recently_viewed_listings_v272.py"
    ),
    "docs/recently_viewed_listings_v272.md",
)


class RecentlyViewedListingsV272Tests(
    TestCase
):
    maxDiff = None

    def setUp(self):
        self.User = get_user_model()

        self.seller = self.User.objects.create_user(
            username="v272-seller",
            email="v272-seller@classifieds.local",
            password="StrongPass123!",
        )

        self.other_seller = self.User.objects.create_user(
            username="v272-other-seller",
            email="v272-other@classifieds.local",
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
            name="V272 Furniture",
            slug="v272-furniture",
        )

        self.other_category = Category.objects.create(
            name="V272 Electronics",
            slug="v272-electronics",
        )

        self.listing_a = self._create_listing(
            title="V272 Listing A",
        )

        self.listing_b = self._create_listing(
            title="V272 Listing B",
            owner=self.other_seller,
        )

        self.listing_c = self._create_listing(
            title="V272 Listing C",
            owner=self.other_seller,
        )

    def _create_listing(
        self,
        *,
        title,
        owner=None,
        category=None,
        status=Listing.Status.APPROVED,
        expires_at=None,
    ):
        return Listing.objects.create(
            title=title,
            description=(
                f"Description for {title}"
            ),
            price=Decimal("125.00"),
            location="Berlin",
            category=(
                category
                or self.category
            ),
            owner=(
                owner
                or self.seller
            ),
            status=status,
            expires_at=expires_at,
        )

    def _request_with_session(self):
        request = RequestFactory().get(
            "/"
        )

        middleware = SessionMiddleware(
            lambda active_request: None
        )

        middleware.process_request(
            request
        )

        request.session.save()

        return request

    def test_v272_scope_and_storage_boundary_are_explicit(self):
        self.assertTrue(
            RECENTLY_VIEWED_LISTINGS_V272
        )

        self.assertTrue(
            V271_COMPATIBILITY_MARKER.endswith(
                "_V271"
            )
        )

        self.assertEqual(
            V272_PRODUCT_FEATURE,
            "recently viewed listings",
        )

        self.assertEqual(
            V272_STORAGE_BOUNDARY,
            "Django session only",
        )

        self.assertEqual(
            len(V272_ALLOWED_SCOPE),
            5,
        )

    def test_v272_limits_and_session_key_are_stable(self):
        self.assertEqual(
            RECENTLY_VIEWED_DISPLAY_LIMIT_V272,
            4,
        )

        self.assertEqual(
            RECENTLY_VIEWED_HISTORY_LIMIT_V272,
            12,
        )

        self.assertEqual(
            RECENTLY_VIEWED_MAX_DISPLAY_LIMIT_V272,
            8,
        )

        self.assertEqual(
            RECENTLY_VIEWED_SESSION_KEY_V272,
            "recently_viewed_listing_ids_v272",
        )

    def test_v272_id_normalization_is_positive_unique_and_bounded(self):
        values = [
            "3",
            3,
            2,
            True,
            0,
            -1,
            "invalid",
            1,
            *range(
                4,
                30,
            ),
        ]

        result = (
            normalize_recently_viewed_listing_ids_v272(
                values
            )
        )

        self.assertEqual(
            result[:3],
            [
                3,
                2,
                1,
            ],
        )

        self.assertEqual(
            len(result),
            12,
        )

        self.assertEqual(
            len(result),
            len(set(result)),
        )

    def test_v272_display_limit_is_bounded(self):
        self.assertEqual(
            normalize_recently_viewed_display_limit_v272(
                "invalid"
            ),
            4,
        )

        self.assertEqual(
            normalize_recently_viewed_display_limit_v272(
                0
            ),
            1,
        )

        self.assertEqual(
            normalize_recently_viewed_display_limit_v272(
                100
            ),
            8,
        )

    def test_v272_public_visibility_rejects_pending_and_expired(self):
        pending = self._create_listing(
            title="V272 Pending",
            status=Listing.Status.PENDING,
        )

        expired = self._create_listing(
            title="V272 Expired",
            expires_at=(
                timezone.now()
                - timedelta(
                    seconds=1
                )
            ),
        )

        self.assertTrue(
            listing_is_publicly_viewable_v272(
                self.listing_a
            )
        )

        self.assertFalse(
            listing_is_publicly_viewable_v272(
                pending
            )
        )

        self.assertFalse(
            listing_is_publicly_viewable_v272(
                expired
            )
        )

    def test_v272_recording_is_newest_first_and_deduplicated(self):
        request = self._request_with_session()

        self.assertTrue(
            record_recently_viewed_listing_v272(
                request,
                self.listing_a,
            )
        )

        self.assertTrue(
            record_recently_viewed_listing_v272(
                request,
                self.listing_b,
            )
        )

        self.assertTrue(
            record_recently_viewed_listing_v272(
                request,
                self.listing_a,
            )
        )

        self.assertEqual(
            request.session[
                RECENTLY_VIEWED_SESSION_KEY_V272
            ],
            [
                self.listing_a.pk,
                self.listing_b.pk,
            ],
        )

    def test_v272_recording_keeps_only_twelve_ids(self):
        request = self._request_with_session()

        listings = [
            self._create_listing(
                title=f"V272 History {index}",
                owner=self.other_seller,
            )
            for index in range(15)
        ]

        for listing in listings:
            record_recently_viewed_listing_v272(
                request,
                listing,
            )

        history = request.session[
            RECENTLY_VIEWED_SESSION_KEY_V272
        ]

        self.assertEqual(
            len(history),
            12,
        )

        self.assertEqual(
            history[0],
            listings[-1].pk,
        )

        self.assertNotIn(
            listings[0].pk,
            history,
        )

    def test_v272_pending_and_expired_listings_are_not_recorded(self):
        request = self._request_with_session()

        pending = self._create_listing(
            title="V272 Pending Record",
            status=Listing.Status.PENDING,
        )

        expired = self._create_listing(
            title="V272 Expired Record",
            expires_at=(
                timezone.now()
                - timedelta(
                    seconds=1
                )
            ),
        )

        self.assertFalse(
            record_recently_viewed_listing_v272(
                request,
                pending,
            )
        )

        self.assertFalse(
            record_recently_viewed_listing_v272(
                request,
                expired,
            )
        )

        self.assertNotIn(
            RECENTLY_VIEWED_SESSION_KEY_V272,
            request.session,
        )

    def test_v272_service_preserves_session_recency_order(self):
        request = self._request_with_session()

        request.session[
            RECENTLY_VIEWED_SESSION_KEY_V272
        ] = [
            self.listing_c.pk,
            self.listing_a.pk,
            self.listing_b.pk,
        ]

        result = (
            get_recently_viewed_listings_v272(
                request,
            )
        )

        self.assertEqual(
            [
                listing.pk
                for listing in result
            ],
            [
                self.listing_c.pk,
                self.listing_a.pk,
                self.listing_b.pk,
            ],
        )

    def test_v272_service_excludes_current_listing(self):
        request = self._request_with_session()

        request.session[
            RECENTLY_VIEWED_SESSION_KEY_V272
        ] = [
            self.listing_b.pk,
            self.listing_a.pk,
        ]

        result = (
            get_recently_viewed_listings_v272(
                request,
                current_listing=self.listing_b,
            )
        )

        self.assertEqual(
            [
                listing.pk
                for listing in result
            ],
            [
                self.listing_a.pk,
            ],
        )

    def test_v272_service_filters_stale_session_ids(self):
        request = self._request_with_session()

        pending = self._create_listing(
            title="V272 Private Pending",
            status=Listing.Status.PENDING,
        )

        expired = self._create_listing(
            title="V272 Private Expired",
            expires_at=(
                timezone.now()
                - timedelta(
                    seconds=1
                )
            ),
        )

        request.session[
            RECENTLY_VIEWED_SESSION_KEY_V272
        ] = [
            pending.pk,
            expired.pk,
            self.listing_a.pk,
            999999,
        ]

        result = (
            get_recently_viewed_listings_v272(
                request,
            )
        )

        self.assertEqual(
            [
                listing.pk
                for listing in result
            ],
            [
                self.listing_a.pk,
            ],
        )

    def test_v272_first_detail_view_hides_empty_section(self):
        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_a.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context[
                "recently_viewed_listings"
            ],
            [],
        )

        self.assertNotContains(
            response,
            "Recently viewed",
        )

    def test_v272_second_detail_view_shows_previous_listing(self):
        self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_a.pk,
                },
            )
        )

        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_b.pk,
                },
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            [
                listing.pk
                for listing
                in response.context[
                    "recently_viewed_listings"
                ]
            ],
            [
                self.listing_a.pk,
            ],
        )

        self.assertContains(
            response,
            "Recently viewed",
        )

        self.assertContains(
            response,
            "V272 Listing A",
        )

        recently_viewed_ids = [
            listing.pk
            for listing
            in response.context[
                "recently_viewed_listings"
            ]
        ]

        self.assertNotIn(
            self.listing_b.pk,
            recently_viewed_ids,
        )

        response_html = response.content.decode(
            response.charset
            or "utf-8"
        )

        section_marker = (
            'class="content-card '
            'recently-viewed-listings-v272"'
        )

        self.assertIn(
            section_marker,
            response_html,
        )

        recently_viewed_section = (
            response_html
            .split(
                section_marker,
                1,
            )[1]
            .split(
                "</section>",
                1,
            )[0]
        )

        self.assertIn(
            "V272 Listing A",
            recently_viewed_section,
        )

        self.assertNotIn(
            "V272 Listing B",
            recently_viewed_section,
        )

    def test_v272_detail_history_is_newest_first(self):
        for listing in (
            self.listing_a,
            self.listing_b,
        ):
            self.client.get(
                reverse(
                    "listings:listing_detail",
                    kwargs={
                        "pk": listing.pk,
                    },
                )
            )

        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_c.pk,
                },
            )
        )

        self.assertEqual(
            [
                listing.pk
                for listing
                in response.context[
                    "recently_viewed_listings"
                ]
            ],
            [
                self.listing_b.pk,
                self.listing_a.pk,
            ],
        )

    def test_v272_history_is_isolated_per_browser_session(self):
        self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_a.pk,
                },
            )
        )

        second_client = self.client_class()

        response = second_client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_b.pk,
                },
            )
        )

        self.assertEqual(
            response.context[
                "recently_viewed_listings"
            ],
            [],
        )

        response_html = response.content.decode(
            response.charset
            or "utf-8"
        )

        self.assertNotIn(
            (
                'class="content-card '
                'recently-viewed-listings-v272"'
            ),
            response_html,
        )

    def test_v272_pending_and_expired_titles_do_not_leak(self):
        pending = self._create_listing(
            title="V272 Secret Pending Title",
            status=Listing.Status.PENDING,
        )

        expired = self._create_listing(
            title="V272 Secret Expired Title",
            expires_at=(
                timezone.now()
                - timedelta(
                    seconds=1
                )
            ),
        )

        session = self.client.session

        session[
            RECENTLY_VIEWED_SESSION_KEY_V272
        ] = [
            pending.pk,
            expired.pk,
            self.listing_a.pk,
        ]

        session.save()

        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_b.pk,
                },
            )
        )

        self.assertContains(
            response,
            "V272 Listing A",
        )

        self.assertNotContains(
            response,
            "V272 Secret Pending Title",
        )

        self.assertNotContains(
            response,
            "V272 Secret Expired Title",
        )

    def test_v272_service_is_database_read_only(self):
        request = self._request_with_session()

        request.session[
            RECENTLY_VIEWED_SESSION_KEY_V272
        ] = [
            self.listing_a.pk,
            self.listing_b.pk,
        ]

        before = list(
            Listing.objects.values_list(
                "pk",
                "status",
                "created_at",
            )
        )

        get_recently_viewed_listings_v272(
            request
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

    def test_v272_detail_url_and_reexport_remain_compatible(self):
        match = resolve(
            reverse(
                "listings:listing_detail",
                kwargs={
                    "pk": self.listing_a.pk,
                },
            )
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

    def test_v272_listing_detail_keeps_48_line_contract_and_both_mixins(self):
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

        self.assertIn(
            "RecentlyViewedListingsContextMixinV272",
            classes,
        )

        base_names = [
            base.id
            for base in target.bases
            if isinstance(
                base,
                ast.Name,
            )
        ]

        self.assertEqual(
            base_names[:2],
            [
                "RecentlyViewedListingsContextMixinV272",
                "RelatedListingsContextMixinV271",
            ],
        )

    def test_v272_source_and_template_markers_are_present(self):
        service_source = Path(
            "listings/"
            "listing_recently_viewed.py"
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
                "RECENTLY_VIEWED_LISTINGS_V272",
                source,
            )

        self.assertIn(
            "Recently viewed",
            template_source,
        )

        self.assertIn(
            (
                '{% include "listings/_listing_card.html" '
                "with listing=recently_viewed_listing"
            ),
            template_source,
        )

    def test_v272_no_migration_0017_exists(self):
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
