"""
LISTING_CRUD_UPLOADS_CONTRACT_V160

Compatibility contracts for the listing_crud_uploads lane.

v160 locked the pre-extraction occurrence-based shape. After v161, these tests
verify the dedicated module preserves that locked shape and listings.views keeps
compatibility re-exports.
"""

from __future__ import annotations

import ast
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_crud_uploads_views
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
EXPECTED_EXTRACTED_LANES_AFTER_V161 = [
    "browse_search_detail",
    "favorites",
    "listing_crud_uploads",
    "listing_promotions",
    "uncategorized"
]


def _report():
    return followup.build_followup_report(Path("."))


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
                "body_start": body_start,
                "decorated_start": decorated_start,
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
    def test_v160_listing_crud_uploads_is_extracted_after_v161(self):
        report = _report()
        extracted = {status.name: status for status in report.extracted_lanes}
        remaining = [candidate.name for candidate in report.remaining_candidates]

        self.assertIn(LANE_NAME, extracted)
        self.assertTrue(extracted[LANE_NAME].extracted)
        self.assertEqual(extracted[LANE_NAME].definition_count, 0)
        self.assertEqual(extracted[LANE_NAME].total_lines, 0)
        self.assertEqual(remaining, [])
        self.assertIsNone(report.recommended_next_lane)

    def test_v160_dedicated_module_preserves_locked_occurrence_counts_and_footprint(self):
        occurrences = _top_level_occurrences(EXPECTED_DEDICATED_MODULE_PATH)
        selected = [item for item in occurrences if item["name"] in EXPECTED_TARGET_NAME_COUNTS]

        counts = {}
        for item in selected:
            counts[item["name"]] = counts.get(item["name"], 0) + 1

        self.assertEqual(counts, EXPECTED_TARGET_NAME_COUNTS)
        self.assertEqual(len(selected), EXPECTED_DEFINITION_COUNT)
        self.assertEqual(sum(item["line_count"] for item in selected), EXPECTED_AUDIT_LINES)
        self.assertEqual(sum(item["span_lines"] for item in selected), EXPECTED_SPAN_LINES_WITH_DECORATORS)

    def test_v160_listings_views_preserves_crud_upload_compatibility_reexports(self):
        for name in EXPECTED_UNIQUE_TARGET_NAMES:
            self.assertTrue(hasattr(listing_views, name), name)
            self.assertIs(
                getattr(listing_views, name),
                getattr(listing_crud_uploads_views, name),
                name,
            )

    def test_v160_crud_upload_local_definitions_are_removed_from_views_after_v161(self):
        occurrences = _top_level_occurrences("listings/views.py")
        names = {item["name"] for item in occurrences}

        for name in EXPECTED_UNIQUE_TARGET_NAMES:
            self.assertNotIn(name, names)

        self.assertTrue(Path(EXPECTED_DEDICATED_MODULE_PATH).exists())

    def test_v160_duplicate_create_update_occurrence_counts_are_preserved_after_v161(self):
        occurrences = _top_level_occurrences(EXPECTED_DEDICATED_MODULE_PATH)

        create_count = sum(1 for item in occurrences if item["name"] == "ListingCreateView")
        update_count = sum(1 for item in occurrences if item["name"] == "ListingUpdateView")

        self.assertEqual(create_count, 2)
        self.assertEqual(update_count, 2)

    def test_v160_routes_still_resolve_to_reexported_current_views_after_v161(self):
        route_targets = [name for name in EXPECTED_UNIQUE_TARGET_NAMES if name in _route_callback_names()]

        self.assertEqual(route_targets, EXPECTED_ROUTE_TARGETS)

        for name in EXPECTED_ROUTE_TARGETS:
            self.assertIs(
                getattr(listing_views, name),
                getattr(listing_crud_uploads_views, name),
                name,
            )

    def test_v160_all_tracked_split_lanes_are_extracted_after_v161(self):
        report = _report()
        extracted = sorted(status.name for status in report.extracted_lanes)
        remaining = [candidate.name for candidate in report.remaining_candidates]

        self.assertEqual(extracted, EXPECTED_EXTRACTED_LANES_AFTER_V161)
        self.assertEqual(remaining, [])

    def test_v160_generated_followup_markdown_documents_completed_split_state(self):
        report = _report()

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8").lower()

        self.assertIn("listing_crud_uploads", text)
        self.assertIn("none", text)

    def test_v160_contract_metadata_remains_locked_after_v161(self):
        self.assertEqual(LANE_NAME, "listing_crud_uploads")
        self.assertEqual(EXPECTED_DEFINITION_COUNT, 7)
        self.assertEqual(EXPECTED_AUDIT_LINES, 145)
        self.assertEqual(EXPECTED_SPAN_LINES_WITH_DECORATORS, 149)
        self.assertEqual(sum(item["line_count"] for item in EXPECTED_TARGET_DEFINITIONS), 145)

    def test_v160_contract_metadata_records_v161_followup(self):
        self.assertEqual(LANE_NAME, "listing_crud_uploads")
        self.assertEqual(EXPECTED_DEFINITION_COUNT, 7)
        self.assertEqual(EXPECTED_AUDIT_LINES, 145)
        self.assertEqual(EXPECTED_SPAN_LINES_WITH_DECORATORS, 149)
        self.assertEqual(EXPECTED_DEDICATED_MODULE_PATH, "listings/listing_crud_uploads_views.py")
        self.assertEqual(EXPECTED_TARGET_NAME_COUNTS["ListingCreateView"], 2)
        self.assertEqual(EXPECTED_TARGET_NAME_COUNTS["ListingUpdateView"], 2)
