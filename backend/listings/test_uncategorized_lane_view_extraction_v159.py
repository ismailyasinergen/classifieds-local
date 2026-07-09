"""
UNCATEGORIZED_LANE_VIEW_EXTRACTION_V159

Extraction checks for moving the uncategorized lane out of listings.views while
preserving listings.views compatibility re-exports.
"""

from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import listing_uncategorized_views
from listings import listing_views_split_lane_followup_audit_v153 as followup
from listings import views as listing_views


UNCATEGORIZED_LANE_VIEW_EXTRACTION_V159 = True
EXPECTED_UNCATEGORIZED_EXPORTS_V159 = [
    "SidebarCategoriesMixin",
    "ListingListView",
    "listing_approve",
    "listing_reject",
    "listing_archive",
    "listing_renew",
    "listing_feature_toggle"
]
EXPECTED_UNCATEGORIZED_DEFINITION_COUNT_V159 = 7
EXPECTED_UNCATEGORIZED_AUDIT_LINES_V159 = 100
EXPECTED_UNCATEGORIZED_AST_BODY_LINES_V159 = 94
EXPECTED_UNCATEGORIZED_SPAN_LINES_WITH_DECORATORS_V159 = 104


def _top_level_definition_ranges(source_path):
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
            "kind": "class" if isinstance(node, ast.ClassDef) else "function",
            "decorated_start": decorated_start,
            "body_start": body_start,
            "end": end_lineno,
            "ast_body_lines": end_lineno - body_start + 1,
            "span_lines": end_lineno - decorated_start + 1,
        })

    return ranges


def _top_level_assignments(source_path):
    source = Path(source_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assignments = {}

    def collect(target, line_number):
        if isinstance(target, ast.Name):
            assignments.setdefault(target.id, []).append(line_number)
        elif isinstance(target, (ast.Tuple, ast.List)):
            for item in target.elts:
                collect(item, line_number)

    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                collect(target, node.lineno)
        elif isinstance(node, ast.AnnAssign):
            collect(node.target, node.lineno)

    return assignments


class UncategorizedLaneViewExtractionV159Tests(SimpleTestCase):
    def test_v159_dedicated_uncategorized_module_exists_and_exports_names(self):
        self.assertTrue(hasattr(listing_uncategorized_views, "LISTING_UNCATEGORIZED_VIEWS_V159"))
        self.assertEqual(
            listing_uncategorized_views.UNCATEGORIZED_VIEW_EXPORTS_V159,
            EXPECTED_UNCATEGORIZED_EXPORTS_V159,
        )
        self.assertEqual(
            listing_uncategorized_views.UNCATEGORIZED_AUDIT_LINES_V159,
            EXPECTED_UNCATEGORIZED_AUDIT_LINES_V159,
        )
        self.assertEqual(
            listing_uncategorized_views.UNCATEGORIZED_AST_BODY_LINES_V159,
            EXPECTED_UNCATEGORIZED_AST_BODY_LINES_V159,
        )
        self.assertEqual(
            listing_uncategorized_views.UNCATEGORIZED_SPAN_LINES_WITH_DECORATORS_V159,
            EXPECTED_UNCATEGORIZED_SPAN_LINES_WITH_DECORATORS_V159,
        )

        for name in EXPECTED_UNCATEGORIZED_EXPORTS_V159:
            self.assertTrue(hasattr(listing_uncategorized_views, name), name)

    def test_v159_listings_views_reexports_same_uncategorized_objects(self):
        for name in EXPECTED_UNCATEGORIZED_EXPORTS_V159:
            self.assertTrue(hasattr(listing_views, name), name)
            self.assertIs(
                getattr(listing_views, name),
                getattr(listing_uncategorized_views, name),
                name,
            )

    def test_v159_sidebar_mixin_reexport_precedes_early_views_consumers(self):
        source = Path("listings/views.py").read_text(encoding="utf-8")
        tree = ast.parse(source)

        reexport_lines = [
            node.lineno
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module == "listing_uncategorized_views"
        ]
        self.assertEqual(len(reexport_lines), 1)

        consumer_lines = []
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue

            for base in node.bases:
                if isinstance(base, ast.Name) and base.id == "SidebarCategoriesMixin":
                    consumer_lines.append(node.lineno)

        if consumer_lines:
            self.assertLess(reexport_lines[0], min(consumer_lines))
        else:
            exported_names = []
            for node in tree.body:
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module == "listing_uncategorized_views"
                ):
                    exported_names.extend(alias.name for alias in node.names)

            self.assertIn("SidebarCategoriesMixin", exported_names)

    def test_v159_views_source_no_longer_defines_any_uncategorized_target_names(self):
        views_source = Path("listings/views.py").read_text(encoding="utf-8")
        ranges = _top_level_definition_ranges("listings/views.py")

        for name in EXPECTED_UNCATEGORIZED_EXPORTS_V159:
            self.assertNotIn(name, ranges, name)

        self.assertIn("from .listing_uncategorized_views import", views_source)

    def test_v159_internal_base_alias_dependency_is_local_to_dedicated_module(self):
        module_ranges = _top_level_definition_ranges("listings/listing_uncategorized_views.py")
        module_assignments = _top_level_assignments("listings/listing_uncategorized_views.py")
        views_assignments = _top_level_assignments("listings/views.py")

        self.assertIn("_BaseAttributeListingListView", module_assignments)
        self.assertNotIn("_BaseAttributeListingListView", views_assignments)

        self.assertGreaterEqual(len(module_ranges["ListingListView"]), 2)

        self.assertLess(
            module_assignments["_BaseAttributeListingListView"][0],
            module_ranges["ListingListView"][-1]["body_start"],
        )

        self.assertEqual(
            listing_uncategorized_views.UNCATEGORIZED_INTERNAL_DEPENDENCIES_V159,
            ["_BaseAttributeListingListView"],
        )

    def test_v159_dedicated_source_preserves_locked_active_uncategorized_footprint(self):
        ranges = _top_level_definition_ranges("listings/listing_uncategorized_views.py")

        for name in EXPECTED_UNCATEGORIZED_EXPORTS_V159:
            self.assertIn(name, ranges, name)
            if name != "ListingListView":
                self.assertEqual(len(ranges[name]), 1, name)

        self.assertGreaterEqual(len(ranges["ListingListView"]), 1)
        extracted_ranges = [ranges[name][-1] for name in EXPECTED_UNCATEGORIZED_EXPORTS_V159]

        self.assertEqual(len(extracted_ranges), EXPECTED_UNCATEGORIZED_DEFINITION_COUNT_V159)
        self.assertEqual(
            sum(item["ast_body_lines"] for item in extracted_ranges),
            EXPECTED_UNCATEGORIZED_AST_BODY_LINES_V159,
        )
        self.assertEqual(
            sum(item["span_lines"] for item in extracted_ranges),
            EXPECTED_UNCATEGORIZED_SPAN_LINES_WITH_DECORATORS_V159,
        )

    def test_v159_duplicate_shadowed_targets_are_removed_from_views(self):
        removed = listing_uncategorized_views.UNCATEGORIZED_DUPLICATE_TARGETS_REMOVED_V159

        self.assertIn("ListingListView", removed)
        self.assertGreaterEqual(len(removed["ListingListView"]), 2)

        views_ranges = _top_level_definition_ranges("listings/views.py")
        self.assertNotIn("ListingListView", views_ranges)

    def test_v159_followup_audit_records_uncategorized_as_extracted(self):
        report = followup.build_followup_report(Path("."))
        extracted = {status.name: status for status in report.extracted_lanes}
        remaining = [candidate.name for candidate in report.remaining_candidates]

        self.assertIn("uncategorized", extracted)
        self.assertTrue(extracted["uncategorized"].extracted)
        self.assertEqual(extracted["uncategorized"].definition_count, 0)
        self.assertEqual(extracted["uncategorized"].total_lines, 0)
        self.assertEqual(
            extracted["uncategorized"].module,
            "backend/listings/listing_uncategorized_views.py",
        )

        self.assertIsNone(report.recommended_next_lane)
        self.assertEqual(remaining, [])

    def test_v159_previous_extracted_lanes_remain_extracted(self):
        report = followup.build_followup_report(Path("."))
        extracted = {status.name: status for status in report.extracted_lanes}

        for lane in ["listing_promotions", "favorites", "browse_search_detail", "uncategorized"]:
            self.assertIn(lane, extracted)
            self.assertTrue(extracted[lane].extracted)

    def test_v159_generated_followup_markdown_records_extraction_and_next_lane(self):
        report = followup.build_followup_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn("LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153", text)
        self.assertIn("uncategorized", text)
        self.assertIn("listing_uncategorized_views.py", text)
        self.assertIn("Recommended next split lane", text)
        self.assertIn("listing_crud_uploads", text)
