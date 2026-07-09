from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_reports_views
from listings import post_extraction_listing_views_audit_v167 as audit
from listings import saved_searches_views
from listings import views as listing_views


REPORT_ROUTE_CALLBACKS_V167 = {
    "listing_report": "listing_report_create",
    "report_queue": "listing_report_queue",
    "report_export_csv": "listing_report_export_csv",
    "my_reports": "my_listing_reports",
    "report_review": "listing_report_review",
    "report_dismiss": "listing_report_dismiss",
    "report_suspend_listing": "listing_report_suspend_listing",
    "report_archive_listing": "listing_report_archive_listing",
}

SAVED_SEARCH_ROUTE_CALLBACKS_V167 = {
    "saved_search_create": "saved_search_create",
    "saved_search_list": "saved_search_list",
    "saved_search_notifications_toggle": "saved_search_notifications_toggle",
    "saved_search_delete": "saved_search_delete",
    "saved_search_bulk_action": "saved_search_bulk_action",
    "saved_search_rename": "saved_search_rename",
}


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


class PostExtractionListingViewsAuditV167Tests(SimpleTestCase):
    def test_v167_marker_is_declared(self):
        self.assertEqual(
            audit.POST_EXTRACTION_LISTING_VIEWS_AUDIT_MARKER_V167,
            "POST_EXTRACTION_LISTING_VIEWS_AUDIT_V167",
        )

    def test_v167_report_records_no_local_runtime_views_in_views_py(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.top_level_function_names, ())
        self.assertEqual(report.top_level_class_names, ())
        self.assertEqual(report.total_top_level_definitions, 0)
        self.assertTrue(report.has_no_local_runtime_views)

    def test_v167_report_records_expected_extracted_modules_and_reexports(self):
        report = audit.build_report(Path("."))
        modules = {module.lane_name: module for module in report.extracted_modules}

        self.assertEqual(set(modules), {"listing_crud_uploads", "listing_reports", "saved_searches"})
        self.assertEqual(report.missing_extracted_modules, ())
        self.assertEqual(report.missing_reexport_mentions, ())

        for expected_module in audit.EXPECTED_VIEWS_REEXPORT_MODULE_NAMES_V167:
            self.assertIn(expected_module, report.reexport_module_names)

    def test_v167_listing_report_routes_still_resolve_through_views_reexports(self):
        callbacks_by_name = _callbacks_by_route_name()

        for route_name, callback_name in REPORT_ROUTE_CALLBACKS_V167.items():
            self.assertIn(route_name, callbacks_by_name)

            reexported_callback = getattr(listing_views, callback_name)
            dedicated_callback = getattr(listing_reports_views, callback_name)

            self.assertIs(reexported_callback, dedicated_callback)
            self.assertIn(reexported_callback, callbacks_by_name[route_name])

    def test_v167_saved_search_routes_still_resolve_through_views_reexports(self):
        callbacks_by_name = _callbacks_by_route_name()

        for route_name, callback_name in SAVED_SEARCH_ROUTE_CALLBACKS_V167.items():
            self.assertIn(route_name, callbacks_by_name)

            reexported_callback = getattr(listing_views, callback_name)
            dedicated_callback = getattr(saved_searches_views, callback_name)

            self.assertIs(reexported_callback, dedicated_callback)
            self.assertIn(reexported_callback, callbacks_by_name[route_name])

    def test_v167_audit_markdown_documents_no_blind_extraction_next_step(self):
        report = audit.build_report(Path("."))
        output = Path("docs/post_extraction_listing_views_audit_v167.md")

        audit.write_markdown_report(output, report)
        text = output.read_text(encoding="utf-8")

        self.assertIn(audit.POST_EXTRACTION_LISTING_VIEWS_AUDIT_MARKER_V167, text)
        self.assertIn("Top-level functions/classes remaining in `views.py`: `0`", text)
        self.assertIn("No top-level functions remain", text)
        self.assertIn("No top-level classes remain", text)
        self.assertIn("No further blind extraction", text)
        self.assertIn("Do not move runtime code in v167", text)
