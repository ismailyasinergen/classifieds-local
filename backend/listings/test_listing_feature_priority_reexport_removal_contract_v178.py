from __future__ import annotations

from collections import defaultdict
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

from listings import listing_feature_priority_reexport_removal_contract_v178 as contract
from listings import listing_promotion_views
from listings import listing_views_direct_import_migration_audit_v176 as audit_v176
from listings import listing_views_direct_import_migration_v177 as migration_v177
from listings import listing_views_remaining_facade_surface_audit_v175 as surface_v175


def _runtime_listing_views_module():
    return import_module("listings.views")


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


class ListingFeaturePriorityReexportRemovalContractV178Tests(SimpleTestCase):
    def test_v178_marker_is_declared(self):
        self.assertEqual(
            contract.LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_CONTRACT_MARKER_V178,
            "LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_CONTRACT_V178",
        )

    def test_v178_freezes_exact_target_and_source_module(self):
        report = contract.build_report(Path("."))

        self.assertEqual(report.target_name, "listing_feature_priority_update")
        self.assertEqual(report.target_source_module, "listing_promotion_views")
        self.assertEqual(report.target_migrated_relative_path, "listings/urls.py")
        self.assertEqual(
            report.target_dedicated_import,
            "from listings.listing_promotion_views import listing_feature_priority_update",
        )

    def test_v178_contract_confirms_v177_migration_state(self):
        report = contract.build_report(Path("."))

        self.assertTrue(report.target_dependency_cleared_by_v177)
        self.assertTrue(report.target_is_only_v175_candidate)
        self.assertTrue(report.target_is_only_v176_missing_migration_name)
        self.assertTrue(report.v177_target_group_migrated)
        self.assertFalse(report.v177_safe_to_remove_facade_reexport)
        self.assertEqual(report.target_migration_record_count_after_v177, 0)

    def test_v178_contract_keeps_facade_reexport_and_source_object(self):
        report = contract.build_report(Path("."))

        self.assertEqual(report.views_path, "listings/views.py")
        self.assertEqual(report.views_total_lines, 155)
        self.assertTrue(report.target_still_reexported_by_facade)
        self.assertTrue(report.target_source_module_defines_name)
        runtime_facade = _runtime_listing_views_module()

        self.assertTrue(hasattr(runtime_facade, report.target_name))
        self.assertIs(
            getattr(runtime_facade, report.target_name),
            getattr(listing_promotion_views, report.target_name),
        )

    def test_v178_contract_ready_but_no_removal_allowed_in_v178(self):
        report = contract.build_report(Path("."))

        self.assertTrue(report.contract_ready_for_later_removal)
        self.assertFalse(report.safe_to_remove_in_v178)
        self.assertIn("v179", report.recommended_next_checkpoint)
        self.assertIn("listing_feature_priority_update", report.recommended_next_checkpoint)

    def test_v178_v175_v176_v177_reports_remain_consistent(self):
        v175_report = surface_v175.build_report(Path("."))
        v176_report = audit_v176.build_report(Path("."))
        v177_report = migration_v177.build_report(Path("."))

        self.assertEqual(v175_report.candidate_names, ("listing_feature_priority_update",))
        self.assertEqual(
            v176_report.names_without_migration_records,
            ("listing_feature_priority_update",),
        )
        self.assertTrue(v177_report.target_group_migrated)
        self.assertEqual(v177_report.migrated_names, ("listing_feature_priority_update",))
        self.assertFalse(v177_report.safe_to_remove_facade_reexport_in_v177)

    def test_v178_route_uses_dedicated_function_object_while_facade_still_matches_identity(self):
        callbacks_by_name = _callbacks_by_route_name()
        callbacks = callbacks_by_name.get("listing_feature_priority_update", [])

        self.assertTrue(callbacks, "listing_feature_priority_update route should exist")

        dedicated_object = listing_promotion_views.listing_feature_priority_update
        runtime_facade = _runtime_listing_views_module()
        facade_object = getattr(runtime_facade, contract.TARGET_FACADE_REEXPORT_NAME_V178)

        for callback in callbacks:
            self.assertIs(callback, dedicated_object)
            self.assertIs(callback, facade_object)
            self.assertEqual(callback.__module__, "listings.listing_promotion_views")

    def test_v178_urls_source_uses_dedicated_import_not_facade_import_for_target(self):
        app_root = contract._resolve_app_root(Path("."))
        urls_text = (app_root / "listings" / "urls.py").read_text(encoding="utf-8")

        self.assertIn(contract.TARGET_DEDICATED_IMPORT_V178, urls_text)
        self.assertNotIn(
            "from .views import listing_feature_priority_update",
            urls_text,
        )
        self.assertNotIn(
            "from listings.views import listing_feature_priority_update",
            urls_text,
        )

    def test_v178_markdown_documents_contract_and_no_removal_guardrail(self):
        report = contract.build_report(Path("."))

        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "listing_feature_priority_reexport_removal_contract_v178.md"
            contract.write_markdown_report(output, report)
            text = output.read_text(encoding="utf-8")

        self.assertIn(contract.LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_CONTRACT_MARKER_V178, text)
        self.assertIn("Target facade re-export: `listing_feature_priority_update`", text)
        self.assertIn("Contract ready for later removal: `True`", text)
        self.assertIn("Safe to remove in v178: `False`", text)
        self.assertIn("v178 is a contract-only checkpoint", text)
        self.assertIn("Do not edit `backend/listings/views.py` in v178", text)
        self.assertIn("Do not remove `listing_feature_priority_update` from the facade in v178", text)
