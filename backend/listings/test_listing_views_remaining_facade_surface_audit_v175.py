from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_remaining_facade_surface_audit_v175 as audit
from listings import listing_views_targeted_reexport_removal_v174 as removal_v174
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


class ListingViewsRemainingFacadeSurfaceAuditV175Tests(SimpleTestCase):
    def test_v175_marker_is_declared(self):
        self.assertEqual(
            audit.LISTING_VIEWS_REMAINING_FACADE_SURFACE_AUDIT_MARKER_V175,
            "LISTING_VIEWS_REMAINING_FACADE_SURFACE_AUDIT_V175",
        )

    def test_v175_audits_post_v174_facade_surface_without_reintroducing_targets(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.views_total_lines, 155)
        self.assertEqual(report.removed_v174_names_present, ())
        self.assertEqual(
            report.removed_v174_names_absent,
            ("SidebarCategoriesMixin", "_safe_reporter_note"),
        )
        self.assertTrue(report.v174_targeted_removal_is_preserved)

    def test_v175_inventory_matches_v174_expected_remaining_surface(self):
        report = audit.build_report(Path("."))
        v174_report = removal_v174.build_report(Path("."))

        self.assertEqual(report.protected_names, v174_report.current_protected_names)
        self.assertEqual(report.view_reexport_modules, v174_report.view_reexport_modules)
        self.assertEqual(report.view_reexport_names, v174_report.view_reexport_names)
        self.assertEqual(report.helper_reexport_names, v174_report.helper_reexport_names)

    def test_v175_preserves_facade_only_import_hygiene(self):
        report = audit.build_report(Path("."))

        self.assertTrue(report.is_facade_only)
        self.assertTrue(report.has_import_hygiene)
        self.assertEqual(report.top_level_definition_names, ())
        self.assertEqual(report.unexpected_import_modules, ())
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v175_records_zero_candidates_and_all_remaining_names_are_still_dependencies(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.protected_name_count, 35)
        self.assertEqual(report.candidate_count, 0)
        self.assertEqual(report.candidate_names, ())
        self.assertFalse(report.next_removal_candidate_available)
        self.assertTrue(report.all_remaining_names_have_facade_dependencies)
        self.assertFalse(report.safe_to_remove_anything_in_v175)

        self.assertEqual(set(report.dependency_names), set(report.protected_names))

    def test_v175_dependency_records_only_reference_remaining_protected_names(self):
        report = audit.build_report(Path("."))
        protected_names = set(report.protected_names)

        for record in report.dependency_records:
            self.assertIn(record.name, protected_names | {"*"})

    def test_v175_route_callback_identity_still_resolves_outside_views(self):
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

    def test_v175_markdown_documents_candidates_and_no_removal_guardrail(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_remaining_facade_surface_audit_v175.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.LISTING_VIEWS_REMAINING_FACADE_SURFACE_AUDIT_MARKER_V175, text)
        self.assertIn("Candidate names without detected facade dependencies", text)
        self.assertIn("No next removal candidates were detected.", text)
        self.assertIn("Next removal candidate available: `False`", text)
        self.assertIn("All remaining names have facade dependencies: `True`", text)
        self.assertIn("Safe to remove anything in v175: `False`", text)
        self.assertIn("v175 is audit-only", text)
        self.assertIn("A later checkpoint may target a candidate only after a dedicated contract freezes it first", text)
