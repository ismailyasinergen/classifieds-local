import json
import re
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse

from config.context_processors import csp_nonce_v332
from config.csp_nonce_v332 import (
    CSP_NONCE_ATTRIBUTE_V332,
    CSP_NONCE_PATTERN_V332,
    CspNonceMiddlewareV332,
    ensure_request_csp_nonce_v332,
    generate_csp_nonce_v332,
)
from listings.listing_detail_asset_boundary_v324 import (
    audit_listing_detail_asset_boundary_v324,
)
from listings.listing_detail_asset_contract_v325 import (
    LISTING_DETAIL_TEMPLATE_PATH_V325,
)
from pages.base_asset_contract_v330 import BASE_TEMPLATE_PATH_V330


V332_MARKER = "DYNAMIC_SEO_JSON_LD_CSP_NONCE_V332"
JSON_LD_SCRIPT_PATTERN_V332 = re.compile(
    r'<script type="application/ld\+json" '
    r'nonce="(?P<nonce>[A-Za-z0-9_-]{43})">'
    r"(?P<body>.*?)</script>",
    re.DOTALL,
)


class DynamicSeoJsonLdCspNonceV332ContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.base_source = (
            cls.backend_dir / BASE_TEMPLATE_PATH_V330
        ).read_text(encoding="utf-8")
        cls.report = audit_listing_detail_asset_boundary_v324(
            template_path=(
                cls.backend_dir / LISTING_DETAIL_TEMPLATE_PATH_V325
            ),
            backend_dir=cls.backend_dir,
        )

    def test_settings_wire_nonce_before_template_rendering(self):
        middleware_path = "config.csp_nonce_v332.CspNonceMiddlewareV332"
        context_processor_path = "config.context_processors.csp_nonce_v332"

        self.assertIn(middleware_path, settings.MIDDLEWARE)
        self.assertGreater(
            settings.MIDDLEWARE.index(middleware_path),
            settings.MIDDLEWARE.index(
                "django.middleware.security.SecurityMiddleware"
            ),
        )
        self.assertIn(
            context_processor_path,
            settings.TEMPLATES[0]["OPTIONS"]["context_processors"],
        )

    def test_nonce_generation_is_256_bit_url_safe_and_request_stable(self):
        generated = generate_csp_nonce_v332()
        self.assertRegex(generated, CSP_NONCE_PATTERN_V332)

        request = RequestFactory().get("/")

        with patch(
            "config.csp_nonce_v332.secrets.token_urlsafe",
            return_value="A" * 43,
        ) as token_urlsafe:
            first = ensure_request_csp_nonce_v332(request)
            second = ensure_request_csp_nonce_v332(request)

        self.assertEqual(first, "A" * 43)
        self.assertEqual(second, first)
        token_urlsafe.assert_called_once_with(32)

    def test_middleware_assigns_nonce_before_view_without_csp_header(self):
        observed = {}

        def get_response(request):
            observed["nonce"] = getattr(
                request,
                CSP_NONCE_ATTRIBUTE_V332,
                "",
            )
            return HttpResponse("ok")

        request = RequestFactory().get("/")
        response = CspNonceMiddlewareV332(get_response)(request)

        self.assertRegex(observed["nonce"], CSP_NONCE_PATTERN_V332)
        self.assertFalse(response.has_header("Content-Security-Policy"))
        self.assertFalse(
            response.has_header("Content-Security-Policy-Report-Only")
        )

    def test_context_processor_reuses_request_nonce(self):
        request = RequestFactory().get("/")
        expected = ensure_request_csp_nonce_v332(request)

        self.assertEqual(
            csp_nonce_v332(request),
            {"csp_nonce_v332": expected},
        )

    def test_base_json_ld_block_is_nonce_guarded_and_fail_closed(self):
        self.assertIn(V332_MARKER, self.base_source)
        self.assertIn(
            "{% if seo_json_ld and csp_nonce_v332 %}",
            self.base_source,
        )
        self.assertIn(
            'type="application/ld+json" nonce="{{ csp_nonce_v332 }}"',
            self.base_source,
        )
        self.assertEqual(
            self.base_source.count('type="application/ld+json"'),
            1,
        )

    def test_asset_audit_distinguishes_nonce_protected_json_ld(self):
        inherited = self.report.inherited_csp_boundary

        self.assertEqual(inherited.style_blocks, ())
        self.assertEqual(len(inherited.script_blocks), 1)
        self.assertTrue(inherited.script_blocks[0].has_csp_nonce)
        self.assertEqual(
            inherited.nonce_protected_script_blocks,
            inherited.script_blocks,
        )
        self.assertEqual(inherited.unprotected_script_blocks, ())
        self.assertTrue(inherited.strict_csp_ready)
        self.assertTrue(self.report.strict_csp_ready)

    def test_text_and_json_audit_report_nonce_readiness(self):
        from django.core.management import call_command

        text_output = StringIO()
        call_command("audit_listing_detail_assets_v324", stdout=text_output)
        rendered = text_output.getvalue()

        self.assertIn("inherited_scripts=1", rendered)
        self.assertIn("inherited_nonce_scripts=1", rendered)
        self.assertIn("inherited_unprotected_scripts=0", rendered)
        self.assertIn("strict_csp_ready=true", rendered)

        json_output = StringIO()
        call_command(
            "audit_listing_detail_assets_v324",
            json=True,
            stdout=json_output,
        )
        payload = json.loads(json_output.getvalue())
        inherited = payload["inherited_csp_boundary"]

        self.assertEqual(len(inherited["script_blocks"]), 1)
        self.assertEqual(
            len(inherited["nonce_protected_script_blocks"]),
            1,
        )
        self.assertEqual(inherited["unprotected_script_blocks"], [])
        self.assertTrue(inherited["strict_csp_ready"])
        self.assertTrue(payload["strict_csp_ready"])

    def test_v332_adds_no_database_migration(self):
        matches = []

        for app_name in (
            "accounts",
            "categories",
            "conversations",
            "listings",
            "pages",
            "promotions",
        ):
            matches.extend(
                (self.backend_dir / app_name / "migrations").glob(
                    "*v332*.py"
                )
            )

        self.assertEqual(matches, [])


class DynamicSeoJsonLdCspNonceV332RenderingTests(TestCase):
    def deals(self):
        return self.client.get(
            reverse("listings:public_deals_v296"),
            secure=True,
        )

    def test_dynamic_json_ld_uses_the_request_nonce(self):
        response = self.deals()
        rendered = response.content.decode(response.charset or "utf-8")
        match = JSON_LD_SCRIPT_PATTERN_V332.search(rendered)

        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(match)
        self.assertEqual(
            match.group("nonce"),
            response.context["csp_nonce_v332"],
        )
        self.assertEqual(rendered.count("application/ld+json"), 1)
        self.assertIsInstance(json.loads(match.group("body")), dict)
        self.assertFalse(response.has_header("Content-Security-Policy"))
        self.assertFalse(
            response.has_header("Content-Security-Policy-Report-Only")
        )

    def test_separate_requests_receive_distinct_nonces(self):
        first = self.deals()
        second = self.deals()
        first_nonce = first.context["csp_nonce_v332"]
        second_nonce = second.context["csp_nonce_v332"]

        self.assertRegex(first_nonce, CSP_NONCE_PATTERN_V332)
        self.assertRegex(second_nonce, CSP_NONCE_PATTERN_V332)
        self.assertNotEqual(first_nonce, second_nonce)
        self.assertContains(first, f'nonce="{first_nonce}"')
        self.assertContains(second, f'nonce="{second_nonce}"')

    def test_non_seo_page_has_nonce_context_but_no_json_ld_script(self):
        response = self.client.get(reverse("pages:home"))

        self.assertEqual(response.status_code, 200)
        self.assertRegex(
            response.context["csp_nonce_v332"],
            CSP_NONCE_PATTERN_V332,
        )
        self.assertNotContains(response, 'type="application/ld+json"')
        self.assertFalse(response.has_header("Content-Security-Policy"))
