import hashlib
import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.seller_restriction_asset_contract_v331 import (
    SELLER_RESTRICTION_CSS_ASSET_V331,
    SELLER_RESTRICTION_CSS_REPOSITORY_PATH_V331,
    SELLER_RESTRICTION_JS_ASSET_V331,
    SELLER_RESTRICTION_JS_REPOSITORY_PATH_V331,
)
from listings.listing_detail_asset_boundary_v324 import (
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    LISTING_DETAIL_TEMPLATE_PATH_V325,
)
from pages.base_asset_contract_v330 import BASE_TEMPLATE_PATH_V330


V331_MARKER = "SELLER_RESTRICTION_CONDITIONAL_ASSET_V331"
V330_NORMALIZED_CSS_SHA256 = (
    "7266beb4c43015bb1cbea86b9cd779636e7a4d3d8ab13090a73edea3b762fc2d"
)
V330_NORMALIZED_JAVASCRIPT_SHA256 = (
    "77f453094769dcfe929f49d0563a896e36f7187d825c2000dcf251d90e76d5a6"
)


class SellerRestrictionConditionalAssetsV331Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.template_source = (
            cls.backend_dir / BASE_TEMPLATE_PATH_V330
        ).read_text(encoding="utf-8")
        cls.css_source = (
            cls.backend_dir / SELLER_RESTRICTION_CSS_REPOSITORY_PATH_V331
        ).read_text(encoding="utf-8")
        cls.javascript_source = (
            cls.backend_dir / SELLER_RESTRICTION_JS_REPOSITORY_PATH_V331
        ).read_text(encoding="utf-8")
        cls.report = audit_listing_detail_asset_boundary_v324(
            template_path=(
                cls.backend_dir / LISTING_DETAIL_TEMPLATE_PATH_V325
            ),
            backend_dir=cls.backend_dir,
        )

    def test_v331_assets_are_discoverable_and_template_independent(self):
        for asset_path, repository_path in (
            (
                SELLER_RESTRICTION_CSS_ASSET_V331,
                SELLER_RESTRICTION_CSS_REPOSITORY_PATH_V331,
            ),
            (
                SELLER_RESTRICTION_JS_ASSET_V331,
                SELLER_RESTRICTION_JS_REPOSITORY_PATH_V331,
            ),
        ):
            with self.subTest(asset_path=asset_path):
                resolved = finders.find(asset_path)
                self.assertIsNotNone(resolved)
                self.assertEqual(
                    Path(resolved).resolve(),
                    (self.backend_dir / repository_path).resolve(),
                )

        for source in (self.css_source, self.javascript_source):
            self.assertTrue(source.startswith(f"/* {V331_MARKER} */\n\n"))
            self.assertNotIn("{{", source)
            self.assertNotIn("{%", source)

    def test_extracted_payloads_match_frozen_v330_hashes(self):
        prefix = f"/* {V331_MARKER} */\n\n"
        cases = (
            (
                self.css_source[len(prefix):],
                157,
                6,
                V330_NORMALIZED_CSS_SHA256,
            ),
            (
                self.javascript_source[len(prefix):],
                1325,
                45,
                V330_NORMALIZED_JAVASCRIPT_SHA256,
            ),
        )

        for payload, character_count, line_count, digest in cases:
            with self.subTest(digest=digest):
                self.assertEqual(len(payload), character_count)
                self.assertEqual(len(payload.splitlines()), line_count)
                self.assertEqual(
                    hashlib.sha256(payload.encode()).hexdigest(),
                    digest,
                )

    def test_conditional_css_loads_after_extra_styles_inside_head(self):
        css_tag = "{% static 'accounts/seller-restriction-v331.css' %}"
        extra_styles = "{% block extra_styles %}{% endblock %}"
        css_position = self.template_source.index(css_tag)

        self.assertLess(self.template_source.index(extra_styles), css_position)
        self.assertLess(css_position, self.template_source.index("</head>"))
        self.assertLess(
            self.template_source.rfind(
                "{% if current_user_is_seller_suspended %}",
                0,
                css_position,
            ),
            css_position,
        )
        self.assertLess(
            css_position,
            self.template_source.index("{% endif %}", css_position),
        )

    def test_conditional_javascript_keeps_original_body_position(self):
        script_tag = "{% static 'accounts/seller-restriction-v331.js' %}"
        script_position = self.template_source.index(script_tag)

        self.assertLess(
            self.template_source.index("seller-restriction-banner-v329"),
            script_position,
        )
        self.assertLess(
            script_position,
            self.template_source.index('class="top-strip"'),
        )
        script_window = self.template_source[
            script_position - 120:script_position + 180
        ]
        self.assertNotIn("defer", script_window)
        self.assertEqual(
            self.template_source.count("data-seller-restriction-js-v331"),
            1,
        )

    def test_audit_reports_only_dynamic_json_ld_inline_boundary(self):
        inherited = self.report.inherited_csp_boundary

        self.assertEqual(inherited.style_blocks, ())
        self.assertEqual(len(inherited.script_blocks), 1)
        self.assertTrue(inherited.script_blocks[0].contains_template_syntax)
        self.assertEqual(inherited.inline_event_handlers, ())
        self.assertEqual(inherited.inline_style_attributes, ())
        self.assertFalse(inherited.strict_csp_ready)
        self.assertFalse(self.report.strict_csp_ready)

    def test_audit_inventories_both_v331_static_assets(self):
        self.assertEqual(len(self.report.static_assets), 5)

        for repository_path, kind in (
            (SELLER_RESTRICTION_CSS_REPOSITORY_PATH_V331, "css"),
            (SELLER_RESTRICTION_JS_REPOSITORY_PATH_V331, "javascript"),
        ):
            with self.subTest(repository_path=repository_path):
                asset = next(
                    item
                    for item in self.report.static_assets
                    if item.path == repository_path
                )
                self.assertEqual(asset.kind, kind)
                self.assertIn(V331_MARKER, asset.markers)

    def test_text_and_json_audit_report_v331_boundary(self):
        text_output = StringIO()
        call_command("audit_listing_detail_assets_v324", stdout=text_output)
        rendered = text_output.getvalue()

        self.assertIn("static_assets=5", rendered)
        self.assertIn("inherited_styles=0", rendered)
        self.assertIn("inherited_scripts=1", rendered)
        self.assertIn("inherited_inline_styles=0", rendered)
        self.assertIn("strict_csp_ready=false", rendered)

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())

        self.assertEqual(len(payload["static_assets"]), 5)
        self.assertEqual(
            len(payload["inherited_csp_boundary"]["script_blocks"]),
            1,
        )
        self.assertFalse(payload["strict_csp_ready"])

    def test_v331_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings", "pages"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v331*.py"
                )
            )

        self.assertEqual(matches, [])


class SellerRestrictionConditionalAssetsV331RenderingTests(TestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="v331-suspended-seller",
            password="StrongPass123!",
        )

    def test_suspended_seller_response_loads_both_assets_once(self):
        profile = self.seller.profile
        profile.seller_suspended_until = (
            timezone.now() + timezone.timedelta(days=2)
        )
        profile.seller_suspension_reason = "V331 policy review."
        profile.save(
            update_fields=(
                "seller_suspended_until",
                "seller_suspension_reason",
            )
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("accounts:dashboard"))
        rendered = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertIn("V331 policy review.", rendered)
        self.assertIn(
            'href="/static/accounts/seller-restriction-v331.css"',
            rendered,
        )
        self.assertIn(
            'src="/static/accounts/seller-restriction-v331.js"',
            rendered,
        )
        self.assertEqual(
            rendered.count("data-seller-restriction-css-v331"),
            1,
        )
        self.assertEqual(
            rendered.count("data-seller-restriction-js-v331"),
            1,
        )
        self.assertNotIn("DOMContentLoaded", rendered)

    def test_unrestricted_seller_response_omits_both_assets(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("accounts:dashboard"))
        rendered = response.content.decode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("seller-restriction-v331.css", rendered)
        self.assertNotIn("seller-restriction-v331.js", rendered)
        self.assertNotIn("seller-restriction-banner-v329", rendered)
