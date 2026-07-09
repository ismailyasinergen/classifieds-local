"""
UNCATEGORIZED_LANE_CONTRACT_V158

Focused source/audit contracts for the uncategorized lane.

v158 locked the lane before extraction. After v159, these contracts remain
green by validating the dedicated module and the listings.views compatibility
re-exports.
"""

from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import listing_uncategorized_views
from listings import listing_views_split_lane_followup_audit_v153 as followup
from listings import views as listing_views


UNCATEGORIZED_LANE_CONTRACT_V158 = True
UNCATEGORIZED_LANE = "uncategorized"
EXPECTED_UNCATEGORIZED_DEFINITION_COUNT = 7
EXPECTED_UNCATEGORIZED_AUDIT_LINES = 100
EXPECTED_UNCATEGORIZED_AST_BODY_LINES = 94
EXPECTED_UNCATEGORIZED_SPAN_LINES_WITH_DECORATORS = 104
EXPECTED_UNCATEGORIZED_READINESS = "candidate_for_first_split"
EXPECTED_UNCATEGORIZED_EXPORTS = [
    "SidebarCategoriesMixin",
    "ListingListView",
    "listing_approve",
    "listing_reject",
    "listing_archive",
    "listing_renew",
    "listing_feature_toggle"
]
EXPECTED_EXTRACTED_LANES_AFTER_V161 = [
    "browse_search_detail",
    "favorites",
    "listing_crud_uploads",
    "listing_promotions",
    "uncategorized",
]


def _report():
    return followup.build_followup_report(Path("."))


def _definition_ranges(source_path):
    source = Path(source_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    ranges = {}

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        body_start = node.lineno
        decorators = getattr(node, "decorator_list", [])
        decorated_start = body_start
        if decorators:
            decorated_start = min(decorator.lineno for decorator in decorators)

        end_lineno = node.end_lineno or node.lineno
        ranges.setdefault(node.name, []).append({
            "ast_body_lines": end_lineno - body_start + 1,
            "span_lines": end_lineno - decorated_start + 1,
        })

    return ranges


class UncategorizedLaneContractV158Tests(SimpleTestCase):
    def test_v158_uncategorized_is_extracted_after_v159(self):
        report = _report()
        extracted = {status.name: status for status in report.extracted_lanes}

        self.assertIn(UNCATEGORIZED_LANE, extracted)
        self.assertTrue(extracted[UNCATEGORIZED_LANE].extracted)
        self.assertEqual(extracted[UNCATEGORIZED_LANE].definition_count, 0)
        self.assertEqual(extracted[UNCATEGORIZED_LANE].total_lines, 0)
        self.assertEqual(
            extracted[UNCATEGORIZED_LANE].module,
            "backend/listings/listing_uncategorized_views.py",
        )

    def test_v158_uncategorized_dedicated_source_preserves_locked_footprint(self):
        ranges = _definition_ranges("listings/listing_uncategorized_views.py")

        self.assertEqual(set(EXPECTED_UNCATEGORIZED_EXPORTS), set(ranges))
        self.assertEqual(len(EXPECTED_UNCATEGORIZED_EXPORTS), EXPECTED_UNCATEGORIZED_DEFINITION_COUNT)
        self.assertEqual(
            listing_uncategorized_views.UNCATEGORIZED_AUDIT_LINES_V159,
            EXPECTED_UNCATEGORIZED_AUDIT_LINES,
        )
        self.assertEqual(
            sum(ranges[name][-1]["ast_body_lines"] for name in EXPECTED_UNCATEGORIZED_EXPORTS),
            EXPECTED_UNCATEGORIZED_AST_BODY_LINES,
        )
        self.assertEqual(
            sum(ranges[name][-1]["span_lines"] for name in EXPECTED_UNCATEGORIZED_EXPORTS),
            EXPECTED_UNCATEGORIZED_SPAN_LINES_WITH_DECORATORS,
        )

    def test_v158_listings_views_preserves_uncategorized_compatibility_reexports(self):
        for name in EXPECTED_UNCATEGORIZED_EXPORTS:
            self.assertTrue(hasattr(listing_views, name), name)
            self.assertIs(
                getattr(listing_views, name),
                getattr(listing_uncategorized_views, name),
                name,
            )

    def test_v158_remaining_candidates_advance_to_listing_crud_uploads_after_v159(self):
        report = _report()
        remaining = [candidate.name for candidate in report.remaining_candidates]

        self.assertIsNone(report.recommended_next_lane)
        self.assertEqual(remaining, [])
        self.assertNotIn(UNCATEGORIZED_LANE, remaining)

    def test_v158_previous_split_lanes_remain_extracted_after_v159(self):
        report = _report()
        extracted = {status.name: status for status in report.extracted_lanes}

        self.assertEqual(sorted(extracted), EXPECTED_EXTRACTED_LANES_AFTER_V161)

        self.assertTrue(extracted["listing_promotions"].extracted)
        self.assertTrue(extracted["favorites"].extracted)
        self.assertTrue(extracted["browse_search_detail"].extracted)
        self.assertTrue(extracted["uncategorized"].extracted)

    def test_v158_uncategorized_local_views_definitions_are_removed_after_v159(self):
        ranges = _definition_ranges("listings/views.py")

        for name in EXPECTED_UNCATEGORIZED_EXPORTS:
            self.assertNotIn(name, ranges, name)

        self.assertTrue(Path("listings/listing_uncategorized_views.py").exists())

    def test_v158_generated_followup_markdown_documents_listing_crud_uploads_next_lane(self):
        report = _report()

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn("LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153", text)
        self.assertIn("uncategorized", text)
        self.assertIn("listing_crud_uploads", text)
        self.assertIn("Recommended next split lane", text)
