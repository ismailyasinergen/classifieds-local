"""
Tests for the v153 split-lane follow-up audit.

Updated in v155 so the audit also records favorites as extracted after
listing_favorite_toggle moved into a dedicated favorite view module.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import listing_views_split_lane_followup_audit_v153 as followup


LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_TESTS_V153 = True


class ListingViewsSplitLaneFollowupAuditV153Tests(SimpleTestCase):
    def test_v153_report_records_extracted_lanes(self):
        report = followup.build_followup_report(Path("."))

        extracted = {status.name: status for status in report.extracted_lanes}

        self.assertIn("listing_promotions", extracted)
        self.assertIn("favorites", extracted)

        self.assertTrue(extracted["listing_promotions"].extracted)
        self.assertEqual(extracted["listing_promotions"].definition_count, 0)
        self.assertEqual(extracted["listing_promotions"].total_lines, 0)
        self.assertEqual(
            extracted["listing_promotions"].view,
            "listing_feature_priority_update",
        )

        self.assertTrue(extracted["favorites"].extracted)
        self.assertEqual(extracted["favorites"].definition_count, 0)
        self.assertEqual(extracted["favorites"].total_lines, 0)
        self.assertEqual(extracted["favorites"].view, "listing_favorite_toggle")
        self.assertEqual(
            extracted["favorites"].module,
            "backend/listings/listing_favorite_views.py",
        )

    def test_v153_recommends_browse_search_detail_after_favorites_extraction(self):
        report = followup.build_followup_report(Path("."))

        self.assertEqual(report.recommended_next_lane.name, "browse_search_detail")
        self.assertEqual(report.recommended_next_lane.definition_count, 1)
        self.assertGreater(report.recommended_next_lane.total_lines, 0)
        self.assertEqual(
            report.recommended_next_lane.readiness,
            "candidate_for_first_split",
        )

    def test_v153_remaining_candidates_exclude_extracted_lanes(self):
        report = followup.build_followup_report(Path("."))

        candidate_names = [candidate.name for candidate in report.remaining_candidates]

        self.assertNotIn("listing_promotions", candidate_names)
        self.assertNotIn("favorites", candidate_names)
        self.assertIn("browse_search_detail", candidate_names)

    def test_v153_candidate_order_prefers_single_small_lanes(self):
        report = followup.build_followup_report(Path("."))

        candidates = list(report.remaining_candidates)

        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0], report.recommended_next_lane)

        sort_keys = [
            (candidate.definition_count, candidate.total_lines, candidate.name)
            for candidate in candidates
        ]
        self.assertEqual(sort_keys, sorted(sort_keys))

    def test_v153_markdown_report_documents_extracted_and_next_lane_without_project_docs_side_effect(self):
        report = followup.build_followup_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn("LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153", text)
        self.assertIn("listing_promotions", text)
        self.assertIn("listing_feature_priority_update", text)
        self.assertIn("favorites", text)
        self.assertIn("listing_favorite_toggle", text)
        self.assertIn("Recommended next split lane", text)
        self.assertIn("browse_search_detail", text)
