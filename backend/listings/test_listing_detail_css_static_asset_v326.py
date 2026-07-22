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


V326_MARKER = "LISTING_DETAIL_CSS_STATIC_ASSET_V326"


class ListingDetailCssStaticAssetV326Tests(SimpleTestCase):
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

    def test_v326_css_asset_is_discoverable_and_template_independent(self):
        resolved = finders.find(PLANNED_CSS_ASSET_V324)

        self.assertIsNotNone(resolved)
        css_source = Path(resolved).read_text(encoding="utf-8")
        self.assertTrue(css_source.startswith(f"/* {V326_MARKER} */"))
        self.assertGreater(len(css_source), 20000)
        self.assertNotIn("{{", css_source)
        self.assertNotIn("{%", css_source)

    def test_template_loads_css_once_and_has_no_inline_style_block(self):
        self.assertIn("{% load static %}", self.template_source)
        self.assertEqual(
            self.template_source.count(
                "{% static 'listings/listing-detail-v324.css' %}"
            ),
            1,
        )
        self.assertEqual(
            self.template_source.count("data-listing-detail-css-v326"),
            1,
        )
        self.assertNotIn("<style", self.template_source.lower())
        self.assertIn(V326_MARKER, self.template_source)

    def test_extra_styles_extension_point_is_inside_document_head(self):
        base_source = (
            self.backend_dir / "templates" / "base.html"
        ).read_text(encoding="utf-8")
        block = "{% block extra_styles %}{% endblock %}"

        self.assertEqual(base_source.count(block), 1)
        self.assertLess(
            base_source.index(block),
            base_source.index("</head>"),
        )
        get_template("listings/listing_detail.html")

    def test_audit_distinguishes_inline_blocks_from_static_assets(self):
        self.assertEqual(self.report.style_blocks, ())
        self.assertEqual(len(self.report.script_blocks), 4)
        self.assertEqual(len(self.report.static_assets), 1)
        css_asset = self.report.static_assets[0]
        self.assertEqual(css_asset.kind, "css")
        self.assertEqual(
            css_asset.path,
            "listings/static/listings/listing-detail-v324.css",
        )
        self.assertIn(V326_MARKER, css_asset.markers)
        self.assertTrue(self.report.cutover_ready)
        self.assertFalse(self.report.strict_csp_ready)

    def test_asset_aware_contract_includes_template_then_css(self):
        paths = listing_detail_contract_paths_v325(self.backend_dir)

        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0], self.template_path)
        self.assertTrue(paths[1].as_posix().endswith(PLANNED_CSS_ASSET_V324))
        self.assertIn(V326_MARKER, self.contract_source)
        self.assertNotIn(PLANNED_JS_ASSET_V324, [path.name for path in paths])

    def test_all_listing_detail_style_markers_survive_extraction(self):
        for marker in (
            "LISTING_DETAIL_GALLERY_INTERACTION_V63",
            "LISTING_DETAIL_CONTACT_SAFETY_V66",
            "LISTING_PRICE_HISTORY_V275",
            "LISTING_GALLERY_LIGHTBOX_V318",
            "LISTING_LOCATION_ACTIONS_V319",
            "MOBILE_LISTING_BUYER_ACTION_BAR_V321",
            "LISTING_DETAIL_ACCESSIBILITY_V322",
            V326_MARKER,
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.contract_source)

    def test_v326_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v326*.py"
                )
            )

        self.assertEqual(matches, [])


class ListingDetailCssStaticAssetV326RenderingTests(TestCase):
    def test_detail_response_loads_css_inside_document_head(self):
        owner = get_user_model().objects.create_user(
            username="v326-css-owner",
            password="StrongPass123!",
        )
        category = Category.objects.create(
            name="V326 CSS Category",
            slug="v326-css-category",
        )
        listing = Listing.objects.create(
            owner=owner,
            category=category,
            title="V326 CSS Listing",
            description="Static CSS response integration fixture.",
            price=Decimal("326.00"),
            location="Berlin",
            status=Listing.Status.APPROVED,
        )

        response = self.client.get(
            reverse("listings:listing_detail", kwargs={"pk": listing.pk})
        )
        rendered = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'href="/static/listings/listing-detail-v324.css"',
            rendered,
        )
        self.assertEqual(rendered.count("data-listing-detail-css-v326"), 1)
        self.assertLess(
            rendered.index("data-listing-detail-css-v326"),
            rendered.index("</head>"),
        )
