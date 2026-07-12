from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.test import SimpleTestCase

from accounts.models import SellerStore


V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS_MARKER = (
    "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS"
)

V212_FORBIDDEN_SELLER_STORE_ADMIN_ACTION_NAMES = (
    "approve_seller_stores",
    "approve_selected_seller_stores",
    "verify_seller_stores",
    "verify_selected_seller_stores",
    "publish_seller_stores",
    "unpublish_seller_stores",
    "suspend_seller_stores",
    "delete_seller_stores",
    "bulk_approve",
    "bulk_verify",
    "bulk_suspend",
    "bulk_delete",
)


class SellerStoreAdminActionSafetyV212Tests(SimpleTestCase):
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

    def _seller_store_v209_block(self) -> str:
        accounts_admin = self._read("accounts/admin.py")
        start = "# V209_SELLER_STORE_ADMIN_UI_POLISH START"
        end = "# V209_SELLER_STORE_ADMIN_UI_POLISH END"

        self.assertIn(start, accounts_admin)
        self.assertIn(end, accounts_admin)

        return accounts_admin.split(start, 1)[1].split(end, 1)[0]

    def test_v212_marker_is_declared_for_seller_store_admin_action_safety(self):
        self.assertEqual(
            V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS_MARKER,
            "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS",
        )

    def test_v212_forbidden_action_name_contract_is_explicit(self):
        self.assertIn(
            "bulk_delete",
            V212_FORBIDDEN_SELLER_STORE_ADMIN_ACTION_NAMES,
        )
        self.assertIn(
            "bulk_suspend",
            V212_FORBIDDEN_SELLER_STORE_ADMIN_ACTION_NAMES,
        )
        self.assertIn(
            "approve_selected_seller_stores",
            V212_FORBIDDEN_SELLER_STORE_ADMIN_ACTION_NAMES,
        )

    def test_v212_seller_store_admin_remains_registered_with_v209_polish(self):
        seller_store_admin = self._seller_store_admin()

        self.assertEqual(seller_store_admin.model, SellerStore)
        self.assertTrue(
            getattr(seller_store_admin, "v209_seller_store_admin_ui_polish", False)
        )
        self.assertIn("v209_store_identity", tuple(seller_store_admin.list_display))
        self.assertIn("v209_owner_label", tuple(seller_store_admin.list_display))
        self.assertIn("v209_profile_status", tuple(seller_store_admin.list_display))
        self.assertIn("v209_profile_summary", tuple(seller_store_admin.readonly_fields))

    def test_v212_seller_store_admin_declares_no_custom_bulk_actions(self):
        seller_store_admin = self._seller_store_admin()

        configured_actions = getattr(seller_store_admin, "actions", None)

        if configured_actions is None:
            self.assertIsNone(configured_actions)
        else:
            self.assertEqual(
                tuple(configured_actions),
                (),
                "SellerStore admin should not declare custom bulk actions.",
            )

    def test_v212_seller_store_admin_has_no_forbidden_action_methods(self):
        seller_store_admin = self._seller_store_admin()

        for action_name in V212_FORBIDDEN_SELLER_STORE_ADMIN_ACTION_NAMES:
            self.assertFalse(
                hasattr(seller_store_admin, action_name),
                f"SellerStore admin must not expose unsafe action method {action_name}.",
            )

    def test_v212_seller_store_admin_source_has_no_action_decorators_or_bulk_hooks(self):
        v209_block = self._seller_store_v209_block()

        forbidden_source_terms = (
            "actions =",
            "delete_queryset",
            "delete_model",
            "response_action",
            "@admin.action",
            "@_v209_admin.action",
            "bulk_approve",
            "bulk_verify",
            "bulk_suspend",
            "bulk_delete",
            "approve_selected",
            "verify_selected",
            "suspend_selected",
            "delete_selected_seller",
        )

        for term in forbidden_source_terms:
            self.assertNotIn(
                term,
                v209_block,
                f"SellerStore v209 admin block should not include unsafe action hook {term}.",
            )

    def test_v212_seller_store_admin_safe_review_helpers_remain_readonly(self):
        seller_store_admin = self._seller_store_admin()
        readonly_fields = tuple(seller_store_admin.readonly_fields)

        self.assertIn("v209_profile_summary", readonly_fields)
        self.assertIn("v209_created_label", readonly_fields)
        self.assertIn("v209_updated_label", readonly_fields)

        instance = SellerStore()
        self.assertTrue(str(seller_store_admin.v209_profile_summary(instance)))
        self.assertTrue(str(seller_store_admin.v209_created_label(instance)))
        self.assertTrue(str(seller_store_admin.v209_updated_label(instance)))

    def test_v212_seller_store_admin_filter_is_review_only_not_action_like(self):
        seller_store_admin = self._seller_store_admin()
        list_filter = tuple(seller_store_admin.list_filter)

        self.assertTrue(list_filter)
        self.assertTrue(
            any(
                getattr(filter_class, "parameter_name", "") == "v209_profile"
                for filter_class in list_filter
            )
        )

        for filter_class in list_filter:
            filter_name = getattr(filter_class, "__name__", "")
            self.assertNotIn("Action", filter_name)
            self.assertNotIn("Bulk", filter_name)

    def test_v212_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
            "listings/test_saved_search_notification_scheduler_design_audit_v211.py": (
                "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT"
            ),
            "listings/test_final_local_release_packaging_checklist_v210.py": (
                "V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST"
            ),
            "accounts/tests/test_seller_store_admin_ui_polish_v209.py": (
                "V209_SELLER_STORE_ADMIN_UI_POLISH"
            ),
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
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )

    def test_v212_marker_does_not_patch_runtime_admin_or_templates(self):
        runtime_surfaces = (
            "accounts/admin.py",
            "accounts/models.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "listings/models.py",
            "listings/templates/listings/saved_search_list.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS",
                self._read(relative_path),
                f"v212 marker should not patch runtime/template surface {relative_path}",
            )

    def test_v212_does_not_touch_saved_search_scheduler_release_packaging_or_category_surfaces(self):
        surfaces = (
            "listings/test_saved_search_notification_scheduler_design_audit_v211.py",
            "listings/test_final_local_release_packaging_checklist_v210.py",
            "listings/saved_searches_views.py",
            "listings/forms.py",
            "listings/urls.py",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in surfaces:
            self.assertNotIn(
                "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS",
                self._read(relative_path),
                f"v212 marker should not be in unrelated surface {relative_path}",
            )

    def test_v212_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
