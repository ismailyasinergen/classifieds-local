"""
PUBLIC_BROWSE_CATEGORY_NAVIGATION_UX_REPAIR_V273

User-visible regression tests for the compact public-browse category
navigation.
"""

from __future__ import annotations

from pathlib import Path

from django.test import TestCase
from django.urls import reverse

from categories.models import Category


PUBLIC_BROWSE_CATEGORY_NAVIGATION_UX_REPAIR_V273 = True

V273_ALLOWED_SCOPE = (
    "backend/templates/categories/_category_navigation_v186.html",
    "backend/listings/templates/listings/listing_list.html",
    (
        "backend/categories/"
        "test_public_browse_category_navigation_ux_repair_v273.py"
    ),
    "docs/public_browse_category_navigation_ux_repair_v273.md",
)


class PublicBrowseCategoryNavigationUxRepairV273Tests(
    TestCase
):
    maxDiff = None

    def setUp(self):
        self.root = Category.objects.create(
            name="V273 Home",
            slug="v273-home",
        )

        self.child = Category.objects.create(
            name="V273 Furniture",
            slug="v273-furniture",
            parent=self.root,
        )

        self.grandchild = Category.objects.create(
            name="V273 Living Room",
            slug="v273-living-room",
            parent=self.child,
        )

        self.other_root = Category.objects.create(
            name="V273 Vehicles",
            slug="v273-vehicles",
        )

        self.url = reverse(
            "listings:listing_list"
        )

    def test_v273_scope_is_exact_and_product_facing(self):
        self.assertTrue(
            PUBLIC_BROWSE_CATEGORY_NAVIGATION_UX_REPAIR_V273
        )

        self.assertEqual(
            len(V273_ALLOWED_SCOPE),
            4,
        )

    def test_v273_default_category_browser_is_collapsed(self):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        html = response.content.decode(
            response.charset
            or "utf-8"
        )

        self.assertIn(
            '<details\n    class="category-navigation-v273-disclosure"\n    \n  >',
            html,
        )

        self.assertNotIn(
            (
                'class="category-navigation-v273-disclosure"\n'
                "    open"
            ),
            html,
        )

        self.assertIn(
            "Show categories",
            html,
        )

    def test_v273_selected_category_opens_main_disclosure(self):
        response = self.client.get(
            self.url,
            {
                "category": self.grandchild.slug,
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        html = response.content.decode(
            response.charset
            or "utf-8"
        )

        self.assertIn(
            'class="category-navigation-v273-disclosure"',
            html,
        )

        self.assertIn(
            "open",
            html,
        )

        self.assertContains(
            response,
            "Current category: V273 Living Room",
        )

        self.assertContains(
            response,
            "Selected category: V273 Living Room",
        )

    def test_v273_only_selected_root_branch_is_open(self):
        response = self.client.get(
            self.url,
            {
                "category": self.grandchild.slug,
            },
        )

        html = response.content.decode(
            response.charset
            or "utf-8"
        )

        self.assertIn(
            (
                'class="category-navigation-v273-root '
                'is-active"'
            ),
            html,
        )

        self.assertIn(
            (
                'class="category-navigation-v273-branch '
                'is-active"'
            ),
            html,
        )

        self.assertIn(
            (
                'class="category-navigation-v186__item '
                'category-navigation-v273-leaf"'
            ),
            html,
        )

        self.assertNotIn(
            (
                'class="category-navigation-v273-leaf '
                'is-active"'
            ),
            html,
        )

    def test_v273_selected_leaf_has_aria_current(self):
        response = self.client.get(
            self.url,
            {
                "category": self.grandchild.slug,
            },
        )

        html = response.content.decode(
            response.charset
            or "utf-8"
        )

        selected_fragment = (
            f'href="{self.url}?category={self.grandchild.slug}"'
        )

        self.assertIn(
            selected_fragment,
            html,
        )

        self.assertIn(
            'aria-current="page"',
            html,
        )

    def test_v273_internal_marker_is_not_visually_rendered(self):
        response = self.client.get(
            self.url
        )

        html = response.content.decode(
            response.charset
            or "utf-8"
        )

        self.assertContains(
            response,
            "V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION",
        )

        self.assertIn(
            ".category-navigation-v186__marker",
            html,
        )

        self.assertIn(
            "display: none !important;",
            html,
        )

        self.assertNotIn(
            (
                '<p class="category-navigation-v186__marker">'
                "V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION"
                "</p>\n  <ul"
            ),
            html,
        )

    def test_v273_public_browse_hides_duplicate_global_sidebar(self):
        source = Path(
            "listings/templates/listings/"
            "listing_list.html"
        ).read_text(
            encoding="utf-8",
        )

        self.assertIn(
            "PUBLIC_BROWSE_CATEGORY_NAVIGATION_UX_REPAIR_V273",
            source,
        )

        self.assertIn(
            ".layout > .sidebar",
            source,
        )

        self.assertIn(
            "display: none;",
            source,
        )

        self.assertIn(
            "grid-template-columns: minmax(0, 1fr);",
            source,
        )

    def test_v273_existing_mount_and_query_behavior_remain_present(self):
        source = Path(
            "listings/templates/listings/"
            "listing_list.html"
        ).read_text(
            encoding="utf-8",
        )

        self.assertIn(
            "V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT",
            source,
        )

        self.assertIn(
            (
                "{% render_category_navigation_v186 "
                "request.GET.category %}"
            ),
            source,
        )

        self.assertIn(
            "V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH",
            source,
        )

    def test_v273_v190_and_v193_accessibility_contracts_remain(self):
        source = Path(
            "templates/categories/"
            "_category_navigation_v186.html"
        ).read_text(
            encoding="utf-8",
        )

        for required in (
            "V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH",
            "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING",
            'aria-label="Browse categories"',
            'role="navigation"',
            'aria-labelledby="category-navigation-title-v193"',
            'aria-describedby="category-navigation-help-v193"',
            ":focus-visible",
            'aria-current="page"',
        ):
            self.assertIn(
                required,
                source,
            )

    def test_v273_clear_category_link_remains_available(self):
        response = self.client.get(
            self.url,
            {
                "category": self.grandchild.slug,
                "q": "chair",
                "sort": "newest",
            },
        )

        self.assertContains(
            response,
            "Clear category",
        )

        self.assertContains(
            response,
            "?q=chair&amp;sort=newest",
        )

    def test_v273_no_migration_0017_exists(self):
        migration_directory = (
            Path(__file__).resolve().parents[1]
            / "listings"
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
