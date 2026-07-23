from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from categories.models import Category
from listings.listing_detail_asset_boundary_v324 import (
    PLANNED_CSS_ASSET_V324,
    PLANNED_JS_ASSET_V324,
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    LISTING_DETAIL_TEMPLATE_PATH_V325,
    listing_detail_contract_paths_v325,
    read_listing_detail_contract_source_v325,
)
from listings.models import Listing


V327_MARKER = "LISTING_DETAIL_JAVASCRIPT_STATIC_ASSET_V327"


class ListingDetailJavascriptStaticAssetV327Tests(SimpleTestCase):
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

    def test_v327_javascript_asset_is_discoverable_and_independent(self):
        resolved = finders.find(PLANNED_JS_ASSET_V324)

        self.assertIsNotNone(resolved)
        script_source = Path(resolved).read_text(encoding="utf-8")
        self.assertTrue(script_source.startswith(f"/* {V327_MARKER} */"))
        self.assertGreater(len(script_source), 12000)
        self.assertNotIn("{{", script_source)
        self.assertNotIn("{%", script_source)

    def test_template_loads_javascript_once_without_inline_scripts(self):
        self.assertEqual(self.template_source.count("<script"), 1)
        self.assertEqual(self.template_source.count("</script>"), 1)
        self.assertEqual(
            self.template_source.count(
                "{% static 'listings/listing-detail-v324.js' %}"
            ),
            1,
        )
        self.assertEqual(
            self.template_source.count("data-listing-detail-js-v327"),
            1,
        )
        self.assertIn(V327_MARKER, self.template_source)

    def test_script_include_remains_after_all_interaction_dom_hooks(self):
        script_position = self.template_source.index(
            "data-listing-detail-js-v327"
        )

        for hook in (
            'id="listing-gallery-lightbox-v318"',
            "data-listing-location-copy-v319",
            "data-listing-share-v317",
            "data-listing-print-v317",
        ):
            with self.subTest(hook=hook):
                self.assertLess(
                    self.template_source.index(hook),
                    script_position,
                )

    def test_feature_script_order_is_preserved_inside_single_asset(self):
        script_source = Path(finders.find(PLANNED_JS_ASSET_V324)).read_text(
            encoding="utf-8"
        )
        ordered_hooks = (
            "fallbackImagesV325",
            "listing-gallery-lightbox-v318",
            "data-listing-location-copy-v319",
            "data-listing-share-v317",
        )
        positions = [script_source.index(hook) for hook in ordered_hooks]

        self.assertEqual(positions, sorted(positions))
        self.assertEqual(script_source.count("\n(function () {"), 4)

    def test_audit_reports_two_static_assets_and_no_inline_blocks(self):
        self.assertEqual(self.report.asset_blocks, ())
        self.assertEqual(self.report.template_dependent_block_count, 0)
        self.assertEqual(
            {asset.kind for asset in self.report.static_assets},
            {"css", "javascript"},
        )
        javascript_asset = next(
            asset
            for asset in self.report.static_assets
            if asset.kind == "javascript"
        )
        self.assertIn(V327_MARKER, javascript_asset.markers)
        self.assertTrue(self.report.mechanically_extractable)
        self.assertTrue(self.report.cutover_ready)
        self.assertTrue(self.report.template_owned_strict_csp_ready)
        self.assertFalse(self.report.strict_csp_ready)

    def test_asset_contract_orders_template_css_and_javascript(self):
        paths = listing_detail_contract_paths_v325(self.backend_dir)

        self.assertEqual(len(paths), 3)
        self.assertEqual(paths[0], self.template_path)
        self.assertTrue(paths[1].as_posix().endswith(PLANNED_CSS_ASSET_V324))
        self.assertTrue(paths[2].as_posix().endswith(PLANNED_JS_ASSET_V324))
        for marker in (
            "LISTING_SHARE_PRINT_ACTIONS_V317",
            "LISTING_GALLERY_LIGHTBOX_V318",
            "LISTING_LOCATION_ACTIONS_V319",
            "LISTING_DETAIL_EXTRACTION_BLOCKER_REMOVAL_V325",
            V327_MARKER,
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.contract_source)

    def test_v327_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v327*.py"
                )
            )

        self.assertEqual(matches, [])


class ListingDetailJavascriptStaticAssetV327RenderingTests(TestCase):
    def test_detail_response_loads_script_after_interaction_dom(self):
        owner = get_user_model().objects.create_user(
            username="v327-javascript-owner",
            password="StrongPass123!",
        )
        category = Category.objects.create(
            name="V327 JavaScript Category",
            slug="v327-javascript-category",
        )
        listing = Listing.objects.create(
            owner=owner,
            category=category,
            title="V327 JavaScript Listing",
            description="Static JavaScript response integration fixture.",
            price=Decimal("327.00"),
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

        response = self.client.get(
            reverse("listings:listing_detail", kwargs={"pk": listing.pk})
        )
        rendered = response.content.decode("utf-8")
        script_position = rendered.index("data-listing-detail-js-v327")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'src="/static/listings/listing-detail-v324.js"',
            rendered,
        )
        self.assertEqual(rendered.count("data-listing-detail-js-v327"), 1)
        self.assertLess(
            rendered.index("data-listing-share-v317"),
            script_position,
        )
        self.assertNotIn(" defer", rendered[script_position - 150:script_position])
