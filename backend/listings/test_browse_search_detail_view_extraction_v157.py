"""
BROWSE_SEARCH_DETAIL_VIEW_EXTRACTION_V157

Extraction checks for moving ListingDetailView out of listings.views while
preserving the public listings.views re-export and listing_detail URL callback.
"""

from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from listings import listing_browse_detail_views
from listings import listing_views_split_lane_followup_audit_v153 as followup
from listings import views as listing_views


BROWSE_SEARCH_DETAIL_VIEW_EXTRACTION_V157 = True


class BrowseSearchDetailViewExtractionV157Tests(SimpleTestCase):
    def test_v157_dedicated_browse_detail_module_exists_and_exports_view(self):
        self.assertTrue(hasattr(listing_browse_detail_views, "LISTING_BROWSE_DETAIL_VIEWS_V157"))
        self.assertTrue(hasattr(listing_browse_detail_views, "ListingDetailView"))


    def test_v157_dedicated_module_contains_listing_detail_dependencies(self):
        source = Path("listings/listing_browse_detail_views.py").read_text(encoding="utf-8")

        self.assertIn("SidebarCategoriesMixin", source)
        self.assertIn("class ListingDetailView", source)
        self.assertIn("LISTING_BROWSE_DETAIL_VIEWS_V157", source)

    def test_v157_listings_views_reexports_same_listing_detail_view_class(self):
        self.assertTrue(hasattr(listing_views, "ListingDetailView"))
        self.assertIs(
            listing_views.ListingDetailView,
            listing_browse_detail_views.ListingDetailView,
        )

    def test_v157_url_resolution_still_uses_reexported_listing_detail_view(self):
        url = reverse("listings:listing_detail", kwargs={"pk": 1})
        match = resolve(url)
        view_class = getattr(match.func, "view_class", None)

        self.assertEqual(match.url_name, "listing_detail")
        self.assertIs(view_class, listing_views.ListingDetailView)
        self.assertIs(view_class, listing_browse_detail_views.ListingDetailView)

    def test_v157_views_source_no_longer_defines_listing_detail_view(self):
        views_source = Path("listings/views.py").read_text(encoding="utf-8")
        tree = ast.parse(views_source)

        top_level_classes = {
            node.name
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }

        self.assertNotIn("ListingDetailView", top_level_classes)
        self.assertIn(
            "from .listing_browse_detail_views import ListingDetailView",
            views_source,
        )

    def test_v157_dedicated_source_preserves_listing_detail_view_shape(self):
        source = Path("listings/listing_browse_detail_views.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        classes = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
        }

        self.assertIn("ListingDetailView", classes)
        target = classes["ListingDetailView"]
        self.assertEqual((target.end_lineno or target.lineno) - target.lineno + 1, 48)
        self.assertIn("LISTING_BROWSE_DETAIL_VIEWS_V157", source)

    def test_v157_followup_audit_records_browse_search_detail_as_extracted(self):
        report = followup.build_followup_report(Path("."))
        extracted = {status.name for status in report.extracted_lanes}

        self.assertIn("browse_search_detail", extracted)
        self.assertIn("listing_crud_uploads", extracted)
        self.assertEqual(report.remaining_candidates, [])
        self.assertIsNone(report.recommended_next_lane)

    def test_v157_generated_followup_markdown_records_extraction_and_next_lane(self):
        report = followup.build_followup_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn("LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153", text)
        self.assertIn("browse_search_detail", text)
        self.assertIn("ListingDetailView", text)
        self.assertIn("listing_browse_detail_views.py", text)
        self.assertIn("Recommended next split lane", text)
        self.assertIn("uncategorized", text)
