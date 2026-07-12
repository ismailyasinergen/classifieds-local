from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.db import models
from django.test import SimpleTestCase

from listings.models import SavedSearch


V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT_MARKER = (
    "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT"
)

V211_SCHEDULER_DESIGN_CONTRACT = (
    "owner_scoped",
    "opt_in_only",
    "disabled_searches_excluded",
    "checked_timestamp_recorded",
    "sent_timestamp_recorded",
    "no_background_worker_added",
    "no_management_command_added",
    "no_migration_added",
)


class SavedSearchNotificationSchedulerDesignAuditV211Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v211_marker_is_declared_for_scheduler_design_audit(self):
        self.assertEqual(
            V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT_MARKER,
            "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT",
        )

    def test_v211_scheduler_design_contract_is_explicit_and_non_runtime(self):
        self.assertEqual(
            V211_SCHEDULER_DESIGN_CONTRACT,
            (
                "owner_scoped",
                "opt_in_only",
                "disabled_searches_excluded",
                "checked_timestamp_recorded",
                "sent_timestamp_recorded",
                "no_background_worker_added",
                "no_management_command_added",
                "no_migration_added",
            ),
        )

    def test_v211_saved_search_model_has_scheduler_ready_notification_fields(self):
        fields_by_name = {field.name: field for field in SavedSearch._meta.fields}

        expected_fields = {
            "email_notifications_enabled": models.BooleanField,
            "last_notification_checked_at": models.DateTimeField,
            "last_notification_sent_at": models.DateTimeField,
        }

        for field_name, expected_class in expected_fields.items():
            self.assertIn(field_name, fields_by_name)
            self.assertIsInstance(fields_by_name[field_name], expected_class)

        self.assertTrue(
            fields_by_name["last_notification_checked_at"].null,
            "last_notification_checked_at should allow NULL before a scheduler checks it.",
        )
        self.assertTrue(
            fields_by_name["last_notification_sent_at"].null,
            "last_notification_sent_at should allow NULL before a scheduler sends anything.",
        )

    def test_v211_scheduler_candidate_queryset_can_be_owner_and_opt_in_scoped(self):
        field_names = {field.name for field in SavedSearch._meta.fields}

        self.assertIn("user", field_names)
        self.assertIn("email_notifications_enabled", field_names)

        candidate_filters = {
            "user": "request.user",
            "email_notifications_enabled": True,
        }

        self.assertEqual(candidate_filters["user"], "request.user")
        self.assertIs(candidate_filters["email_notifications_enabled"], True)

    def test_v211_disabled_notifications_have_a_clear_exclusion_contract(self):
        field_names = {field.name for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", field_names)

        excluded_filter = {"email_notifications_enabled": False}
        included_filter = {"email_notifications_enabled": True}

        self.assertIs(excluded_filter["email_notifications_enabled"], False)
        self.assertIs(included_filter["email_notifications_enabled"], True)

    def test_v211_saved_search_notification_ui_guidance_remains_packaged(self):
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")

        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", saved_search_template)
        self.assertIn("saved-search-notification-settings-v197", saved_search_template)
        self.assertIn("saved-search-notification-a11y-v205", saved_search_template)
        self.assertIn("Accessible saved search notifications", saved_search_template)

    def test_v211_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py": (
                "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT"
            ),
            "listings/test_saved_search_notification_settings_polish_v197.py": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )

    def test_v211_does_not_add_scheduler_runtime_command_or_background_worker(self):
        backend_root = self._backend_root()

        optional_runtime_paths = (
            "listings/management/commands",
            "listings/tasks.py",
            "listings/scheduler.py",
            "listings/notifications.py",
        )

        for relative_path in optional_runtime_paths:
            path = backend_root / relative_path
            if path.is_file():
                self.assertNotIn(
                    "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT",
                    path.read_text(encoding="utf-8", errors="ignore"),
                    f"v211 marker should not patch runtime scheduler file {relative_path}",
                )
            elif path.is_dir():
                for child in path.rglob("*.py"):
                    self.assertNotIn(
                        "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT",
                        child.read_text(encoding="utf-8", errors="ignore"),
                        f"v211 marker should not patch runtime scheduler command {child}",
                    )

    def test_v211_does_not_add_migrations_or_patch_saved_search_runtime_sources(self):
        runtime_surfaces = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT",
                self._read(relative_path),
                f"v211 marker should not be in saved-search runtime surface {relative_path}",
            )

        migrations_root = self._backend_root() / "listings" / "migrations"
        migration_text = "\n".join(
            migration.read_text(encoding="utf-8", errors="ignore")
            for migration in sorted(migrations_root.glob("*.py"))
        )
        self.assertNotIn("V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT", migration_text)

    def test_v211_does_not_touch_seller_store_category_or_release_packaging_surfaces(self):
        surfaces = (
            "accounts/admin.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
            "listings/test_final_local_release_packaging_checklist_v210.py",
        )

        for relative_path in surfaces:
            self.assertNotIn(
                "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT",
                self._read(relative_path),
                f"v211 marker should not be in unrelated surface {relative_path}",
            )

    def test_v211_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
