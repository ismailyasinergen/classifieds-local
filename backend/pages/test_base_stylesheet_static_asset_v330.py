import hashlib
import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.template.loader import get_template
from django.test import SimpleTestCase, TestCase

from listings.listing_detail_asset_boundary_v324 import (
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    LISTING_DETAIL_TEMPLATE_PATH_V325,
)
from pages.base_asset_contract_v330 import (
    BASE_CSS_ASSET_V330,
    BASE_CSS_REPOSITORY_PATH_V330,
    BASE_TEMPLATE_PATH_V330,
)


V330_MARKER = "BASE_STYLESHEET_STATIC_ASSET_V330"
V329_NORMALIZED_CSS_SHA256 = (
    "3a1b33b3c20919209371fa2c978ab4475a068272bd28db6bd8f9fc2471e05b42"
)


class BaseStylesheetStaticAssetV330Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.template_path = cls.backend_dir / BASE_TEMPLATE_PATH_V330
        cls.css_path = cls.backend_dir / BASE_CSS_REPOSITORY_PATH_V330
        cls.template_source = cls.template_path.read_text(encoding="utf-8")
        cls.css_source = cls.css_path.read_text(encoding="utf-8")
        cls.report = audit_listing_detail_asset_boundary_v324(
            template_path=(
                cls.backend_dir / LISTING_DETAIL_TEMPLATE_PATH_V325
            ),
            backend_dir=cls.backend_dir,
        )

    def test_v330_css_asset_is_discoverable_and_template_independent(self):
        resolved = finders.find(BASE_CSS_ASSET_V330)

        self.assertIsNotNone(resolved)
        self.assertEqual(Path(resolved).resolve(), self.css_path.resolve())
        self.assertTrue(
            self.css_source.startswith(f"/* {V330_MARKER} */\n\n")
        )
        self.assertNotIn("{{", self.css_source)
        self.assertNotIn("{%", self.css_source)

    def test_extracted_css_matches_frozen_v329_normalized_payload(self):
        prefix = f"/* {V330_MARKER} */\n\n"
        payload = self.css_source[len(prefix):]

        self.assertEqual(len(payload), 19725)
        self.assertEqual(len(payload.splitlines()), 1118)
        self.assertEqual(
            hashlib.sha256(payload.encode()).hexdigest(),
            V329_NORMALIZED_CSS_SHA256,
        )

    def test_base_template_loads_css_once_before_extra_styles(self):
        static_tag = "{% static 'pages/base-v330.css' %}"
        extra_styles = "{% block extra_styles %}{% endblock %}"

        self.assertIn("{% load nav_extras static %}", self.template_source)
        self.assertEqual(self.template_source.count(static_tag), 1)
        self.assertEqual(
            self.template_source.count("data-base-stylesheet-v330"),
            1,
        )
        self.assertLess(
            self.template_source.index(static_tag),
            self.template_source.index(extra_styles),
        )
        self.assertLess(
            self.template_source.index(extra_styles),
            self.template_source.index("</head>"),
        )
        get_template("base.html")

    def test_only_conditional_seller_style_block_remains_inline(self):
        inherited = self.report.inherited_csp_boundary

        self.assertEqual(len(inherited.style_blocks), 1)
        self.assertIn(".seller-action-disabled", self.template_source)
        self.assertEqual(len(inherited.script_blocks), 2)
        self.assertEqual(inherited.inline_event_handlers, ())
        self.assertEqual(inherited.inline_style_attributes, ())
        self.assertFalse(inherited.strict_csp_ready)
        self.assertFalse(self.report.strict_csp_ready)

    def test_audit_inventories_base_css_as_third_static_asset(self):
        self.assertEqual(len(self.report.static_assets), 3)
        base_asset = next(
            asset
            for asset in self.report.static_assets
            if asset.path == BASE_CSS_REPOSITORY_PATH_V330
        )

        self.assertEqual(base_asset.kind, "css")
        self.assertEqual(base_asset.character_count, len(self.css_source))
        self.assertIn(V330_MARKER, base_asset.markers)

    def test_text_and_json_audit_report_v330_boundary(self):
        text_output = StringIO()
        call_command("audit_listing_detail_assets_v324", stdout=text_output)
        rendered = text_output.getvalue()

        self.assertIn("static_assets=3", rendered)
        self.assertIn("inherited_styles=1", rendered)
        self.assertIn("inherited_scripts=2", rendered)
        self.assertIn("inherited_inline_styles=0", rendered)
        self.assertIn("strict_csp_ready=false", rendered)

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())

        self.assertEqual(len(payload["static_assets"]), 3)
        self.assertEqual(
            len(payload["inherited_csp_boundary"]["style_blocks"]),
            1,
        )
        self.assertFalse(payload["strict_csp_ready"])

    def test_v330_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings", "pages"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v330*.py"
                )
            )

        self.assertEqual(matches, [])


class BaseStylesheetStaticAssetV330RenderingTests(TestCase):
    def test_home_response_loads_base_css_inside_document_head(self):
        response = self.client.get("/")
        rendered = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn('href="/static/pages/base-v330.css"', rendered)
        self.assertEqual(rendered.count("data-base-stylesheet-v330"), 1)
        self.assertLess(
            rendered.index("data-base-stylesheet-v330"),
            rendered.index("</head>"),
        )
