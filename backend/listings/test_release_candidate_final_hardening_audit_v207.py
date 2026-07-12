from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.db import models
from django.test import SimpleTestCase

from accounts.models import SellerStore
from categories.models import Category
from listings.models import SavedSearch


V207_RELEASE_CANDIDATE_FINAL_HARDENING_AUDIT_MARKER = (
    "V207_RELEASE_CANDIDATE_FINAL_HARDENING_AUDIT"
)


class ReleaseCandidateFinalHardeningAuditV207Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _accounts_source_bundle(self) -> str:
        accounts_root = self._backend_root() / "accounts"
        sources: list[str] = []

        for path in sorted(accounts_root.glob("*.py")):
            if path.name.startswith("test_"):
                continue
            sources.append(f"\n# SOURCE: accounts/{path.name}\n")
            sources.append(path.read_text(encoding="utf-8", errors="ignore"))

        return "\n".join(sources)

    def test_v207_marker_is_declared_for_release_candidate_final_hardening_audit(self):
        self.assertEqual(
            V207_RELEASE_CANDIDATE_FINAL_HARDENING_AUDIT_MARKER,
            "V207_RELEASE_CANDIDATE_FINAL_HARDENING_AUDIT",
        )

    def test_v207_recent_checkpoint_audit_files_remain_available(self):
        expected_files = (
            "accounts/tests/test_seller_store_admin_detail_polish_audit_v206.py",
            "listings/test_saved_search_notification_ui_accessibility_polish_v205.py",
            "listings/test_release_candidate_dry_run_checklist_v204.py",
            "categories/test_category_taxonomy_admin_template_guidance_v203.py",
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py",
            "accounts/tests/test_seller_store_public_page_accessibility_polish_v201.py",
            "listings/test_project_milestone_audit_release_readiness_v200.py",
            "categories/test_category_taxonomy_admin_changelist_filtering_polish_v199.py",
            "accounts/tests/test_seller_store_public_page_responsive_polish_v198.py",
            "listings/test_saved_search_notification_settings_polish_v197.py",
            "categories/test_category_taxonomy_admin_ux_polish_v196.py",
        )

        for relative_path in expected_files:
            self.assertTrue(
                (self._backend_root() / relative_path).is_file(),
                f"Expected final-hardening checkpoint file missing: {relative_path}",
            )

    def test_v207_recent_checkpoint_markers_remain_present_and_scoped(self):
        marker_locations = {
            "accounts/tests/test_seller_store_admin_detail_polish_audit_v206.py": (
                "V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT",
            ),
            "listings/templates/listings/saved_search_list.html": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH",
                "V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH",
            ),
            "accounts/templates/accounts/seller_store_public.html": (
                "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH",
                "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH",
            ),
            "accounts/templates/accounts/seller_store_directory.html": (
                "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH",
            ),
            "categories/admin.py": (
                "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH",
                "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH",
                "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE",
            ),
            "templates/admin/categories/category/change_list.html": (
                "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE",
            ),
            "templates/categories/_category_navigation_v186.html": (
                "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING",
            ),
        }

        for relative_path, markers in marker_locations.items():
            text = self._read(relative_path)
            for marker in markers:
                self.assertIn(marker, text, f"Expected {marker} in {relative_path}")

    def test_v207_backend_docs_directory_is_absent_for_final_hardening(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v207_category_admin_release_candidate_contract_is_stable(self):
        category_admin = admin.site._registry[Category]

        self.assertEqual(category_admin.list_display, ("name", "slug", "parent"))
        self.assertTrue(getattr(category_admin, "v196_category_taxonomy_admin_ux_polish", False))
        self.assertTrue(
            getattr(
                category_admin,
                "v199_category_taxonomy_admin_changelist_filtering_polish",
                False,
            )
        )
        self.assertTrue(
            getattr(category_admin, "v203_category_taxonomy_admin_template_guidance", False)
        )
        self.assertEqual(
            category_admin.change_list_template,
            "admin/categories/category/change_list.html",
        )

    def test_v207_category_admin_template_release_candidate_contract_is_stable(self):
        template = self._read("templates/admin/categories/category/change_list.html")

        self.assertIn("category-taxonomy-admin-guidance-v203", template)
        self.assertIn('data-v203-category-admin-template-guidance="true"', template)
        self.assertIn("Category taxonomy filtering guidance", template)
        self.assertIn("v199_category_filter_guidance", template)
        self.assertIn("v199_category_filter_summary", template)

    def test_v207_saved_search_notification_contract_is_stable(self):
        fields_by_name = {field.name: field for field in SavedSearch._meta.fields}

        expected_fields = {
            "email_notifications_enabled": models.BooleanField,
            "last_notification_checked_at": models.DateTimeField,
            "last_notification_sent_at": models.DateTimeField,
        }

        for field_name, expected_class in expected_fields.items():
            self.assertIn(field_name, fields_by_name)
            self.assertIsInstance(fields_by_name[field_name], expected_class)

        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        self.assertIn("saved-search-notification-settings-v197", saved_search_template)
        self.assertIn("saved-search-notification-a11y-v205", saved_search_template)
        self.assertIn('data-v205-saved-search-notification-accessibility="true"', saved_search_template)
        self.assertIn("Accessible saved search notifications", saved_search_template)
        self.assertIn(":focus-visible", saved_search_template)

    def test_v207_seller_store_admin_and_public_contracts_are_stable(self):
        accounts_source_bundle = self._accounts_source_bundle()
        seller_store_admin = admin.site._registry.get(SellerStore)

        self.assertIsNotNone(seller_store_admin)
        self.assertTrue(tuple(getattr(seller_store_admin, "list_display", ())))
        self.assertTrue(
            tuple(getattr(seller_store_admin, "search_fields", ()))
            or tuple(getattr(seller_store_admin, "list_filter", ()))
        )

        self.assertIn("SellerStore", accounts_source_bundle)
        self.assertIn("seller_store_public", accounts_source_bundle)
        self.assertIn("seller_store_directory", accounts_source_bundle)
        self.assertIn("seller_store_public.html", accounts_source_bundle)
        self.assertIn("seller_store_directory.html", accounts_source_bundle)

        compatibility_views = self._read("accounts/views.py")
        self.assertIn("ACCOUNT_VIEWS_REFACTOR_V97", compatibility_views)
        self.assertIn("Compatibility re-export module", compatibility_views)

    def test_v207_seller_store_templates_keep_responsive_and_accessibility_contracts(self):
        public_template = self._read("accounts/templates/accounts/seller_store_public.html")
        directory_template = self._read("accounts/templates/accounts/seller_store_directory.html")

        self.assertIn("seller-store-public-responsive-v198", public_template)
        self.assertIn("seller-store-public-a11y-v201", public_template)
        self.assertIn('data-v198-seller-store-public-responsive="true"', public_template)
        self.assertIn('data-v201-seller-store-public-accessibility="true"', public_template)
        self.assertIn("Accessible seller store browsing", public_template)
        self.assertIn(":focus-visible", public_template)

        self.assertIn("seller-store-directory-responsive-v195", directory_template)
        self.assertIn('data-v195-seller-store-directory-responsive="true"', directory_template)
        self.assertIn("V192_SELLER_STORE_CATEGORY_UI_POLISH", directory_template)

    def test_v207_feature_markers_do_not_cross_runtime_surfaces(self):
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        seller_public_template = self._read("accounts/templates/accounts/seller_store_public.html")
        seller_directory_template = self._read("accounts/templates/accounts/seller_store_directory.html")
        category_admin_source = self._read("categories/admin.py")
        category_admin_template = self._read("templates/admin/categories/category/change_list.html")
        category_nav_template = self._read("templates/categories/_category_navigation_v186.html")

        self.assertNotIn("V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT", saved_search_template)
        self.assertNotIn("V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT", seller_public_template)
        self.assertNotIn("V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT", seller_directory_template)

        self.assertNotIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", seller_public_template)
        self.assertNotIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", seller_directory_template)
        self.assertNotIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", category_admin_source)
        self.assertNotIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", category_admin_template)

        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", saved_search_template)
        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", seller_public_template)
        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", seller_directory_template)
        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_nav_template)

    def test_v207_marker_does_not_patch_runtime_or_template_surfaces(self):
        runtime_surfaces = (
            "accounts/models.py",
            "accounts/admin.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "listings/models.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V207_RELEASE_CANDIDATE_FINAL_HARDENING_AUDIT",
                self._read(relative_path),
                f"v207 audit marker should not be in runtime/template surface {relative_path}",
            )
