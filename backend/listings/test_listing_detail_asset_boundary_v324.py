import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase

from listings.listing_detail_asset_boundary_v324 import (
    PLANNED_CSS_ASSET_V324,
    PLANNED_JS_ASSET_V324,
    V324_MARKER,
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    read_listing_detail_contract_source_v325,
)


class ListingDetailAssetBoundaryV324Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.template_path = (
            cls.backend_dir
            / "listings"
            / "templates"
            / "listings"
            / "listing_detail.html"
        )
        cls.report = audit_listing_detail_asset_boundary_v324(
            template_path=cls.template_path,
            backend_dir=cls.backend_dir,
        )

    def test_v324_marker_and_planned_asset_paths_are_stable(self):
        source = read_listing_detail_contract_source_v325(
            self.backend_dir,
        )

        self.assertIn(V324_MARKER, source)
        self.assertEqual(
            PLANNED_CSS_ASSET_V324,
            "listings/listing-detail-v324.css",
        )
        self.assertEqual(
            PLANNED_JS_ASSET_V324,
            "listings/listing-detail-v324.js",
        )

    def test_current_inline_assets_are_template_independent(self):
        self.assertEqual(len(self.report.style_blocks), 1)
        self.assertEqual(len(self.report.script_blocks), 4)
        self.assertEqual(len(self.report.asset_blocks), 5)
        self.assertEqual(self.report.template_dependent_block_count, 0)
        self.assertTrue(self.report.mechanically_extractable)

        for block in self.report.asset_blocks:
            with self.subTest(kind=block.kind, index=block.index):
                self.assertFalse(block.contains_template_syntax)
                self.assertGreater(block.character_count, 100)
                self.assertGreaterEqual(block.end_line, block.start_line)

    def test_asset_marker_ownership_is_inventoried(self):
        style_markers = set(self.report.style_blocks[0].markers)

        self.assertTrue(
            {
                "LISTING_DETAIL_GALLERY_INTERACTION_V63",
                "LISTING_DETAIL_CONTACT_SAFETY_V66",
                "LISTING_PRICE_HISTORY_V275",
                "LISTING_GALLERY_LIGHTBOX_V318",
                "LISTING_LOCATION_ACTIONS_V319",
                "MOBILE_LISTING_BUYER_ACTION_BAR_V321",
                "LISTING_DETAIL_ACCESSIBILITY_V322",
            }.issubset(style_markers)
        )
        self.assertIn(V324_MARKER, self.report.template_markers)

    def test_v325_clears_cutover_blockers_without_overclaiming_csp(self):
        self.assertEqual(self.report.inline_event_handlers, ())
        self.assertEqual(self.report.source_contract_tests, ())
        self.assertGreaterEqual(
            len(self.report.asset_aware_source_tests),
            8,
        )
        self.assertEqual(self.report.blocker_codes, ())
        self.assertTrue(self.report.cutover_ready)
        self.assertGreater(len(self.report.inline_style_attributes), 0)
        self.assertFalse(self.report.strict_csp_ready)

    def test_known_source_contracts_are_asset_aware(self):
        self.assertIn(
            "listings/test_listing_gallery_lightbox_v318.py",
            self.report.asset_aware_source_tests,
        )
        self.assertIn(
            "listings/test_listing_detail_accessibility_v322.py",
            self.report.asset_aware_source_tests,
        )

    def test_text_and_json_commands_are_deterministic_and_read_only(self):
        text_output = StringIO()
        call_command("audit_listing_detail_assets_v324", stdout=text_output)
        rendered = text_output.getvalue()

        self.assertIn("styles=1 scripts=4", rendered)
        self.assertIn("template_dependent=0", rendered)
        self.assertIn("mechanically_extractable=true", rendered)
        self.assertIn("cutover_ready=true", rendered)
        self.assertIn("read_only=true", rendered)

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())

        self.assertEqual(payload["asset_block_count"], 5)
        self.assertEqual(payload["inline_event_handlers"], [])
        self.assertGreater(len(payload["inline_style_attributes"]), 0)
        self.assertEqual(payload["source_contract_tests"], [])
        self.assertTrue(payload["read_only"])

    def test_fail_on_blockers_succeeds_after_v325_remediation(self):
        call_command(
            "audit_listing_detail_assets_v324",
            fail_on_blockers=True,
            stdout=StringIO(),
            stderr=StringIO(),
        )

    def test_v324_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v324*.py"
                )
            )

        self.assertEqual(matches, [])
