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
from listings import listing_views_import_cleanup_contract_v169 as contract_v169
from listings import listing_views_import_cleanup_v170 as cleanup
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


class ListingViewsImportCleanupV170Tests(SimpleTestCase):
    def test_v170_marker_is_declared(self):
        self.assertEqual(
            cleanup.LISTING_VIEWS_IMPORT_CLEANUP_MARKER_V170,
            "LISTING_VIEWS_IMPORT_CLEANUP_V170",
        )

    def test_v170_views_py_is_facade_only_with_only_compatibility_reexports(self):
        report = cleanup.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.top_level_definition_names, ())
        self.assertTrue(report.is_facade_only)
        self.assertTrue(report.has_only_compatibility_reexports)
        self.assertEqual(report.non_compatibility_import_modules, ())

    def test_v170_preserves_v169_protected_view_reexport_surface(self):
        report = cleanup.build_report(Path("."))

        self.assertEqual(
            report.compatibility_view_reexport_modules,
            contract_v169.SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_MODULES_V169,
        )
        self.assertEqual(
            report.compatibility_view_reexport_names,
            contract_v169.SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_NAMES_V169,
        )
        self.assertEqual(report.missing_expected_view_reexport_modules, ())

    def test_v170_preserves_legacy_helper_compatibility_reexports(self):
        report = cleanup.build_report(Path("."))

        self.assertEqual(report.missing_expected_helper_reexport_names, ())
        self.assertIs(listing_views.apply_listing_filters, listing_filter_helpers.apply_listing_filters)
        self.assertIs(
            listing_views._create_moderation_notice,
            listing_moderation_helpers._create_moderation_notice,
        )
        self.assertIs(
            listing_views.default_listing_expiry,
            listing_lifecycle_helpers.default_listing_expiry,
        )
        self.assertIs(
            listing_views.active_approved_listings,
            listing_visibility_helpers.active_approved_listings,
        )
        self.assertIs(
            listing_views.save_uploaded_listing_images,
            listing_image_helpers.save_uploaded_listing_images,
        )
        self.assertIs(
            listing_views.validate_uploaded_images,
            listing_image_helpers.validate_uploaded_images,
        )

    def test_v170_has_no_wildcard_imports(self):
        report = cleanup.build_report(Path("."))

        self.assertTrue(report.has_no_wildcard_imports)
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v170_public_url_callbacks_still_resolve_through_non_views_modules(self):
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

                self.assertNotEqual(
                    getattr(callback, "__module__", ""),
                    "listings.views",
                    f"{route_name} unexpectedly resolves to an object defined in listings.views",
                )

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

    def test_v170_markdown_documents_cleanup_and_guardrails(self):
        report = cleanup.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_import_cleanup_v170.md"
            cleanup.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(cleanup.LISTING_VIEWS_IMPORT_CLEANUP_MARKER_V170, text)
        self.assertIn("Only compatibility re-exports remain: `True`", text)
        self.assertIn("No runtime code was moved", text)
        self.assertIn("Legacy helper compatibility re-exports", text)
