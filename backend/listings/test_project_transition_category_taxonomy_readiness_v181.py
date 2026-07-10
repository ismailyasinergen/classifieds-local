from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from listings import project_transition_category_taxonomy_readiness_v181 as readiness
from listings import listing_views_facade_closeout_audit_v180 as closeout_v180


class ProjectTransitionCategoryTaxonomyReadinessV181Tests(SimpleTestCase):
    def test_v181_marker_is_declared(self):
        self.assertEqual(
            readiness.PROJECT_TRANSITION_CATEGORY_TAXONOMY_READINESS_MARKER_V181,
            "PROJECT_TRANSITION_CATEGORY_TAXONOMY_READINESS_V181",
        )

    def test_v181_recommends_category_taxonomy_as_next_feature_area(self):
        report = readiness.build_report(Path("."))

        self.assertEqual(report.recommended_next_feature_area, "category_taxonomy")
        self.assertEqual(
            report.recommended_next_checkpoint,
            "v182-category-hierarchy-model-admin-safeguards",
        )
        self.assertTrue(report.implementation_should_start_after_v181)
        self.assertTrue(report.v182_should_include_model_or_admin_safeguards)
        self.assertTrue(report.v183_should_include_seed_data)
        self.assertTrue(report.v184_should_include_navigation_and_filters)

    def test_v181_confirms_transition_baseline_after_v180_closeout(self):
        v180_report = closeout_v180.build_report(Path("."))
        v181_report = readiness.build_report(Path("."))

        self.assertTrue(v180_report.closeout_complete)
        self.assertTrue(v181_report.v180_closeout_module_present)
        self.assertTrue(v181_report.transition_audit_complete)

    def test_v181_category_model_baseline_is_present(self):
        report = readiness.build_report(Path("."))

        self.assertTrue(report.category_model_exists)
        self.assertTrue(report.category_model_has_category_class)
        self.assertTrue(report.category_model_has_name_field)
        self.assertTrue(report.category_model_has_slug_field)
        self.assertNotEqual(report.category_model_path, "")

    def test_v181_listing_model_is_already_category_aware(self):
        report = readiness.build_report(Path("."))

        self.assertTrue(report.listing_model_has_category_reference)
        self.assertNotEqual(report.listing_model_path, "")
        self.assertTrue(
            report.category_taxonomy_touches_listing_create_update
            or report.category_taxonomy_touches_browse_filters
        )

    def test_v181_records_marketplace_touchpoints_without_changing_production(self):
        report = readiness.build_report(Path("."))

        self.assertIsInstance(report.category_taxonomy_touches_listing_create_update, bool)
        self.assertIsInstance(report.category_taxonomy_touches_browse_filters, bool)
        self.assertIsInstance(report.category_taxonomy_touches_saved_searches, bool)
        self.assertIsInstance(report.category_taxonomy_touches_seller_store_tabs, bool)

    def test_v181_markdown_documents_transition_without_backend_docs_side_effect(self):
        report = readiness.build_report(Path("."))

        with TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "project_transition_category_taxonomy_readiness_v181.md"
            readiness.write_markdown_report(output_path, report)
            text = output_path.read_text(encoding="utf-8")

        self.assertIn(readiness.PROJECT_TRANSITION_CATEGORY_TAXONOMY_READINESS_MARKER_V181, text)
        self.assertIn("Recommended next feature area: `category_taxonomy`", text)
        self.assertIn("v182-category-hierarchy-model-admin-safeguards", text)
        self.assertIn("v181 is audit-only", text)
        self.assertFalse(Path("backend/docs").exists())
