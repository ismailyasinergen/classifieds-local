from __future__ import annotations

import importlib
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.test import SimpleTestCase

from accounts.models import SellerStore
from listings.models import SavedSearch


V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST_MARKER = (
    "V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST"
)


class FinalLocalReleasePackagingChecklistV210Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v210_marker_is_declared_for_final_local_release_packaging_checklist(self):
        self.assertEqual(
            V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST_MARKER,
            "V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST",
        )

    def test_v210_backend_runtime_entrypoints_are_packaged(self):
        backend_root = self._backend_root()

        self.assertTrue((backend_root / "manage.py").is_file())
        self.assertTrue((backend_root / "accounts").is_dir())
        self.assertTrue((backend_root / "listings").is_dir())
        self.assertTrue((backend_root / "categories").is_dir())

        root_urlconf_module = importlib.import_module(settings.ROOT_URLCONF)
        self.assertTrue(Path(root_urlconf_module.__file__).is_file())

        if getattr(settings, "WSGI_APPLICATION", None):
            wsgi_module_name = settings.WSGI_APPLICATION.rsplit(".", 1)[0]
            wsgi_module = importlib.import_module(wsgi_module_name)
            self.assertTrue(Path(wsgi_module.__file__).is_file())

    def test_v210_required_local_apps_remain_installed(self):
        installed_apps = set(settings.INSTALLED_APPS)
        installed_app_roots = {
            app.split(".apps.", 1)[0] if ".apps." in app else app
            for app in installed_apps
        }

        for app_label in (
            "accounts",
            "listings",
            "categories",
            "conversations",
            "promotions",
            "pages",
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.sessions",
            "django.contrib.staticfiles",
        ):
            self.assertTrue(
                app_label in installed_apps or app_label in installed_app_roots,
                f"{app_label} should be installed either as a bare app label or AppConfig path.",
            )

    def test_v210_database_and_static_settings_are_configured_for_local_runtime(self):
        default_database = settings.DATABASES.get("default", {})
        engine = default_database.get("ENGINE", "")

        self.assertIn("django.db.backends", engine)
        self.assertTrue(getattr(settings, "STATIC_URL", None))
        self.assertIsNotNone(getattr(settings, "MEDIA_URL", None))

    def test_v210_migration_packages_and_key_migrations_are_packaged(self):
        backend_root = self._backend_root()

        required_migration_packages = (
            "accounts/migrations/__init__.py",
            "listings/migrations/__init__.py",
            "categories/migrations/__init__.py",
            "conversations/migrations/__init__.py",
            "promotions/migrations/__init__.py",
        )

        for relative_path in required_migration_packages:
            self.assertTrue(
                (backend_root / relative_path).is_file(),
                f"Expected migration package file missing: {relative_path}",
            )

        expected_key_migrations = (
            "accounts/migrations/0014_seller_store.py",
            "accounts/migrations/0015_seller_store_branding.py",
            "listings/migrations/0014_savedsearch.py",
            "listings/migrations/0015_savedsearch_notifications.py",
            "promotions/migrations/0004_alter_listingpromotion_status.py",
        )

        for relative_path in expected_key_migrations:
            self.assertTrue(
                (backend_root / relative_path).is_file(),
                f"Expected key local-release migration missing: {relative_path}",
            )

    def test_v210_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_release_candidate_dry_run_checklist_v204.py": (
                "V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST"
            ),
            "categories/test_category_taxonomy_admin_template_guidance_v203.py": (
                "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE"
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

    def test_v210_seller_store_admin_polish_remains_packaged(self):
        seller_store_admin = admin.site._registry.get(SellerStore)

        self.assertIsNotNone(seller_store_admin)
        self.assertTrue(
            getattr(seller_store_admin, "v209_seller_store_admin_ui_polish", False)
        )
        self.assertIn("v209_store_identity", tuple(seller_store_admin.list_display))
        self.assertIn("v209_owner_label", tuple(seller_store_admin.list_display))
        self.assertIn("v209_profile_status", tuple(seller_store_admin.list_display))
        self.assertIn("v209_profile_summary", tuple(seller_store_admin.readonly_fields))

    def test_v210_saved_search_notification_behavior_remains_packaged(self):
        saved_search_fields = {field.name for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", saved_search_fields)
        self.assertIn("last_notification_checked_at", saved_search_fields)
        self.assertIn("last_notification_sent_at", saved_search_fields)

        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", saved_search_template)

    def test_v210_release_templates_remain_packaged_and_scoped(self):
        template_contracts = {
            "accounts/templates/accounts/seller_store_public.html": (
                "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH",
                "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH",
            ),
            "accounts/templates/accounts/seller_store_directory.html": (
                "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH",
                "V192_SELLER_STORE_CATEGORY_UI_POLISH",
            ),
            "templates/admin/categories/category/change_list.html": (
                "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE",
            ),
            "templates/categories/_category_navigation_v186.html": (
                "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING",
            ),
        }

        for relative_path, markers in template_contracts.items():
            template = self._read(relative_path)
            for marker in markers:
                self.assertIn(marker, template)

            self.assertNotIn("V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST", template)

    def test_v210_marker_does_not_patch_runtime_or_template_surfaces(self):
        runtime_surfaces = (
            "accounts/admin.py",
            "accounts/models.py",
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
                "V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST",
                self._read(relative_path),
                f"v210 marker should not be in runtime/template surface {relative_path}",
            )

    def test_v210_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
