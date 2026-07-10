"""
Tests for the v153 split-lane follow-up audit.

Updated through v161 so all tracked split lanes are extracted and there are no
remaining split-lane candidates.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import listing_views_split_lane_followup_audit_v153 as followup


LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_TESTS_V153 = True

EXPECTED_EXTRACTED_LANES_AFTER_V161 = [
    "browse_search_detail",
    "favorites",
    "listing_crud_uploads",
    "listing_promotions",
    "uncategorized",
]


class ListingViewsSplitLaneFollowupAuditV153Tests(SimpleTestCase):
    def test_v153_report_records_all_tracked_extracted_lanes_after_v161(self):
        report = followup.build_followup_report(Path("."))

        extracted = {status.name: status for status in report.extracted_lanes}

        self.assertEqual(sorted(extracted), EXPECTED_EXTRACTED_LANES_AFTER_V161)

        for lane in EXPECTED_EXTRACTED_LANES_AFTER_V161:
            self.assertTrue(extracted[lane].extracted, lane)
            self.assertEqual(extracted[lane].definition_count, 0, lane)
            self.assertEqual(extracted[lane].total_lines, 0, lane)

        self.assertEqual(
            extracted["listing_crud_uploads"].module,
            "backend/listings/listing_crud_uploads_views.py",
        )

    def test_v153_has_no_remaining_candidates_after_v161(self):
        report = followup.build_followup_report(Path("."))

        self.assertEqual(tuple(report.remaining_candidates), ())
        self.assertIsNone(report.recommended_next_lane)

    def test_v153_remaining_candidates_exclude_all_extracted_lanes_after_v161(self):
        report = followup.build_followup_report(Path("."))

        candidate_names = [candidate.name for candidate in report.remaining_candidates]

        for lane in EXPECTED_EXTRACTED_LANES_AFTER_V161:
            self.assertNotIn(lane, candidate_names)

        self.assertEqual(candidate_names, [])

    def test_v153_candidate_order_handles_completed_split_state(self):
        report = followup.build_followup_report(Path("."))

        self.assertEqual(tuple(report.remaining_candidates), ())
        self.assertIsNone(report.recommended_next_lane)

    def test_v153_markdown_report_documents_completed_split_state_without_project_docs_side_effect(self):
        report = followup.build_followup_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8").lower()

        self.assertIn("listing_views_split_lane_followup_audit_v153", text)
        self.assertIn("listing_crud_uploads", text)
        self.assertIn("listing_crud_uploads_views.py", text)
        self.assertIn("none", text)
