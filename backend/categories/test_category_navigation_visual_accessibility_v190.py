from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.template import Context, Template
from django.test import RequestFactory, TestCase

from categories.public_browse_mount_v187 import V187_MOUNTED_TEMPLATE_PROJECT_PATHS


V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_MARKER = (
    "V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH"
)


class CategoryNavigationVisualAccessibilityV190Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _partial_path(self) -> Path:
        return self._backend_root() / "templates" / "categories" / "_category_navigation_v186.html"

    def _render_navigation(self, params: dict[str, str]) -> str:
        request = RequestFactory().get("/", params)
        request.user = AnonymousUser()

        template = Template(
            "{% load category_navigation_v186 %}"
            "{% render_category_navigation_v186 request.GET.category %}"
        )

        return template.render(Context({"request": request}))

    def test_v190_marker_is_declared_for_category_navigation_accessibility(self):
        self.assertEqual(
            V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_MARKER,
            "V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH",
        )

    def test_v190_partial_contains_accessible_landmark_and_visual_hooks(self):
        text = self._partial_path().read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION", text)
        self.assertIn("V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH", text)
        self.assertIn("category-navigation-v190-shell", text)
        self.assertIn('role="navigation"', text)
        self.assertIn('aria-label="Browse categories"', text)
        self.assertIn('data-v190-category-navigation="true"', text)
        self.assertIn("Browse by category", text)
        self.assertIn("focus-visible", text)
        self.assertNotIn('aria-label="Category navigation"', text)

    def test_v190_rendered_navigation_keeps_existing_v186_behavior_and_adds_accessibility(self):
        html = self._render_navigation(
            {
                "category": "home-garden-furniture",
                "q": "chair",
                "sort": "newest",
                "page": "9",
            }
        )

        self.assertIn("V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION", html)
        self.assertIn("V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH", html)
        self.assertIn('role="navigation"', html)
        self.assertIn('aria-label="Browse categories"', html)
        self.assertIn('data-v190-category-navigation="true"', html)
        self.assertIn("Browse by category", html)
        self.assertIn("home-garden-furniture", html)
        self.assertIn("q=chair", html)
        self.assertIn("sort=newest", html)
        self.assertNotIn("page=9", html)
        self.assertNotIn('aria-label="Category navigation"', html)

    def test_v190_public_browse_mount_manifest_remains_scoped_to_listing_browse_template(self):
        self.assertEqual(
            V187_MOUNTED_TEMPLATE_PROJECT_PATHS,
            ("listings/templates/listings/listing_list.html",),
        )

        mounted_template = self._backend_root() / V187_MOUNTED_TEMPLATE_PROJECT_PATHS[0]
        self.assertTrue(mounted_template.exists())

        text = mounted_template.read_text(encoding="utf-8", errors="ignore")

        self.assertIn("render_category_navigation_v186", text)
        self.assertIn("V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT", text)

    def test_v190_category_navigation_polish_does_not_leak_into_seller_store_templates(self):
        candidate_roots = (
            self._backend_root() / "accounts" / "templates",
            self._backend_root() / "templates" / "accounts",
        )

        seller_store_templates: list[Path] = []
        for root in candidate_roots:
            if root.exists():
                seller_store_templates.extend(
                    path
                    for path in root.rglob("*.html")
                    if "seller" in path.as_posix().lower() or "store" in path.as_posix().lower()
                )

        self.assertTrue(
            seller_store_templates,
            "No seller/store templates were found for v190 leak-scope verification.",
        )

        for path in seller_store_templates:
            text = path.read_text(encoding="utf-8", errors="ignore")

            self.assertNotIn(
                "V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH",
                text,
                f"v190 public category navigation polish leaked into seller/store template: {path}",
            )
            self.assertNotIn(
                "category-navigation-v190-shell",
                text,
                f"v190 public category navigation CSS hook leaked into seller/store template: {path}",
            )
            self.assertNotIn(
                "render_category_navigation_v186",
                text,
                f"public category navigation tag leaked into seller/store template: {path}",
            )
