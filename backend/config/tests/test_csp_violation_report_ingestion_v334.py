import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import (
    Client,
    RequestFactory,
    SimpleTestCase,
    TestCase,
    override_settings,
)
from django.urls import resolve, reverse

from config.csp_report_ingestion_v334 import (
    CSP_REPORT_INGESTION_FOUNDATION_V334,
    CSP_REPORT_LOGGER_NAME_V334,
    CSP_REPORT_MAX_BATCH_ITEMS_V334,
    CSP_REPORT_MAX_BODY_BYTES_V334,
    CSP_REPORT_MEDIA_TYPES_V334,
    CSP_REPORT_RATE_LIMIT_V334,
    CSP_REPORT_RATE_WINDOW_SECONDS_V334,
    InvalidCspReportV334,
    _read_bounded_body_v334,
    csp_report_ingestion_v334,
    logger,
    parse_csp_report_payload_v334,
    sanitize_csp_report_v334,
)
from config.csp_report_only_v333 import (
    CSP_ENFORCEMENT_HEADER_V333,
    CSP_REPORT_ONLY_HEADER_V333,
)


def legacy_report_v334():
    return {
        "csp-report": {
            "document-uri": (
                "https://testserver/private/listing"
                "?token=document-secret"
            ),
            "blocked-uri": (
                "https://cdn.example.test/private.js"
                "?token=blocked-secret"
            ),
            "effective-directive": "script-src-elem",
            "violated-directive": "script-src-elem 'self'",
            "original-policy": "secret-policy-value",
            "source-file": (
                "https://testserver/static/private.js"
                "?token=source-secret"
            ),
            "script-sample": "secret-script-sample",
            "line-number": 41,
            "column-number": "7",
            "status-code": 200,
            "disposition": "report",
        }
    }


def reporting_api_payload_v334():
    return [
        {
            "age": 20,
            "type": "csp-violation",
            "url": "https://testserver/ignored-wrapper-url?secret=yes",
            "body": {
                "documentURL": "https://testserver/deals/?private=yes",
                "blockedURL": "inline",
                "effectiveDirective": "script-src-attr",
                "violatedDirective": "script-src-attr",
                "sourceFile": "https://testserver/accounts/private.js",
                "lineNumber": 9,
                "columnNumber": 3,
                "statusCode": 200,
                "disposition": "report",
                "sample": "ignored-sensitive-sample",
            },
        },
        {
            "age": 10,
            "type": "csp-violation",
            "url": "https://testserver/ignored",
            "body": {
                "documentURL": "https://testserver/",
                "blockedURL": "blob:",
                "effectiveDirective": "media-src",
                "violatedDirective": "media-src",
                "statusCode": 200,
                "disposition": "report",
            },
        },
    ]


class CspViolationReportIngestionV334ContractTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)

    def test_route_and_default_off_setting_are_explicit(self):
        match = resolve("/__csp_reports__/")

        self.assertTrue(CSP_REPORT_INGESTION_FOUNDATION_V334)
        self.assertIs(match.func, csp_report_ingestion_v334)
        self.assertEqual(match.url_name, "csp_report_ingestion_v334")
        self.assertEqual(
            reverse("csp_report_ingestion_v334"),
            "/__csp_reports__/",
        )
        self.assertFalse(settings.CSP_REPORT_INGESTION_ENABLED)

    def test_hard_limits_and_media_types_are_small_and_fixed(self):
        self.assertEqual(
            CSP_REPORT_MEDIA_TYPES_V334,
            {
                "application/csp-report",
                "application/reports+json",
            },
        )
        self.assertEqual(CSP_REPORT_MAX_BODY_BYTES_V334, 16 * 1024)
        self.assertEqual(CSP_REPORT_MAX_BATCH_ITEMS_V334, 10)
        self.assertEqual(CSP_REPORT_RATE_LIMIT_V334, 60)
        self.assertEqual(CSP_REPORT_RATE_WINDOW_SECONDS_V334, 60)

    def test_legacy_parser_returns_only_the_report_body(self):
        payload = legacy_report_v334()
        reports = parse_csp_report_payload_v334(
            body=json.dumps(payload).encode(),
            media_type="application/csp-report",
        )

        self.assertEqual(reports, (payload["csp-report"],))

    def test_reporting_api_parser_accepts_a_bounded_violation_batch(self):
        payload = reporting_api_payload_v334()
        reports = parse_csp_report_payload_v334(
            body=json.dumps(payload).encode(),
            media_type="application/reports+json",
        )

        self.assertEqual(
            reports,
            tuple(item["body"] for item in payload),
        )

    def test_parser_rejects_malformed_or_unapproved_shapes(self):
        cases = (
            (b"{", "application/csp-report"),
            (b"{}", "application/csp-report"),
            (b"{}", "application/reports+json"),
            (
                json.dumps(
                    [{"type": "other", "body": {}}]
                ).encode(),
                "application/reports+json",
            ),
            (
                json.dumps(
                    [
                        {
                            "type": "csp-violation",
                            "body": {},
                        }
                    ]
                    * (CSP_REPORT_MAX_BATCH_ITEMS_V334 + 1)
                ).encode(),
                "application/reports+json",
            ),
            (b"{}", "application/json"),
        )

        for body, media_type in cases:
            with self.subTest(media_type=media_type, body=body[:20]):
                with self.assertRaises(InvalidCspReportV334):
                    parse_csp_report_payload_v334(
                        body=body,
                        media_type=media_type,
                    )

    def test_sanitizer_removes_paths_queries_policy_and_samples(self):
        report = legacy_report_v334()["csp-report"]
        evidence = sanitize_csp_report_v334(report)
        serialized = json.dumps(evidence, sort_keys=True)

        self.assertEqual(
            evidence["document_origin"],
            "https://testserver",
        )
        self.assertEqual(
            evidence["blocked_resource"],
            "https://cdn.example.test",
        )
        self.assertEqual(
            evidence["source_origin"],
            "https://testserver",
        )
        self.assertEqual(
            evidence["effective_directive"],
            "script-src-elem",
        )
        self.assertEqual(
            evidence["violated_directive"],
            "script-src-elem",
        )
        self.assertEqual(evidence["line_number"], 41)
        self.assertEqual(evidence["column_number"], 7)

        for secret in (
            "private",
            "document-secret",
            "blocked-secret",
            "source-secret",
            "secret-policy-value",
            "secret-script-sample",
        ):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, serialized)

    def test_sanitizer_bounds_invalid_fields_and_classifies_resources(self):
        evidence = sanitize_csp_report_v334(
            {
                "document-uri": "/relative/private?secret=yes",
                "blocked-uri": "data:",
                "source-file": "javascript:alert(1)",
                "effective-directive": "INVALID DIRECTIVE!",
                "violated-directive": 123,
                "line-number": -1,
                "column-number": 10_000_001,
                "status-code": 999,
                "disposition": "unexpected",
            }
        )

        self.assertEqual(
            evidence["document_origin"],
            "same-origin-relative",
        )
        self.assertEqual(evidence["blocked_resource"], "data")
        self.assertEqual(
            evidence["source_origin"],
            "javascript-scheme",
        )
        self.assertEqual(evidence["effective_directive"], "invalid")
        self.assertEqual(evidence["violated_directive"], "unknown")
        self.assertIsNone(evidence["line_number"])
        self.assertIsNone(evidence["column_number"])
        self.assertIsNone(evidence["status_code"])
        self.assertEqual(evidence["disposition"], "unknown")

    def test_source_has_no_model_file_or_raw_payload_persistence(self):
        source = (
            self.backend_dir
            / "config"
            / "csp_report_ingestion_v334.py"
        ).read_text(encoding="utf-8")
        settings_source = (
            self.backend_dir / "config" / "settings.py"
        ).read_text(encoding="utf-8")

        self.assertNotIn(".objects", source)
        self.assertNotIn("open(", source)
        self.assertNotIn("request.body", source)
        self.assertIn("DJANGO_CSP_REPORT_INGESTION_ENABLED", settings_source)

    def test_bounded_reader_rejects_invalid_length_and_stream_errors(self):
        invalid_length = RequestFactory().post("/__csp_reports__/")
        invalid_length.META["CONTENT_LENGTH"] = "not-an-integer"

        self.assertEqual(
            _read_bounded_body_v334(invalid_length),
            (None, "invalid-content-length"),
        )

        unreadable = RequestFactory().post("/__csp_reports__/")
        unreadable.META["CONTENT_LENGTH"] = ""

        with patch.object(
            unreadable,
            "read",
            side_effect=OSError("simulated stream failure"),
        ):
            self.assertEqual(
                _read_bounded_body_v334(unreadable),
                (None, "unreadable-report"),
            )

    def test_v334_adds_no_database_migration(self):
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
                    "*v334*.py"
                )
            )

        self.assertEqual(matches, [])


@override_settings(CSP_REPORT_INGESTION_ENABLED=True)
class CspViolationReportIngestionV334EndpointTests(TestCase):
    endpoint = "/__csp_reports__/"

    def setUp(self):
        digest = hashlib.sha256(
            self._testMethodName.encode()
        ).digest()[0]
        self.remote_address = f"198.51.100.{digest or 1}"
        self.cache_key = (
            "csp-report-v334:"
            + hashlib.sha256(
                self.remote_address.encode()
            ).hexdigest()[:24]
        )
        cache.delete(self.cache_key)

    def tearDown(self):
        cache.delete(self.cache_key)
        super().tearDown()

    def post(
        self,
        payload,
        *,
        media_type="application/csp-report",
        client=None,
    ):
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload)
        else:
            body = payload

        return (client or self.client).post(
            self.endpoint,
            data=body,
            content_type=media_type,
            REMOTE_ADDR=self.remote_address,
        )

    def test_valid_legacy_report_logs_only_sanitized_evidence(self):
        with self.assertLogs(
            CSP_REPORT_LOGGER_NAME_V334,
            level="INFO",
        ) as captured:
            with self.assertNumQueries(0):
                response = self.post(
                    legacy_report_v334(),
                    media_type=(
                        "application/csp-report; charset=utf-8"
                    ),
                )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b"")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertFalse(
            response.has_header(CSP_ENFORCEMENT_HEADER_V333)
        )
        self.assertFalse(
            response.has_header("Access-Control-Allow-Origin")
        )
        self.assertEqual(len(captured.output), 1)
        rendered_log = captured.output[0]
        self.assertIn("script-src-elem", rendered_log)
        self.assertIn("https://cdn.example.test", rendered_log)

        for secret in (
            "private",
            "document-secret",
            "blocked-secret",
            "source-secret",
            "secret-policy-value",
            "secret-script-sample",
        ):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, rendered_log)

    def test_reporting_api_batch_logs_one_sanitized_event_per_item(self):
        with self.assertLogs(
            CSP_REPORT_LOGGER_NAME_V334,
            level="INFO",
        ) as captured:
            response = self.post(
                reporting_api_payload_v334(),
                media_type="application/reports+json",
            )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(captured.output), 2)
        self.assertIn('"report_index":1', captured.output[0])
        self.assertIn('"report_index":2', captured.output[1])
        self.assertNotIn("ignored-sensitive-sample", "".join(captured.output))

    def test_unsupported_media_and_invalid_json_fail_without_logging(self):
        with patch.object(logger, "info") as log_info:
            unsupported = self.post(
                legacy_report_v334(),
                media_type="application/json",
            )
            malformed = self.post(
                "{",
                media_type="application/csp-report",
            )
            invalid_shape = self.post(
                {},
                media_type="application/csp-report",
            )

        self.assertEqual(unsupported.status_code, 415)
        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(invalid_shape.status_code, 400)
        self.assertEqual(unsupported["Cache-Control"], "no-store")
        log_info.assert_not_called()

    def test_empty_oversized_and_excessive_batch_payloads_are_rejected(self):
        excessive_batch = [
            {
                "type": "csp-violation",
                "body": {},
            }
        ] * (CSP_REPORT_MAX_BATCH_ITEMS_V334 + 1)

        with patch.object(logger, "info") as log_info:
            empty = self.client.generic(
                "POST",
                self.endpoint,
                data=b"",
                CONTENT_TYPE="application/csp-report",
                REMOTE_ADDR=self.remote_address,
            )
            oversized = self.post(
                b"x" * (CSP_REPORT_MAX_BODY_BYTES_V334 + 1),
                media_type="application/csp-report",
            )
            excessive = self.post(
                excessive_batch,
                media_type="application/reports+json",
            )

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(excessive.status_code, 400)
        log_info.assert_not_called()

    def test_non_post_methods_are_rejected(self):
        response = self.client.get(
            self.endpoint,
            REMOTE_ADDR=self.remote_address,
        )

        self.assertEqual(response.status_code, 405)

    def test_csrf_checked_browser_report_is_accepted_without_token(self):
        csrf_client = Client(enforce_csrf_checks=True)

        with patch.object(logger, "info"):
            response = self.post(
                legacy_report_v334(),
                client=csrf_client,
            )

        self.assertEqual(response.status_code, 204)

    def test_hashed_client_rate_limit_stops_work_before_parsing(self):
        with (
            patch(
                "config.csp_report_ingestion_v334."
                "CSP_REPORT_RATE_LIMIT_V334",
                2,
            ),
            patch.object(logger, "info"),
        ):
            first = self.post(legacy_report_v334())
            second = self.post(legacy_report_v334())
            limited = self.post(legacy_report_v334())

        self.assertEqual(first.status_code, 204)
        self.assertEqual(second.status_code, 204)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(
            limited["Retry-After"],
            str(CSP_REPORT_RATE_WINDOW_SECONDS_V334),
        )
        self.assertNotIn(self.remote_address, self.cache_key)

    @override_settings(CSP_REPORT_INGESTION_ENABLED=False)
    def test_default_off_gate_returns_not_found_without_logging(self):
        with patch.object(logger, "info") as log_info:
            response = self.post(legacy_report_v334())

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response["Cache-Control"], "no-store")
        log_info.assert_not_called()

    @override_settings(
        CSP_REPORT_ONLY_ENABLED=True,
        CSP_REPORT_ONLY_REPORT_URI="/__csp_reports__/",
    )
    def test_report_only_header_can_target_ingestion_without_enforcement(self):
        with patch.object(logger, "info"):
            response = self.post(legacy_report_v334())

        self.assertEqual(response.status_code, 204)
        self.assertTrue(
            response.has_header(CSP_REPORT_ONLY_HEADER_V333)
        )
        self.assertIn(
            "report-uri /__csp_reports__/",
            response[CSP_REPORT_ONLY_HEADER_V333],
        )
        self.assertFalse(
            response.has_header(CSP_ENFORCEMENT_HEADER_V333)
        )
