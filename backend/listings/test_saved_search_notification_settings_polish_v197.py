from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from listings.models import SavedSearch


V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_MARKER = (
    "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
)


class SavedSearchNotificationSettingsPolishV197Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())
        cls.user = get_user_model().objects.create_user(
            username="v197-saved-search-notification-user",
            email="v197-saved-search-notification-user@example.com",
            password="test-password",
        )

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _saved_search_management_template_path(self) -> Path:
        return (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / "saved_search_list.html"
        )

    def _category_admin_path(self) -> Path:
        return self._backend_root() / "categories" / "admin.py"

    def _category_navigation_partial_path(self) -> Path:
        return self._backend_root() / "templates" / "categories" / "_category_navigation_v186.html"

    def _seller_store_directory_template_path(self) -> Path:
        return (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_directory.html"
        )

    def _saved_search_management_url(self) -> str:
        candidates = (
            "listings:saved_search_list",
            "listings:saved_searches",
            "listings:saved_search_management",
            "saved_search_list",
            "saved_searches",
            "saved_search_management",
        )

        for name in candidates:
            try:
                return reverse(name)
            except NoReverseMatch:
                continue

        return "/listings/saved-searches/"

    def _get_saved_search_management_content(self):
        self.client.force_login(self.user)
        response = self.client.get(self._saved_search_management_url())
        content = response.content.decode("utf-8", errors="ignore")
        return response, content

    def test_v197_marker_is_declared_for_saved_search_notification_settings_polish(self):
        self.assertEqual(
            V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_MARKER,
            "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH",
        )

    def test_v197_saved_search_model_still_has_notification_related_contract(self):
        field_names = {field.name for field in SavedSearch._meta.get_fields() if hasattr(field, "name")}
        notification_fields = {
            name
            for name in field_names
            if "notification" in name.lower() or "alert" in name.lower()
        }

        self.assertTrue(
            notification_fields,
            f"Expected at least one saved-search notification/alert field; found fields: {sorted(field_names)}",
        )

    def test_v197_template_contains_notification_settings_guidance(self):
        text = self._saved_search_management_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", text)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", text)
        self.assertIn("saved-search-notification-settings-v197", text)
        self.assertIn('data-v197-saved-search-notification-settings="true"', text)
        self.assertIn('aria-label="Saved search notification settings guidance"', text)
        self.assertIn('aria-label="Saved search notification tips"', text)
        self.assertIn("Fine-tune saved search notifications", text)
        self.assertIn(
            "Keep alerts useful by reviewing which saved searches should notify you and which should simply stay saved for later.",
            text,
        )
        self.assertIn("Use names that explain what each alert is watching.", text)
        self.assertIn("Pause or remove searches that no longer need updates.", text)
        self.assertIn("Check the filter summary before relying on a saved search notification.", text)
        self.assertIn("@media (max-width: 640px)", text)

    def test_v197_empty_saved_search_management_page_renders_notification_guidance(self):
        response, content = self._get_saved_search_management_content()

        self.assertEqual(response.status_code, 200)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", content)
        self.assertIn('data-v197-saved-search-notification-settings="true"', content)
        self.assertIn("Fine-tune saved search notifications", content)
        self.assertIn("Use names that explain what each alert is watching.", content)
        self.assertIn("Pause or remove searches that no longer need updates.", content)
        self.assertIn("Check the filter summary before relying on a saved search notification.", content)

    def test_v197_preserves_v194_saved_search_management_copy(self):
        response, content = self._get_saved_search_management_content()

        self.assertEqual(response.status_code, 200)
        self.assertIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", content)
        self.assertIn('data-v194-saved-search-management-copy="true"', content)
        self.assertIn("Manage saved searches with confidence", content)
        self.assertIn("No saved searches yet", content)

    def test_v197_does_not_touch_category_admin_category_nav_or_seller_store_templates(self):
        category_admin = self._category_admin_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        category_partial = self._category_navigation_partial_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )
        seller_store_directory = self._seller_store_directory_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", category_admin)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_partial)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", seller_store_directory)

        for text in (category_admin, category_partial, seller_store_directory):
            self.assertNotIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", text)
            self.assertNotIn("saved-search-notification-settings-v197", text)
            self.assertNotIn("Fine-tune saved search notifications", text)

    def test_v197_saved_search_template_does_not_receive_category_or_seller_store_or_admin_hooks(self):
        text = self._saved_search_management_template_path().read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertNotIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", text)
        self.assertNotIn("v196_parent_path", text)
        self.assertNotIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", text)
        self.assertNotIn("seller-store-directory-responsive-v195", text)
        self.assertNotIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", text)
        self.assertNotIn("category-navigation-v193-keyboard-ready", text)

    def test_v197_existing_checkpoint_guards_remain_present(self):
        v194_test = self._backend_root() / "listings" / "test_saved_search_management_copy_polish_v194.py"
        v195_test = (
            self._backend_root()
            / "accounts"
            / "tests"
            / "test_seller_store_directory_responsive_polish_v195.py"
        )
        v196_test = self._backend_root() / "categories" / "test_category_taxonomy_admin_ux_polish_v196.py"

        self.assertTrue(v194_test.exists())
        self.assertTrue(v195_test.exists())
        self.assertTrue(v196_test.exists())

        self.assertIn(
            "V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH",
            v194_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH",
            v195_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH",
            v196_test.read_text(encoding="utf-8", errors="ignore"),
        )
