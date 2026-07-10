from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_direct_import_migration_v177 as migration
from listings import listing_views_direct_import_migration_audit_v176 as audit_v176
from listings import listing_views_remaining_facade_surface_audit_v175 as surface_v175
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


class ListingViewsDirectImportMigrationV177Tests(SimpleTestCase):
    def test_v177_marker_is_declared(self):
        self.assertEqual(
            migration.LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_MARKER_V177,
            "LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_V177",
        )

    def test_v177_target_group_is_migrated_and_removed_by_v179(self):
        report = migration.build_report(Path("."))

        self.assertEqual(report.migrated_source_module, "listing_promotion_views")
        self.assertEqual(report.migrated_names, ("listing_feature_priority_update",))
        self.assertEqual(report.migrated_relative_path, "listings/urls.py")
        self.assertEqual(report.remaining_target_migration_records, 0)
        self.assertTrue(report.target_removed_from_facade)
        self.assertTrue(report.target_group_migrated)
        self.assertFalse(report.safe_to_remove_facade_reexport_in_v177)

    def test_v177_target_file_uses_dedicated_import_not_facade_dependency(self):
        target_path = migration.resolve_migrated_file_path(Path("."))
        text = target_path.read_text(encoding="utf-8")

        self.assertIn(migration.MIGRATED_IMPORT_V177, text)
        self.assertNotIn(f"views.{migration.MIGRATED_NAMES_V177[0]}", text)
        self.assertNotIn(
            f"from listings.views import {migration.MIGRATED_NAMES_V177[0]}",
            text,
        )
        self.assertNotIn(
            f"from .views import {migration.MIGRATED_NAMES_V177[0]}",
            text,
        )

    def test_v177_v176_audit_shows_migrated_name_removed_from_facade_after_v179(self):
        report = audit_v176.build_report(Path("."))

        self.assertEqual(report.names_without_migration_records, ())
        self.assertNotIn(migration.MIGRATED_NAMES_V177[0], report.protected_names)
        self.assertNotIn(migration.MIGRATED_NAMES_V177[0], report.migration_names)
        self.assertTrue(report.all_remaining_names_have_migration_paths)
        self.assertFalse(report.safe_to_change_imports_in_v176)

    def test_v177_v175_surface_no_longer_sees_removed_name_as_candidate_after_v179(self):
        report = surface_v175.build_report(Path("."))

        self.assertEqual(report.candidate_names, ())
        self.assertNotIn(migration.MIGRATED_NAMES_V177[0], report.protected_names)
        self.assertFalse(report.next_removal_candidate_available)
        self.assertFalse(report.safe_to_remove_anything_in_v175)

    def test_v177_source_module_remains_after_v179_facade_reexport_removal(self):
        views_text = migration.resolve_views_file_path(Path(".")).read_text(encoding="utf-8")
        runtime_facade = listing_views

        self.assertNotIn(migration.MIGRATED_NAMES_V177[0], views_text)
        self.assertFalse(hasattr(runtime_facade, migration.MIGRATED_NAMES_V177[0]))
        self.assertEqual(migration.build_report(Path(".")).views_total_lines, len(views_text.splitlines()))

    def test_v177_route_callback_identity_still_resolves_outside_views(self):
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

    def test_v177_markdown_documents_import_migration_and_no_removal_guardrail(self):
        report = migration.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_direct_import_migration_v177.md"
            migration.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(migration.LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_MARKER_V177, text)
        self.assertIn("Target removed from facade by v179: `True`", text)
        self.assertIn("Target group migrated: `True`", text)
        self.assertIn("Safe to remove facade re-export in v177: `False`", text)
        self.assertIn("v177 does not edit `backend/listings/views.py`", text)
        self.assertIn("v177 does not remove any facade re-export", text)
