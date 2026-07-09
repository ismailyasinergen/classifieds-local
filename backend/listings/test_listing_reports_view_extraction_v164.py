from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_reports_views
from listings import remaining_listing_views_post_v161_audit as remaining_audit
from listings import views as listing_views


LISTING_REPORTS_VIEW_EXTRACTION_MARKER_V164 = "LISTING_REPORTS_VIEW_EXTRACTION_V164"

REPORT_NAMES_V164 = {
    "moderation_queue",
    "listing_report_create",
    "listing_report_queue",
    "listing_report_export_csv",
    "my_listing_reports",
    "_safe_reporter_note",
    "listing_report_review",
    "listing_report_dismiss",
    "listing_report_suspend_listing",
    "listing_report_archive_listing",
}

EXPECTED_REPORT_DEFINITION_COUNTS_V164 = {
    "moderation_queue": 2,
    "listing_report_create": 4,
    "listing_report_queue": 4,
    "listing_report_review": 4,
    "listing_report_dismiss": 4,
    "listing_report_archive_listing": 5,
    "listing_report_export_csv": 2,
    "my_listing_reports": 3,
    "_safe_reporter_note": 1,
    "listing_report_suspend_listing": 4,
}

EXPECTED_ACTIVE_REPORT_LINE_COUNTS_V164 = {
    "moderation_queue": 49,
    "listing_report_create": 54,
    "listing_report_queue": 80,
    "listing_report_export_csv": 86,
    "my_listing_reports": 18,
    "_safe_reporter_note": 2,
    "listing_report_review": 13,
    "listing_report_dismiss": 13,
    "listing_report_suspend_listing": 13,
    "listing_report_archive_listing": 13,
}

EXPECTED_REPORT_ROUTE_CALLBACKS_V164 = {
    "listing_report": "listing_report_create",
    "report_queue": "listing_report_queue",
    "report_export_csv": "listing_report_export_csv",
    "my_reports": "my_listing_reports",
    "report_review": "listing_report_review",
    "report_dismiss": "listing_report_dismiss",
    "report_suspend_listing": "listing_report_suspend_listing",
    "report_archive_listing": "listing_report_archive_listing",
}


def _definitions(path: str):
    source = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(source)
    return [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    ]


def _callbacks_by_route_name():
    callbacks: dict[str, list[object]] = defaultdict(list)

    def visit(patterns):
        for pattern in patterns:
            if isinstance(pattern, URLPattern):
                if pattern.name:
                    callbacks[pattern.name].append(pattern.callback)
            elif isinstance(pattern, URLResolver):
                visit(pattern.url_patterns)

    visit(get_resolver().url_patterns)
    return callbacks


class ListingReportsViewExtractionV164Tests(SimpleTestCase):
    def test_v164_marker_is_declared(self):
        self.assertEqual(
            LISTING_REPORTS_VIEW_EXTRACTION_MARKER_V164,
            "LISTING_REPORTS_VIEW_EXTRACTION_V164",
        )

    def test_v164_dedicated_module_exists_and_exports_active_names(self):
        self.assertTrue(Path("listings/listing_reports_views.py").exists())

        for name in REPORT_NAMES_V164:
            self.assertTrue(hasattr(listing_reports_views, name), f"{name} missing from dedicated module")
            self.assertTrue(hasattr(listing_views, name), f"{name} missing from listings.views re-export")
            self.assertIs(getattr(listing_views, name), getattr(listing_reports_views, name))

    def test_v164_views_no_longer_defines_listing_report_functions_locally(self):
        views_source = Path("listings/views.py").read_text(encoding="utf-8")
        self.assertIn("# V164 listing reports re-export", views_source)
        self.assertIn("listing_reports_views", views_source)

        local_names = {
            node.name
            for node in _definitions("listings/views.py")
            if node.name in REPORT_NAMES_V164
        }

        self.assertEqual(local_names, set())

    def test_v164_dedicated_module_preserves_duplicate_counts_and_active_footprint(self):
        definitions = _definitions("listings/listing_reports_views.py")
        counts = Counter(node.name for node in definitions if node.name in REPORT_NAMES_V164)

        self.assertEqual(dict(counts), EXPECTED_REPORT_DEFINITION_COUNTS_V164)

        grouped: dict[str, list[ast.FunctionDef]] = defaultdict(list)
        for node in definitions:
            if node.name in REPORT_NAMES_V164:
                grouped[node.name].append(node)

        for name, expected_line_count in EXPECTED_ACTIVE_REPORT_LINE_COUNTS_V164.items():
            active_node = grouped[name][-1]
            actual_line_count = active_node.end_lineno - active_node.lineno + 1
            self.assertEqual(actual_line_count, expected_line_count)

    def test_v164_routes_still_resolve_to_reexported_listing_views_callbacks(self):
        callbacks_by_name = _callbacks_by_route_name()

        for route_name, callback_name in EXPECTED_REPORT_ROUTE_CALLBACKS_V164.items():
            self.assertIn(route_name, callbacks_by_name)
            reexported_callback = getattr(listing_views, callback_name)
            dedicated_callback = getattr(listing_reports_views, callback_name)

            self.assertIs(reexported_callback, dedicated_callback)
            self.assertIn(reexported_callback, callbacks_by_name[route_name])

    def test_v164_v162_remaining_audit_records_completed_state_after_v166(self):
        report = remaining_audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertNotIn("listing_reports", lanes)
        self.assertNotIn("saved_searches", lanes)
        self.assertIsNone(report.recommended_next_lane)

    def test_v164_report_module_keeps_runtime_safety_terms(self):
        source = Path("listings/listing_reports_views.py").read_text(encoding="utf-8")

        required_terms = [
            "ModerationNotice",
            "report_trust_safety_events",
            "record_listing_report_reviewed",
            "record_listing_report_suspended",
            "_TrustSafetyOriginalListingReportReview",
            "_TrustSafetyOriginalListingReportDismiss",
            "_TrustSafetyOriginalListingReportSuspendListing",
            "_TrustSafetyOriginalListingReportArchiveListing",
        ]

        for term in required_terms:
            self.assertIn(term, source)
