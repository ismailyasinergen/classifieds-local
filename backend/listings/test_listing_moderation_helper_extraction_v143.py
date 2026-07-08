import ast
from pathlib import Path

from django.test import SimpleTestCase

from listings import listing_moderation_helpers
from listings.views import _create_moderation_notice as views_create_moderation_notice


class ListingModerationHelperExtractionV143Tests(SimpleTestCase):
    def test_v143_helper_module_exports_create_moderation_notice(self):
        self.assertTrue(callable(listing_moderation_helpers._create_moderation_notice))

    def test_v143_views_reexports_extracted_create_moderation_notice(self):
        self.assertIs(
            views_create_moderation_notice,
            listing_moderation_helpers._create_moderation_notice,
        )

    def test_v143_views_imports_create_moderation_notice_from_helper_module(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        found_import = False

        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level == 1 and node.module == "listing_moderation_helpers":
                imported_names = {alias.name for alias in node.names}
                if "_create_moderation_notice" in imported_names:
                    found_import = True
                    break

        self.assertTrue(found_import)

    def test_v143_views_no_longer_defines_create_moderation_notice(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertNotIn("_create_moderation_notice", top_level_function_names)

    def test_v143_helper_module_defines_create_moderation_notice(self):
        helper_path = Path("listings/listing_moderation_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_moderation_helpers.py")

        tree = ast.parse(helper_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("_create_moderation_notice", top_level_function_names)

    def test_v143_marker_is_present_in_helper_module(self):
        helper_path = Path("listings/listing_moderation_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_moderation_helpers.py")

        self.assertIn(
            "LISTING_MODERATION_HELPER_EXTRACTION_V143",
            helper_path.read_text(encoding="utf-8"),
        )

    def test_v143_helper_module_does_not_copy_view_only_imports(self):
        helper_path = Path("listings/listing_moderation_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_moderation_helpers.py")

        helper_text = helper_path.read_text(encoding="utf-8")

        self.assertNotIn("LoginRequiredMixin", helper_text)
        self.assertNotIn("UserPassesTestMixin", helper_text)
        self.assertNotIn("django.contrib.auth.mixins", helper_text)
        self.assertNotIn("django.views.generic", helper_text)
        self.assertNotIn("Paginator", helper_text)
        self.assertNotIn("render", helper_text)
