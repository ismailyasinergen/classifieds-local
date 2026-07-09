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


SAVED_SEARCHES_CONTRACT_MARKER_V165 = "SAVED_SEARCHES_CONTRACT_V165"

EXPECTED_SAVED_SEARCH_CALLBACKS_V165 = (
    "saved_search_create",
    "saved_search_list",
    "saved_search_notifications_toggle",
    "saved_search_delete",
    "saved_search_bulk_action",
    "saved_search_rename",
)

EXPECTED_SAVED_SEARCH_LINE_COUNTS_V165 = {
    "saved_search_create": 28,
    "saved_search_list": 358,
    "saved_search_notifications_toggle": 36,
    "saved_search_delete": 7,
    "saved_search_bulk_action": 49,
    "saved_search_rename": 48,
}

EXPECTED_SAVED_SEARCH_TOTAL_LINES_V165 = 526


def _views_source() -> str:
    return Path("listings/views.py").read_text(encoding="utf-8")


def _saved_searches_source() -> str:
    return Path("listings/saved_searches_views.py").read_text(encoding="utf-8")


def _urls_source() -> str:
    return Path("listings/urls.py").read_text(encoding="utf-8")


def _top_level_functions(source: str):
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


def _route_names_for_callback(callback_name: str) -> tuple[str, ...]:
    callbacks_by_name = _callbacks_by_route_name()
    expected_callback = getattr(listing_views, callback_name)

    return tuple(
        sorted(
            route_name
            for route_name, callbacks in callbacks_by_name.items()
            if expected_callback in callbacks
        )
    )


class SavedSearchesContractV165Tests(SimpleTestCase):
    def test_v165_saved_searches_contract_marker_is_declared(self):
        self.assertEqual(SAVED_SEARCHES_CONTRACT_MARKER_V165, "SAVED_SEARCHES_CONTRACT_V165")

    def test_v165_v162_audit_records_completed_state_after_v166(self):
        report = remaining_audit.build_report(Path("."))
        lanes = {lane.name: lane for lane in report.lanes}

        self.assertIsNone(report.recommended_next_lane)
        self.assertNotIn("saved_searches", lanes)
        self.assertNotIn("listing_reports", lanes)

    def test_v165_saved_searches_are_extracted_to_dedicated_module(self):
        views_source = _views_source()
        saved_searches_source = _saved_searches_source()

        views_functions = _top_level_functions(views_source)
        saved_searches_functions = _top_level_functions(saved_searches_source)

        local_saved_search_names = {
            node.name
            for node in views_functions
            if node.name in EXPECTED_SAVED_SEARCH_CALLBACKS_V165
        }
        self.assertEqual(local_saved_search_names, set())

        grouped: dict[str, list[ast.FunctionDef]] = defaultdict(list)
        for node in saved_searches_functions:
            if node.name in EXPECTED_SAVED_SEARCH_CALLBACKS_V165:
                grouped[node.name].append(node)

        self.assertEqual(set(grouped), set(EXPECTED_SAVED_SEARCH_CALLBACKS_V165))

        for name in EXPECTED_SAVED_SEARCH_CALLBACKS_V165:
            self.assertEqual(len(grouped[name]), 1)

        self.assertTrue(Path("listings/saved_searches_views.py").exists())

    def test_v165_saved_searches_source_footprint_is_preserved_in_module(self):
        source = _saved_searches_source()
        functions = _top_level_functions(source)
        grouped = {node.name: node for node in functions if node.name in EXPECTED_SAVED_SEARCH_CALLBACKS_V165}

        for name, expected_line_count in EXPECTED_SAVED_SEARCH_LINE_COUNTS_V165.items():
            node = grouped[name]
            actual_line_count = node.end_lineno - node.lineno + 1
            self.assertEqual(actual_line_count, expected_line_count, f"{name} line count changed")

        self.assertEqual(sum(EXPECTED_SAVED_SEARCH_LINE_COUNTS_V165.values()), EXPECTED_SAVED_SEARCH_TOTAL_LINES_V165)

    def test_v165_saved_search_routes_point_to_current_views_reexports(self):
        for callback_name in EXPECTED_SAVED_SEARCH_CALLBACKS_V165:
            route_names = _route_names_for_callback(callback_name)

            self.assertGreaterEqual(
                len(route_names),
                1,
                f"{callback_name} should have at least one URL route resolving to listings.views.{callback_name}",
            )
            self.assertIs(getattr(listing_views, callback_name), getattr(saved_searches_views, callback_name))

    def test_v165_urls_source_mentions_saved_search_callbacks(self):
        urls_source = _urls_source()

        for callback_name in EXPECTED_SAVED_SEARCH_CALLBACKS_V165:
            self.assertIn(callback_name, urls_source)

    def test_v165_saved_search_source_keeps_key_runtime_contract_terms(self):
        source = _saved_searches_source()

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

    def test_v165_existing_saved_search_runtime_tests_remain_in_place(self):
        existing_files = [
            "test_saved_search_bulk_actions.py",
            "test_saved_search_bulk_ui_polish.py",
            "test_saved_search_management_hardening.py",
            "test_saved_search_management_ui_polish.py",
        ]

        for filename in existing_files:
            self.assertTrue(Path("listings", filename).exists(), f"Missing existing saved-search test file: {filename}")
