import json
import re
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.management import call_command
from django.template import engines
from django.test import SimpleTestCase

from listings.listing_detail_asset_boundary_v324 import (
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    LISTING_DETAIL_TEMPLATE_PATH_V325,
)
from pages.base_asset_contract_v330 import (
    BASE_CSS_REPOSITORY_PATH_V330,
)


V329_MARKER = "BASE_INLINE_STYLE_ATTRIBUTE_CLEANUP_V329"


class BaseInlineStyleAttributeCleanupV329Tests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.base_template_path = cls.backend_dir / "templates" / "base.html"
        cls.base_source = cls.base_template_path.read_text(encoding="utf-8")
        cls.base_css_source = (
            cls.backend_dir / BASE_CSS_REPOSITORY_PATH_V330
        ).read_text(encoding="utf-8")
        cls.base_contract_source = (
            cls.base_css_source + "\n" + cls.base_source
        )
        cls.report = audit_listing_detail_asset_boundary_v324(
            template_path=(
                cls.backend_dir / LISTING_DETAIL_TEMPLATE_PATH_V325
            ),
            backend_dir=cls.backend_dir,
        )

    def test_v329_marker_and_base_inline_style_cleanup_are_packaged(self):
        self.assertIn(V329_MARKER, self.base_css_source)
        self.assertEqual(
            re.findall(r"\sstyle\s*=", self.base_source, re.IGNORECASE),
            [],
        )
        self.assertEqual(
            self.report.inherited_csp_boundary.inline_style_attributes,
            (),
        )

    def test_replacement_classes_have_stable_source_cardinality(self):
        for class_name in (
            "seller-restriction-banner-v329",
            "django-message-list-v329",
            "django-message-v329",
        ):
            with self.subTest(class_name=class_name):
                self.assertEqual(
                    self.base_contract_source.count(class_name),
                    2,
                )

    def test_base_css_preserves_all_former_inline_declarations(self):
        fragments = (
            ".seller-restriction-banner-v329 {",
            "background: #7f1d1d;",
            "color: #fff;",
            "padding: 14px 18px;",
            "text-align: center;",
            "font-weight: bold;",
            ".django-message-list-v329 {",
            "margin-bottom: 16px;",
            ".django-message-v329 {",
            "padding: 10px;",
            "border-radius: 6px;",
            "margin-bottom: 8px;",
            "border: 1px solid #ddd;",
            "background: #f8f9fa;",
        )

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, self.base_css_source)

    def test_v329_rules_remain_at_end_of_base_css_asset(self):
        marker_index = self.base_css_source.index(V329_MARKER)

        self.assertGreater(
            marker_index,
            self.base_css_source.rindex("@media"),
        )

    def test_rendered_banner_and_messages_use_replacement_classes(self):
        request = SimpleNamespace(
            user=AnonymousUser(),
            resolver_match=SimpleNamespace(namespace="", url_name=""),
        )
        context = {
            "request": request,
            "root_categories": (),
            "messages": ("Saved successfully.",),
            "current_user_is_seller_suspended": True,
            "current_user_seller_profile": SimpleNamespace(
                seller_suspended_until=None,
                seller_suspension_reason="Policy review.",
            ),
        }

        rendered = engines["django"].from_string(self.base_source).render(
            context
        )

        self.assertIn('class="seller-restriction-banner-v329"', rendered)
        self.assertIn('class="django-message-list-v329"', rendered)
        self.assertIn('class="django-message-v329"', rendered)
        self.assertIn("Policy review.", rendered)
        self.assertIn("Saved successfully.", rendered)
        self.assertNotRegex(rendered, r"\sstyle\s*=")

    def test_inherited_csp_boundary_is_nonce_ready_after_v332(self):
        inherited = self.report.inherited_csp_boundary

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

    def test_text_and_json_audit_report_zero_inherited_inline_styles(self):
        text_output = StringIO()
        call_command("audit_listing_detail_assets_v324", stdout=text_output)
        rendered = text_output.getvalue()

        self.assertIn("inherited_styles=0", rendered)
        self.assertIn("inherited_scripts=1", rendered)
        self.assertIn("inherited_nonce_scripts=1", rendered)
        self.assertIn("inherited_unprotected_scripts=0", rendered)
        self.assertIn("inherited_handlers=0", rendered)
        self.assertIn("inherited_inline_styles=0", rendered)
        self.assertIn("strict_csp_ready=true", rendered)

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())
        inherited_payload = payload["inherited_csp_boundary"]

        self.assertEqual(inherited_payload["inline_style_attributes"], [])
        self.assertTrue(inherited_payload["strict_csp_ready"])
        self.assertTrue(payload["strict_csp_ready"])

    def test_v329_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v329*.py"
                )
            )

        self.assertEqual(matches, [])
