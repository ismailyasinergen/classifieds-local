"""
LISTING_COMPARISON_V274

Product tests for session-based comparison of two to four public listings.
"""

from __future__ import annotations

import ast
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import (
    RequestFactory,
    TestCase,
)
from django.urls import (
    resolve,
    reverse,
)
from django.utils import timezone

from categories.models import Category

from listings.listing_comparison_v274 import (
    LISTING_COMPARISON_MAX_ITEMS_V274,
    LISTING_COMPARISON_MIN_ITEMS_V274,
    LISTING_COMPARISON_SESSION_KEY_V274,
    LISTING_COMPARISON_V274,
    build_comparison_attribute_rows_v274,
    build_listing_comparison_context_v274,
    clear_comparison_listings_v274,
    comparison_listing_is_eligible_v274,
    get_comparison_listing_ids_v274,
    get_comparison_listings_v274,
    normalize_comparison_listing_ids_v274,
    set_comparison_listing_ids_v274,
    toggle_comparison_listing_v274,
)
from listings.listing_comparison_views_v274 import (
    listing_comparison_clear_v274,
    listing_comparison_toggle_v274,
    listing_comparison_view_v274,
)
from listings.models import Listing


V274_ALLOWED_SCOPE = (
    "backend/listings/listing_comparison_v274.py",
    "backend/listings/listing_comparison_views_v274.py",
    (
        "backend/listings/templatetags/"
        "listing_comparison_v274.py"
    ),
    "backend/listings/urls.py",
    (
        "backend/listings/templates/listings/"
        "_listing_card.html"
    ),
    (
        "backend/listings/templates/listings/"
        "listing_detail.html"
    ),
    (
        "backend/listings/templates/listings/"
        "listing_comparison_v274.html"
    ),
    "backend/listings/test_listing_comparison_v274.py",
    "docs/listing_comparison_v274.md",
)


class ListingComparisonV274Tests(TestCase):
    maxDiff = None

    def setUp(self):
        User = get_user_model()

        self.seller = User.objects.create_user(
            username="v274-seller",
            email="v274-seller@classifieds.local",
            password="StrongPass123!",
        )

        self.other_seller = User.objects.create_user(
            username="v274-other-seller",
            email="v274-other@classifieds.local",
            password="StrongPass123!",
        )

        self.category = Category.objects.create(
            name="V274 Cars",
            slug="v274-cars",
        )

        self.listing_a = self._create_listing(
            title="V274 Listing A",
            price="1000.00",
        )

        self.listing_b = self._create_listing(
            title="V274 Listing B",
            owner=self.other_seller,
            price="1250.00",
        )

        self.listing_c = self._create_listing(
            title="V274 Listing C",
            owner=self.other_seller,
            price="1500.00",
        )

        self.listing_d = self._create_listing(
            title="V274 Listing D",
            owner=self.other_seller,
            price="1750.00",
        )

        self.listing_e = self._create_listing(
            title="V274 Listing E",
            owner=self.other_seller,
            price="2000.00",
        )

    def _create_listing(
        self,
        *,
        title,
        owner=None,
        price="1000.00",
        status=Listing.Status.APPROVED,
        expires_at=None,
    ):
        return Listing.objects.create(
            title=title,
            description=f"Description for {title}",
            price=Decimal(price),
            category=self.category,
            owner=owner or self.seller,
            location="Berlin",
            attributes={},
            status=status,
            expires_at=expires_at,
        )

    def _request_with_session(self):
        request = RequestFactory().get("/")

        from django.contrib.sessions.middleware import (
            SessionMiddleware,
        )

        middleware = SessionMiddleware(
            lambda active_request: None
        )

        middleware.process_request(request)
        request.session.save()

        return request

    def _toggle_url(self, listing):
        return reverse(
            "listings:listing_compare_toggle",
            kwargs={"pk": listing.pk},
        )

    def test_v274_marker_scope_and_limits_are_stable(self):
        self.assertTrue(LISTING_COMPARISON_V274)
        self.assertEqual(LISTING_COMPARISON_MIN_ITEMS_V274, 2)
        self.assertEqual(LISTING_COMPARISON_MAX_ITEMS_V274, 4)
        self.assertEqual(
            LISTING_COMPARISON_SESSION_KEY_V274,
            "listing_comparison_ids_v274",
        )
        self.assertEqual(len(V274_ALLOWED_SCOPE), 9)

    def test_v274_normalization_is_positive_unique_and_capped(self):
        self.assertEqual(
            normalize_comparison_listing_ids_v274(
                [
                    "3",
                    3,
                    2,
                    True,
                    0,
                    -1,
                    "invalid",
                    1,
                    4,
                    5,
                ]
            ),
            [3, 2, 1, 4],
        )

    def test_v274_eligibility_rejects_pending_and_expired(self):
        pending = self._create_listing(
            title="V274 Pending",
            status=Listing.Status.PENDING,
        )

        expired = self._create_listing(
            title="V274 Expired",
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        self.assertTrue(
            comparison_listing_is_eligible_v274(self.listing_a)
        )
        self.assertFalse(
            comparison_listing_is_eligible_v274(pending)
        )
        self.assertFalse(
            comparison_listing_is_eligible_v274(expired)
        )

    def test_v274_service_adds_and_removes_listing(self):
        request = self._request_with_session()

        added = toggle_comparison_listing_v274(
            request,
            self.listing_a,
        )

        self.assertEqual(added["action"], "added")
        self.assertEqual(
            get_comparison_listing_ids_v274(request),
            [self.listing_a.pk],
        )

        removed = toggle_comparison_listing_v274(
            request,
            self.listing_a,
        )

        self.assertEqual(removed["action"], "removed")
        self.assertEqual(
            get_comparison_listing_ids_v274(request),
            [],
        )

    def test_v274_selection_preserves_user_order(self):
        request = self._request_with_session()

        for listing in (
            self.listing_c,
            self.listing_a,
            self.listing_b,
        ):
            toggle_comparison_listing_v274(
                request,
                listing,
            )

        expected = [
            self.listing_c.pk,
            self.listing_a.pk,
            self.listing_b.pk,
        ]

        self.assertEqual(
            get_comparison_listing_ids_v274(request),
            expected,
        )

        self.assertEqual(
            [
                listing.pk
                for listing in get_comparison_listings_v274(
                    request
                )
            ],
            expected,
        )

    def test_v274_fifth_listing_is_refused_without_mutation(self):
        request = self._request_with_session()

        for listing in (
            self.listing_a,
            self.listing_b,
            self.listing_c,
            self.listing_d,
        ):
            toggle_comparison_listing_v274(
                request,
                listing,
            )

        result = toggle_comparison_listing_v274(
            request,
            self.listing_e,
        )

        self.assertFalse(result["changed"])
        self.assertEqual(result["action"], "full")
        self.assertEqual(result["count"], 4)
        self.assertNotIn(
            self.listing_e.pk,
            result["listing_ids"],
        )

    def test_v274_clear_removes_all_selection(self):
        request = self._request_with_session()

        set_comparison_listing_ids_v274(
            request,
            [
                self.listing_a.pk,
                self.listing_b.pk,
            ],
        )

        self.assertEqual(
            clear_comparison_listings_v274(request),
            2,
        )
        self.assertEqual(
            get_comparison_listing_ids_v274(request),
            [],
        )

    def test_v274_get_prunes_pending_expired_and_missing_ids(self):
        request = self._request_with_session()

        pending = self._create_listing(
            title="V274 Hidden Pending",
            status=Listing.Status.PENDING,
        )

        expired = self._create_listing(
            title="V274 Hidden Expired",
            expires_at=timezone.now() - timedelta(seconds=1),
        )

        request.session[
            LISTING_COMPARISON_SESSION_KEY_V274
        ] = [
            pending.pk,
            self.listing_a.pk,
            expired.pk,
            999999,
        ]

        listings = get_comparison_listings_v274(request)

        self.assertEqual(
            [listing.pk for listing in listings],
            [self.listing_a.pk],
        )

        self.assertEqual(
            get_comparison_listing_ids_v274(request),
            [self.listing_a.pk],
        )

    def test_v274_context_reports_readiness_and_slots(self):
        request = self._request_with_session()

        set_comparison_listing_ids_v274(
            request,
            [
                self.listing_a.pk,
                self.listing_b.pk,
            ],
        )

        context = build_listing_comparison_context_v274(
            request
        )

        self.assertEqual(context["comparison_count"], 2)
        self.assertTrue(context["comparison_ready"])
        self.assertEqual(
            context["comparison_slots_remaining"],
            2,
        )

    def test_v274_dynamic_attribute_rows_use_union_and_missing_marker(self):
        listing_one = SimpleNamespace(
            display_attributes=[
                ("Brand", "Toyota"),
                ("Year", "2020"),
            ],
            attributes={},
        )

        listing_two = SimpleNamespace(
            display_attributes=[
                ("Brand", "Honda"),
                ("KM", "45000"),
            ],
            attributes={},
        )

        rows = build_comparison_attribute_rows_v274(
            [
                listing_one,
                listing_two,
            ]
        )

        row_map = {
            row["label"]: row["values"]
            for row in rows
        }

        self.assertEqual(
            row_map["Brand"],
            ["Toyota", "Honda"],
        )
        self.assertEqual(
            row_map["Year"],
            ["2020", "—"],
        )
        self.assertEqual(
            row_map["KM"],
            ["—", "45000"],
        )

    def test_v274_comparison_page_is_public_and_has_empty_state(self):
        response = self.client.get(
            reverse("listings:listing_compare")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Compare listings")
        self.assertContains(
            response,
            "No listings selected yet",
        )
        self.assertContains(
            response,
            'data-listing-comparison-v274="true"',
        )

    def test_v274_toggle_post_adds_listing_and_redirects(self):
        next_url = reverse("listings:listing_list")

        response = self.client.post(
            self._toggle_url(self.listing_a),
            {"next": next_url},
        )

        self.assertRedirects(
            response,
            next_url,
            fetch_redirect_response=False,
        )

        self.assertEqual(
            self.client.session[
                LISTING_COMPARISON_SESSION_KEY_V274
            ],
            [self.listing_a.pk],
        )

    def test_v274_toggle_rejects_get(self):
        response = self.client.get(
            self._toggle_url(self.listing_a)
        )

        self.assertEqual(response.status_code, 405)

    def test_v274_toggle_rejects_pending_listing(self):
        pending = self._create_listing(
            title="V274 Endpoint Pending",
            status=Listing.Status.PENDING,
        )

        response = self.client.post(
            self._toggle_url(pending)
        )

        self.assertEqual(response.status_code, 404)

    def test_v274_unsafe_next_redirects_to_comparison_page(self):
        response = self.client.post(
            self._toggle_url(self.listing_a),
            {
                "next": (
                    "https://attacker.example/unsafe"
                )
            },
        )

        self.assertRedirects(
            response,
            reverse("listings:listing_compare"),
            fetch_redirect_response=False,
        )

    def test_v274_clear_endpoint_is_post_only(self):
        clear_url = reverse(
            "listings:listing_compare_clear"
        )

        self.assertEqual(
            self.client.get(clear_url).status_code,
            405,
        )

        self.client.post(
            self._toggle_url(self.listing_a)
        )

        response = self.client.post(clear_url)

        self.assertRedirects(
            response,
            reverse("listings:listing_compare"),
            fetch_redirect_response=False,
        )

        self.assertNotIn(
            LISTING_COMPARISON_SESSION_KEY_V274,
            self.client.session,
        )

    def test_v274_comparison_page_preserves_selection_order(self):
        session = self.client.session
        session[
            LISTING_COMPARISON_SESSION_KEY_V274
        ] = [
            self.listing_b.pk,
            self.listing_a.pk,
        ]
        session.save()

        response = self.client.get(
            reverse("listings:listing_compare")
        )

        self.assertEqual(
            [
                listing.pk
                for listing
                in response.context["comparison_listings"]
            ],
            [
                self.listing_b.pk,
                self.listing_a.pk,
            ],
        )

        html = response.content.decode(
            response.charset or "utf-8"
        )

        self.assertLess(
            html.index("V274 Listing B"),
            html.index("V274 Listing A"),
        )

    def test_v274_browser_sessions_are_isolated(self):
        self.client.post(
            self._toggle_url(self.listing_a)
        )

        second_client = self.client_class()

        response = second_client.get(
            reverse("listings:listing_compare")
        )

        self.assertEqual(
            response.context["comparison_count"],
            0,
        )

        self.assertNotContains(
            response,
            "V274 Listing A",
        )

    def test_v274_listing_card_renders_compare_control(self):
        response = self.client.get(
            reverse("listings:listing_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add to compare")
        self.assertContains(
            response,
            self._toggle_url(self.listing_a),
        )

        self.client.post(
            self._toggle_url(self.listing_a)
        )

        selected_response = self.client.get(
            reverse("listings:listing_list")
        )

        self.assertContains(
            selected_response,
            "Remove from compare",
        )

        self.assertContains(
            selected_response,
            "Compare selected (1)",
        )

    def test_v274_listing_detail_renders_compare_control(self):
        response = self.client.get(
            reverse(
                "listings:listing_detail",
                kwargs={"pk": self.listing_a.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "listing-comparison-detail-v274",
        )
        self.assertContains(
            response,
            "Add to compare",
        )

    def test_v274_comparison_routes_resolve_to_dedicated_module(self):
        cases = (
            (
                reverse("listings:listing_compare"),
                listing_comparison_view_v274,
            ),
            (
                reverse("listings:listing_compare_clear"),
                listing_comparison_clear_v274,
            ),
            (
                self._toggle_url(self.listing_a),
                listing_comparison_toggle_v274,
            ),
        )

        for url, expected in cases:
            self.assertIs(
                resolve(url).func,
                expected,
            )

    def test_v274_existing_detail_view_contract_is_untouched(self):
        source = Path(
            "listings/listing_browse_detail_views.py"
        ).read_text(
            encoding="utf-8",
        )

        tree = ast.parse(source)

        classes = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }

        target = classes["ListingDetailView"]

        line_count = (
            (target.end_lineno or target.lineno)
            - target.lineno
            + 1
        )

        self.assertEqual(line_count, 48)
        self.assertIn(
            "RelatedListingsContextMixinV271",
            classes,
        )
        self.assertIn(
            "RecentlyViewedListingsContextMixinV272",
            classes,
        )

    def test_v274_compare_forms_do_not_reflect_raw_query_strings(self):
        backend_root = Path(__file__).resolve().parents[1]

        cases = (
            (
                backend_root
                / "listings"
                / "templates"
                / "listings"
                / "_listing_card.html",
                (
                    'class="listing-card-action '
                    'listing-comparison-action-v274"'
                ),
            ),
            (
                backend_root
                / "listings"
                / "templates"
                / "listings"
                / "listing_detail.html",
                'class="listing-comparison-detail-v274"',
            ),
        )

        for template_path, block_marker in cases:
            source = template_path.read_text(
                encoding="utf-8",
            )

            marker_position = source.index(
                block_marker
            )

            preceding_form_start = source.rfind(
                "<form",
                0,
                marker_position + 1,
            )

            preceding_form_end = source.rfind(
                "</form>",
                0,
                marker_position + 1,
            )

            if preceding_form_start > preceding_form_end:
                form_start = preceding_form_start
            else:
                form_start = source.index(
                    "<form",
                    marker_position,
                )

            form_end = source.index(
                "</form>",
                form_start,
            )

            comparison_form = source[
                form_start:form_end
            ]

            self.assertIn(
                "listing_compare_toggle",
                comparison_form,
            )

            self.assertIn(
                'value="{{ request.path }}"',
                comparison_form,
            )

            self.assertNotIn(
                "request.get_full_path",
                comparison_form,
            )

    def test_v274_markers_and_no_migration_are_present(self):
        backend_root = Path(__file__).resolve().parents[1]

        relative_paths = (
            "listings/listing_comparison_v274.py",
            "listings/listing_comparison_views_v274.py",
            (
                "listings/templatetags/"
                "listing_comparison_v274.py"
            ),
            "listings/urls.py",
            (
                "listings/templates/listings/"
                "_listing_card.html"
            ),
            (
                "listings/templates/listings/"
                "listing_detail.html"
            ),
            (
                "listings/templates/listings/"
                "listing_comparison_v274.html"
            ),
            "listings/test_listing_comparison_v274.py",
        )

        for relative_path in relative_paths:
            source = (
                backend_root / relative_path
            ).read_text(
                encoding="utf-8",
            )

            self.assertIn(
                "LISTING_COMPARISON_V274",
                source,
            )

        migration_directory = (
            backend_root
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(migration_directory.glob("0017*")),
            [],
        )
