"""
LISTING_CRUD_UPLOADS_CONTRACT_V160

Focused pre-extraction contracts for the listing_crud_uploads lane.

These tests lock the current audit/source/runtime shape before moving this
remaining lane into a dedicated module. The contract is occurrence-based because
this lane currently includes duplicate/shadowed top-level class definitions.
"""

from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_split_lane_audit_v150 as split_audit
from listings import listing_views_split_lane_followup_audit_v153 as followup
from listings import urls as listing_urls
from listings import views as listing_views


LISTING_CRUD_UPLOADS_CONTRACT_V160 = True

LANE_NAME = "listing_crud_uploads"
EXPECTED_DEFINITION_COUNT = 7
EXPECTED_AUDIT_LINES = 145
EXPECTED_SPAN_LINES_WITH_DECORATORS = 149
EXPECTED_TARGET_DEFINITIONS = [
    {
        "name": "ListingCreateView",
        "kind": "class",
        "start_line": 52,
        "end_line": 84,
        "line_count": 33
    },
    {
        "name": "ListingUpdateView",
        "kind": "class",
        "start_line": 87,
        "end_line": 126,
        "line_count": 40
    },
    {
        "name": "ListingDeleteView",
        "kind": "class",
        "start_line": 129,
        "end_line": 143,
        "line_count": 15
    },
    {
        "name": "listing_image_delete",
        "kind": "function",
        "start_line": 148,
        "end_line": 161,
        "line_count": 14
    },
    {
        "name": "listing_feature_days_update",
        "kind": "function",
        "start_line": 241,
        "end_line": 261,
        "line_count": 21
    },
    {
        "name": "ListingCreateView",
        "kind": "class",
        "start_line": 1152,
        "end_line": 1162,
        "line_count": 11
    },
    {
        "name": "ListingUpdateView",
        "kind": "class",
        "start_line": 1166,
        "end_line": 1176,
        "line_count": 11
    }
]
EXPECTED_UNIQUE_TARGET_NAMES = [
    "ListingCreateView",
    "ListingUpdateView",
    "ListingDeleteView",
    "listing_image_delete",
    "listing_feature_days_update"
]
EXPECTED_TARGET_NAME_COUNTS = {
    "ListingCreateView": 2,
    "ListingUpdateView": 2,
    "ListingDeleteView": 1,
    "listing_image_delete": 1,
    "listing_feature_days_update": 1
}
EXPECTED_ROUTE_TARGETS = [
    "ListingCreateView",
    "ListingUpdateView",
    "ListingDeleteView",
    "listing_image_delete",
    "listing_feature_days_update"
]
EXPECTED_DEDICATED_MODULE_PATH = "listings/listing_crud_uploads_views.py"
EXPECTED_EXTRACTED_LANES_AFTER_V159 = [
    "browse_search_detail",
    "favorites",
    "listing_promotions",
    "uncategorized"
]


def _followup_report():
    return followup.build_followup_report(Path("."))


def _split_lane_report():
    report = split_audit.build_report(Path("."))
    lanes = {lane.name: lane for lane in report.lane_reports}
    return lanes[LANE_NAME]


def _top_level_occurrences(source_path):
    source = Path(source_path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    occurrences = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        body_start = node.lineno
        decorators = getattr(node, "decorator_list", [])
        decorated_start = body_start
        if decorators:
            decorated_start = min(decorator.lineno for decorator in decorators)

        end_lineno = node.end_lineno or node.lineno
        occurrences.append(
            {
                "name": node.name,
                "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                "decorated_start": decorated_start,
                "start_line": body_start,
                "end_line": end_lineno,
                "line_count": end_lineno - body_start + 1,
                "span_lines": end_lineno - decorated_start + 1,
            }
        )

    return occurrences


def _route_callback_names():
    names = set()

    def visit(patterns):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):
                callback = pattern.callback
                view_class = getattr(callback, "view_class", None)
                callback_name = getattr(callback, "__name__", "")

                if view_class is not None:
                    names.add(view_class.__name__)
                if callback_name:
                    names.add(callback_name)

            elif isinstance(pattern, URLResolver):
                visit(pattern.url_patterns)

    visit(listing_urls.urlpatterns)
    return names


class ListingCrudUploadsContractV160Tests(SimpleTestCase):
    def test_v160_listing_crud_uploads_is_current_recommended_next_lane(self):
        report = _followup_report()
        remaining = [candidate.name for candidate in report.remaining_candidates]

        self.assertEqual(report.recommended_next_lane.name, LANE_NAME)
        self.assertEqual(report.recommended_next_lane.definition_count, EXPECTED_DEFINITION_COUNT)
        self.assertEqual(report.recommended_next_lane.total_lines, EXPECTED_AUDIT_LINES)
        self.assertEqual(remaining, [LANE_NAME])

    def test_v160_v150_audit_lane_occurrences_are_locked(self):
        lane = _split_lane_report()
        definitions = [
            {
                "name": item.name,
                "kind": item.kind,
                "start_line": item.start_line,
                "end_line": item.end_line,
                "line_count": item.line_count,
            }
            for item in sorted(lane.definitions, key=lambda item: item.start_line)
        ]

        self.assertEqual(lane.definition_count, EXPECTED_DEFINITION_COUNT)
        self.assertEqual(lane.total_lines, EXPECTED_AUDIT_LINES)
        self.assertEqual(definitions, EXPECTED_TARGET_DEFINITIONS)

    def test_v160_listing_crud_uploads_source_occurrences_are_locked_before_extraction(self):
        occurrences = _top_level_occurrences("listings/views.py")
        source_by_key = {
            (item["name"], item["start_line"], item["end_line"]): item
            for item in occurrences
        }

        active_occurrences = []
        for expected in EXPECTED_TARGET_DEFINITIONS:
            key = (expected["name"], expected["start_line"], expected["end_line"])
            self.assertIn(key, source_by_key)
            active_occurrences.append(source_by_key[key])

        self.assertEqual(len(active_occurrences), EXPECTED_DEFINITION_COUNT)
        self.assertEqual(
            sum(item["line_count"] for item in active_occurrences),
            EXPECTED_AUDIT_LINES,
        )
        self.assertEqual(
            sum(item["span_lines"] for item in active_occurrences),
            EXPECTED_SPAN_LINES_WITH_DECORATORS,
        )

    def test_v160_listing_crud_uploads_duplicate_occurrence_counts_are_locked(self):
        occurrences = _top_level_occurrences("listings/views.py")
        counts = {}

        expected_keys = {
            (item["name"], item["start_line"], item["end_line"])
            for item in EXPECTED_TARGET_DEFINITIONS
        }

        for item in occurrences:
            key = (item["name"], item["start_line"], item["end_line"])
            if key in expected_keys:
                counts[item["name"]] = counts.get(item["name"], 0) + 1

        self.assertEqual(counts, EXPECTED_TARGET_NAME_COUNTS)

    def test_v160_listing_crud_uploads_definitions_are_still_local_to_listings_views(self):
        occurrences = _top_level_occurrences("listings/views.py")
        names = {item["name"] for item in occurrences}

        for name in EXPECTED_UNIQUE_TARGET_NAMES:
            self.assertIn(name, names)
            self.assertTrue(hasattr(listing_views, name), name)

    def test_v160_listing_crud_uploads_dedicated_module_does_not_exist_yet(self):
        views_source = Path("listings/views.py").read_text(encoding="utf-8")

        self.assertFalse(Path(EXPECTED_DEDICATED_MODULE_PATH).exists())
        self.assertNotIn("listing_crud_uploads_views", views_source)

    def test_v160_listing_crud_uploads_routes_still_resolve_to_current_views(self):
        route_targets = [name for name in EXPECTED_UNIQUE_TARGET_NAMES if name in _route_callback_names()]

        self.assertEqual(route_targets, EXPECTED_ROUTE_TARGETS)

        for name in EXPECTED_ROUTE_TARGETS:
            self.assertTrue(hasattr(listing_views, name), name)

    def test_v160_previous_split_lanes_remain_extracted_after_v159(self):
        report = _followup_report()
        extracted = {status.name: status for status in report.extracted_lanes}

        self.assertEqual(sorted(extracted), EXPECTED_EXTRACTED_LANES_AFTER_V159)

        for lane in EXPECTED_EXTRACTED_LANES_AFTER_V159:
            self.assertTrue(extracted[lane].extracted, lane)

    def test_v160_generated_followup_markdown_documents_listing_crud_uploads_next_lane(self):
        report = _followup_report()

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn("LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153", text)
        self.assertIn("listing_crud_uploads", text)
        self.assertIn("Recommended next split lane", text)

    def test_v160_contract_metadata_records_occurrences_and_non_goals(self):
        self.assertEqual(LANE_NAME, "listing_crud_uploads")
        self.assertEqual(EXPECTED_DEFINITION_COUNT, 7)
        self.assertEqual(EXPECTED_AUDIT_LINES, 145)
        self.assertEqual(EXPECTED_SPAN_LINES_WITH_DECORATORS, 149)

        self.assertEqual(len(EXPECTED_TARGET_DEFINITIONS), EXPECTED_DEFINITION_COUNT)
        self.assertEqual(
            sum(item["line_count"] for item in EXPECTED_TARGET_DEFINITIONS),
            EXPECTED_AUDIT_LINES,
        )

        self.assertIn("ListingCreateView", EXPECTED_TARGET_NAME_COUNTS)
        self.assertIn("ListingUpdateView", EXPECTED_TARGET_NAME_COUNTS)
        self.assertGreater(EXPECTED_TARGET_NAME_COUNTS["ListingCreateView"], 1)
        self.assertGreater(EXPECTED_TARGET_NAME_COUNTS["ListingUpdateView"], 1)

        self.assertEqual(
            EXPECTED_DEDICATED_MODULE_PATH,
            "listings/listing_crud_uploads_views.py",
        )
        self.assertIn("listing_feature_days_update", EXPECTED_ROUTE_TARGETS)
