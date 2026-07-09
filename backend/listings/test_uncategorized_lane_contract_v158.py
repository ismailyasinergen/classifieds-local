"""
UNCATEGORIZED_LANE_CONTRACT_V158

Focused source/audit contracts for the uncategorized lane before moving it
out of listings.views in a later checkpoint.

v158 is intentionally test/docs only.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import listing_views_split_lane_followup_audit_v153 as followup


UNCATEGORIZED_LANE_CONTRACT_V158 = True
UNCATEGORIZED_LANE = "uncategorized"
EXPECTED_UNCATEGORIZED_DEFINITION_COUNT = 7
EXPECTED_UNCATEGORIZED_TOTAL_LINES = 100
EXPECTED_UNCATEGORIZED_READINESS = 'candidate_for_first_split'
EXPECTED_REMAINING_CANDIDATES = [
    "uncategorized",
    "listing_crud_uploads"
]
EXPECTED_EXTRACTED_LANES = ["browse_search_detail", "favorites", "listing_promotions"]


def _report():
    return followup.build_followup_report(Path("."))


def _remaining_candidate_map(report):
    return {candidate.name: candidate for candidate in report.remaining_candidates}


def _extracted_lane_map(report):
    return {status.name: status for status in report.extracted_lanes}


class UncategorizedLaneContractV158Tests(SimpleTestCase):
    def test_v158_uncategorized_is_current_recommended_next_lane(self):
        report = _report()

        self.assertEqual(report.recommended_next_lane.name, UNCATEGORIZED_LANE)
        self.assertEqual(
            getattr(report.recommended_next_lane, "readiness", None),
            EXPECTED_UNCATEGORIZED_READINESS,
        )

    def test_v158_uncategorized_source_footprint_is_locked_before_extraction(self):
        report = _report()
        candidate = report.recommended_next_lane

        self.assertEqual(candidate.name, UNCATEGORIZED_LANE)
        self.assertEqual(candidate.definition_count, EXPECTED_UNCATEGORIZED_DEFINITION_COUNT)
        self.assertEqual(candidate.total_lines, EXPECTED_UNCATEGORIZED_TOTAL_LINES)
        self.assertGreater(candidate.definition_count, 0)
        self.assertGreater(candidate.total_lines, 0)

    def test_v158_remaining_candidates_are_locked_after_v157(self):
        report = _report()
        candidate_names = [candidate.name for candidate in report.remaining_candidates]

        self.assertEqual(candidate_names, EXPECTED_REMAINING_CANDIDATES)
        self.assertIn(UNCATEGORIZED_LANE, candidate_names)
        self.assertIn("listing_crud_uploads", candidate_names)
        self.assertNotIn("browse_search_detail", candidate_names)

    def test_v158_uncategorized_is_first_remaining_candidate_by_sort_order(self):
        report = _report()
        candidates = list(report.remaining_candidates)

        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0].name, UNCATEGORIZED_LANE)
        self.assertEqual(candidates[0], report.recommended_next_lane)

        sort_keys = [
            (candidate.definition_count, candidate.total_lines, candidate.name)
            for candidate in candidates
        ]
        self.assertEqual(sort_keys, sorted(sort_keys))

    def test_v158_previous_split_lanes_remain_extracted(self):
        report = _report()
        extracted = _extracted_lane_map(report)

        self.assertEqual(sorted(extracted), EXPECTED_EXTRACTED_LANES)

        self.assertTrue(extracted["listing_promotions"].extracted)
        self.assertEqual(extracted["listing_promotions"].view, "listing_feature_priority_update")

        self.assertTrue(extracted["favorites"].extracted)
        self.assertEqual(extracted["favorites"].view, "listing_favorite_toggle")

        self.assertTrue(extracted["browse_search_detail"].extracted)
        self.assertEqual(extracted["browse_search_detail"].view, "ListingDetailView")
        self.assertEqual(
            extracted["browse_search_detail"].module,
            "backend/listings/listing_browse_detail_views.py",
        )

    def test_v158_uncategorized_has_not_been_extracted_yet(self):
        report = _report()
        remaining = _remaining_candidate_map(report)

        self.assertIn(UNCATEGORIZED_LANE, remaining)
        self.assertFalse(getattr(remaining[UNCATEGORIZED_LANE], "extracted", False))
        self.assertFalse(Path("listings/listing_uncategorized_views.py").exists())
        self.assertFalse(Path("listings/uncategorized_views.py").exists())

    def test_v158_generated_followup_markdown_documents_uncategorized_next_lane(self):
        report = _report()

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn("LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153", text)
        self.assertIn("Recommended next split lane", text)
        self.assertIn(UNCATEGORIZED_LANE, text)
        self.assertIn("listing_crud_uploads", text)
        self.assertIn("browse_search_detail", text)
        self.assertIn("ListingDetailView", text)
