from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.core.management import call_command
from django.test import TestCase

from categories.models import Category


V196_CATEGORY_TAXONOMY_ADMIN_UX_MARKER = "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH"


class CategoryTaxonomyAdminUxPolishV196Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=StringIO())

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _admin_source_path(self) -> Path:
        return self._backend_root() / "categories" / "admin.py"

    def _category_admin(self):
        return admin.site._registry[Category]

    def test_v196_marker_is_declared_for_category_taxonomy_admin_ux(self):
        self.assertEqual(
            V196_CATEGORY_TAXONOMY_ADMIN_UX_MARKER,
            "V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH",
        )

    def test_v196_category_admin_source_contains_safe_ux_polish_hooks(self):
        text = self._admin_source_path().read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", text)
        self.assertIn("_v196_category_parent_path(self, obj)", text)
        self.assertIn("_v196_category_child_count(self, obj)", text)
        self.assertIn("_v196_category_status_label(self, obj)", text)
        self.assertIn("_v196_apply_category_admin_ux_polish", text)
        self.assertIn("v196_preserved_list_display_contract", text)
        self.assertIn("v196_parent_path", text)
        self.assertIn("v196_child_count", text)
        self.assertIn("v196_status_label", text)
        self.assertIn("list_per_page = 50", text)
        self.assertIn("save_on_top = True", text)
        self.assertIn("show_full_result_count = False", text)
        self.assertIn("preserve_filters = True", text)

    def test_v196_preserves_existing_v182_v185_admin_field_contract(self):
        category_admin = self._category_admin()

        self.assertEqual(category_admin.list_display, ("name", "slug", "parent"))

        self.assertEqual(
            tuple(getattr(category_admin, "v196_preserved_list_display_contract", ())),
            ("name", "slug", "parent"),
        )

        self.assertTrue(getattr(category_admin, "v196_category_taxonomy_admin_ux_polish", False))

    def test_v196_category_admin_runtime_options_are_safe_polish_only(self):
        category_admin = self._category_admin()

        self.assertTrue(callable(category_admin.v196_parent_path))
        self.assertTrue(callable(category_admin.v196_child_count))
        self.assertTrue(callable(category_admin.v196_status_label))

        self.assertEqual(category_admin.list_per_page, 50)
        self.assertTrue(category_admin.save_on_top)
        self.assertTrue(category_admin.actions_on_top)
        self.assertFalse(category_admin.show_full_result_count)
        self.assertTrue(category_admin.preserve_filters)

        list_select_related = category_admin.get_list_select_related(request=None)

        if list_select_related is not True:
            self.assertIn("parent", tuple(list_select_related))

    def test_v196_category_admin_helpers_return_readable_taxonomy_signals(self):
        category_admin = self._category_admin()

        child = Category.objects.filter(parent__isnull=False).select_related("parent").first()
        self.assertIsNotNone(child)

        parent_path = category_admin.v196_parent_path(child)
        child_count = category_admin.v196_child_count(child)
        status_label = category_admin.v196_status_label(child)

        self.assertIsInstance(parent_path, str)
        self.assertTrue(parent_path)
        self.assertNotEqual(parent_path, "None")
        self.assertIsInstance(child_count, int)
        self.assertGreaterEqual(child_count, 0)
        self.assertIn(status_label, {"Active", "Inactive", "Available"})

    def test_v196_root_category_parent_path_is_top_level(self):
        category_admin = self._category_admin()

        root = Category.objects.filter(parent__isnull=True).first()
        self.assertIsNotNone(root)

        self.assertEqual(category_admin.v196_parent_path(root), "Top-level")

    def test_v196_verify_command_accepts_admin_fields_after_polish(self):
        verify_output = StringIO()
        call_command("verify_marketplace_category_seed", "--require-applied", stdout=verify_output)

        output = verify_output.getvalue()

        self.assertIn("Admin registered: True", output)
        self.assertIn("Admin fields OK: True", output)
        self.assertIn("Verified: True", output)

    def test_v196_templates_from_v193_v194_v195_are_untouched(self):
        category_partial = (
            self._backend_root()
            / "templates"
            / "categories"
            / "_category_navigation_v186.html"
        )
        saved_search_management = (
            self._backend_root()
            / "listings"
            / "templates"
            / "listings"
            / "saved_search_list.html"
        )
        seller_store_directory = (
            self._backend_root()
            / "accounts"
            / "templates"
            / "accounts"
            / "seller_store_directory.html"
        )

        category_text = category_partial.read_text(encoding="utf-8", errors="ignore")
        saved_search_text = saved_search_management.read_text(encoding="utf-8", errors="ignore")
        seller_store_text = seller_store_directory.read_text(encoding="utf-8", errors="ignore")

        self.assertIn("V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING", category_text)
        self.assertIn("V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH", saved_search_text)
        self.assertIn("V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH", seller_store_text)

        for text in (category_text, saved_search_text, seller_store_text):
            self.assertNotIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", text)
            self.assertNotIn("v196_parent_path", text)
            self.assertNotIn("v196_child_count", text)

    def test_v196_category_models_and_seed_files_are_not_used_as_patch_surface(self):
        model_text = (
            self._backend_root()
            / "categories"
            / "models.py"
        ).read_text(encoding="utf-8", errors="ignore")

        self.assertNotIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", model_text)

        for filename in ("seed_taxonomy_v183.py", "seed_taxonomy_v184.py"):
            path = self._backend_root() / "categories" / filename
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn("V196_CATEGORY_TAXONOMY_ADMIN_UX_POLISH", text)

    def test_v196_existing_checkpoint_guards_remain_present(self):
        v193_test = self._backend_root() / "categories" / "test_category_navigation_keyboard_a11y_v193.py"
        v194_test = self._backend_root() / "listings" / "test_saved_search_management_copy_polish_v194.py"
        v195_test = (
            self._backend_root()
            / "accounts"
            / "tests"
            / "test_seller_store_directory_responsive_polish_v195.py"
        )

        self.assertTrue(v193_test.exists())
        self.assertTrue(v194_test.exists())
        self.assertTrue(v195_test.exists())

        self.assertIn(
            "V193_CATEGORY_NAVIGATION_KEYBOARD_A11Y_DEEPENING",
            v193_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V194_SAVED_SEARCH_MANAGEMENT_COPY_POLISH",
            v194_test.read_text(encoding="utf-8", errors="ignore"),
        )
        self.assertIn(
            "V195_SELLER_STORE_DIRECTORY_RESPONSIVE_POLISH",
            v195_test.read_text(encoding="utf-8", errors="ignore"),
        )
