import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from listings.listing_detail_asset_boundary_v324 import (
    PLANNED_CSS_ASSET_V324,
    PLANNED_JS_ASSET_V324,
    V324_MARKER,
    audit_listing_detail_asset_boundary_v324,
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
        source = self.template_path.read_text(encoding="utf-8")

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

    def test_cutover_blockers_are_explicit_and_csp_is_not_overclaimed(self):
        self.assertEqual(len(self.report.inline_event_handlers), 2)
        self.assertEqual(
            {
                handler.attribute
                for handler in self.report.inline_event_handlers
            },
            {"onerror"},
        )
        self.assertGreaterEqual(len(self.report.source_contract_tests), 8)
        self.assertEqual(
            self.report.blocker_codes,
            (
                "inline-event-handlers",
                "legacy-source-contract-tests",
            ),
        )
        self.assertFalse(self.report.cutover_ready)
        self.assertFalse(self.report.strict_csp_ready)

    def test_known_source_contracts_are_discovered(self):
        self.assertIn(
            "listings/test_listing_gallery_lightbox_v318.py",
            self.report.source_contract_tests,
        )
        self.assertIn(
            "listings/test_listing_detail_accessibility_v322.py",
            self.report.source_contract_tests,
        )

    def test_text_and_json_commands_are_deterministic_and_read_only(self):
        text_output = StringIO()
        call_command("audit_listing_detail_assets_v324", stdout=text_output)
        rendered = text_output.getvalue()

        self.assertIn("styles=1 scripts=4", rendered)
        self.assertIn("template_dependent=0", rendered)
        self.assertIn("mechanically_extractable=true", rendered)
        self.assertIn("cutover_ready=false", rendered)
        self.assertIn("read_only=true", rendered)

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())

        self.assertEqual(payload["asset_block_count"], 5)
        self.assertEqual(payload["inline_event_handlers"][0]["tag"], "img")
        self.assertTrue(payload["read_only"])

    def test_fail_on_blockers_is_ci_compatible(self):
        with self.assertRaisesMessage(
            CommandError,
            "Listing-detail asset cutover blockers remain",
        ):
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
