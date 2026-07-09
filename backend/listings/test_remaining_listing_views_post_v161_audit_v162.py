from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from listings import remaining_listing_views_post_v161_audit as audit
from listings import listing_reports_views
from listings import saved_searches_views


class RemainingListingViewsPostV161AuditTests(TestCase):
    def test_v162_report_targets_current_views_file_after_v166(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.total_top_level_definitions, 0)

    def test_v162_listing_reports_lane_is_extracted_after_v166(self):
        report = audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertNotIn("listing_reports", lanes)
        self.assertTrue(Path("listings/listing_reports_views.py").exists())
        self.assertIsNotNone(listing_reports_views.listing_report_queue)

    def test_v162_saved_searches_lane_is_extracted_after_v166(self):
        report = audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertNotIn("saved_searches", lanes)
        self.assertTrue(Path("listings/saved_searches_views.py").exists())
        self.assertIsNotNone(saved_searches_views.saved_search_list)

        views_source = Path("listings/views.py").read_text(encoding="utf-8")
        tree = ast.parse(views_source)

        local_saved_search_defs = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name.startswith("saved_search_")
        }

        self.assertEqual(local_saved_search_defs, set())

    def test_v162_recommends_no_remaining_lane_after_v166(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.lanes, [])
        self.assertIsNone(report.recommended_next_lane)

    def test_v162_markdown_documents_completed_remaining_views_state(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "remaining_views_audit.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.MARKER, text)
        self.assertIn("No remaining candidate lanes", text)
        self.assertNotIn("Recommended next lane: `listing_reports`", text)
        self.assertNotIn("Recommended next lane: `saved_searches`", text)
