from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from listings import remaining_listing_views_post_v161_audit as audit


class RemainingListingViewsPostV161AuditTests(TestCase):
    def test_v162_report_targets_current_views_file(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertGreaterEqual(report.total_lines, 1900)
        self.assertEqual(report.total_top_level_definitions, 39)

    def test_v162_report_records_listing_report_lane(self):
        report = audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertIn("listing_reports", lanes)
        lane = lanes["listing_reports"]

        self.assertGreater(lane.definition_count, 25)
        self.assertGreater(lane.total_lines, 900)
        self.assertIn("listing_report_create", lane.duplicate_names)
        self.assertIn("listing_report_queue", lane.duplicate_names)
        self.assertIn("listing_report_export_csv", lane.duplicate_names)
        self.assertIn("listing_report_review", lane.duplicate_names)
        self.assertIn("listing_report_dismiss", lane.duplicate_names)
        self.assertIn("listing_report_suspend_listing", lane.duplicate_names)
        self.assertIn("listing_report_archive_listing", lane.duplicate_names)

    def test_v162_report_records_saved_search_lane(self):
        report = audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertIn("saved_searches", lanes)
        lane = lanes["saved_searches"]

        self.assertEqual(lane.definition_count, 6)
        self.assertGreater(lane.total_lines, 500)
        self.assertIn("saved_search_create", lane.definition_names)
        self.assertIn("saved_search_list", lane.definition_names)
        self.assertIn("saved_search_notifications_toggle", lane.definition_names)
        self.assertIn("saved_search_delete", lane.definition_names)
        self.assertIn("saved_search_bulk_action", lane.definition_names)
        self.assertIn("saved_search_rename", lane.definition_names)

    def test_v162_recommends_listing_reports_before_saved_searches(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.recommended_next_lane.name, "listing_reports")
        self.assertGreater(
            report.recommended_next_lane.total_lines,
            next(lane.total_lines for lane in report.lanes if lane.name == "saved_searches"),
        )

    def test_v162_markdown_documents_remaining_lanes_without_project_doc_side_effect(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "remaining_views_audit.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.MARKER, text)
        self.assertIn("`listing_reports`", text)
        self.assertIn("`saved_searches`", text)
        self.assertIn("Recommended next lane: `listing_reports`", text)
        self.assertIn("Do not move runtime code", text)
