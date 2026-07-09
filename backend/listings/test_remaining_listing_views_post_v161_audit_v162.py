from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from listings import remaining_listing_views_post_v161_audit as audit
from listings import listing_reports_views


class RemainingListingViewsPostV161AuditTests(TestCase):
    def test_v162_report_targets_current_views_file_after_v164(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.total_top_level_definitions, 6)

    def test_v162_listing_reports_lane_is_extracted_after_v164(self):
        report = audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertNotIn("listing_reports", lanes)
        self.assertTrue(Path("listings/listing_reports_views.py").exists())
        self.assertIsNotNone(listing_reports_views.listing_report_queue)

        views_source = Path("listings/views.py").read_text(encoding="utf-8")
        tree = ast.parse(views_source)
        local_report_defs = {
            node.name
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and (
                node.name == "moderation_queue"
                or node.name == "my_listing_reports"
                or node.name == "_safe_reporter_note"
                or node.name.startswith("listing_report_")
            )
        }

        self.assertEqual(local_report_defs, set())

    def test_v162_report_records_saved_search_lane_as_next_remaining_lane(self):
        report = audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertIn("saved_searches", lanes)
        lane = lanes["saved_searches"]

        self.assertEqual(lane.definition_count, 6)
        self.assertEqual(lane.total_lines, 526)
        self.assertIn("saved_search_create", lane.definition_names)
        self.assertIn("saved_search_list", lane.definition_names)
        self.assertIn("saved_search_notifications_toggle", lane.definition_names)
        self.assertIn("saved_search_delete", lane.definition_names)
        self.assertIn("saved_search_bulk_action", lane.definition_names)
        self.assertIn("saved_search_rename", lane.definition_names)

    def test_v162_recommends_saved_searches_after_listing_reports_extraction(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.recommended_next_lane.name, "saved_searches")
        self.assertEqual(report.recommended_next_lane.total_lines, 526)

    def test_v162_markdown_documents_post_v164_remaining_lane_without_project_doc_side_effect(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "remaining_views_audit.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.MARKER, text)
        self.assertIn("`saved_searches`", text)
        self.assertIn("Recommended next lane: `saved_searches`", text)
        self.assertIn("Do not move runtime code", text)
        self.assertNotIn("Recommended next lane: `listing_reports`", text)
