from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_filter_helpers
from listings import listing_image_helpers
from listings import listing_lifecycle_helpers
from listings import listing_moderation_helpers
from listings import listing_views_facade_consolidation_audit_v171 as audit
from listings import listing_views_import_cleanup_v170 as cleanup_v170
from listings import listing_visibility_helpers
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


class ListingViewsFacadeConsolidationAuditV171Tests(SimpleTestCase):
    def test_v171_marker_is_declared(self):
        self.assertEqual(
            audit.LISTING_VIEWS_FACADE_CONSOLIDATION_AUDIT_MARKER_V171,
            "LISTING_VIEWS_FACADE_CONSOLIDATION_AUDIT_V171",
        )

    def test_v171_views_py_remains_facade_only(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.top_level_definition_names, ())
        self.assertTrue(report.is_facade_only)
        self.assertTrue(report.has_only_approved_reexports)
        self.assertEqual(report.unexpected_import_modules, ())

    def test_v171_protected_view_reexports_match_v170_cleanup_surface(self):
        report = audit.build_report(Path("."))
        v170_report = cleanup_v170.build_report(Path("."))

        self.assertEqual(report.view_reexport_modules, v170_report.compatibility_view_reexport_modules)
        self.assertEqual(report.view_reexport_names, v170_report.compatibility_view_reexport_names)
        self.assertEqual(report.missing_view_reexport_modules, ())

    def test_v171_protected_helper_reexports_match_v170_cleanup_surface(self):
        report = audit.build_report(Path("."))
        v170_report = cleanup_v170.build_report(Path("."))

        self.assertEqual(report.helper_reexport_modules, v170_report.helper_compatibility_reexport_modules)
        self.assertEqual(report.helper_reexport_names, v170_report.helper_compatibility_reexport_names)
        self.assertEqual(report.missing_helper_reexport_names, ())

    def test_v171_helper_reexports_are_still_identity_preserved(self):
        self.assertIs(listing_views.apply_listing_filters, listing_filter_helpers.apply_listing_filters)
        self.assertIs(listing_views._create_moderation_notice, listing_moderation_helpers._create_moderation_notice)
        self.assertIs(listing_views.default_listing_expiry, listing_lifecycle_helpers.default_listing_expiry)
        self.assertIs(listing_views.active_approved_listings, listing_visibility_helpers.active_approved_listings)
        self.assertIs(listing_views.save_uploaded_listing_images, listing_image_helpers.save_uploaded_listing_images)
        self.assertIs(listing_views.validate_uploaded_images, listing_image_helpers.validate_uploaded_images)

    def test_v171_url_callbacks_still_resolve_through_non_views_modules(self):
        callbacks_by_name = _callbacks_by_route_name()
        matched_route_names: list[str] = []

        for route_name, callbacks in callbacks_by_name.items():
            for callback in callbacks:
                callback_name = getattr(callback, "__name__", "")
                if not callback_name or not hasattr(listing_views, callback_name):
                    continue

                reexported_callback = getattr(listing_views, callback_name)
                if reexported_callback is not callback:
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

    def test_v171_has_no_wildcard_imports(self):
        report = audit.build_report(Path("."))

        self.assertTrue(report.has_no_wildcard_imports)
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v171_markdown_documents_no_removal_yet_guardrail(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_facade_consolidation_audit_v171.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.LISTING_VIEWS_FACADE_CONSOLIDATION_AUDIT_MARKER_V171, text)
        self.assertIn("Do not remove helper compatibility re-exports", text)
        self.assertIn("Do not remove `*_views` compatibility re-export paths", text)
        self.assertIn("A future checkpoint must first prove", text)
