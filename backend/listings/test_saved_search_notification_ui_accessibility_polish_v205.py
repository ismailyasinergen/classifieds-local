from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_MARKER = (
    "V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH"
)


class SavedSearchNotificationUiAccessibilityPolishV205Tests(SimpleTestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _saved_search_template(self) -> str:
        return self._read("listings/templates/listings/saved_search_list.html")

    def test_v205_marker_is_declared_for_saved_search_notification_ui_accessibility_polish(self):
        self.assertEqual(
            V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_MARKER,
            "V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH",
        )

    def test_v205_saved_search_template_preserves_v197_notification_guidance(self):
        template = self._saved_search_template()

        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", template)
        self.assertIn("saved-search-notification-settings-v197", template)
        self.assertIn('data-v197-saved-search-notification-settings="true"', template)
        self.assertIn("Fine-tune saved search notifications", template)
        self.assertIn("Keep alerts useful by reviewing which saved searches should notify you", template)
        self.assertIn("Pause or remove searches that no longer need updates.", template)

    def test_v205_saved_search_template_contains_accessibility_region_contract(self):
        template = self._saved_search_template()

        self.assertIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", template)
        self.assertIn("saved-search-notification-a11y-v205", template)
        self.assertIn('data-v205-saved-search-notification-accessibility="true"', template)
        self.assertIn('role="region"', template)
        self.assertIn('tabindex="-1"', template)
        self.assertIn('aria-labelledby="saved-search-notification-a11y-v205-title"', template)
        self.assertIn('aria-describedby="saved-search-notification-a11y-v205-help"', template)
        self.assertIn('id="saved-search-notification-a11y-v205-title"', template)
        self.assertIn('id="saved-search-notification-a11y-v205-help"', template)
        self.assertIn("Accessible saved search notifications", template)

    def test_v205_saved_search_template_contains_screen_reader_and_focus_helpers(self):
        template = self._saved_search_template()

        self.assertIn("saved-search-notification-a11y-v205__sr-only", template)
        self.assertIn("Notification settings should be reviewed before enabling, pausing, renaming, or deleting saved searches.", template)
        self.assertIn(":focus-visible", template)
        self.assertIn("outline: 3px solid #4f46e5", template)
        self.assertIn("outline-offset: 3px", template)
        self.assertIn("@media (max-width: 820px)", template)
        self.assertIn("@media (max-width: 520px)", template)

    def test_v205_saved_search_template_contains_notification_accessibility_tip_copy(self):
        template = self._saved_search_template()

        self.assertIn('aria-label="Saved search notification accessibility tips"', template)
        self.assertIn("Check alert status", template)
        self.assertIn("Confirm which saved searches are allowed to send email updates.", template)
        self.assertIn("Keep focus visible", template)
        self.assertIn("Keyboard users get a stronger focus outline on notification controls and saved-search actions.", template)
        self.assertIn("Pause stale alerts", template)
        self.assertIn("Remove or pause searches that no longer need notification updates.", template)

    def test_v205_does_not_touch_category_admin_seller_store_or_navigation_templates(self):
        category_admin = self._read("categories/admin.py")
        category_admin_template = self._read("templates/admin/categories/category/change_list.html")
        seller_store_public = self._read("accounts/templates/accounts/seller_store_public.html")
        seller_store_directory = self._read("accounts/templates/accounts/seller_store_directory.html")
        category_nav = self._read("templates/categories/_category_navigation_v186.html")

        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_admin)
        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", category_admin_template)
        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", seller_store_public)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", seller_store_directory)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_nav)

        for text in (
            category_admin,
            category_admin_template,
            seller_store_public,
            seller_store_directory,
            category_nav,
        ):
            self.assertNotIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", text)
            self.assertNotIn("saved-search-notification-a11y-v205", text)
            self.assertNotIn("Accessible saved search notifications", text)

    def test_v205_does_not_patch_saved_search_runtime_sources_or_migrations(self):
        runtime_sources = (
            "listings/models.py",
            "listings/saved_searches_views.py",
            "listings/urls.py",
        )

        for relative_path in runtime_sources:
            text = self._read(relative_path)
            self.assertNotIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", text)
            self.assertNotIn("saved-search-notification-a11y-v205", text)

        migrations_text = "\n".join(
            path.read_text(encoding="utf-8", errors="ignore")
            for path in (self._backend_root() / "listings" / "migrations").glob("*.py")
        )
        self.assertNotIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", migrations_text)
        self.assertNotIn("saved-search-notification-a11y-v205", migrations_text)

    def test_v205_recent_checkpoint_guards_remain_present(self):
        expected_test_markers = {
            "listings/test_release_candidate_dry_run_checklist_v204.py": (
                "V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST"
            ),
            "categories/test_category_taxonomy_admin_template_guidance_v203.py": (
                "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE"
            ),
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py": (
                "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT"
            ),
            "accounts/tests/test_seller_store_public_page_accessibility_polish_v201.py": (
                "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH"
            ),
            "listings/test_saved_search_notification_settings_polish_v197.py": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
            ),
        }

        for relative_path, marker in expected_test_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected guard marker {marker} in {relative_path}",
            )
