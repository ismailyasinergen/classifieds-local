"""
LISTING_CRUD_UPLOADS_VIEW_EXTRACTION_V161

Extraction checks for moving the listing_crud_uploads lane out of listings.views
while preserving listings.views compatibility re-exports.
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


LISTING_CRUD_UPLOADS_VIEW_EXTRACTION_V161 = True

EXPECTED_VIEW_EXPORTS_V161 = [
    "ListingCreateView",
    "ListingUpdateView",
    "ListingDeleteView",
    "listing_image_delete",
    "listing_feature_days_update"
]
EXPECTED_DEFINITION_OCCURRENCES_V161 = [
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
EXPECTED_TARGET_NAME_COUNTS_V161 = {
    "ListingCreateView": 2,
    "ListingUpdateView": 2,
    "ListingDeleteView": 1,
    "listing_image_delete": 1,
    "listing_feature_days_update": 1
}
EXPECTED_AUDIT_LINES_V161 = 145
EXPECTED_SPAN_LINES_WITH_DECORATORS_V161 = 149
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


class ListingCrudUploadsViewExtractionV161Tests(SimpleTestCase):
    def test_v161_dedicated_module_exists_and_exports_names(self):
        self.assertTrue(listing_crud_uploads_views.LISTING_CRUD_UPLOADS_VIEWS_V161)
        self.assertEqual(
            listing_crud_uploads_views.LISTING_CRUD_UPLOADS_VIEW_EXPORTS_V161,
            EXPECTED_VIEW_EXPORTS_V161,
        )
        self.assertEqual(
            listing_crud_uploads_views.LISTING_CRUD_UPLOADS_DEFINITION_OCCURRENCES_V161,
            EXPECTED_DEFINITION_OCCURRENCES_V161,
        )
        self.assertEqual(
            listing_crud_uploads_views.LISTING_CRUD_UPLOADS_TARGET_NAME_COUNTS_V161,
            EXPECTED_TARGET_NAME_COUNTS_V161,
        )

        for name in EXPECTED_VIEW_EXPORTS_V161:
            self.assertTrue(hasattr(listing_crud_uploads_views, name), name)

    def test_v161_listings_views_reexports_same_active_objects(self):
        for name in EXPECTED_VIEW_EXPORTS_V161:
            self.assertTrue(hasattr(listing_views, name), name)
            self.assertIs(
                getattr(listing_views, name),
                getattr(listing_crud_uploads_views, name),
                name,
            )

    def test_v161_views_source_no_longer_defines_crud_upload_target_names(self):
        occurrences = _top_level_occurrences("listings/views.py")
        names = {item["name"] for item in occurrences}

        for name in EXPECTED_VIEW_EXPORTS_V161:
            self.assertNotIn(name, names)

        source = Path("listings/views.py").read_text(encoding="utf-8")
        self.assertIn("from .listing_crud_uploads_views import", source)

    def test_v161_dedicated_source_preserves_occurrence_counts_and_footprint(self):
        occurrences = _top_level_occurrences("listings/listing_crud_uploads_views.py")

        counts = {}
        selected = []

        for item in occurrences:
            if item["name"] in EXPECTED_TARGET_NAME_COUNTS_V161:
                counts[item["name"]] = counts.get(item["name"], 0) + 1
                selected.append(item)

        self.assertEqual(counts, EXPECTED_TARGET_NAME_COUNTS_V161)
        self.assertEqual(len(selected), 7)
        self.assertEqual(sum(item["line_count"] for item in selected), EXPECTED_AUDIT_LINES_V161)
        self.assertEqual(sum(item["span_lines"] for item in selected), EXPECTED_SPAN_LINES_WITH_DECORATORS_V161)

    def test_v161_internal_report_original_aliases_are_local_to_dedicated_module(self):
        occurrences = _top_level_occurrences("listings/listing_crud_uploads_views.py")
        assignments = _top_level_assignments("listings/listing_crud_uploads_views.py")

        create_lines = [
            item["body_start"]
            for item in occurrences
            if item["name"] == "ListingCreateView"
        ]
        update_lines = [
            item["body_start"]
            for item in occurrences
            if item["name"] == "ListingUpdateView"
        ]

        self.assertEqual(
            listing_crud_uploads_views.LISTING_CRUD_UPLOADS_INTERNAL_DEPENDENCIES_V161,
            ["_ReportOriginalListingCreateView", "_ReportOriginalListingUpdateView"],
        )

        self.assertIn("_ReportOriginalListingCreateView", assignments)
        self.assertIn("_ReportOriginalListingUpdateView", assignments)

        self.assertLess(create_lines[0], assignments["_ReportOriginalListingCreateView"][0])
        self.assertLess(assignments["_ReportOriginalListingCreateView"][0], create_lines[-1])

        self.assertLess(update_lines[0], assignments["_ReportOriginalListingUpdateView"][0])
        self.assertLess(assignments["_ReportOriginalListingUpdateView"][0], update_lines[-1])

    def test_v161_duplicate_shadowed_create_update_classes_are_preserved_in_module(self):
        occurrences = _top_level_occurrences("listings/listing_crud_uploads_views.py")

        create_occurrences = [item for item in occurrences if item["name"] == "ListingCreateView"]
        update_occurrences = [item for item in occurrences if item["name"] == "ListingUpdateView"]

        self.assertEqual(len(create_occurrences), 2)
        self.assertEqual(len(update_occurrences), 2)
        self.assertLess(create_occurrences[0]["body_start"], create_occurrences[-1]["body_start"])
        self.assertLess(update_occurrences[0]["body_start"], update_occurrences[-1]["body_start"])

    def test_v161_routes_still_resolve_to_reexported_views(self):
        route_names = _route_callback_names()

        for name in EXPECTED_VIEW_EXPORTS_V161:
            self.assertIn(name, route_names)
            self.assertIs(
                getattr(listing_views, name),
                getattr(listing_crud_uploads_views, name),
                name,
            )

    def test_v161_followup_audit_records_listing_crud_uploads_as_extracted(self):
        report = _report()
        extracted = {status.name: status for status in report.extracted_lanes}
        remaining = [candidate.name for candidate in report.remaining_candidates]

        self.assertIn("listing_crud_uploads", extracted)
        self.assertTrue(extracted["listing_crud_uploads"].extracted)
        self.assertEqual(extracted["listing_crud_uploads"].definition_count, 0)
        self.assertEqual(extracted["listing_crud_uploads"].total_lines, 0)
        self.assertEqual(
            extracted["listing_crud_uploads"].module,
            "backend/listings/listing_crud_uploads_views.py",
        )

        self.assertEqual(remaining, [])
        self.assertIsNone(report.recommended_next_lane)

    def test_v161_all_tracked_split_lanes_are_extracted(self):
        report = _report()
        extracted = sorted(status.name for status in report.extracted_lanes)
        remaining = [candidate.name for candidate in report.remaining_candidates]

        self.assertEqual(extracted, EXPECTED_EXTRACTED_LANES_AFTER_V161)
        self.assertEqual(remaining, [])

    def test_v161_generated_followup_markdown_handles_no_remaining_candidates(self):
        report = _report()

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_split_lane_followup_audit_v153.md"
            followup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8").lower()

        self.assertIn("listing_crud_uploads", text)
        self.assertIn("none", text)

    def test_v161_metadata_records_extraction_and_completed_state(self):
        self.assertEqual(EXPECTED_VIEW_EXPORTS_V161, [
            "ListingCreateView",
            "ListingUpdateView",
            "ListingDeleteView",
            "listing_image_delete",
            "listing_feature_days_update",
        ])
        self.assertEqual(EXPECTED_AUDIT_LINES_V161, 145)
        self.assertEqual(EXPECTED_SPAN_LINES_WITH_DECORATORS_V161, 149)
        self.assertEqual(EXPECTED_TARGET_NAME_COUNTS_V161["ListingCreateView"], 2)
        self.assertEqual(EXPECTED_TARGET_NAME_COUNTS_V161["ListingUpdateView"], 2)
        self.assertEqual(EXPECTED_EXTRACTED_LANES_AFTER_V161, [
            "browse_search_detail",
            "favorites",
            "listing_crud_uploads",
            "listing_promotions",
            "uncategorized",
        ])
