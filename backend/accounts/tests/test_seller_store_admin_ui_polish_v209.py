from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.test import SimpleTestCase

from accounts.models import SellerStore


V209_SELLER_STORE_ADMIN_UI_POLISH_MARKER = "V209_SELLER_STORE_ADMIN_UI_POLISH"


class SellerStoreAdminUiPolishV209Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _seller_store_admin(self):
        registered_admin = admin.site._registry.get(SellerStore)
        self.assertIsNotNone(
            registered_admin,
            "SellerStore should remain registered in Django admin.",
        )
        return registered_admin

    def test_v209_marker_is_declared_for_seller_store_admin_ui_polish(self):
        self.assertEqual(
            V209_SELLER_STORE_ADMIN_UI_POLISH_MARKER,
            "V209_SELLER_STORE_ADMIN_UI_POLISH",
        )

    def test_v209_accounts_admin_contains_polish_block_and_marker(self):
        accounts_admin = self._read("accounts/admin.py")

        self.assertIn("V209_SELLER_STORE_ADMIN_UI_POLISH", accounts_admin)
        self.assertIn("v209_seller_store_admin_ui_polish", accounts_admin)
        self.assertIn("_V209SellerStoreProfileCompletenessFilter", accounts_admin)
        self.assertIn("v209_store_identity", accounts_admin)
        self.assertIn("v209_owner_label", accounts_admin)
        self.assertIn("v209_profile_status", accounts_admin)
        self.assertIn("v209_profile_summary", accounts_admin)
        self.assertIn("get_search_fields", accounts_admin)
        self.assertIn("get_list_select_related", accounts_admin)

    def test_v209_seller_store_admin_registration_uses_polished_admin_class(self):
        seller_store_admin = self._seller_store_admin()

        self.assertTrue(
            getattr(seller_store_admin, "v209_seller_store_admin_ui_polish", False)
        )
        self.assertEqual(seller_store_admin.model, SellerStore)
        self.assertEqual(getattr(seller_store_admin, "list_per_page", None), 50)

    def test_v209_seller_store_admin_list_display_is_review_friendly(self):
        seller_store_admin = self._seller_store_admin()

        self.assertEqual(
            tuple(seller_store_admin.list_display),
            (
                "v209_store_identity",
                "v209_owner_label",
                "v209_profile_status",
                "v209_updated_label",
            ),
        )

        for method_name in seller_store_admin.list_display:
            self.assertTrue(
                hasattr(seller_store_admin, method_name),
                f"SellerStore admin missing list_display method {method_name}",
            )

    def test_v209_seller_store_admin_search_and_filter_controls_are_available(self):
        seller_store_admin = self._seller_store_admin()

        self.assertIn("=id", tuple(seller_store_admin.search_fields))

        dynamic_search_fields = tuple(seller_store_admin.get_search_fields(request=None))
        self.assertIn("=id", dynamic_search_fields)
        self.assertTrue(
            len(dynamic_search_fields) >= 1,
            "SellerStore admin should expose at least an exact id search field.",
        )

        list_filter = tuple(seller_store_admin.list_filter)
        self.assertTrue(list_filter, "SellerStore admin should expose a list_filter.")
        self.assertTrue(
            any(
                getattr(filter_class, "parameter_name", "") == "v209_profile"
                for filter_class in list_filter
            ),
            "SellerStore admin should expose the v209 profile polish filter.",
        )

    def test_v209_seller_store_admin_readonly_review_summary_is_available(self):
        seller_store_admin = self._seller_store_admin()

        readonly_fields = tuple(seller_store_admin.readonly_fields)

        self.assertIn("v209_profile_summary", readonly_fields)
        self.assertIn("v209_created_label", readonly_fields)
        self.assertIn("v209_updated_label", readonly_fields)

        for method_name in readonly_fields:
            self.assertTrue(
                hasattr(seller_store_admin, method_name),
                f"SellerStore admin missing readonly method {method_name}",
            )

    def test_v209_seller_store_admin_display_helpers_are_safe_for_unsaved_instance(self):
        seller_store_admin = self._seller_store_admin()
        instance = SellerStore()

        self.assertTrue(str(seller_store_admin.v209_store_identity(instance)))
        self.assertTrue(str(seller_store_admin.v209_owner_label(instance)))
        self.assertTrue(str(seller_store_admin.v209_profile_status(instance)))
        self.assertTrue(str(seller_store_admin.v209_profile_summary(instance)))
        self.assertTrue(str(seller_store_admin.v209_created_label(instance)))
        self.assertTrue(str(seller_store_admin.v209_updated_label(instance)))

    def test_v209_seller_store_admin_filter_lookups_are_review_friendly(self):
        seller_store_admin = self._seller_store_admin()
        filter_class = next(
            filter_class
            for filter_class in seller_store_admin.list_filter
            if getattr(filter_class, "parameter_name", "") == "v209_profile"
        )

        self.assertEqual(filter_class.title, "Profile polish")
        self.assertEqual(filter_class.parameter_name, "v209_profile")

    def test_v209_does_not_touch_saved_search_category_or_public_seller_store_templates(self):
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        seller_public_template = self._read("accounts/templates/accounts/seller_store_public.html")
        seller_directory_template = self._read("accounts/templates/accounts/seller_store_directory.html")
        category_admin_template = self._read("templates/admin/categories/category/change_list.html")
        category_nav_template = self._read("templates/categories/_category_navigation_v186.html")

        for template in (
            saved_search_template,
            seller_public_template,
            seller_directory_template,
            category_admin_template,
            category_nav_template,
        ):
            self.assertNotIn("V209_SELLER_STORE_ADMIN_UI_POLISH", template)

        self.assertIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", saved_search_template)
        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", seller_public_template)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", seller_directory_template)
        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_admin_template)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_nav_template)

    def test_v209_recent_checkpoint_markers_remain_available(self):
        expected_markers = {
            "listings/test_saved_search_notification_behavior_execution_v208.py": (
                "V208_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_EXECUTION_TESTS"
            ),
            "listings/test_release_candidate_final_hardening_audit_v207.py": (
                "V207_RELEASE_CANDIDATE_FINAL_HARDENING_AUDIT"
            ),
            "accounts/tests/test_seller_store_admin_detail_polish_audit_v206.py": (
                "V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT"
            ),
            "listings/test_saved_search_notification_ui_accessibility_polish_v205.py": (
                "V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH"
            ),
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py": (
                "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )

    def test_v209_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
