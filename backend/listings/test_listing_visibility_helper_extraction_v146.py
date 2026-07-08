import ast
from pathlib import Path

from django.test import SimpleTestCase

from listings import listing_visibility_helpers
from listings.views import active_approved_listings as views_active_approved_listings


class ListingVisibilityHelperExtractionV146Tests(SimpleTestCase):
    def test_v146_helper_module_exports_active_approved_listings(self):
        self.assertTrue(callable(listing_visibility_helpers.active_approved_listings))

    def test_v146_views_reexports_extracted_active_approved_listings(self):
        self.assertIs(
            views_active_approved_listings,
            listing_visibility_helpers.active_approved_listings,
        )

    def test_v146_views_imports_active_approved_listings_from_helper_module(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        found_import = False

        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level == 1 and node.module == "listing_visibility_helpers":
                imported_names = {alias.name for alias in node.names}
                if "active_approved_listings" in imported_names:
                    found_import = True
                    break

        self.assertTrue(found_import)

    def test_v146_views_no_longer_defines_active_approved_listings(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertNotIn("active_approved_listings", top_level_function_names)

    def test_v146_helper_module_defines_active_approved_listings(self):
        helper_path = Path("listings/listing_visibility_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_visibility_helpers.py")

        tree = ast.parse(helper_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("active_approved_listings", top_level_function_names)

    def test_v146_marker_is_present_in_helper_module(self):
        helper_path = Path("listings/listing_visibility_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_visibility_helpers.py")

        self.assertIn(
            "ACTIVE_APPROVED_LISTINGS_HELPER_EXTRACTION_V146",
            helper_path.read_text(encoding="utf-8"),
        )

    def test_v146_helper_module_does_not_copy_view_only_imports(self):
        helper_path = Path("listings/listing_visibility_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_visibility_helpers.py")

        helper_text = helper_path.read_text(encoding="utf-8")

        self.assertNotIn("LoginRequiredMixin", helper_text)
        self.assertNotIn("UserPassesTestMixin", helper_text)
        self.assertNotIn("django.contrib.auth.mixins", helper_text)
        self.assertNotIn("django.views.generic", helper_text)
        self.assertNotIn("Paginator", helper_text)
        self.assertNotIn("render", helper_text)
        self.assertNotIn("redirect", helper_text)
        self.assertNotIn("messages", helper_text)
