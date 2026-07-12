from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.test import SimpleTestCase

from accounts.models import SellerStore


V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT_MARKER = (
    "V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT"
)


class SellerStoreAdminDetailPolishAuditV206Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _accounts_python_source_bundle(self) -> str:
        accounts_root = self._backend_root() / "accounts"
        sources: list[str] = []

        for path in sorted(accounts_root.glob("*.py")):
            if path.name.startswith("test_"):
                continue
            sources.append(f"\n# SOURCE: accounts/{path.name}\n")
            sources.append(path.read_text(encoding="utf-8", errors="ignore"))

        return "\n".join(sources)

    def test_v206_marker_is_declared_for_seller_store_admin_detail_polish_audit(self):
        self.assertEqual(
            V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT_MARKER,
            "V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT",
        )

    def test_v206_seller_store_model_contract_is_available_for_admin_and_detail_surfaces(self):
        model_source = self._read("accounts/models.py")

        self.assertIn("class SellerStore", model_source)
        self.assertEqual(SellerStore._meta.app_label, "accounts")
        self.assertEqual(SellerStore.__name__, "SellerStore")

        field_names = {field.name for field in SellerStore._meta.fields}
        self.assertIn("id", field_names)
        self.assertTrue(
            len(field_names) >= 3,
            "SellerStore should expose enough concrete fields for admin/detail display.",
        )
        self.assertTrue(
            any(
                token in field_name.lower()
                for field_name in field_names
                for token in ("name", "store", "slug", "user", "owner", "seller")
            ),
            f"SellerStore should expose at least one readable identity field; saw {field_names}",
        )

    def test_v206_seller_store_admin_registration_and_safe_display_contract_remain_available(self):
        accounts_admin_source = self._read("accounts/admin.py")
        registered_admin = admin.site._registry.get(SellerStore)

        self.assertIn("SellerStore", accounts_admin_source)
        self.assertIsNotNone(
            registered_admin,
            "SellerStore should remain registered in Django admin for release-candidate review.",
        )

        list_display = tuple(getattr(registered_admin, "list_display", ()))
        search_fields = tuple(getattr(registered_admin, "search_fields", ()))
        list_filter = tuple(getattr(registered_admin, "list_filter", ()))

        self.assertTrue(list_display, "SellerStore admin should expose a non-empty list_display.")
        self.assertTrue(
            search_fields or list_filter,
            "SellerStore admin should expose search_fields or list_filter for admin review.",
        )
        self.assertNotIn(
            "V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT",
            accounts_admin_source,
            "v206 is audit-only and should not patch accounts/admin.py.",
        )

    def test_v206_seller_store_view_entry_points_exist_across_accounts_modules(self):
        accounts_source_bundle = self._accounts_python_source_bundle()
        compatibility_views_source = self._read("accounts/views.py")

        self.assertIn("ACCOUNT_VIEWS_REFACTOR_V97", compatibility_views_source)
        self.assertIn("Compatibility re-export module", compatibility_views_source)

        self.assertIn("SellerStore", accounts_source_bundle)
        self.assertIn("seller_store_public", accounts_source_bundle)
        self.assertIn("seller_store_directory", accounts_source_bundle)
        self.assertIn("seller_store_public.html", accounts_source_bundle)
        self.assertIn("seller_store_directory.html", accounts_source_bundle)
        self.assertNotIn("V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT", accounts_source_bundle)

    def test_v206_seller_store_public_detail_template_keeps_responsive_and_accessibility_contracts(self):
        public_template = self._read("accounts/templates/accounts/seller_store_public.html")

        self.assertIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", public_template)
        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", public_template)
        self.assertIn('data-v198-seller-store-public-responsive="true"', public_template)
        self.assertIn('data-v201-seller-store-public-accessibility="true"', public_template)
        self.assertIn("seller-store-public-responsive-v198", public_template)
        self.assertIn("seller-store-public-a11y-v201", public_template)
        self.assertIn("Accessible seller store browsing", public_template)
        self.assertIn(":focus-visible", public_template)
        self.assertNotIn("V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT", public_template)

    def test_v206_seller_store_directory_template_keeps_discovery_and_responsive_contracts(self):
        directory_template = self._read("accounts/templates/accounts/seller_store_directory.html")

        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", directory_template)
        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", directory_template)
        self.assertIn("seller-store-directory-responsive-v195", directory_template)
        self.assertIn('data-v195-seller-store-directory-responsive="true"', directory_template)
        self.assertNotIn("V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT", directory_template)

    def test_v206_seller_store_public_and_directory_tests_remain_available(self):
        expected_test_markers = {
            "accounts/tests/test_seller_store_public_page_accessibility_polish_v201.py": (
                "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH"
            ),
            "accounts/tests/test_seller_store_public_page_responsive_polish_v198.py": (
                "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH"
            ),
            "accounts/tests/test_seller_store_directory_responsive_polish_v195.py": (
                "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH"
            ),
            "listings/test_saved_search_notification_ui_accessibility_polish_v205.py": (
                "V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH"
            ),
            "listings/test_release_candidate_dry_run_checklist_v204.py": (
                "V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST"
            ),
        }

        for relative_path, marker in expected_test_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected guard marker {marker} in {relative_path}",
            )

    def test_v206_does_not_touch_saved_search_category_admin_or_navigation_surfaces(self):
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        category_admin = self._read("categories/admin.py")
        category_admin_template = self._read("templates/admin/categories/category/change_list.html")
        category_nav = self._read("templates/categories/_category_navigation_v186.html")

        self.assertIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", saved_search_template)
        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_admin)
        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_admin_template)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_nav)

        for text in (saved_search_template, category_admin, category_admin_template, category_nav):
            self.assertNotIn("V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT", text)
            self.assertNotIn("seller-store-admin-detail-audit-v206", text)

    def test_v206_marker_does_not_patch_runtime_or_template_surfaces(self):
        runtime_surfaces = (
            "accounts/models.py",
            "accounts/admin.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "listings/templates/listings/saved_search_list.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT",
                self._read(relative_path),
                f"v206 audit marker should not be in runtime/template surface {relative_path}",
            )

    def test_v206_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
