"""
LISTING_FAVORITE_VIEW_EXTRACTION_V155

Extraction checks for moving listing_favorite_toggle out of listings.views
while preserving the public re-export used by urls and older imports.
"""

from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from listings import listing_favorite_views
from listings import views as listing_views
from listings import listing_views_split_lane_followup_audit_v153 as followup


LISTING_FAVORITE_VIEW_EXTRACTION_V155 = True


class ListingFavoriteViewExtractionV155Tests(SimpleTestCase):
    def test_v155_dedicated_favorite_module_exists_and_exports_view(self):
        self.assertTrue(hasattr(listing_favorite_views, "LISTING_FAVORITE_VIEWS_V155"))
        self.assertTrue(hasattr(listing_favorite_views, "listing_favorite_toggle"))

    def test_v155_listings_views_reexports_same_favorite_view_object(self):
        self.assertTrue(hasattr(listing_views, "listing_favorite_toggle"))
        self.assertIs(
            listing_views.listing_favorite_toggle,
            listing_favorite_views.listing_favorite_toggle,
        )

    def test_v155_url_resolution_still_uses_reexported_callback(self):
        url = reverse("listings:listing_favorite_toggle", kwargs={"pk": 1})
        match = resolve(url)

        self.assertEqual(match.url_name, "listing_favorite_toggle")
        self.assertIs(match.func, listing_views.listing_favorite_toggle)
        self.assertIs(match.func, listing_favorite_views.listing_favorite_toggle)

    def test_v155_views_source_no_longer_defines_favorite_view(self):
        views_source = Path("listings/views.py").read_text(encoding="utf-8")
        tree = ast.parse(views_source)

        top_level_functions = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
        }

        self.assertNotIn("listing_favorite_toggle", top_level_functions)
        self.assertIn(
            "from .listing_favorite_views import listing_favorite_toggle",
            views_source,
        )

    def test_v155_dedicated_module_preserves_decorators_and_marker(self):
        source = Path("listings/listing_favorite_views.py").read_text(encoding="utf-8")

        self.assertIn("LISTING_FAVORITE_VIEWS_V155", source)
        self.assertIn("@login_required", source)
        self.assertIn("@require_POST", source)
        self.assertIn("def listing_favorite_toggle", source)

    def test_v155_followup_audit_records_favorites_as_extracted(self):
        from listings import listing_views_split_lane_followup_audit_v153 as followup

        report = followup.build_followup_report(Path("."))
        extracted = {status.name for status in report.extracted_lanes}

        self.assertIn("favorites", extracted)
        self.assertIn("listing_crud_uploads", extracted)
        self.assertEqual(tuple(report.remaining_candidates), ())
        self.assertIsNone(report.recommended_next_lane)
