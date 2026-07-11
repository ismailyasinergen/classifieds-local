from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import RequestFactory, TestCase

from categories.models import Category


V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_MARKER = (
    "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH"
)


class CategoryTaxonomyAdminChangelistFilteringPolishV199Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())
        cls.superuser = get_user_model().objects.create_superuser(
            username="v199-admin",
            email="v199-admin@example.com",
            password="test-password",
        )

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _admin_source_path(self) -> Path:
        return self._backend_root() / "categories" / "admin.py"

    def _category_admin(self):
        return admin.site._registry[Category]

    def _request(self, params=None):
        request = RequestFactory().get("/admin/categories/category/", data=params or {})
        request.user = self.superuser
        return request

    def test_v199_marker_is_declared_for_category_admin_changelist_filtering_polish(self):
        self.assertEqual(
            V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_MARKER,
            "V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH",
        )

    def test_v199_category_admin_source_contains_changelist_filtering_hooks(self):
        text = self._admin_source_path().read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", text)
        self.assertIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", text)
        self.assertIn("_v199_category_changelist_active_filter_pairs", text)
        self.assertIn("_v199_category_changelist_filters_active", text)
        self.assertIn("_v199_category_changelist_filter_summary", text)
        self.assertIn("_v199_category_changelist_filter_guidance", text)
        self.assertIn("_v199_category_changelist_filter_context", text)
        self.assertIn("_v199_category_changelist_view", text)
        self.assertIn("_v199_apply_category_admin_changelist_filtering_polish", text)
        self.assertIn("v199_original_changelist_view", text)
        self.assertIn("v199_category_taxonomy_admin_changelist_filtering_polish = True", text)

    def test_v199_preserves_existing_admin_field_contracts(self):
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

        self.assertEqual(
            tuple(getattr(category_admin, "v199_preserved_list_display_contract", ())),
            ("name", "slug", "parent"),
        )

    def test_v199_changelist_filter_summary_handles_unfiltered_request(self):
        category_admin = self._category_admin()
        request = self._request()

        self.assertFalse(category_admin.v199_changelist_filter_context(request)["v199_category_filters_active"])
        self.assertEqual(
            category_admin.v199_changelist_filter_summary(request),
            "No category changelist filters are active.",
        )
        self.assertEqual(
            category_admin.v199_changelist_filter_guidance(request),
            "Use search, parent, and status filters to narrow large category taxonomies before editing.",
        )

    def test_v199_changelist_filter_summary_handles_active_search_and_status(self):
        category_admin = self._category_admin()
        request = self._request({"q": "furniture", "is_active__exact": "1"})

        context = category_admin.v199_changelist_filter_context(request)

        self.assertTrue(context["v199_category_changelist_filtering_polish"])
        self.assertTrue(context["v199_category_filters_active"])
        self.assertIn("Search: furniture", context["v199_category_filter_summary"])
        self.assertIn("Status: active", context["v199_category_filter_summary"])
        self.assertEqual(
            context["v199_category_filter_guidance"],
            "Review the filtered category set, then clear filters before broad taxonomy edits.",
        )

    def test_v199_changelist_view_injects_filter_context_without_breaking_admin_response(self):
        category_admin = self._category_admin()
        response = category_admin.changelist_view(self._request({"q": "home"}))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["v199_category_changelist_filtering_polish"])
        self.assertTrue(response.context_data["v199_category_filters_active"])
        self.assertIn("Search: home", response.context_data["v199_category_filter_summary"])
        self.assertEqual(
            response.context_data["v199_category_filter_guidance"],
            "Review the filtered category set, then clear filters before broad taxonomy edits.",
        )

    def test_v199_verify_command_still_accepts_admin_fields_after_changelist_polish(self):
        verify_output = StringIO()
        call_command("verify_marketplace_category_seed", "--require-applied", stdout=verify_output)

        output = verify_output.getvalue()

        self.assertIn("Admin registered: True", output)
        self.assertIn("Admin fields OK: True", output)
        self.assertIn("Verified: True", output)

    def test_v199_templates_from_v193_v195_v197_v198_are_untouched(self):
        category_partial = (
            self._backend_root()
            / "templates"
            / "categories"
            / "_category_navigation_v186.html"
        )
        seller_store_directory = (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_directory.html"
        )
        saved_search_management = (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / "saved_search_list.html"
        )
        seller_store_public = (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_public.html"
        )

        category_text = category_partial.read_text(encoding="utf-8", errors="ignore")
        directory_text = seller_store_directory.read_text(encoding="utf-8", errors="ignore")
        saved_search_text = saved_search_management.read_text(encoding="utf-8", errors="ignore")
        public_store_text = seller_store_public.read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_text)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", directory_text)
        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_text)
        self.assertIn("V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH", public_store_text)

        for text in (category_text, directory_text, saved_search_text, public_store_text):
            self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", text)
            self.assertNotIn("v199_category_filter_guidance", text)
            self.assertNotIn("v199_category_filter_summary", text)

    def test_v199_category_models_and_seed_files_are_not_used_as_patch_surface(self):
        model_text = (
            self._backend_root()
            / "categories"
            / "models.py"
        ).read_text(encoding="utf-8", errors="ignore")

        self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", model_text)

        for filename in ("seed_taxonomy_v183.py", "seed_taxonomy_v184.py"):
            path = self._backend_root() / "categories" / filename
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn("V199_CATEGORY_TAXONOMY_ADMIN_CHANGELIST_FILTERING_POLISH", text)

    def test_v199_existing_checkpoint_guards_remain_present(self):
        v196_test = self._backend_root() / "categories" / "test_category_taxonomy_admin_ux_polish_v196.py"
        v197_test = self._backend_root() / "listings" / "test_saved_search_notification_settings_polish_v197.py"
        v198_test = (
            self._backend_root()
            / "accounts"
            / "tests"
            / "test_seller_store_public_page_responsive_polish_v198.py"
        )

        self.assertTrue(v196_test.exists())
        self.assertTrue(v197_test.exists())
        self.assertTrue(v198_test.exists())

        self.assertIn(
            "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH",
            v196_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH",
            v197_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V198_SELLER_STORE_PUBLIC_PAGE_RESPONSIVE_POLISH",
            v198_test.read_text(encoding="utf-8", errors="ignore"),
        )
