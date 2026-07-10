from __future__ import annotations

from collections import defaultdict
from importlib import import_module
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_facade_closeout_audit_v180 as closeout
from listings import listing_feature_priority_reexport_removal_v179 as removal_v179


class ListingViewsFacadeCloseoutAuditV180Tests(SimpleTestCase):
    def test_v180_marker_is_declared(self):
        self.assertEqual(
            closeout.LISTING_VIEWS_FACADE_CLOSEOUT_AUDIT_MARKER_V180,
            "LISTING_VIEWS_FACADE_CLOSEOUT_AUDIT_V180",
        )

    def test_v180_report_confirms_closeout_complete(self):
        report = closeout.build_report(Path("."))

        self.assertTrue(report.closeout_complete)
        self.assertEqual(report.remaining_known_candidate_names, ())
        self.assertEqual(
            report.removed_target_name,
            closeout.REMOVED_FACADE_REEXPORT_NAME_V180,
        )
        self.assertTrue(report.target_absent_from_views_source)
        self.assertTrue(report.facade_reexport_import_absent)
        self.assertTrue(report.source_module_still_defines_target)
        self.assertTrue(report.urls_use_dedicated_import)
        self.assertTrue(report.urls_avoid_facade_import_for_target)
        self.assertTrue(report.views_line_count_within_closeout_limit)

    def test_v180_runtime_facade_does_not_reexport_removed_target(self):
        listing_views = import_module("listings.views")
        promotion_views = import_module("listings.listing_promotion_views")

        self.assertFalse(
            hasattr(listing_views, closeout.REMOVED_FACADE_REEXPORT_NAME_V180)
        )
        self.assertTrue(
            hasattr(promotion_views, closeout.REMOVED_FACADE_REEXPORT_NAME_V180)
        )
        self.assertIs(
            getattr(promotion_views, closeout.REMOVED_FACADE_REEXPORT_NAME_V180),
            promotion_views.listing_feature_priority_update,
        )

    def test_v180_public_route_uses_dedicated_source_callback(self):
        from listings import listing_promotion_views

        callbacks_by_name = defaultdict(list)

        def visit(patterns):
            for pattern in patterns:
                if isinstance(pattern, URLPattern):
                    if pattern.name:
                        callbacks_by_name[pattern.name].append(pattern.callback)
                elif isinstance(pattern, URLResolver):
                    visit(pattern.url_patterns)

        visit(get_resolver().url_patterns)
        callbacks = callbacks_by_name.get(
            closeout.REMOVED_FACADE_REEXPORT_NAME_V180,
            [],
        )

        self.assertTrue(callbacks)
        for callback in callbacks:
            self.assertIs(
                callback,
                listing_promotion_views.listing_feature_priority_update,
            )
            self.assertEqual(callback.__module__, "listings.listing_promotion_views")

    def test_v180_v179_removal_report_still_complete(self):
        report = removal_v179.build_report(Path("."))

        self.assertTrue(report.removal_complete)
        self.assertTrue(report.removed_from_facade_source)
        self.assertTrue(report.absent_from_runtime_facade)
        self.assertTrue(report.source_module_still_defines_name)
        self.assertTrue(report.urls_use_dedicated_import)

    def test_v180_markdown_documents_closeout_without_backend_docs_side_effect(self):
        from tempfile import TemporaryDirectory

        report = closeout.build_report(Path("."))

        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "listing_views_facade_closeout_audit_v180.md"
            closeout.write_markdown_report(output_path, report)
            text = output_path.read_text(encoding="utf-8")

        self.assertIn(closeout.LISTING_VIEWS_FACADE_CLOSEOUT_AUDIT_MARKER_V180, text)
        self.assertIn("Closeout complete: `True`", text)
        self.assertIn("Remaining known candidate names: `()`", text)
        self.assertFalse(Path("backend/docs").exists())
        self.assertFalse(Path("docs/listing_views_facade_closeout_audit_v180.md").exists())
