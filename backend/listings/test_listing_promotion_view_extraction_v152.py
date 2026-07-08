"""
LISTING_PROMOTION_VIEW_EXTRACTION_V152

Verifies that listing_feature_priority_update was moved out of listings.views
while preserving the public listings.views re-export and URL callback behavior.
"""

from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase
from django.urls import resolve, reverse

from listings import listing_promotion_views
from listings import views as listing_views


LISTING_PROMOTION_VIEW_EXTRACTION_V152 = True
PROMOTION_VIEW_NAME = "listing_feature_priority_update"
PROMOTION_URL_NAME = "listing_feature_priority_update"


def _project_file(*parts):
    backend_path = Path("backend").joinpath(*parts)
    if backend_path.exists():
        return backend_path

    app_path = Path(*parts)
    if app_path.exists():
        return app_path

    return backend_path


class ListingPromotionViewExtractionV152Tests(SimpleTestCase):
    def test_v152_dedicated_promotion_module_exists_and_exports_view(self):
        self.assertTrue(hasattr(listing_promotion_views, "LISTING_PROMOTION_VIEWS_V152"))
        self.assertTrue(hasattr(listing_promotion_views, PROMOTION_VIEW_NAME))

    def test_v152_listings_views_reexports_same_promotion_view_object(self):
        self.assertTrue(hasattr(listing_views, PROMOTION_VIEW_NAME))
        self.assertIs(
            getattr(listing_views, PROMOTION_VIEW_NAME),
            getattr(listing_promotion_views, PROMOTION_VIEW_NAME),
        )

    def test_v152_views_source_no_longer_defines_promotion_view(self):
        views_source = _project_file("listings", "views.py").read_text(encoding="utf-8")
        promotion_source = _project_file("listings", "listing_promotion_views.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn(f"def {PROMOTION_VIEW_NAME}(", views_source)
        self.assertIn(
            "from .listing_promotion_views import listing_feature_priority_update",
            views_source,
        )
        self.assertIn(f"def {PROMOTION_VIEW_NAME}(", promotion_source)
        self.assertIn("@login_required", promotion_source)
        self.assertIn("@require_POST", promotion_source)

    def test_v152_url_resolution_still_uses_reexported_callback(self):
        url = reverse(f"listings:{PROMOTION_URL_NAME}", kwargs={"pk": 1})
        match = resolve(url)

        self.assertEqual(match.url_name, PROMOTION_URL_NAME)
        self.assertIs(match.func, getattr(listing_views, PROMOTION_VIEW_NAME))
        self.assertIs(match.func, getattr(listing_promotion_views, PROMOTION_VIEW_NAME))

    def test_v152_no_listing_promotions_definition_remains_in_views_audit(self):
        from listings import listing_views_split_lane_audit_v150 as split_audit

        report = split_audit.build_report(Path("."))
        lane = next(lane for lane in report.lane_reports if lane.name == "listing_promotions")

        self.assertEqual(lane.definition_count, 0)
        self.assertEqual(lane.total_lines, 0)
