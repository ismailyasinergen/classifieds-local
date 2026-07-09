from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import remaining_listing_views_post_v161_audit as remaining_audit
from listings import saved_searches_views
from listings import views as listing_views


SAVED_SEARCHES_VIEW_EXTRACTION_MARKER_V166 = "SAVED_SEARCHES_VIEW_EXTRACTION_V166"

SAVED_SEARCH_NAMES_V166 = (
    "saved_search_create",
    "saved_search_list",
    "saved_search_notifications_toggle",
    "saved_search_delete",
    "saved_search_bulk_action",
    "saved_search_rename",
)

EXPECTED_SAVED_SEARCH_LINE_COUNTS_V166 = {
    "saved_search_create": 28,
    "saved_search_list": 358,
    "saved_search_notifications_toggle": 36,
    "saved_search_delete": 7,
    "saved_search_bulk_action": 49,
    "saved_search_rename": 48,
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


class SavedSearchesViewExtractionV166Tests(SimpleTestCase):
    def test_v166_marker_is_declared(self):
        self.assertEqual(
            SAVED_SEARCHES_VIEW_EXTRACTION_MARKER_V166,
            "SAVED_SEARCHES_VIEW_EXTRACTION_V166",
        )

    def test_v166_dedicated_module_exists_and_exports_active_names(self):
        self.assertTrue(Path("listings/saved_searches_views.py").exists())

        for name in SAVED_SEARCH_NAMES_V166:
            self.assertTrue(hasattr(saved_searches_views, name), f"{name} missing from dedicated module")
            self.assertTrue(hasattr(listing_views, name), f"{name} missing from listings.views re-export")
            self.assertIs(getattr(listing_views, name), getattr(saved_searches_views, name))

    def test_v166_views_no_longer_defines_saved_search_functions_locally(self):
        views_source = Path("listings/views.py").read_text(encoding="utf-8")
        self.assertIn("# V166 saved searches re-export", views_source)
        self.assertIn("saved_searches_views", views_source)

        local_names = {
            node.name
            for node in _definitions("listings/views.py")
            if node.name in SAVED_SEARCH_NAMES_V166
        }

        self.assertEqual(local_names, set())

    def test_v166_dedicated_module_preserves_counts_and_active_footprint(self):
        definitions = _definitions("listings/saved_searches_views.py")
        grouped: dict[str, list[ast.FunctionDef]] = defaultdict(list)

        for node in definitions:
            if node.name in SAVED_SEARCH_NAMES_V166:
                grouped[node.name].append(node)

        self.assertEqual(set(grouped), set(SAVED_SEARCH_NAMES_V166))

        for name, expected_line_count in EXPECTED_SAVED_SEARCH_LINE_COUNTS_V166.items():
            self.assertEqual(len(grouped[name]), 1)
            node = grouped[name][0]
            actual_line_count = node.end_lineno - node.lineno + 1
            self.assertEqual(actual_line_count, expected_line_count)

    def test_v166_routes_still_resolve_to_reexported_listing_views_callbacks(self):
        callbacks_by_name = _callbacks_by_route_name()

        for callback_name in SAVED_SEARCH_NAMES_V166:
            reexported_callback = getattr(listing_views, callback_name)
            dedicated_callback = getattr(saved_searches_views, callback_name)
            route_names = [
                route_name
                for route_name, callbacks in callbacks_by_name.items()
                if reexported_callback in callbacks
            ]

            self.assertIs(reexported_callback, dedicated_callback)
            self.assertGreaterEqual(len(route_names), 1, f"{callback_name} has no route")

    def test_v166_v162_remaining_audit_has_no_remaining_lanes(self):
        report = remaining_audit.build_report(Path("."))

        self.assertEqual(report.lanes, [])
        self.assertIsNone(report.recommended_next_lane)

    def test_v166_saved_search_module_keeps_runtime_terms(self):
        source = Path("listings/saved_searches_views.py").read_text(encoding="utf-8")

        required_terms = [
            "SavedSearch",
            "saved_search_create",
            "saved_search_list",
            "saved_search_notifications_toggle",
            "saved_search_delete",
            "saved_search_bulk_action",
            "saved_search_rename",
            "messages.success",
            "messages.warning",
            "redirect",
            "render",
        ]

        for term in required_terms:
            self.assertIn(term, source)
