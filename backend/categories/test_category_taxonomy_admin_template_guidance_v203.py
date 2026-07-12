from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from categories.models import Category


V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE_MARKER = (
    "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE"
)


class CategoryTaxonomyAdminTemplateGuidanceV203Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())
        cls.superuser = get_user_model().objects.create_superuser(
            username="v203-admin",
            email="v203-admin@example.com",
            password="test-password",
        )

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _category_admin(self):
        return admin.site._registry[Category]

    def _login(self):
        self.client.force_login(self.superuser)

    def test_v203_marker_is_declared_for_category_admin_template_guidance(self):
        self.assertEqual(
            V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE_MARKER,
            "V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE",
        )

    def test_v203_category_admin_source_mounts_dedicated_changelist_template(self):
        admin_source = self._read("categories/admin.py")

        self.assertIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", admin_source)
        self.assertIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", admin_source)
        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", admin_source)
        self.assertIn("_v203_apply_category_admin_template_guidance", admin_source)
        self.assertIn('change_list_template = "admin/categories/category/change_list.html"', admin_source)
        self.assertIn("v203_category_taxonomy_admin_template_guidance = True", admin_source)

    def test_v203_admin_class_preserves_existing_contracts(self):
        category_admin = self._category_admin()

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
            getattr(
                category_admin,
                "v203_category_taxonomy_admin_template_guidance",
                False,
            )
        )
        self.assertEqual(
            category_admin.change_list_template,
            "admin/categories/category/change_list.html",
        )
        self.assertEqual(
            category_admin.v203_category_admin_template_guidance_path,
            "admin/categories/category/change_list.html",
        )

    def test_v203_admin_template_contains_guidance_contract(self):
        template = self._read("templates/admin/categories/category/change_list.html")

        self.assertIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", template)
        self.assertIn("{% extends \"admin/change_list.html\" %}", template)
        self.assertIn('data-v203-category-admin-template-guidance="true"', template)
        self.assertIn('role="note"', template)
        self.assertIn('aria-label="Category taxonomy changelist guidance"', template)
        self.assertIn("Category taxonomy filtering guidance", template)
        self.assertIn("v199_category_filter_guidance", template)
        self.assertIn("v199_category_filter_summary", template)
        self.assertIn("Active filter summary:", template)
        self.assertIn("Keep broad taxonomy edits unfiltered", template)

    def test_v203_admin_changelist_renders_unfiltered_guidance(self):
        self._login()
        response = self.client.get(reverse("admin:categories_category_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "category-taxonomy-admin-guidance-v203")
        self.assertContains(response, 'data-v203-category-admin-template-guidance="true"')
        self.assertContains(response, "Category taxonomy filtering guidance")
        self.assertContains(
            response,
            "Use search, parent, and status filters to narrow large category taxonomies before editing.",
        )
        self.assertContains(response, "No category changelist filters are active.")

    def test_v203_admin_changelist_renders_active_filter_summary_from_v199_context(self):
        self._login()
        response = self.client.get(
            reverse("admin:categories_category_changelist"),
            {"q": "furniture"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "category-taxonomy-admin-guidance-v203")
        self.assertContains(
            response,
            "Review the filtered category set, then clear filters before broad taxonomy edits.",
        )
        self.assertContains(response, "Search: furniture")

    def test_v203_does_not_touch_saved_search_seller_store_or_category_nav_templates(self):
        saved_search = self._read("listings/templates/listings/saved_search_list.html")
        seller_store_public = self._read("accounts/templates/accounts/seller_store_public.html")
        seller_store_directory = self._read("accounts/templates/accounts/seller_store_directory.html")
        category_nav = self._read("templates/categories/_category_navigation_v186.html")
        v202_audit = self._read("listings/test_saved_search_notification_behavior_contract_audit_v202.py")

        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search)
        self.assertIn("V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH", seller_store_public)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", seller_store_directory)
        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_nav)
        self.assertIn("V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT", v202_audit)

        for text in (saved_search, seller_store_public, seller_store_directory, category_nav, v202_audit):
            self.assertNotIn("V203_CATEGORY_TAXONOMY_ADMIN_TEMPLATE_GUIDANCE", text)
            self.assertNotIn("category-taxonomy-admin-guidance-v203", text)

    def test_v203_existing_checkpoint_guards_remain_present(self):
        expected_test_markers = {
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py": (
                "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT"
            ),
            "accounts/tests/test_seller_store_public_page_accessibility_polish_v201.py": (
                "V201_SELLER_STORE_PUBLIC_PAGE_ACCESSIBILITY_POLISH"
            ),
            "listings/test_project_milestone_audit_release_readiness_v200.py": (
                "V200_PROJECT_MILESTONE_AUDIT_RELEASE_READINESS_SNAPSHOT"
            ),
            "categories/test_category_taxonomy_admin_changelist_filtering_polish_v199.py": (
                "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH"
            ),
            "categories/test_category_taxonomy_admin_ux_polish_v196.py": (
                "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH"
            ),
        }

        for relative_path, marker in expected_test_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected guard marker {marker} in {relative_path}",
            )
