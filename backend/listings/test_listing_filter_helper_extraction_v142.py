import ast
from pathlib import Path

from django.test import SimpleTestCase

from listings import listing_filter_helpers
from listings.views import apply_listing_filters as views_apply_listing_filters


class ListingFilterHelperExtractionV142Tests(SimpleTestCase):
    def test_v142_helper_module_exports_apply_listing_filters(self):
        self.assertTrue(callable(listing_filter_helpers.apply_listing_filters))

    def test_v142_views_reexports_extracted_apply_listing_filters(self):
        self.assertIs(views_apply_listing_filters, listing_filter_helpers.apply_listing_filters)

    def test_v142_views_imports_apply_listing_filters_from_helper_module(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        found_import = False

        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level == 1 and node.module == "listing_filter_helpers":
                imported_names = {alias.name for alias in node.names}
                if "apply_listing_filters" in imported_names:
                    found_import = True
                    break

        self.assertTrue(found_import)

    def test_v142_views_no_longer_defines_apply_listing_filters(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertNotIn("apply_listing_filters", top_level_function_names)

    def test_v142_helper_module_defines_apply_listing_filters(self):
        helper_path = Path("listings/listing_filter_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_filter_helpers.py")

        tree = ast.parse(helper_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("apply_listing_filters", top_level_function_names)

    def test_v142_marker_is_present_in_helper_module(self):
        helper_path = Path("listings/listing_filter_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_filter_helpers.py")

        self.assertIn(
            "LISTING_FILTER_HELPER_EXTRACTION_V142",
            helper_path.read_text(encoding="utf-8"),
        )

    def test_v142_helper_module_does_not_copy_view_only_imports(self):
        helper_path = Path("listings/listing_filter_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_filter_helpers.py")

        helper_text = helper_path.read_text(encoding="utf-8")

        self.assertNotIn("LoginRequiredMixin", helper_text)
        self.assertNotIn("UserPassesTestMixin", helper_text)
        self.assertNotIn("django.contrib.auth.mixins", helper_text)
        self.assertNotIn("django.views.generic", helper_text)

