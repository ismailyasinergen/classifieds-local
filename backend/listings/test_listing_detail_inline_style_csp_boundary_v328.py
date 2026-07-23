import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase

from listings.listing_detail_asset_boundary_v324 import (
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    LISTING_DETAIL_TEMPLATE_PATH_V325,
    read_listing_detail_contract_source_v325,
)


V328_MARKER = "LISTING_DETAIL_INLINE_STYLE_CSP_BOUNDARY_V328"


class ListingDetailInlineStyleCspBoundaryV328Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.template_path = (
            cls.backend_dir / LISTING_DETAIL_TEMPLATE_PATH_V325
        )
        cls.template_source = cls.template_path.read_text(
            encoding="utf-8"
        )
        cls.contract_source = read_listing_detail_contract_source_v325(
            cls.backend_dir,
        )
        cls.report = audit_listing_detail_asset_boundary_v324(
            template_path=cls.template_path,
            backend_dir=cls.backend_dir,
        )

    def test_v328_marker_and_template_inline_style_cleanup_are_packaged(self):
        self.assertIn(V328_MARKER, self.template_source)
        self.assertNotIn(" style=", self.template_source.lower())
        self.assertEqual(self.report.inline_style_attributes, ())

    def test_replacement_classes_have_stable_template_cardinality(self):
        self.assertEqual(
            self.template_source.count("listing-comparison-layout-v328"),
            1,
        )
        self.assertEqual(
            self.template_source.count(
                "classified-section-panel-spaced-v328"
            ),
            3,
        )

    def test_static_css_preserves_all_former_inline_declarations(self):
        for fragment in (
            ".listing-comparison-layout-v328 {",
            "display: flex;",
            "gap: 8px;",
            "align-items: center;",
            "flex-wrap: wrap;",
            "margin-top: 10px;",
            ".classified-section-panel-spaced-v328 {",
            "margin-top: 12px;",
            "border-top: 1px solid #ddd;",
            "border-radius: 4px;",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.contract_source)

        self.assertIn(V328_MARKER, self.contract_source)
        self.assertGreater(
            self.contract_source.rindex(
                ".classified-section-panel-spaced-v328 {"
            ),
            self.contract_source.rindex(".classified-section-panel {"),
        )

    def test_listing_template_owned_csp_boundary_is_ready(self):
        self.assertEqual(self.report.style_blocks, ())
        self.assertEqual(self.report.script_blocks, ())
        self.assertEqual(self.report.inline_event_handlers, ())
        self.assertEqual(self.report.inline_style_attributes, ())
        self.assertTrue(self.report.template_owned_strict_csp_ready)
        self.assertTrue(self.report.cutover_ready)

    def test_inherited_base_boundary_is_nonce_ready_after_v332(self):
        inherited = self.report.inherited_csp_boundary

        self.assertEqual(inherited.template_path, "templates/base.html")
        self.assertEqual(inherited.style_blocks, ())
        self.assertEqual(len(inherited.script_blocks), 1)
        self.assertEqual(inherited.inline_event_handlers, ())
        self.assertEqual(inherited.inline_style_attributes, ())
        self.assertEqual(
            inherited.nonce_protected_script_blocks,
            inherited.script_blocks,
        )
        self.assertEqual(inherited.unprotected_script_blocks, ())
        self.assertTrue(inherited.strict_csp_ready)
        self.assertTrue(self.report.strict_csp_ready)

    def test_text_and_json_audit_expose_both_csp_scopes(self):
        text_output = StringIO()
        call_command("audit_listing_detail_assets_v324", stdout=text_output)
        rendered = text_output.getvalue()

        self.assertIn("inline_styles=0", rendered)
        self.assertIn("template_csp_ready=true", rendered)
        self.assertIn("inherited_styles=0", rendered)
        self.assertIn("inherited_scripts=1", rendered)
        self.assertIn("inherited_nonce_scripts=1", rendered)
        self.assertIn("inherited_unprotected_scripts=0", rendered)
        self.assertIn("inherited_inline_styles=0", rendered)
        self.assertIn("strict_csp_ready=true", rendered)

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())

        self.assertTrue(payload["template_owned_strict_csp_ready"])
        self.assertTrue(payload["strict_csp_ready"])
        self.assertTrue(
            payload["inherited_csp_boundary"]["strict_csp_ready"]
        )

    def test_static_asset_cutover_contract_remains_complete(self):
        self.assertEqual(
            {asset.kind for asset in self.report.static_assets},
            {"css", "javascript"},
        )
        self.assertEqual(self.report.source_contract_tests, ())
        self.assertGreaterEqual(
            len(self.report.asset_aware_source_tests),
            15,
        )
        self.assertEqual(self.report.blocker_codes, ())

    def test_v328_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v328*.py"
                )
            )

        self.assertEqual(matches, [])
