import ast
from pathlib import Path

from django.test import SimpleTestCase

from listings import listing_image_helpers
from listings.views import save_uploaded_listing_images as views_save_uploaded_listing_images


class ListingImageHelperExtractionV147Tests(SimpleTestCase):
    def test_v147_helper_module_exports_save_uploaded_listing_images(self):
        self.assertTrue(callable(listing_image_helpers.save_uploaded_listing_images))

    def test_v147_views_reexports_extracted_save_uploaded_listing_images(self):
        self.assertIs(
            views_save_uploaded_listing_images,
            listing_image_helpers.save_uploaded_listing_images,
        )

    def test_v147_views_imports_save_uploaded_listing_images_from_helper_module(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        found_import = False

        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.level == 1 and node.module == "listing_image_helpers":
                imported_names = {alias.name for alias in node.names}
                if "save_uploaded_listing_images" in imported_names:
                    found_import = True
                    break

        self.assertTrue(found_import)

    def test_v147_views_no_longer_defines_save_uploaded_listing_images(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertNotIn("save_uploaded_listing_images", top_level_function_names)

    def test_v147_helper_module_defines_save_uploaded_listing_images(self):
        helper_path = Path("listings/listing_image_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_image_helpers.py")

        tree = ast.parse(helper_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("save_uploaded_listing_images", top_level_function_names)

    def test_v147_marker_is_present_in_helper_module(self):
        helper_path = Path("listings/listing_image_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_image_helpers.py")

        self.assertIn(
            "SAVE_UPLOADED_LISTING_IMAGES_HELPER_EXTRACTION_V147",
            helper_path.read_text(encoding="utf-8"),
        )

    def test_v147_helper_module_does_not_copy_view_only_imports(self):
        helper_path = Path("listings/listing_image_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_image_helpers.py")

        helper_text = helper_path.read_text(encoding="utf-8")

        self.assertNotIn("LoginRequiredMixin", helper_text)
        self.assertNotIn("UserPassesTestMixin", helper_text)
        self.assertNotIn("django.contrib.auth.mixins", helper_text)
        self.assertNotIn("django.views.generic", helper_text)
        self.assertNotIn("Paginator", helper_text)
        self.assertNotIn("render", helper_text)
        self.assertNotIn("redirect", helper_text)
        self.assertNotIn("messages", helper_text)
