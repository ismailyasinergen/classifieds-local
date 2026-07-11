from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


V192_SELLER_STORE_CATEGORY_UI_MARKER = "V192_SELLER_STORE_CATEGORY_UI_POLISH"


class SellerStoreCategoryUiPolishV192Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _store_directory_template_path(self) -> Path:
        return self._backend_root() / "accounts" / "templates" / "accounts" / "seller_store_directory.html"

    def _public_browse_template_path(self) -> Path:
        return self._backend_root() / "listings" / "templates" / "listings" / "listing_list.html"

    def _category_nav_partial_path(self) -> Path:
        return self._backend_root() / "templates" / "categories" / "_category_navigation_v186.html"

    def _store_directory_url(self) -> str:
        try:
            return reverse("accounts:store_directory")
        except Exception:
            return "/accounts/stores/"

    def test_v192_marker_is_declared_for_seller_store_category_ui(self):
        self.assertEqual(
            V192_SELLER_STORE_CATEGORY_UI_MARKER,
            "V192_SELLER_STORE_CATEGORY_UI_POLISH",
        )

    def test_v192_store_directory_template_contains_category_filter_clarity_copy(self):
        text = self._store_directory_template_path().read_text(encoding="utf-8", errors="ignore")

        self.assertIn("Seller Stores", text)
        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", text)
        self.assertIn("seller-store-category-state-v192", text)
        self.assertIn('data-v192-seller-store-category-state="true"', text)
        self.assertIn('aria-label="Seller store category filter note"', text)
        self.assertIn("Category filter active", text)
        self.assertIn(
            "Showing seller stores with active listings in this category and related subcategories.",
            text,
        )
        self.assertIn(
            "Search, sorting, location, and pagination stay connected to this category filter.",
            text,
        )

    def test_v192_store_directory_category_state_renders_clarity_copy(self):
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
        self.assertIn("Seller Stores", content)
        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", content)
        self.assertIn('data-v192-seller-store-category-state="true"', content)
        self.assertIn('aria-label="Seller store category filter note"', content)
        self.assertIn("Category filter active", content)
        self.assertIn(
            "Showing seller stores with active listings in this category and related subcategories.",
            content,
        )
        self.assertIn(
            "Search, sorting, location, and pagination stay connected to this category filter.",
            content,
        )

    def test_v192_default_store_directory_does_not_show_category_specific_note(self):
        response = self.client.get(self._store_directory_url())
        content = response.content.decode("utf-8", errors="ignore")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Seller Stores", content)
        self.assertNotIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", content)
        self.assertNotIn("seller-store-category-state-v192", content)
        self.assertNotIn("Category filter active", content)

    def test_v192_public_browse_navigation_and_saved_search_templates_are_untouched(self):
        listing_browse = self._public_browse_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        category_partial = self._category_nav_partial_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", listing_browse)
        self.assertIn("V190_CATEGORY_NAVIGATION_VISUAL_ACCESSIBILITY_POLISH", category_partial)

        for text in (listing_browse, category_partial):
            self.assertNotIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", text)
            self.assertNotIn("seller-store-category-state-v192", text)
            self.assertNotIn("Category filter active", text)

    def test_v192_public_browse_navigation_tag_does_not_leak_into_store_directory_template(self):
        text = self._store_directory_template_path().read_text(encoding="utf-8", errors="ignore")

        self.assertNotIn("render_category_navigation_v186", text)
        self.assertNotIn("V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT", text)
        self.assertNotIn("V191_SAVED_SEARCH_CATEGORY_STATE_UX_POLISH", text)
        self.assertNotIn("saved-search-category-state-v191", text)

    def test_v192_existing_v189_seller_store_category_contract_remains_present(self):
        v189_test = (
            self._backend_root()
            / "accounts"
            / "tests"
            / "test_seller_store_category_compat_v189.py"
        )
        self.assertTrue(v189_test.exists())

        text = v189_test.read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V189_SELLER_STORE_CATEGORY_COMPATIBILITY_POLISH", text)
        self.assertIn("test_v189_existing_seller_store_category_tabs_coverage_remains_present", text)
        self.assertIn(
            "test_v189_existing_seller_store_directory_category_discovery_coverage_remains_present",
            text,
        )
        self.assertIn("test_v189_existing_seller_store_saved_search_cta_coverage_remains_present", text)
