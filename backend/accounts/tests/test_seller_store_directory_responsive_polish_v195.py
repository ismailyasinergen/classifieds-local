from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, reverse


V195_SELLER_STORE_DIRECTORY_RESPONSIVE_MARKER = (
    "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH"
)


class SellerStoreDirectoryResponsivePolishV195Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _seller_store_directory_template_path(self) -> Path:
        return (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_directory.html"
        )

    def _category_navigation_partial_path(self) -> Path:
        return self._backend_root() / "templates" / "categories" / "_category_navigation_v186.html"

    def _saved_search_management_template_path(self) -> Path:
        return (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / "saved_search_list.html"
        )

    def _public_browse_template_path(self) -> Path:
        return self._backend_root() / "listings" / "templates" / "listings" / "listing_list.html"

    def _store_directory_url(self) -> str:
        candidates = (
            "accounts:store_directory",
            "accounts:seller_store_directory",
            "accounts:stores",
            "accounts:seller_stores",
            "store_directory",
            "seller_store_directory",
        )

        for name in candidates:
            try:
                return reverse(name)
            except NoReverseMatch:
                continue

        return "/accounts/stores/"

    def test_v195_marker_is_declared_for_seller_store_directory_responsive_polish(self):
        self.assertEqual(
            V195_SELLER_STORE_DIRECTORY_RESPONSIVE_MARKER,
            "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH",
        )

    def test_v195_seller_store_directory_template_contains_responsive_guidance(self):
        text = self._seller_store_directory_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", text)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", text)
        self.assertIn("seller-store-directory-responsive-v195", text)
        self.assertIn('data-v195-seller-store-directory-responsive="true"', text)
        self.assertIn('aria-label="Seller store directory responsive browsing guidance"', text)
        self.assertIn('aria-label="Seller store directory browsing tips"', text)
        self.assertIn("Browse seller stores clearly on any screen", text)
        self.assertIn(
            "Search, category, location, sort, and pagination controls stay connected as you narrow the directory.",
            text,
        )
        self.assertIn("Start broad", text)
        self.assertIn("Use search or category chips first, then refine by location or verification.", text)
        self.assertIn("Keep context", text)
        self.assertIn("Active filters and sort choices remain visible while moving through pages.", text)
        self.assertIn("Open stores faster", text)
        self.assertIn(
            "On smaller screens, store cards stack into a clearer single-column reading flow.",
            text,
        )

    def test_v195_seller_store_directory_template_contains_mobile_css_contract(self):
        text = self._seller_store_directory_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("@media (max-width: 820px)", text)
        self.assertIn("@media (max-width: 520px)", text)
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr));", text)
        self.assertIn("grid-template-columns: 1fr;", text)
        self.assertIn("seller-store-directory-responsive-v195__steps", text)
        self.assertIn("seller-store-directory-responsive-v195__step", text)

    def test_v195_seller_store_directory_renders_responsive_guidance_default_state(self):
        response = self.client.get(self._store_directory_url())
        content = response.content.decode("utf-8", errors="ignore")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Seller Stores", content)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", content)
        self.assertIn('data-v195-seller-store-directory-responsive="true"', content)
        self.assertIn("Browse seller stores clearly on any screen", content)
        self.assertIn("Start broad", content)
        self.assertIn("Keep context", content)
        self.assertIn("Open stores faster", content)

    def test_v195_seller_store_directory_preserves_v192_category_state_rendering(self):
        response = self.client.get(
            self._store_directory_url(),
            {
                "category": "home-garden-furniture",
                "q": "chair",
                "sort": "newest",
                "location": "Berlin",
            },
        )
        content = response.content.decode("utf-8", errors="ignore")

        self.assertEqual(response.status_code, 200)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", content)
        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", content)
        self.assertIn("Category filter active", content)
        self.assertIn(
            "Search, sorting, location, and pagination stay connected to this category filter.",
            content,
        )

    def test_v195_category_navigation_and_saved_search_management_are_untouched(self):
        category_partial = self._category_navigation_partial_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        saved_search_template = self._saved_search_management_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        public_browse = self._public_browse_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_partial)
        self.assertIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", saved_search_template)
        self.assertIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", public_browse)

        for text in (category_partial, saved_search_template, public_browse):
            self.assertNotIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", text)
            self.assertNotIn("seller-store-directory-responsive-v195", text)
            self.assertNotIn("Browse seller stores clearly on any screen", text)

    def test_v195_seller_store_directory_does_not_receive_public_nav_or_saved_search_hooks(self):
        text = self._seller_store_directory_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertNotIn("render_category_navigation_v186", text)
        self.assertNotIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)
        self.assertNotIn("category-navigation-v193-keyboard-ready", text)
        self.assertNotIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", text)
        self.assertNotIn("saved-search-management-copy-v194", text)

    def test_v195_existing_checkpoint_guards_remain_present(self):
        v192_test = (
            self._backend_root()
            / "accounts"
            / "tests"
            / "test_seller_store_category_ui_polish_v192.py"
        )
        v193_test = self._backend_root() / "categories" / "test_category_navigation_keyboard_a11y_v193.py"
        v194_test = self._backend_root() / "listings" / "test_saved_search_management_copy_polish_v194.py"

        self.assertTrue(v192_test.exists())
        self.assertTrue(v193_test.exists())
        self.assertTrue(v194_test.exists())

        self.assertIn(
            "V192_SELLER_STORE_CATEGORY_UI_POLISH",
            v192_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING",
            v193_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH",
            v194_test.read_text(encoding="utf-8", errors="ignore"),
        )
