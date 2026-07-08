import ast
from pathlib import Path

from django.test import SimpleTestCase

from listings import listing_image_helpers
from listings.views import validate_uploaded_images as views_validate_uploaded_images


class ListingImageValidationHelperExtractionV148Tests(SimpleTestCase):
    def test_v148_helper_module_exports_validate_uploaded_images(self):
        self.assertTrue(callable(listing_image_helpers.validate_uploaded_images))

    def test_v148_views_reexports_extracted_validate_uploaded_images(self):
        self.assertIs(
            views_validate_uploaded_images,
            listing_image_helpers.validate_uploaded_images,
        )

    def test_v148_views_imports_validate_uploaded_images_from_helper_module(self):
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
                if "validate_uploaded_images" in imported_names:
                    found_import = True
                    break

        self.assertTrue(found_import)

    def test_v148_views_no_longer_defines_validate_uploaded_images(self):
        views_path = Path("listings/views.py")
        if not views_path.exists():
            views_path = Path("backend/listings/views.py")

        tree = ast.parse(views_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertNotIn("validate_uploaded_images", top_level_function_names)

    def test_v148_helper_module_defines_validate_uploaded_images(self):
        helper_path = Path("listings/listing_image_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_image_helpers.py")

        tree = ast.parse(helper_path.read_text(encoding="utf-8"))
        top_level_function_names = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        self.assertIn("validate_uploaded_images", top_level_function_names)

    def test_v148_marker_is_present_in_helper_module(self):
        helper_path = Path("listings/listing_image_helpers.py")
        if not helper_path.exists():
            helper_path = Path("backend/listings/listing_image_helpers.py")

        helper_text = helper_path.read_text(encoding="utf-8")
        self.assertIn("SAVE_UPLOADED_LISTING_IMAGES_HELPER_EXTRACTION_V147", helper_text)
        self.assertIn("VALIDATE_UPLOADED_IMAGES_HELPER_EXTRACTION_V148", helper_text)

    def test_v148_helper_module_keeps_both_image_helpers(self):
        self.assertTrue(callable(listing_image_helpers.save_uploaded_listing_images))
        self.assertTrue(callable(listing_image_helpers.validate_uploaded_images))
