from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import remaining_listing_views_post_v161_audit as remaining_audit
from listings import views as listing_views


LISTING_REPORTS_CONTRACT_MARKER_V163 = "LISTING_REPORTS_CONTRACT_V163"

EXPECTED_REPORT_DEFINITION_COUNTS_V163 = {
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

EXPECTED_ACTIVE_REPORT_LINE_COUNTS_V163 = {
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

# These are the existing public URL names. Do not rename them during extraction.
EXPECTED_REPORT_ROUTE_CALLBACKS_V163 = {
    "listing_report": "listing_report_create",
    "report_queue": "listing_report_queue",
    "report_export_csv": "listing_report_export_csv",
    "my_reports": "my_listing_reports",
    "report_review": "listing_report_review",
    "report_dismiss": "listing_report_dismiss",
    "report_suspend_listing": "listing_report_suspend_listing",
    "report_archive_listing": "listing_report_archive_listing",
}


def _views_source() -> str:
    return Path("listings/views.py").read_text(encoding="utf-8")


def _urls_source() -> str:
    return Path("listings/urls.py").read_text(encoding="utf-8")


def _top_level_definitions(source: str):
    tree = ast.parse(source)
    definitions = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            definitions.append(
                {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": node.end_lineno,
                    "line_count": node.end_lineno - node.lineno + 1,
                    "node": node,
                }
            )

    return definitions


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


class ListingReportsContractV163Tests(SimpleTestCase):
    def test_v163_listing_reports_contract_marker_is_declared(self):
        self.assertEqual(LISTING_REPORTS_CONTRACT_MARKER_V163, "LISTING_REPORTS_CONTRACT_V163")

    def test_v163_v162_audit_recommends_listing_reports_lane(self):
        report = remaining_audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertEqual(report.recommended_next_lane.name, "listing_reports")
        self.assertIn("listing_reports", lanes)
        self.assertIn("saved_searches", lanes)

        listing_reports = lanes["listing_reports"]
        saved_searches = lanes["saved_searches"]

        self.assertEqual(listing_reports.definition_count, 33)
        self.assertEqual(listing_reports.total_lines, 1173)
        self.assertEqual(saved_searches.definition_count, 6)
        self.assertEqual(saved_searches.total_lines, 526)

        self.assertGreater(listing_reports.total_lines, saved_searches.total_lines)

    def test_v163_listing_reports_definitions_are_still_local_to_views(self):
        source = _views_source()
        definitions = _top_level_definitions(source)
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)

        for definition in definitions:
            grouped[definition["name"]].append(definition)

        for name, expected_count in EXPECTED_REPORT_DEFINITION_COUNTS_V163.items():
            self.assertIn(name, grouped)
            self.assertEqual(
                len(grouped[name]),
                expected_count,
                f"{name} should preserve its pre-extraction duplicate/shadowed source count",
            )

        self.assertFalse(
            Path("listings/listing_reports_views.py").exists(),
            "v163 is a contract checkpoint only; the dedicated report module should not exist yet.",
        )

    def test_v163_active_listing_report_definitions_preserve_current_footprint(self):
        source = _views_source()
        definitions = _top_level_definitions(source)
        grouped: dict[str, list[dict[str, object]]] = defaultdict(list)

        for definition in definitions:
            grouped[definition["name"]].append(definition)

        for name, expected_line_count in EXPECTED_ACTIVE_REPORT_LINE_COUNTS_V163.items():
            active_definition = grouped[name][-1]
            self.assertEqual(
                active_definition["line_count"],
                expected_line_count,
                f"{name} active definition footprint changed before extraction",
            )

    def test_v163_report_urls_point_to_current_views_callbacks(self):
        callbacks_by_name = _callbacks_by_route_name()

        for route_name, callback_name in EXPECTED_REPORT_ROUTE_CALLBACKS_V163.items():
            self.assertIn(route_name, callbacks_by_name)
            expected_callback = getattr(listing_views, callback_name)
            self.assertIn(
                expected_callback,
                callbacks_by_name[route_name],
                f"{route_name} should still resolve to listings.views.{callback_name}",
            )

    def test_v163_urls_source_keeps_existing_listing_report_route_aliases(self):
        urls_source = _urls_source()

        for route_name, callback_name in EXPECTED_REPORT_ROUTE_CALLBACKS_V163.items():
            self.assertIn(f'name="{route_name}"', urls_source)
            self.assertIn(callback_name, urls_source)

    def test_v163_listing_report_source_keeps_key_runtime_contract_terms(self):
        source = _views_source()

        required_terms = [
            "ListingReport",
            "ModerationNotice",
            "report_trust_safety_events",
            "record_listing_report_reviewed",
            "record_listing_report_suspended",
            "messages.success",
            "messages.warning",
            "redirect",
            "render",
            "listing_report_queue",
            "listing_report_export_csv",
            "listing_report_suspend_listing",
            "listing_report_archive_listing",
            "_safe_reporter_note",
        ]

        for term in required_terms:
            self.assertIn(term, source)

    def test_v163_existing_listing_report_status_ux_tests_remain_in_place(self):
        test_path = Path("listings/test_listing_report_status_ux.py")
        source = test_path.read_text(encoding="utf-8")

        self.assertIn("ListingReportStatusUxTests", source)
        self.assertIn("test_listing_status_filter_limits_listing_reports", source)
        self.assertIn("test_report_queue_uses_clear_report_and_listing_status_labels", source)
        self.assertIn("test_suspend_listing_action_marks_report_reviewed", source)
