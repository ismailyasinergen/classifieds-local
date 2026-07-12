from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_MARKER = (
    "V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT"
)


class ProjectMilestoneAuditReleaseReadinessV200Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v200_marker_is_declared_for_project_milestone_audit(self):
        self.assertEqual(
            V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_MARKER,
            "V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT",
        )

    def test_recent_milestone_markers_are_present_on_expected_surfaces(self):
        expected_markers = {
            "templates/categories/_category_navigation_v186.html": (
                "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING"
            ),
            "listings/templates/listings/saved_search_list.html": (
                "V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH"
            ),
            "accounts/templates/accounts/seller_store_directory.html": (
                "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH"
            ),
            "categories/admin.py": (
                "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH"
            ),
            "listings/templates/listings/saved_search_list.html": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
            ),
            "accounts/templates/accounts/seller_store_public.html": (
                "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH"
            ),
            "categories/admin.py": (
                "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected {marker} in {relative_path}",
            )

    def test_recent_checkpoint_guard_tests_remain_present(self):
        expected_test_markers = {
            "categories/test_category_navigation_keyboard_a11y_v193.py": (
                "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING"
            ),
            "listings/test_saved_search_management_copy_polish_v194.py": (
                "V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH"
            ),
            "accounts/tests/test_seller_store_directory_responsive_polish_v195.py": (
                "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH"
            ),
            "categories/test_category_taxonomy_admin_ux_polish_v196.py": (
                "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH"
            ),
            "listings/test_saved_search_notification_settings_polish_v197.py": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
            ),
            "accounts/tests/test_seller_store_public_page_responsive_polish_v198.py": (
                "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH"
            ),
            "categories/test_category_taxonomy_admin_changelist_filtering_polish_v199.py": (
                "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH"
            ),
        }

        for relative_path, marker in expected_test_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected guard marker {marker} in {relative_path}",
            )

    def test_release_readiness_runtime_surfaces_do_not_receive_v200_marker(self):
        runtime_surfaces = (
            "categories/admin.py",
            "categories/models.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_directory.html",
            "accounts/templates/accounts/seller_store_public.html",
            "listings/models.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
            "listings/templates/listings/listing_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT",
                self._read(relative_path),
                f"v200 marker should not be in runtime surface {relative_path}",
            )

    def test_release_readiness_recent_runtime_markers_do_not_cross_leak(self):
        category_admin = self._read("categories/admin.py")
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        seller_store_directory = self._read("accounts/templates/accounts/seller_store_directory.html")
        seller_store_public = self._read("accounts/templates/accounts/seller_store_public.html")
        category_navigation = self._read("templates/categories/_category_navigation_v186.html")

        self.assertIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", category_admin)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", seller_store_directory)
        self.assertIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", seller_store_public)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_navigation)

        self.assertNotIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", category_admin)
        self.assertNotIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", category_admin)
        self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", saved_search_template)
        self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", seller_store_directory)
        self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", seller_store_public)
        self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", category_navigation)

    def test_release_readiness_migration_files_do_not_receive_v200_marker(self):
        migration_roots = (
            self._backend_root() / "accounts" / "migrations",
            self._backend_root() / "categories" / "migrations",
            self._backend_root() / "listings" / "migrations",
            self._backend_root() / "promotions" / "migrations",
            self._backend_root() / "conversations" / "migrations",
        )

        for root in migration_roots:
            if not root.exists():
                continue

            for path in root.glob("*.py"):
                self.assertNotIn(
                    "V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT",
                    path.read_text(encoding="utf-8", errors="ignore"),
                    f"v200 marker should not be in migration file {path}",
                )

    def test_release_readiness_admin_contract_markers_remain_present(self):
        category_admin = self._read("categories/admin.py")

        self.assertIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", category_admin)
        self.assertIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", category_admin)
        self.assertIn("v196_category_taxonomy_admin_ux_polish = True", category_admin)
        self.assertIn("v199_category_taxonomy_admin_changelist_filtering_polish = True", category_admin)
        self.assertIn("list_per_page = 50", category_admin)
        self.assertIn("preserve_filters = True", category_admin)
        self.assertIn("v199_preserved_list_display_contract", category_admin)

    def test_release_readiness_saved_search_contract_markers_remain_present(self):
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")

        self.assertIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", saved_search_template)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("data-v194-saved-search-management-copy", saved_search_template)
        self.assertIn("data-v197-saved-search-notification-settings", saved_search_template)
        self.assertIn("Manage saved searches with confidence", saved_search_template)
        self.assertIn("Fine-tune saved search notifications", saved_search_template)

    def test_release_readiness_seller_store_contract_markers_remain_present(self):
        directory_template = self._read("accounts/templates/accounts/seller_store_directory.html")
        public_template = self._read("accounts/templates/accounts/seller_store_public.html")

        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", directory_template)
        self.assertIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", public_template)
        self.assertIn("data-v195-seller-store-directory-responsive", directory_template)
        self.assertIn("data-v198-seller-store-public-responsive", public_template)
        self.assertIn("Browse seller stores clearly on any screen", directory_template)
        self.assertIn("Browse this seller store comfortably on any screen", public_template)
