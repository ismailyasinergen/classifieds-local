from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_uncategorized_views
from listings import listing_reports_views
from listings import listing_views_facade_consolidation_audit_v171 as facade_v171
from listings import listing_views_targeted_removal_contract_v173 as contract
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


class ListingViewsTargetedRemovalContractV173Tests(SimpleTestCase):
    def test_v173_marker_is_declared(self):
        self.assertEqual(
            contract.LISTING_VIEWS_TARGETED_REMOVAL_CONTRACT_MARKER_V173,
            "LISTING_VIEWS_TARGETED_REMOVAL_CONTRACT_V173",
        )

    def test_v173_candidate_names_are_exactly_the_frozen_v172_unused_pair(self):
        report = contract.build_report(Path("."))

        self.assertEqual(
            report.candidate_names,
            ("SidebarCategoriesMixin", "_safe_reporter_note"),
        )
        self.assertEqual(report.candidate_names_present_in_facade, report.candidate_names)
        self.assertEqual(report.candidate_names_missing_from_facade, ())

    def test_v173_facade_surface_still_matches_v171_before_any_removal(self):
        report = contract.build_report(Path("."))
        v171_report = facade_v171.build_report(Path("."))

        self.assertEqual(report.view_reexport_modules, v171_report.view_reexport_modules)
        self.assertEqual(report.view_reexport_names, v171_report.view_reexport_names)
        self.assertEqual(report.helper_reexport_modules, v171_report.helper_reexport_modules)
        self.assertEqual(report.helper_reexport_names, v171_report.helper_reexport_names)
        self.assertEqual(report.unexpected_import_modules, ())
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v173_candidates_are_still_identity_preserved_until_future_removal(self):
        self.assertIs(
            listing_views.SidebarCategoriesMixin,
            listing_uncategorized_views.SidebarCategoriesMixin,
        )
        self.assertIs(
            listing_views._safe_reporter_note,
            listing_reports_views._safe_reporter_note,
        )

    def test_v173_detects_no_target_facade_dependencies(self):
        report = contract.build_report(Path("."))

        self.assertEqual(report.target_facade_dependency_records, ())
        self.assertTrue(report.eligible_for_future_targeted_removal_checkpoint)
        self.assertFalse(report.safe_to_remove_in_v173)

    def test_v173_plain_references_are_informational_not_blocking(self):
        report = contract.build_report(Path("."))

        self.assertGreater(len(report.target_informational_plain_reference_records), 0)
        self.assertTrue(report.eligible_for_future_targeted_removal_checkpoint)

    def test_v173_non_candidate_facade_names_remain_protected(self):
        report = contract.build_report(Path("."))

        self.assertIn("ListingListView", report.protected_non_candidate_names)
        self.assertIn("saved_search_list", report.protected_non_candidate_names)
        self.assertIn("listing_report_queue", report.protected_non_candidate_names)
        self.assertIn("apply_listing_filters", report.protected_non_candidate_names)
        self.assertIn("validate_uploaded_images", report.protected_non_candidate_names)

    def test_v173_route_callback_identity_still_resolves_outside_views(self):
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

    def test_v173_markdown_documents_contract_only_no_removal_guardrail(self):
        report = contract.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_targeted_removal_contract_v173.md"
            contract.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(contract.LISTING_VIEWS_TARGETED_REMOVAL_CONTRACT_MARKER_V173, text)
        self.assertIn("v173 does not remove either candidate", text)
        self.assertIn("Do not remove `SidebarCategoriesMixin` or `_safe_reporter_note` in v173", text)
        self.assertIn("Plain references are informational only", text)
        self.assertIn("Eligible for future targeted removal checkpoint: `True`", text)
        self.assertIn("Safe to remove in v173: `False`", text)
