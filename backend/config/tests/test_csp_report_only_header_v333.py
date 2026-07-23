import re
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TestCase,
    override_settings,
)
from django.urls import reverse

from config.csp_nonce_v332 import (
    CSP_NONCE_ATTRIBUTE_V332,
    CSP_NONCE_PATTERN_V332,
)
from config.csp_report_only_v333 import (
    CSP_ENFORCEMENT_HEADER_V333,
    CSP_REPORT_ONLY_HEADER_V333,
    CSP_REPORT_ONLY_HEADER_ROLLOUT_V333,
    CspReportOnlyMiddlewareV333,
    build_csp_report_only_policy_v333,
    normalize_csp_report_uri_v333,
)


INLINE_SCRIPT_PATTERN_V333 = re.compile(
    r"<script\b(?![^>]*\bsrc\s*=)[^>]*>",
    re.IGNORECASE,
)
INLINE_STYLE_BLOCK_PATTERN_V333 = re.compile(
    r"<style\b",
    re.IGNORECASE,
)
INLINE_HANDLER_PATTERN_V333 = re.compile(
    r"\son[a-z]+\s*=",
    re.IGNORECASE,
)
INLINE_STYLE_ATTRIBUTE_PATTERN_V333 = re.compile(
    r"\sstyle\s*=",
    re.IGNORECASE,
)
EXTERNAL_SUBRESOURCE_PATTERN_V333 = re.compile(
    r"""<(?:script|img|iframe|video|audio|source)\b"""
    r"""[^>]*\bsrc\s*=\s*["']https?://"""
    r"""|<link\b[^>]*\bhref\s*=\s*["']https?://""",
    re.IGNORECASE,
)


class CspReportOnlyHeaderV333ContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.template_sources = {
            path.relative_to(cls.backend_dir).as_posix(): path.read_text(
                encoding="utf-8"
            )
            for path in cls.backend_dir.rglob("*.html")
            if "templates" in path.parts
        }

    def test_settings_keep_rollout_default_off_and_wrap_nonce_middleware(self):
        nonce_middleware = "config.csp_nonce_v332.CspNonceMiddlewareV332"
        report_middleware = (
            "config.csp_report_only_v333.CspReportOnlyMiddlewareV333"
        )

        self.assertTrue(CSP_REPORT_ONLY_HEADER_ROLLOUT_V333)
        self.assertFalse(settings.CSP_REPORT_ONLY_ENABLED)
        self.assertEqual(settings.CSP_REPORT_ONLY_REPORT_URI, "")
        self.assertIn(nonce_middleware, settings.MIDDLEWARE)
        self.assertIn(report_middleware, settings.MIDDLEWARE)
        self.assertLess(
            settings.MIDDLEWARE.index(report_middleware),
            settings.MIDDLEWARE.index(nonce_middleware),
        )

    def test_policy_is_deterministic_nonce_bound_and_non_enforcing(self):
        nonce = "A" * 43
        policy = build_csp_report_only_policy_v333(nonce=nonce)

        self.assertEqual(
            policy.split("; "),
            [
                "default-src 'self'",
                "base-uri 'self'",
                "object-src 'none'",
                "frame-ancestors 'none'",
                "form-action 'self'",
                f"script-src 'self' 'nonce-{nonce}'",
                "script-src-attr 'none'",
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: blob:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "media-src 'self' blob:",
                "frame-src 'none'",
                "worker-src 'self' blob:",
                "manifest-src 'self'",
            ],
        )
        self.assertNotIn("report-uri", policy)

    def test_report_uri_accepts_same_origin_path_or_https_collector(self):
        accepted = (
            "",
            "/__csp_reports__/",
            "/__csp_reports__/?source=v333",
            "https://reports.example.test/csp",
        )

        for value in accepted:
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_csp_report_uri_v333(value),
                    value,
                )

    def test_report_uri_rejects_unsafe_or_ambiguous_values(self):
        rejected = (
            "reports",
            "//reports.example.test/csp",
            "http://reports.example.test/csp",
            "https://user:pass@reports.example.test/csp",
            "https://reports.example.test/csp#fragment",
            "/reports; script-src *",
            "/reports\\collector",
            '/reports"collector',
            "/reports\u00e9",
            "/reports\nX-Injected: yes",
            "/reports with-space",
        )

        for value in rejected:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    normalize_csp_report_uri_v333(value)

    def test_policy_rejects_invalid_nonce_and_appends_valid_report_uri(self):
        with self.assertRaises(ValueError):
            build_csp_report_only_policy_v333(nonce="too-short")

        policy = build_csp_report_only_policy_v333(
            nonce="B" * 43,
            report_uri="/__csp_reports__/",
        )

        self.assertTrue(policy.endswith("report-uri /__csp_reports__/"))

    @override_settings(CSP_REPORT_ONLY_ENABLED=False)
    def test_disabled_middleware_emits_no_policy_header(self):
        request = RequestFactory().get("/")
        response = CspReportOnlyMiddlewareV333(
            lambda _request: HttpResponse("ok")
        )(request)

        self.assertFalse(response.has_header(CSP_REPORT_ONLY_HEADER_V333))
        self.assertFalse(response.has_header(CSP_ENFORCEMENT_HEADER_V333))

    @override_settings(
        CSP_REPORT_ONLY_ENABLED=True,
        CSP_REPORT_ONLY_REPORT_URI="/__csp_reports__/",
    )
    def test_enabled_middleware_uses_request_nonce_without_enforcement(self):
        request = RequestFactory().get("/")
        response = CspReportOnlyMiddlewareV333(
            lambda _request: HttpResponse("ok")
        )(request)
        nonce = getattr(request, CSP_NONCE_ATTRIBUTE_V332)

        self.assertRegex(nonce, CSP_NONCE_PATTERN_V332)
        self.assertEqual(
            response[CSP_REPORT_ONLY_HEADER_V333],
            build_csp_report_only_policy_v333(
                nonce=nonce,
                report_uri="/__csp_reports__/",
            ),
        )
        self.assertFalse(response.has_header(CSP_ENFORCEMENT_HEADER_V333))

    @override_settings(
        CSP_REPORT_ONLY_ENABLED=True,
        CSP_REPORT_ONLY_REPORT_URI="",
    )
    def test_existing_upstream_report_only_header_is_preserved(self):
        def get_response(_request):
            response = HttpResponse("ok")
            response[CSP_REPORT_ONLY_HEADER_V333] = "upstream-policy"
            return response

        response = CspReportOnlyMiddlewareV333(get_response)(
            RequestFactory().get("/")
        )

        self.assertEqual(
            response[CSP_REPORT_ONLY_HEADER_V333],
            "upstream-policy",
        )

    def test_template_inventory_justifies_transitional_source_policy(self):
        inline_script_paths = {
            path
            for path, source in self.template_sources.items()
            if INLINE_SCRIPT_PATTERN_V333.search(source)
        }
        style_block_paths = {
            path
            for path, source in self.template_sources.items()
            if INLINE_STYLE_BLOCK_PATTERN_V333.search(source)
        }
        handler_paths = {
            path
            for path, source in self.template_sources.items()
            if INLINE_HANDLER_PATTERN_V333.search(source)
        }
        style_attribute_paths = {
            path
            for path, source in self.template_sources.items()
            if INLINE_STYLE_ATTRIBUTE_PATTERN_V333.search(source)
        }
        external_subresources = {
            path
            for path, source in self.template_sources.items()
            if EXTERNAL_SUBRESOURCE_PATTERN_V333.search(source)
        }
        object_url_count = sum(
            source.count("URL.createObjectURL")
            for source in self.template_sources.values()
        )
        nonce_template_paths = {
            path
            for path, source in self.template_sources.items()
            if 'nonce="{{ csp_nonce_v332 }}"' in source
        }

        self.assertEqual(len(inline_script_paths), 10)
        self.assertEqual(len(style_block_paths), 18)
        self.assertEqual(len(handler_paths), 9)
        self.assertEqual(len(style_attribute_paths), 41)
        self.assertEqual(external_subresources, set())
        self.assertEqual(object_url_count, 4)
        self.assertEqual(
            nonce_template_paths,
            {"templates/base.html"},
        )

    def test_settings_source_exposes_both_environment_controls(self):
        source = (
            self.backend_dir / "config" / "settings.py"
        ).read_text(encoding="utf-8")

        self.assertIn("DJANGO_CSP_REPORT_ONLY_ENABLED", source)
        self.assertIn("DJANGO_CSP_REPORT_ONLY_REPORT_URI", source)

    def test_v333_adds_no_database_migration(self):
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
                    "*v333*.py"
                )
            )

        self.assertEqual(matches, [])


@override_settings(
    CSP_REPORT_ONLY_ENABLED=True,
    CSP_REPORT_ONLY_REPORT_URI="/__csp_reports__/",
)
class CspReportOnlyHeaderV333RenderingTests(TestCase):
    def deals(self):
        return self.client.get(
            reverse("listings:public_deals_v296"),
            secure=True,
        )

    def test_deals_response_uses_same_nonce_in_header_and_json_ld(self):
        response = self.deals()
        nonce = response.context["csp_nonce_v332"]
        policy = response[CSP_REPORT_ONLY_HEADER_V333]

        self.assertEqual(response.status_code, 200)
        self.assertRegex(nonce, CSP_NONCE_PATTERN_V332)
        self.assertIn(f"'nonce-{nonce}'", policy)
        self.assertIn("report-uri /__csp_reports__/", policy)
        self.assertContains(response, f'nonce="{nonce}"')
        self.assertFalse(response.has_header(CSP_ENFORCEMENT_HEADER_V333))

    def test_separate_responses_receive_distinct_policy_nonces(self):
        first = self.deals()
        second = self.deals()
        first_nonce = first.context["csp_nonce_v332"]
        second_nonce = second.context["csp_nonce_v332"]

        self.assertNotEqual(first_nonce, second_nonce)
        self.assertIn(
            f"'nonce-{first_nonce}'",
            first[CSP_REPORT_ONLY_HEADER_V333],
        )
        self.assertIn(
            f"'nonce-{second_nonce}'",
            second[CSP_REPORT_ONLY_HEADER_V333],
        )

    def test_non_seo_and_health_responses_receive_observation_header(self):
        home = self.client.get(reverse("pages:home"))
        health = self.client.get(reverse("healthz"))

        self.assertNotContains(home, 'type="application/ld+json"')

        for response in (home, health):
            with self.subTest(path=response.request["PATH_INFO"]):
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    response.has_header(CSP_REPORT_ONLY_HEADER_V333)
                )
                self.assertFalse(
                    response.has_header(CSP_ENFORCEMENT_HEADER_V333)
                )

    def test_custom_405_response_retains_observation_header(self):
        response = self.client.get("/listings/compare/clear/")

        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            response.has_header(CSP_REPORT_ONLY_HEADER_V333)
        )
        self.assertFalse(
            response.has_header(CSP_ENFORCEMENT_HEADER_V333)
        )
