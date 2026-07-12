from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.db import models
from django.test import SimpleTestCase

from categories.models import Category
from listings.models import SavedSearch


V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST_MARKER = (
    "V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST"
)


class ReleaseCandidateDryRunChecklistV204Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v204_marker_is_declared_for_release_candidate_dry_run_checklist(self):
        self.assertEqual(
            V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST_MARKER,
            "V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST",
        )

    def test_v204_recent_checkpoint_files_remain_available_for_release_candidate_review(self):
        expected_files = (
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "categories/test_category_taxonomy_admin_template_guidance_v203.py",
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py",
            "accounts/tests/test_seller_store_public_page_accessibility_polish_v201.py",
            "listings/test_project_milestone_audit_release_readiness_v200.py",
            "categories/test_category_taxonomy_admin_changelist_filtering_polish_v199.py",
            "accounts/tests/test_seller_store_public_page_responsive_polish_v198.py",
            "listings/test_saved_search_notification_settings_polish_v197.py",
            "categories/test_category_taxonomy_admin_ux_polish_v196.py",
            "listings/templates/listings/saved_search_list.html",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in expected_files:
            self.assertTrue(
                (self._backend_root() / relative_path).is_file(),
                f"Expected release-candidate baseline file missing: {relative_path}",
            )

    def test_v204_recent_checkpoint_markers_remain_present(self):
        marker_locations = {
            "categories/admin.py": (
                "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH",
                "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH",
                "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE",
            ),
            "templates/admin/categories/category/change_list.html": (
                "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE",
            ),
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py": (
                "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT",
            ),
            "accounts/templates/accounts/seller_store_public.html": (
                "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH",
                "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH",
            ),
            "listings/templates/listings/saved_search_list.html": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH",
            ),
            "accounts/templates/accounts/seller_store_directory.html": (
                "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH",
            ),
            "templates/categories/_category_navigation_v186.html": (
                "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING",
            ),
        }

        for relative_path, markers in marker_locations.items():
            text = self._read(relative_path)
            for marker in markers:
                self.assertIn(marker, text, f"Expected {marker} in {relative_path}")

    def test_v204_backend_docs_directory_is_absent_for_release_candidate(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v204_category_admin_contract_is_release_candidate_ready(self):
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

    def test_v204_category_admin_template_guidance_is_release_candidate_ready(self):
        template = self._read("templates/admin/categories/category/change_list.html")

        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", template)
        self.assertIn("{% extends \"admin/change_list.html\" %}", template)
        self.assertIn('data-v203-category-admin-template-guidance="true"', template)
        self.assertIn('role="note"', template)
        self.assertIn('aria-label="Category taxonomy changelist guidance"', template)
        self.assertIn("v199_category_filter_guidance", template)
        self.assertIn("v199_category_filter_summary", template)
        self.assertIn("Active filter summary:", template)

    def test_v204_saved_search_notification_contract_is_release_candidate_ready(self):
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
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("Fine-tune saved search notifications", saved_search_template)
        self.assertIn("Keep alerts useful by reviewing which saved searches should notify you", saved_search_template)

    def test_v204_seller_store_public_contract_is_release_candidate_ready(self):
        public_template = self._read("accounts/templates/accounts/seller_store_public.html")

        self.assertIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", public_template)
        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", public_template)
        self.assertIn('data-v198-seller-store-public-responsive="true"', public_template)
        self.assertIn('data-v201-seller-store-public-accessibility="true"', public_template)
        self.assertIn("Accessible seller store browsing", public_template)
        self.assertIn(":focus-visible", public_template)

    def test_v204_marker_does_not_patch_runtime_surfaces(self):
        runtime_surfaces = (
            "categories/admin.py",
            "categories/models.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
            "listings/models.py",
            "listings/saved_searches_views.py",
            "listings/urls.py",
            "listings/templates/listings/saved_search_list.html",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "accounts/views.py",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST",
                self._read(relative_path),
                f"v204 audit marker should not be in runtime surface {relative_path}",
            )

    def test_v204_recent_feature_markers_remain_scoped(self):
        category_admin = self._read("categories/admin.py")
        category_admin_template = self._read("templates/admin/categories/category/change_list.html")
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        seller_public_template = self._read("accounts/templates/accounts/seller_store_public.html")
        seller_directory_template = self._read("accounts/templates/accounts/seller_store_directory.html")
        category_nav_template = self._read("templates/categories/_category_navigation_v186.html")

        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_admin)
        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_admin_template)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", seller_public_template)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", seller_directory_template)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_nav_template)

        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", saved_search_template)
        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", seller_public_template)
        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", seller_directory_template)
        self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_nav_template)
        self.assertNotIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", category_admin)
        self.assertNotIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", category_admin)
