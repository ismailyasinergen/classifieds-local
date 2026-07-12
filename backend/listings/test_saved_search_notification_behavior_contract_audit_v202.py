from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.db import models
from django.test import SimpleTestCase

from listings.models import SavedSearch


V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_MARKER = (
    "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT"
)


class SavedSearchNotificationBehaviorContractAuditV202Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _saved_search_notification_fields(self):
        return [
            field
            for field in SavedSearch._meta.fields
            if "notification" in field.name.lower() or "alert" in field.name.lower()
        ]

    def test_v202_marker_is_declared_for_saved_search_notification_behavior_contract_audit(self):
        self.assertEqual(
            V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_MARKER,
            "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT",
        )

    def test_v202_saved_search_model_keeps_notification_related_fields(self):
        notification_fields = self._saved_search_notification_fields()
        fields_by_name = {field.name: field for field in notification_fields}

        expected_names = {
            "email_notifications_enabled",
            "last_notification_checked_at",
            "last_notification_sent_at",
        }

        self.assertTrue(
            notification_fields,
            "SavedSearch should keep concrete notification/alert fields.",
        )
        self.assertTrue(
            expected_names.issubset(fields_by_name),
            f"SavedSearch notification fields missing: {expected_names - set(fields_by_name)}",
        )
        self.assertIsInstance(fields_by_name["email_notifications_enabled"], models.BooleanField)
        self.assertIsInstance(fields_by_name["last_notification_checked_at"], models.DateTimeField)
        self.assertIsInstance(fields_by_name["last_notification_sent_at"], models.DateTimeField)

        for field in notification_fields:
            self.assertFalse(field.primary_key)
            self.assertIsInstance(field, models.Field)

    def test_v202_saved_search_notification_migration_remains_present_with_django_model_name_serialization(self):
        migrations_root = self._backend_root() / "listings" / "migrations"
        notification_migrations = sorted(
            path
            for path in migrations_root.glob("*.py")
            if "savedsearch" in path.name.lower() and "notification" in path.name.lower()
        )

        self.assertTrue(
            notification_migrations,
            "Expected a saved-search notification migration file to remain present.",
        )

        combined = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in notification_migrations
        )

        # Django migrations serialize model names in lowercase, e.g. model_name='savedsearch'.
        self.assertTrue(
            "model_name='savedsearch'" in combined
            or 'model_name="savedsearch"' in combined,
            "Saved-search notification migration should target model_name='savedsearch'.",
        )
        self.assertIn("migrations.AddField", combined)
        self.assertIn("email_notifications_enabled", combined)
        self.assertIn("last_notification_checked_at", combined)
        self.assertIn("last_notification_sent_at", combined)
        self.assertIn("models.BooleanField", combined)
        self.assertIn("models.DateTimeField", combined)
        self.assertNotIn("V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT", combined)

    def test_v202_saved_search_management_template_keeps_notification_settings_guidance(self):
        template = self._read("listings/templates/listings/saved_search_list.html")

        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", template)
        self.assertIn("saved-search-notification-settings-v197", template)
        self.assertIn('data-v197-saved-search-notification-settings="true"', template)
        self.assertIn("Fine-tune saved search notifications", template)
        self.assertIn("Keep alerts useful by reviewing which saved searches should notify you", template)
        self.assertIn("Pause or remove searches that no longer need updates.", template)

    def test_v202_saved_search_runtime_contract_sources_remain_in_place(self):
        views_source = self._read("listings/saved_searches_views.py")
        urls_source = self._read("listings/urls.py")
        model_source = self._read("listings/models.py")

        self.assertIn("SavedSearch", views_source)
        self.assertIn("SavedSearch", model_source)
        self.assertIn("saved-search", urls_source.lower())
        self.assertIn("email_notifications_enabled", model_source)
        self.assertIn("last_notification_checked_at", model_source)
        self.assertIn("last_notification_sent_at", model_source)

    def test_v202_notification_contract_is_audit_only_and_does_not_patch_runtime_surfaces(self):
        runtime_surfaces = (
            "listings/models.py",
            "listings/saved_searches_views.py",
            "listings/urls.py",
            "listings/templates/listings/saved_search_list.html",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "categories/admin.py",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT",
                self._read(relative_path),
                f"v202 marker should not be in runtime surface {relative_path}",
            )

    def test_v202_recent_checkpoint_markers_remain_scoped(self):
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")
        seller_store_public = self._read("accounts/templates/accounts/seller_store_public.html")
        category_admin = self._read("categories/admin.py")
        v200_audit = self._read("listings/test_project_milestone_audit_release_readiness_v200.py")

        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", seller_store_public)
        self.assertIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", category_admin)
        self.assertIn("V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT", v200_audit)

        self.assertNotIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", saved_search_template)
        self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", saved_search_template)
        self.assertNotIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", seller_store_public)
        self.assertNotIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", category_admin)

    def test_v202_existing_saved_search_checkpoint_guards_remain_present(self):
        expected_test_markers = {
            "listings/test_saved_search_notification_settings_polish_v197.py": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
            ),
            "listings/test_project_milestone_audit_release_readiness_v200.py": (
                "V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT"
            ),
            "accounts/tests/test_seller_store_public_page_accessibility_polish_v201.py": (
                "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH"
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

    def test_v202_notification_contract_does_not_add_new_migrations(self):
        migration_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (self._backend_root() / "listings" / "migrations").glob("*.py")
        )

        self.assertNotIn("V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT", migration_text)
