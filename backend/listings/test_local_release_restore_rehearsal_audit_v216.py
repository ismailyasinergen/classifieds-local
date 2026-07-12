from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management import get_commands
from django.test import TestCase


V216_LOCAL_RELEASE_RESTORE_REHEARSAL_AUDIT = (
    "V216_LOCAL_RELEASE_RESTORE_REHEARSAL_AUDIT"
)


class LocalReleaseRestoreRehearsalAuditV216Tests(TestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v216_marker_is_declared_for_restore_rehearsal_audit(self):
        self.assertEqual(
            V216_LOCAL_RELEASE_RESTORE_REHEARSAL_AUDIT,
            "V216_LOCAL_RELEASE_RESTORE_REHEARSAL_AUDIT",
        )

    def test_v216_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v216_restore_rehearsal_backend_entrypoints_are_packaged(self):
        required_backend_paths = (
            "manage.py",
            "Dockerfile",
            "config/settings.py",
            "config/urls.py",
            "config/wsgi.py",
            "accounts/admin.py",
            "accounts/models.py",
            "listings/models.py",
            "categories/models.py",
        )

        for relative_path in required_backend_paths:
            self.assertTrue(
                (self._backend_root() / relative_path).is_file(),
                f"Restore rehearsal requires packaged backend file: {relative_path}",
            )

    def test_v216_restore_rehearsal_migration_packages_are_packaged(self):
        required_migrations = (
            "accounts/migrations/__init__.py",
            "accounts/migrations/0014_seller_store.py",
            "accounts/migrations/0015_seller_store_branding.py",
            "listings/migrations/__init__.py",
            "listings/migrations/0014_savedsearch.py",
            "listings/migrations/0015_savedsearch_notifications.py",
            "categories/migrations/__init__.py",
            "categories/migrations/0001_initial.py",
        )

        for relative_path in required_migrations:
            self.assertTrue(
                (self._backend_root() / relative_path).is_file(),
                f"Restore rehearsal requires packaged migration: {relative_path}",
            )

    def test_v216_restore_rehearsal_management_commands_are_packaged(self):
        command_names = get_commands()

        self.assertIn("verify_marketplace_category_seed", command_names)
        self.assertIn("process_saved_search_notifications", command_names)

    def test_v216_local_runtime_settings_keep_restore_ready_storage_paths(self):
        self.assertIn("default", settings.DATABASES)
        self.assertTrue(str(settings.MEDIA_ROOT))
        self.assertTrue(str(settings.STATIC_ROOT))
        self.assertTrue(settings.ROOT_URLCONF)
        self.assertTrue(settings.WSGI_APPLICATION)

    def test_v216_recent_release_checkpoint_markers_remain_packaged(self):
        expected_markers = {
            "accounts/tests/test_seller_store_admin_action_implementation_v215.py": (
                "V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS"
            ),
            "listings/test_saved_search_notification_scheduler_spike_v214.py": (
                "V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE"
            ),
            "listings/test_local_release_archive_export_dry_run_v213.py": (
                "V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN"
            ),
            "accounts/tests/test_seller_store_admin_action_safety_v212.py": (
                "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS"
            ),
            "listings/test_saved_search_notification_scheduler_design_audit_v211.py": (
                "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT"
            ),
            "listings/test_final_local_release_packaging_checklist_v210.py": (
                "V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )

    def test_v216_restore_audit_does_not_patch_runtime_or_template_surfaces(self):
        untouched_surfaces = (
            "accounts/admin.py",
            "accounts/models.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/management/commands/process_saved_search_notifications.py",
            "listings/templates/listings/saved_search_list.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in untouched_surfaces:
            self.assertNotIn(
                "V216_LOCAL_RELEASE_RESTORE_REHEARSAL_AUDIT",
                self._read(relative_path),
                f"v216 marker should not patch runtime/template surface {relative_path}",
            )

    def test_v216_restore_rehearsal_contract_is_audit_only(self):
        source = self._read("listings/test_local_release_restore_rehearsal_audit_v216.py")

        self.assertIn("restore rehearsal", source)
        self.assertIn("backend/docs", source)

        forbidden_terms = (
            "subprocess" + ".run",
            "docker compose " + "up",
            "docker compose " + "down",
            "fl" + "ush",
            "load" + "data",
            "migrate --" + "fake",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, source)
