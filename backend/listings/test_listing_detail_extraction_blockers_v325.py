import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase

from listings.listing_detail_asset_boundary_v324 import (
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    LISTING_DETAIL_STATIC_ASSET_PATHS_V325,
    LISTING_DETAIL_TEMPLATE_PATH_V325,
    V325_MARKER,
    listing_detail_contract_paths_v325,
    read_listing_detail_contract_source_v325,
)


class ListingDetailExtractionBlockersV325Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.template_path = (
            cls.backend_dir / LISTING_DETAIL_TEMPLATE_PATH_V325
        )
        cls.source = read_listing_detail_contract_source_v325(
            cls.backend_dir,
        )
        cls.report = audit_listing_detail_asset_boundary_v324(
            template_path=cls.template_path,
            backend_dir=cls.backend_dir,
        )

    def test_v325_marker_and_current_contract_path_are_stable(self):
        paths = listing_detail_contract_paths_v325(self.backend_dir)

        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0], self.template_path)
        self.assertEqual(
            paths[1].as_posix(),
            (
                self.backend_dir
                / LISTING_DETAIL_STATIC_ASSET_PATHS_V325[0]
            ).as_posix(),
        )
        self.assertIn(V325_MARKER, self.source)
        self.assertIn(
            "LISTING_DETAIL_CONTRACT_SOURCE: "
            + LISTING_DETAIL_TEMPLATE_PATH_V325,
            self.source,
        )

    def test_contract_reader_includes_planned_assets_in_load_order(self):
        with TemporaryDirectory() as directory:
            backend_dir = Path(directory)
            relative_paths = (
                LISTING_DETAIL_TEMPLATE_PATH_V325,
                *LISTING_DETAIL_STATIC_ASSET_PATHS_V325,
            )

            for index, relative_path in enumerate(relative_paths):
                path = backend_dir / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"source-{index}", encoding="utf-8")

            source = read_listing_detail_contract_source_v325(backend_dir)

        self.assertLess(
            source.index("source-0"),
            source.index("source-1"),
        )
        self.assertLess(
            source.index("source-1"),
            source.index("source-2"),
        )

    def test_inline_image_handlers_are_replaced_by_data_hooks(self):
        self.assertEqual(self.report.inline_event_handlers, ())
        self.assertNotIn("onerror=", self.source.lower())
        self.assertEqual(
            self.source.count('data-listing-image-fallback-v325="'),
            2,
        )
        self.assertIn("classified-main-placeholder", self.source)
        self.assertIn("classified-thumb-placeholder", self.source)

    def test_fallback_listener_handles_early_and_late_failures(self):
        for fragment in (
            '"[data-listing-image-fallback-v325]"',
            "image.addEventListener(",
            '"error",',
            "{ once: true }",
            "image.dataset.listingImageFallbackV325",
            'fallback.textContent = "No image";',
            "image.replaceWith(fallback);",
            "image.complete && image.naturalWidth === 0",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.source)

    def test_audit_reports_cutover_ready_but_not_strict_csp_ready(self):
        self.assertEqual(self.report.source_contract_tests, ())
        self.assertGreaterEqual(
            len(self.report.asset_aware_source_tests),
            11,
        )
        self.assertIn(
            "listings/test_listing_price_history_v275.py",
            self.report.asset_aware_source_tests,
        )
        self.assertIn(
            "listings/test_public_listing_price_history_timeline_v283.py",
            self.report.asset_aware_source_tests,
        )
        self.assertEqual(self.report.blocker_codes, ())
        self.assertTrue(self.report.cutover_ready)
        self.assertGreater(len(self.report.inline_style_attributes), 0)
        self.assertFalse(self.report.strict_csp_ready)

    def test_fail_on_blockers_and_json_output_are_ci_compatible(self):
        text_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            fail_on_blockers=True,
            stdout=text_output,
        )
        self.assertIn("cutover_ready=true", text_output.getvalue())

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())
        self.assertEqual(payload["inline_event_handlers"], [])
        self.assertGreater(len(payload["inline_style_attributes"]), 0)
        self.assertEqual(payload["source_contract_tests"], [])
        self.assertTrue(payload["cutover_ready"])

    def test_v325_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v325*.py"
                )
            )

        self.assertEqual(matches, [])
