from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from config.csp_report_ingestion_v334 import (
    CSP_REPORT_MAX_BODY_BYTES_V334,
    CSP_REPORT_RATE_LIMIT_V334,
    CSP_REPORT_RATE_WINDOW_SECONDS_V334,
)
from scripts.check_csp_report_edge_config_v336 import (
    CSP_REPORT_EDGE_ABUSE_CONTROL_BASELINE_V336,
    CSP_REPORT_EDGE_CHECK_IDS_V336,
    CSP_REPORT_EDGE_CHECK_KEYS_V336,
    CSP_REPORT_EDGE_CONFIG_MAX_BYTES_V336,
    CSP_REPORT_EDGE_REASON_CODES_V336,
    CSP_REPORT_EDGE_RESULT_KEYS_V336,
    _read_config_v336,
    audit_csp_report_edge_config_v336,
)


VALID_EDGE_CONFIG_V336 = """
limit_req_zone $binary_remote_addr zone=csp_reports_v336:10m rate=1r/s;

server {
    location = /__csp_reports__/ {
        client_max_body_size 16k;
        client_body_timeout 10s;
        limit_req zone=csp_reports_v336 burst=10 nodelay;
        limit_req_status 429;
        limit_req_log_level notice;
        proxy_pass http://web:8000;
        proxy_redirect off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://web:8000;
    }
}
"""


class CspReportEdgeAbuseControlV336Tests(SimpleTestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)

    def checks_by_id(self, result):
        return {
            check["check_id"]: check
            for check in result["checks"]
        }

    def test_exact_contract_is_ready_for_the_approved_baseline(self):
        result = audit_csp_report_edge_config_v336(
            VALID_EDGE_CONFIG_V336
        )

        self.assertEqual(
            CSP_REPORT_EDGE_ABUSE_CONTROL_BASELINE_V336,
            "CSP_REPORT_EDGE_ABUSE_CONTROL_BASELINE_V336",
        )
        self.assertEqual(
            tuple(result),
            CSP_REPORT_EDGE_RESULT_KEYS_V336,
        )
        self.assertEqual(
            tuple(result["checks"][0]),
            CSP_REPORT_EDGE_CHECK_KEYS_V336,
        )
        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            CSP_REPORT_EDGE_CHECK_IDS_V336,
        )
        self.assertTrue(
            {
                check["reason_code"]
                for check in result["checks"]
            }.issubset(set(CSP_REPORT_EDGE_REASON_CODES_V336))
        )
        self.assertTrue(result["ready"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["ready_count"], 13)
        self.assertEqual(result["not_ready_count"], 0)

    def test_edge_and_application_limits_are_intentionally_aligned(self):
        self.assertEqual(CSP_REPORT_MAX_BODY_BYTES_V334, 16 * 1024)
        self.assertEqual(CSP_REPORT_RATE_LIMIT_V334, 60)
        self.assertEqual(CSP_REPORT_RATE_WINDOW_SECONDS_V334, 60)
        self.assertIn(
            "client_max_body_size 16k;",
            VALID_EDGE_CONFIG_V336,
        )
        self.assertIn("rate=1r/s;", VALID_EDGE_CONFIG_V336)
        self.assertIn("burst=10 nodelay;", VALID_EDGE_CONFIG_V336)

    def test_unreadable_or_duplicate_exact_location_fails_closed(self):
        unreadable = audit_csp_report_edge_config_v336(None)
        duplicate = audit_csp_report_edge_config_v336(
            VALID_EDGE_CONFIG_V336
            + VALID_EDGE_CONFIG_V336
        )

        self.assertFalse(unreadable["ready"])
        self.assertEqual(
            self.checks_by_id(unreadable)[
                "configuration_readable"
            ]["reason_code"],
            "configuration_unreadable",
        )
        self.assertFalse(duplicate["ready"])
        self.assertEqual(
            self.checks_by_id(duplicate)[
                "exact_report_location_unique"
            ]["reason_code"],
            "exact_report_location_missing",
        )

    def test_each_endpoint_abuse_control_is_required(self):
        cases = (
            (
                "client_max_body_size 16k;",
                "client_max_body_size 230M;",
                "endpoint_body_bound",
                "endpoint_body_bound_missing",
            ),
            (
                "client_body_timeout 10s;",
                "",
                "endpoint_body_timeout",
                "endpoint_body_timeout_missing",
            ),
            (
                "limit_req zone=csp_reports_v336 burst=10 nodelay;",
                "",
                "endpoint_rate_limit_enabled",
                "endpoint_rate_limit_missing",
            ),
            (
                "limit_req_status 429;",
                "",
                "rate_limit_status_bounded",
                "rate_limit_status_missing",
            ),
            (
                "limit_req_log_level notice;",
                "",
                "rate_limit_observable",
                "rate_limit_log_level_missing",
            ),
        )

        for original, replacement, check_id, reason in cases:
            with self.subTest(check_id=check_id):
                result = audit_csp_report_edge_config_v336(
                    VALID_EDGE_CONFIG_V336.replace(
                        original,
                        replacement,
                    )
                )
                check = self.checks_by_id(result)[check_id]

                self.assertFalse(result["ready"])
                self.assertFalse(check["passed"])
                self.assertEqual(check["reason_code"], reason)

    def test_proxy_target_headers_and_fallback_are_required(self):
        cases = (
            (
                "proxy_pass http://web:8000;",
                "proxy_pass http://other:9000;",
                "endpoint_proxy_target_preserved",
                "endpoint_proxy_target_missing",
                1,
            ),
            (
                "proxy_set_header X-Real-IP $remote_addr;",
                "",
                "forwarding_headers_preserved",
                "forwarding_headers_missing",
                -1,
            ),
            (
                "location / {",
                "location /fallback {",
                "fallback_proxy_preserved",
                "fallback_proxy_missing",
                -1,
            ),
        )

        for original, replacement, check_id, reason, count in cases:
            with self.subTest(check_id=check_id):
                source = VALID_EDGE_CONFIG_V336.replace(
                    original,
                    replacement,
                    count,
                )
                result = audit_csp_report_edge_config_v336(source)
                check = self.checks_by_id(result)[check_id]

                self.assertFalse(result["ready"])
                self.assertFalse(check["passed"])
                self.assertEqual(check["reason_code"], reason)

    def test_dry_run_or_enforcement_header_fails_closed(self):
        dry_run = VALID_EDGE_CONFIG_V336.replace(
            "limit_req_status 429;",
            "limit_req_status 429;\nlimit_req_dry_run on;",
        )
        enforcement = VALID_EDGE_CONFIG_V336.replace(
            "client_body_timeout 10s;",
            (
                "client_body_timeout 10s;\n"
                'add_header Content-Security-Policy "default-src self";'
            ),
        )
        dry_run_result = audit_csp_report_edge_config_v336(dry_run)
        enforcement_result = audit_csp_report_edge_config_v336(
            enforcement
        )

        self.assertEqual(
            self.checks_by_id(dry_run_result)[
                "rate_limit_enforcement_active"
            ]["reason_code"],
            "rate_limit_dry_run_enabled",
        )
        self.assertEqual(
            self.checks_by_id(enforcement_result)[
                "csp_enforcement_absent"
            ]["reason_code"],
            "csp_enforcement_detected",
        )

    def test_comments_cannot_forge_required_directives(self):
        source = VALID_EDGE_CONFIG_V336.replace(
            "client_max_body_size 16k;",
            "# client_max_body_size 16k;",
        )
        result = audit_csp_report_edge_config_v336(source)

        self.assertFalse(result["ready"])
        self.assertEqual(
            self.checks_by_id(result)[
                "endpoint_body_bound"
            ]["reason_code"],
            "endpoint_body_bound_missing",
        )

    def test_reader_is_bounded_and_rejects_missing_configuration(self):
        missing = self.backend_dir / "missing-v336-nginx.conf"

        self.assertEqual(
            CSP_REPORT_EDGE_CONFIG_MAX_BYTES_V336,
            256 * 1024,
        )
        self.assertIsNone(_read_config_v336(missing))

    def test_validator_source_has_no_network_write_or_reload_path(self):
        source = (
            self.backend_dir
            / "scripts"
            / "check_csp_report_edge_config_v336.py"
        ).read_text(encoding="utf-8")

        for forbidden in (
            "requests.",
            "urllib.",
            "write_text(",
            "open(",
            "subprocess",
            "nginx -s reload",
            ".objects",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

        self.assertIn("read_text(", source)
        self.assertIn("read_only", source)

    def test_v336_adds_no_database_migration(self):
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
                    "*v336*.py"
                )
            )

        self.assertEqual(matches, [])
