from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_import_hygiene_audit_v168 as audit
from listings import views as listing_views


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


class ListingViewsImportHygieneAuditV168Tests(SimpleTestCase):
    def test_v168_marker_is_declared(self):
        self.assertEqual(
            audit.LISTING_VIEWS_IMPORT_HYGIENE_AUDIT_MARKER_V168,
            "LISTING_VIEWS_IMPORT_HYGIENE_AUDIT_V168",
        )

    def test_v168_views_py_remains_facade_only(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.top_level_function_names, ())
        self.assertEqual(report.top_level_class_names, ())
        self.assertEqual(report.total_top_level_definitions, 0)
        self.assertTrue(report.is_facade_only)

    def test_v168_expected_compatibility_reexport_modules_are_present(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.missing_expected_reexport_modules, ())
        self.assertIn("listing_crud_uploads_views", report.compatibility_reexport_modules)
        self.assertIn("listing_reports_views", report.compatibility_reexport_modules)
        self.assertIn("saved_searches_views", report.compatibility_reexport_modules)

    def test_v168_views_facade_has_no_wildcard_imports(self):
        report = audit.build_report(Path("."))

        self.assertTrue(report.has_no_wildcard_imports)
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v168_url_callbacks_that_resolve_through_listing_views_are_dedicated_objects(self):
        callbacks_by_name = _callbacks_by_route_name()
        matched_route_names: list[str] = []

        for route_name, callbacks in callbacks_by_name.items():
            for callback in callbacks:
                callback_name = getattr(callback, "__name__", "")
                if not callback_name or not hasattr(listing_views, callback_name):
                    continue

                reexported = getattr(listing_views, callback_name)
                if reexported is not callback:
                    continue

                matched_route_names.append(route_name)
                self.assertNotEqual(
                    getattr(callback, "__module__", ""),
                    "listings.views",
                    f"{route_name} unexpectedly resolves to an object defined in listings.views",
                )

        self.assertIn("saved_search_list", matched_route_names)
        self.assertIn("report_queue", matched_route_names)

    def test_v168_markdown_documents_hygiene_and_non_goals(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_import_hygiene_audit_v168.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.LISTING_VIEWS_IMPORT_HYGIENE_AUDIT_MARKER_V168, text)
        self.assertIn("Facade-only state: `True`", text)
        self.assertIn("Wildcard imports present: `False`", text)
        self.assertIn("Compatibility view re-export modules", text)
        self.assertIn("Do not move runtime code in v168", text)
        self.assertIn("Do not delete imports without a separate cleanup contract", text)
