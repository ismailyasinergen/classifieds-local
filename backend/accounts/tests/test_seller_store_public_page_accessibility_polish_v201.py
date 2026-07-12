from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_MARKER = (
    "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH"
)


class SellerStorePublicPageAccessibilityPolishV201Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _public_template(self) -> str:
        return self._read("accounts/templates/accounts/seller_store_public.html")

    def test_v201_marker_is_declared_for_seller_store_public_accessibility_polish(self):
        self.assertEqual(
            V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_MARKER,
            "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH",
        )

    def test_v201_public_template_preserves_v198_responsive_contract(self):
        text = self._public_template()

        self.assertIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", text)
        self.assertIn("seller-store-public-responsive-v198", text)
        self.assertIn('data-v198-seller-store-public-responsive="true"', text)
        self.assertIn("Browse this seller store comfortably on any screen", text)

    def test_v201_public_template_contains_accessibility_region_contract(self):
        text = self._public_template()

        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", text)
        self.assertIn("seller-store-public-a11y-v201", text)
        self.assertIn('data-v201-seller-store-public-accessibility="true"', text)
        self.assertIn('role="region"', text)
        self.assertIn('tabindex="-1"', text)
        self.assertIn('aria-labelledby="seller-store-public-a11y-v201-title"', text)
        self.assertIn('aria-describedby="seller-store-public-a11y-v201-help"', text)
        self.assertIn('id="seller-store-public-a11y-v201-title"', text)
        self.assertIn('id="seller-store-public-a11y-v201-help"', text)
        self.assertIn("Accessible seller store browsing", text)

    def test_v201_public_template_contains_screen_reader_and_focus_helpers(self):
        text = self._public_template()

        self.assertIn("seller-store-public-a11y-v201__sr-only", text)
        self.assertIn("Keyboard users can move through seller details, active listings, filters, and pagination in reading order.", text)
        self.assertIn(":focus-visible", text)
        self.assertIn("outline: 3px solid #2563eb", text)
        self.assertIn("outline-offset: 3px", text)
        self.assertIn("@media (max-width: 820px)", text)
        self.assertIn("@media (max-width: 520px)", text)

    def test_v201_public_template_contains_accessibility_tip_copy(self):
        text = self._public_template()

        self.assertIn('aria-label="Seller store accessibility tips"', text)
        self.assertIn("Follow the page structure", text)
        self.assertIn("Headings and labeled regions help screen-reader users understand each store section.", text)
        self.assertIn("Keep keyboard focus visible", text)
        self.assertIn("Interactive controls receive a stronger focus outline while browsing the store.", text)
        self.assertIn("Read filters in context", text)
        self.assertIn("Search, sorting, and pagination stay connected to the active seller-store listing view.", text)

    def test_v201_does_not_touch_directory_saved_search_category_admin_or_category_nav(self):
        directory = self._read("accounts/templates/accounts/seller_store_directory.html")
        saved_search = self._read("listings/templates/listings/saved_search_list.html")
        category_admin = self._read("categories/admin.py")
        category_nav = self._read("templates/categories/_category_navigation_v186.html")
        v200_audit = self._read("listings/test_project_milestone_audit_release_readiness_v200.py")

        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", directory)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search)
        self.assertIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", category_admin)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_nav)
        self.assertIn("V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT", v200_audit)

        for text in (directory, saved_search, category_admin, category_nav, v200_audit):
            self.assertNotIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", text)
            self.assertNotIn("seller-store-public-a11y-v201", text)
            self.assertNotIn("Accessible seller store browsing", text)

    def test_v201_public_template_does_not_receive_saved_search_admin_directory_or_audit_hooks(self):
        text = self._public_template()

        self.assertNotIn("V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT", text)
        self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", text)
        self.assertNotIn("v199_category_filter_guidance", text)
        self.assertNotIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", text)
        self.assertNotIn("saved-search-notification-settings-v197", text)
        self.assertNotIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", text)
        self.assertNotIn("v196_parent_path", text)
        self.assertNotIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", text)
        self.assertNotIn("seller-store-directory-responsive-v195", text)
        self.assertNotIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)
        self.assertNotIn("category-navigation-v193-keyboard-ready", text)

    def test_v201_existing_checkpoint_guards_remain_present(self):
        expected_test_markers = {
            "listings/test_project_milestone_audit_release_readiness_v200.py": (
                "V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT"
            ),
            "categories/test_category_taxonomy_admin_changelist_filtering_polish_v199.py": (
                "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH"
            ),
            "accounts/tests/test_seller_store_public_page_responsive_polish_v198.py": (
                "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH"
            ),
            "listings/test_saved_search_notification_settings_polish_v197.py": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
            ),
            "categories/test_category_taxonomy_admin_ux_polish_v196.py": (
                "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH"
            ),
        }

        for relative_path, marker in expected_test_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected guard marker {marker} in {relative_path}",
            )
