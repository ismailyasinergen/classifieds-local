from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_views_direct_import_migration_audit_v176 as audit
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


class ListingViewsDirectImportMigrationAuditV176Tests(SimpleTestCase):
    def test_v176_marker_is_declared(self):
        self.assertEqual(
            audit.LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_AUDIT_MARKER_V176,
            "LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_AUDIT_V176",
        )

    def test_v176_audits_post_v175_surface_without_reintroducing_removed_targets(self):
        report = audit.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertLess(report.views_total_lines, 155)
        self.assertEqual(report.protected_name_count, 34)
        self.assertEqual(report.removed_v174_names_present, ())
        self.assertEqual(
            report.removed_v174_names_absent,
            ("SidebarCategoriesMixin", "_safe_reporter_note"),
        )
        self.assertTrue(report.v174_targeted_removal_is_preserved)

    def test_v176_inventory_matches_v175_remaining_surface(self):
        report = audit.build_report(Path("."))
        v175_report = surface_v175.build_report(Path("."))

        self.assertEqual(report.protected_names, v175_report.protected_names)
        self.assertEqual(report.view_reexport_modules, v175_report.view_reexport_modules)
        self.assertEqual(report.view_reexport_names, v175_report.view_reexport_names)
        self.assertEqual(report.helper_reexport_names, v175_report.helper_reexport_names)

    def test_v176_maps_every_remaining_facade_name_after_v179_removal(self):
        report = audit.build_report(Path("."))

        self.assertGreaterEqual(report.migration_record_count, 33)
        self.assertEqual(report.names_without_migration_records, ())
        self.assertEqual(report.names_migrated_after_v176, ())
        self.assertEqual(
            report.names_removed_after_v177_migration,
            ("listing_feature_priority_update",),
        )
        self.assertTrue(report.all_remaining_names_have_migration_paths)
        self.assertTrue(report.all_unmigrated_names_still_have_migration_paths)
        self.assertTrue(report.v179_removed_names_are_absent_from_migration_records)
        self.assertNotIn("listing_feature_priority_update", report.protected_names)
        self.assertNotIn("listing_feature_priority_update", report.migration_names)
        self.assertFalse(report.safe_to_change_imports_in_v176)

    def test_v176_migration_records_target_dedicated_modules_not_views(self):
        report = audit.build_report(Path("."))

        for record in report.migration_records:
            self.assertNotEqual(record.source_module, "views")
            self.assertNotIn("listings.views", record.migration_import)
            self.assertTrue(record.migration_import.startswith("from listings."))
            self.assertIn(record.source_kind, {"view_reexport", "helper_reexport"})

    def test_v176_preserves_facade_only_import_hygiene(self):
        report = audit.build_report(Path("."))

        self.assertTrue(report.is_facade_only)
        self.assertTrue(report.has_import_hygiene)
        self.assertEqual(report.top_level_definition_names, ())
        self.assertEqual(report.unexpected_import_modules, ())
        self.assertEqual(report.wildcard_import_modules, ())

    def test_v176_route_callback_identity_still_resolves_outside_views(self):
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

    def test_v176_markdown_documents_migration_paths_and_no_change_guardrail(self):
        report = audit.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_views_direct_import_migration_audit_v176.md"
            audit.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(audit.LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_AUDIT_MARKER_V176, text)
        self.assertIn("Migration records", text)
        self.assertIn("All remaining names have migration paths: `True`", text)
        self.assertIn("Names removed after v177 migration: `('listing_feature_priority_update',)`", text)
        self.assertIn("v179 removed names absent from migration records: `True`", text)
        self.assertIn("Safe to change imports in v176: `False`", text)
        self.assertIn("v176 is audit-only", text)
        self.assertIn("Do not change imports in v176", text)
        self.assertIn("Do not edit `backend/listings/views.py` in v176", text)
