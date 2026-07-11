from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.template import Context, Template
from django.test import RequestFactory, TestCase


V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_MARKER = (
    "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING"
)


class CategoryNavigationKeyboardA11yV193Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _partial_path(self) -> Path:
        return self._backend_root() / "templates" / "categories" / "_category_navigation_v186.html"

    def _public_browse_template_path(self) -> Path:
        return self._backend_root() / "listings" / "templates" / "listings" / "listing_list.html"

    def _seller_store_directory_template_path(self) -> Path:
        return (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_directory.html"
        )

    def _render_navigation(self, params: dict[str, str]) -> str:
        request = RequestFactory().get("/", params)
        request.user = AnonymousUser()

        template = Template(
            "{% load category_navigation_v186 %}"
            "{% render_category_navigation_v186 request.GET.category %}"
        )

        return template.render(Context({"request": request}))

    def test_v193_marker_is_declared_for_category_navigation_keyboard_a11y(self):
        self.assertEqual(
            V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_MARKER,
            "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING",
        )

    def test_v193_partial_adds_keyboard_and_screen_reader_relationships(self):
        text = self._partial_path().read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION", text)
        self.assertIn("V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH", text)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)

        self.assertIn("category-navigation-v193-keyboard-ready", text)
        self.assertIn("category-navigation-v193-sr-only", text)
        self.assertIn('data-v193-category-navigation-keyboard-a11y="true"', text)

        self.assertIn('id="category-navigation-title-v193"', text)
        self.assertIn('id="category-navigation-help-v193"', text)
        self.assertIn('aria-labelledby="category-navigation-title-v193"', text)
        self.assertIn('aria-describedby="category-navigation-help-v193"', text)
        self.assertIn('aria-label="Browse categories"', text)

        self.assertIn("Use Tab and Shift+Tab to move through category links.", text)
        self.assertIn("preserving safe search and sort state", text)
        self.assertIn("a:focus-visible", text)

    def test_v193_rendered_navigation_exposes_keyboard_help_and_keeps_url_state(self):
        html = self._render_navigation(
            {
                "category": "home-garden-furniture",
                "q": "chair",
                "sort": "newest",
                "page": "9",
            }
        )

        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", html)
        self.assertIn('data-v193-category-navigation-keyboard-a11y="true"', html)
        self.assertIn('aria-labelledby="category-navigation-title-v193"', html)
        self.assertIn('aria-describedby="category-navigation-help-v193"', html)
        self.assertIn('id="category-navigation-title-v193"', html)
        self.assertIn('id="category-navigation-help-v193"', html)
        self.assertIn("Use Tab and Shift+Tab to move through category links.", html)

        self.assertIn("home-garden-furniture", html)
        self.assertIn("q=chair", html)
        self.assertIn("sort=newest", html)
        self.assertNotIn("page=9", html)

    def test_v193_preserves_v190_navigation_accessibility_contract(self):
        html = self._render_navigation({"category": "home-garden-furniture"})

        self.assertIn("V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH", html)
        self.assertIn("category-navigation-v190-shell", html)
        self.assertIn('role="navigation"', html)
        self.assertIn('aria-label="Browse categories"', html)
        self.assertIn("Browse by category", html)
        self.assertIn("focus-visible", html)

    def test_v193_does_not_touch_public_browse_saved_search_or_seller_store_ui_templates(self):
        public_browse = self._public_browse_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        seller_store_directory = self._seller_store_directory_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", public_browse)
        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", seller_store_directory)

        for text in (public_browse, seller_store_directory):
            self.assertNotIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)
            self.assertNotIn("category-navigation-v193-keyboard-ready", text)
            self.assertNotIn("category-navigation-help-v193", text)

    def test_v193_seller_store_directory_still_has_no_public_category_navigation_tag(self):
        text = self._seller_store_directory_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertNotIn("render_category_navigation_v186", text)
        self.assertNotIn("V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT", text)
        self.assertNotIn("V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH", text)
        self.assertNotIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)

    def test_v193_existing_checkpoint_guards_remain_present(self):
        v190_test = self._backend_root() / "categories" / "test_category_navigation_visual_accessibility_v190.py"
        v191_test = self._backend_root() / "listings" / "test_saved_search_category_state_ux_v191.py"
        v192_test = self._backend_root() / "accounts" / "tests" / "test_seller_store_category_ui_polish_v192.py"

        self.assertTrue(v190_test.exists())
        self.assertTrue(v191_test.exists())
        self.assertTrue(v192_test.exists())

        self.assertIn(
            "V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH",
            v190_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH",
            v191_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V192_SELLER_STORE_CATEGORY_UI_POLISH",
            v192_test.read_text(encoding="utf-8", errors="ignore"),
        )
