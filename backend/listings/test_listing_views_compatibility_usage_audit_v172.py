from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_compatibility_usage_audit_v172 as audit
from listings import listing_views_facade_consolidation_audit_v171 as facade_v171
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


class ListingViewsCompatibilityUsageAuditV172Tests(SimpleTestCase):
    def test_v172_marker_is_declared(self):
        self.assertEqual(
            audit.LISTING_VIEWS_COMPATIBILITY_USAGE_AUDIT_MARKER_V172,
            "LISTING_VIEWS_COMPATIBILITY_USAGE_AUDIT_V172",
        )

    def test_v172_facade_inventory_matches_v171_surface(self):
        report = audit.build_report(Path("."))
        v171_report = facade_v171.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.top_level_definition_names, ())
        self.assertEqual(report.view_reexport_modules, v171_report.view_reexport_modules)
        self.assertEqual(report.view_reexport_names, v171_report.view_reexport_names)
        self.assertEqual(report.helper_reexport_modules, v171_report.helper_reexport_modules)
        self.assertEqual(report.helper_reexport_names, v171_report.helper_reexport_names)
        self.assertEqual(report.unexpected_import_modules, ())
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v172_detects_helper_compatibility_usage_dependencies(self):
        report = audit.build_report(Path("."))

        for helper_name in [
            "apply_listing_filters",
            "_create_moderation_notice",
            "default_listing_expiry",
            "active_approved_listings",
            "save_uploaded_listing_images",
            "validate_uploaded_images",
        ]:
            self.assertIn(helper_name, report.helper_names_with_usage)

        self.assertFalse(report.safe_to_remove_any_reexports_now)

    def test_v172_detects_url_facade_usage_for_public_route_callbacks(self):
        report = audit.build_report(Path("."))

        for callback_name in [
            "saved_search_list",
            "saved_search_create",
            "saved_search_bulk_action",
            "listing_report_create",
            "listing_report_queue",
            "listing_favorite_toggle",
            "listing_feature_toggle",
            "listing_archive",
            "listing_image_delete",
        ]:
            self.assertIn(callback_name, report.view_names_with_usage)

    def test_v172_dynamic_route_identity_still_uses_facade_reexports(self):
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

    def test_v172_usage_records_exclude_the_v172_audit_itself(self):
        report = audit.build_report(Path("."))

        for record in report.usage_records:
            self.assertNotIn("listing_views_compatibility_usage_audit_v172.py", record.relative_path)
            self.assertNotIn("test_listing_views_compatibility_usage_audit_v172.py", record.relative_path)

    def test_v172_markdown_documents_dependency_based_no_removal_guardrail(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_compatibility_usage_audit_v172.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.LISTING_VIEWS_COMPATIBILITY_USAGE_AUDIT_MARKER_V172, text)
        self.assertIn("Safe to remove any re-exports now: `False`", text)
        self.assertIn("Do not remove helper compatibility re-exports", text)
        self.assertIn("Do not remove `*_views` compatibility re-export paths", text)
        self.assertIn("only after this audit reports no source", text)
