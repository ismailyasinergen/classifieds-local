from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_reports_views
from listings import listing_uncategorized_views
from listings import listing_views_targeted_reexport_removal_v174 as removal
from listings import listing_views_targeted_removal_contract_v173 as contract_v173
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


class ListingViewsTargetedReexportRemovalV174Tests(SimpleTestCase):
    def test_v174_marker_is_declared(self):
        self.assertEqual(
            removal.LISTING_VIEWS_TARGETED_REEXPORT_REMOVAL_MARKER_V174,
            "LISTING_VIEWS_TARGETED_REEXPORT_REMOVAL_V174",
        )

    def test_v174_removed_exactly_the_target_pair_from_facade(self):
        report = removal.build_report(Path("."))

        self.assertTrue(report.removed_exactly_target_pair)
        self.assertEqual(report.target_names_present_in_facade, ())
        self.assertEqual(
            report.target_names_absent_from_facade,
            ("SidebarCategoriesMixin", "_safe_reporter_note"),
        )
        self.assertEqual(report.missing_expected_remaining_names, ())
        self.assertEqual(report.unexpected_remaining_names, ())

    def test_v174_does_not_remove_source_module_objects(self):
        self.assertFalse(hasattr(listing_views, "SidebarCategoriesMixin"))
        self.assertFalse(hasattr(listing_views, "_safe_reporter_note"))

        self.assertTrue(hasattr(listing_uncategorized_views, "SidebarCategoriesMixin"))
        self.assertTrue(hasattr(listing_reports_views, "_safe_reporter_note"))

    def test_v174_preserves_facade_import_hygiene_and_helpers(self):
        report = removal.build_report(Path("."))

        self.assertTrue(report.preserved_facade_only_state)
        self.assertTrue(report.preserved_import_hygiene)
        self.assertTrue(report.preserved_helper_reexports)
        self.assertEqual(report.view_reexport_modules, removal.EXPECTED_VIEW_REEXPORT_MODULES_V174)
        self.assertEqual(report.helper_reexport_names, removal.EXPECTED_HELPER_REEXPORT_NAMES_V174)

    def test_v174_v173_contract_is_satisfied_after_targeted_removal(self):
        report = contract_v173.build_report(Path("."))

        self.assertEqual(report.target_facade_dependency_records, ())
        self.assertEqual(report.candidate_names_present_in_facade, ())
        self.assertEqual(
            report.candidate_names_missing_from_facade,
            ("SidebarCategoriesMixin", "_safe_reporter_note"),
        )
        self.assertTrue(report.targeted_removal_completed_in_v174)
        self.assertFalse(report.safe_to_remove_in_v173)

    def test_v174_route_callback_identity_still_resolves_outside_views(self):
        callbacks_by_name = _callbacks_by_route_name()
        matched_route_names: list[str] = []

        for route_name, callbacks in callbacks_by_name.items():
            for callback in callbacks:
                callback_name = getattr(callback, "__name__", "")
                if not callback_name or not hasattr(listing_views, callback_name):
                    continue

                if getattr(listing_views, callback_name) is not callback:
                    continue

                matched_route_names.append(route_name)
                self.assertNotEqual(getattr(callback, "__module__", ""), "listings.views")

        for route_name in [
            "saved_search_list",
            "saved_search_create",
            "saved_search_bulk_action",
            "report_queue",
            "listing_report",
            "listing_favorite_toggle",
            "listing_feature_toggle",
            "listing_archive",
            "listing_image_delete",
        ]:
            self.assertIn(route_name, matched_route_names)

    def test_v174_markdown_documents_targeted_removal(self):
        report = removal.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_targeted_reexport_removal_v174.md"
            removal.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(removal.LISTING_VIEWS_TARGETED_REEXPORT_REMOVAL_MARKER_V174, text)
        self.assertIn("Removed exactly target pair: `True`", text)
        self.assertIn("`SidebarCategoriesMixin` remains defined/exported by `listing_uncategorized_views`", text)
        self.assertIn("`_safe_reporter_note` remains defined/exported by `listing_reports_views`", text)
