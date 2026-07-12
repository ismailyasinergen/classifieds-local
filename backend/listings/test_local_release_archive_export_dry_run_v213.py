from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN_MARKER = (
    "V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN"
)

V213_LOCAL_RELEASE_EXPORT_CONTRACT = (
    "git_archive_dry_run",
    "git_bundle_dry_run",
    "tmp_only_artifacts",
    "compose_config_validated",
    "backend_docs_absent",
    "no_runtime_changes",
    "no_committed_archive_artifacts",
)


class LocalReleaseArchiveExportDryRunV213Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v213_marker_is_declared_for_local_release_archive_export_dry_run(self):
        self.assertEqual(
            V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN_MARKER,
            "V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN",
        )

    def test_v213_local_release_export_contract_is_explicit_and_non_runtime(self):
        self.assertEqual(
            V213_LOCAL_RELEASE_EXPORT_CONTRACT,
            (
                "git_archive_dry_run",
                "git_bundle_dry_run",
                "tmp_only_artifacts",
                "compose_config_validated",
                "backend_docs_absent",
                "no_runtime_changes",
                "no_committed_archive_artifacts",
            ),
        )

    def test_v213_backend_runtime_entrypoints_remain_packaged(self):
        backend_root = self._backend_root()

        for relative_path in (
            "manage.py",
            "accounts",
            "listings",
            "categories",
            "conversations",
            "promotions",
            "pages",
            "templates",
        ):
            self.assertTrue(
                (backend_root / relative_path).exists(),
                f"Expected backend runtime entrypoint/package missing: {relative_path}",
            )

    def test_v213_key_release_checkpoint_tests_remain_packaged(self):
        expected_markers = {
            "accounts/tests/test_seller_store_admin_action_safety_v212.py": (
                "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS"
            ),
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

    def test_v213_migration_packages_remain_packaged_for_local_restore(self):
        backend_root = self._backend_root()

        for relative_path in (
            "accounts/migrations/__init__.py",
            "listings/migrations/__init__.py",
            "categories/migrations/__init__.py",
            "conversations/migrations/__init__.py",
            "promotions/migrations/__init__.py",
        ):
            self.assertTrue(
                (backend_root / relative_path).is_file(),
                f"Expected migration package file missing: {relative_path}",
            )

    def test_v213_static_media_and_template_settings_remain_available(self):
        self.assertTrue(getattr(settings, "STATIC_URL", None))
        self.assertIsNotNone(getattr(settings, "MEDIA_URL", None))
        self.assertTrue(getattr(settings, "TEMPLATES", None))

    def test_v213_dry_run_does_not_commit_archive_or_bundle_artifacts(self):
        backend_root = self._backend_root()
        forbidden_suffixes = (".zip", ".tar", ".tar.gz", ".tgz", ".bundle")

        suspicious_artifacts = [
            path
            for path in backend_root.rglob("*")
            if path.is_file()
            and path.suffix in forbidden_suffixes
            and "site-packages" not in str(path)
        ]

        self.assertEqual(
            suspicious_artifacts,
            [],
            "Release archive/bundle artifacts must not be committed into backend tree.",
        )

    def test_v213_marker_does_not_patch_runtime_or_template_surfaces(self):
        runtime_surfaces = (
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
            "listings/templates/listings/saved_search_list.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN",
                self._read(relative_path),
                f"v213 marker should not patch runtime/template surface {relative_path}",
            )

    def test_v213_does_not_touch_recent_audit_surfaces(self):
        audit_surfaces = (
            "accounts/tests/test_seller_store_admin_action_safety_v212.py",
            "listings/test_saved_search_notification_scheduler_design_audit_v211.py",
            "listings/test_final_local_release_packaging_checklist_v210.py",
            "accounts/tests/test_seller_store_admin_ui_polish_v209.py",
            "listings/test_saved_search_notification_behavior_execution_v208.py",
        )

        for relative_path in audit_surfaces:
            self.assertNotIn(
                "V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN",
                self._read(relative_path),
                f"v213 marker should not patch existing audit surface {relative_path}",
            )

    def test_v213_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
