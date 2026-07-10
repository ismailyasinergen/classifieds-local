from __future__ import annotations

from collections import defaultdict
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_feature_priority_reexport_removal_v179 as removal
from listings import listing_promotion_views


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


class ListingFeaturePriorityReexportRemovalV179Tests(SimpleTestCase):
    def test_v179_marker_is_declared(self):
        self.assertEqual(
            removal.LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_MARKER_V179,
            "LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_V179",
        )

    def test_v179_removed_target_from_facade_but_kept_source_module(self):
        report = removal.build_report(Path("."))
        runtime_facade = import_module("listings.views")

        self.assertEqual(report.removed_name, "listing_feature_priority_update")
        self.assertTrue(report.removed_from_facade_source)
        self.assertTrue(report.absent_from_runtime_facade)
        self.assertFalse(hasattr(runtime_facade, report.removed_name))
        self.assertTrue(report.source_module_still_defines_name)
        self.assertTrue(hasattr(listing_promotion_views, report.removed_name))

    def test_v179_urls_keep_dedicated_import_and_route_to_source_object(self):
        report = removal.build_report(Path("."))
        callbacks = _callbacks_by_route_name().get("listing_feature_priority_update", [])

        self.assertTrue(report.urls_use_dedicated_import)
        self.assertTrue(report.urls_avoid_facade_import_for_target)
        self.assertTrue(callbacks)

        for callback in callbacks:
            self.assertIs(callback, listing_promotion_views.listing_feature_priority_update)
            self.assertEqual(callback.__module__, "listings.listing_promotion_views")

    def test_v179_prior_audits_are_updated_to_completed_removal_state(self):
        report = removal.build_report(Path("."))

        self.assertEqual(report.v175_candidate_names, ())
        self.assertEqual(report.v176_names_without_migration_records, ())
        self.assertTrue(report.v177_target_group_migrated)
        self.assertTrue(report.v178_contract_satisfied_by_v179)
        self.assertTrue(report.removal_complete)

    def test_v179_markdown_documents_completed_removal(self):
        report = removal.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_feature_priority_reexport_removal_v179.md"
            removal.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(removal.LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_MARKER_V179, text)
        self.assertIn("Removed facade re-export: `listing_feature_priority_update`", text)
        self.assertIn("Removed from facade source: `True`", text)
        self.assertIn("Absent from runtime facade: `True`", text)
        self.assertIn("Source module still defines name: `True`", text)
        self.assertIn("Removal complete: `True`", text)
