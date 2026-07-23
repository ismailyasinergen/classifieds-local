import hashlib
import json
import logging
from pathlib import Path
from urllib.error import URLError

from django.conf import settings
from django.test import (
    LiveServerTestCase,
    SimpleTestCase,
    override_settings,
)

from config.csp_report_ingestion_v334 import (
    CSP_REPORT_LOGGER_NAME_V334,
    CSP_REPORT_MAX_BODY_BYTES_V334,
    parse_csp_report_payload_v334,
    sanitize_csp_report_v334,
)
from config.csp_report_logging_v337 import (
    CSP_REPORT_EVIDENCE_EXTRA_V337,
    SanitizedCspReportFormatterV337,
)
from scripts.run_csp_observation_smoke_v338 import (
    CSP_OBSERVATION_SYNTHETIC_DELIVERY_SMOKE_V338,
    CSP_SMOKE_LOG_INPUT_MAX_BYTES_V338,
    CSP_SMOKE_PATH_V338,
    CSP_SMOKE_REASON_CODES_V338,
    CSP_SMOKE_RESPONSE_MAX_BYTES_V338,
    CSP_SMOKE_RESULT_KEYS_V338,
    InvalidCspSmokeTargetV338,
    _NoRedirectHandlerV338,
    build_csp_smoke_plan_v338,
    build_csp_smoke_result_v338,
    execute_csp_smoke_v338,
    verify_csp_smoke_log_v338,
)


SMOKE_ID_V338 = "0123456789abcdef"


class FakeResponseV338:
    def __init__(
        self,
        *,
        status=204,
        headers=None,
        body=b"",
    ):
        self.status = status
        self.headers = headers or {
            "Cache-Control": "no-store",
        }
        self.body = body
        self.closed = False

    def read(self, limit):
        return self.body[:limit]

    def getcode(self):
        return self.status

    def close(self):
        self.closed = True


class FakeOpenerV338:
    def __init__(self, response=None, error=None):
        self.response = response or FakeResponseV338()
        self.error = error
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))

        if self.error is not None:
            raise self.error

        return self.response


class CspObservationSyntheticDeliverySmokeV338Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)

    def build_plan(self, **overrides):
        options = {
            "target_url": (
                "http://127.0.0.1:8080/__csp_reports__/"
            ),
            "smoke_id": SMOKE_ID_V338,
            "timeout_seconds": 5.0,
        }
        options.update(overrides)

        return build_csp_smoke_plan_v338(**options)

    def test_plan_is_deterministic_bounded_and_contains_only_invented_data(self):
        plan = self.build_plan()
        result = build_csp_smoke_result_v338(
            plan=plan,
            execute=False,
            verify_log=False,
        )

        self.assertEqual(
            CSP_OBSERVATION_SYNTHETIC_DELIVERY_SMOKE_V338,
            "CSP_OBSERVATION_SYNTHETIC_DELIVERY_SMOKE_V338",
        )
        self.assertEqual(plan.target_origin, "http://127.0.0.1:8080")
        self.assertEqual(plan.target_path, CSP_SMOKE_PATH_V338)
        self.assertLess(
            len(plan.payload),
            CSP_REPORT_MAX_BODY_BYTES_V334,
        )
        self.assertEqual(
            plan.expected_log_sha256,
            hashlib.sha256(
                plan.expected_log.encode("utf-8")
            ).hexdigest(),
        )
        self.assertEqual(tuple(result), CSP_SMOKE_RESULT_KEYS_V338)
        self.assertEqual(result["mode"], "plan")
        self.assertTrue(result["passed"])
        self.assertEqual(
            result["reason_codes"],
            (
                "plan_ready",
                "delivery_not_run",
                "log_not_checked",
            ),
        )
        self.assertTrue(
            set(result["reason_codes"]).issubset(
                CSP_SMOKE_REASON_CODES_V338
            )
        )

        serialized_result = json.dumps(result)

        for forbidden in (
            "private",
            "document-secret",
            "source-secret",
            "script-sample-secret",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, plan.expected_log)
                self.assertNotIn(forbidden, serialized_result)

    def test_expected_log_matches_real_v334_v337_pipeline(self):
        plan = self.build_plan()
        reports = parse_csp_report_payload_v334(
            body=plan.payload,
            media_type="application/csp-report",
        )
        evidence = {
            "media_type": "application/csp-report",
            "report_index": 1,
            **sanitize_csp_report_v334(reports[0]),
        }
        record = logging.LogRecord(
            name=CSP_REPORT_LOGGER_NAME_V334,
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="ignored raw message",
            args=(),
            exc_info=None,
        )
        setattr(
            record,
            CSP_REPORT_EVIDENCE_EXTRA_V337,
            evidence,
        )
        rendered = SanitizedCspReportFormatterV337().format(record)

        self.assertEqual(rendered, plan.expected_log)
        self.assertEqual(
            json.loads(rendered)["evidence"]["document_origin"],
            f"https://v338-{SMOKE_ID_V338}.invalid",
        )

    def test_loopback_http_and_confirmed_remote_https_are_allowed(self):
        loopback = self.build_plan()
        remote = self.build_plan(
            target_url=(
                "https://reports.example.invalid/__csp_reports__/"
            ),
            confirmed_remote_host="reports.example.invalid",
        )

        self.assertEqual(
            loopback.target_url,
            "http://127.0.0.1:8080/__csp_reports__/",
        )
        self.assertEqual(
            remote.target_origin,
            "https://reports.example.invalid",
        )

    def test_unsafe_or_ambiguous_targets_fail_closed(self):
        targets = (
            "http://reports.example.invalid/__csp_reports__/",
            "https://reports.example.invalid/wrong/",
            "https://reports.example.invalid/__csp_reports__/?x=1",
            "https://reports.example.invalid/__csp_reports__/#fragment",
            "https://user:pass@reports.example.invalid/__csp_reports__/",
            "//reports.example.invalid/__csp_reports__/",
            "https://reports.example.invalid/__csp_reports__/ ",
        )

        for target in targets:
            with self.subTest(target=target):
                with self.assertRaises(InvalidCspSmokeTargetV338):
                    self.build_plan(target_url=target)

        with self.assertRaises(InvalidCspSmokeTargetV338):
            self.build_plan(
                target_url=(
                    "https://reports.example.invalid/"
                    "__csp_reports__/"
                ),
                confirmed_remote_host="other.example.invalid",
            )

    def test_smoke_id_and_timeout_bounds_fail_closed(self):
        invalid_options = (
            {"smoke_id": "not-hex"},
            {"smoke_id": "A" * 16},
            {"timeout_seconds": 0.9},
            {"timeout_seconds": 10.1},
            {"timeout_seconds": True},
        )

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaises(ValueError):
                    self.build_plan(**options)

    def test_execute_sends_one_bounded_post_and_accepts_safe_204(self):
        plan = self.build_plan()
        response = FakeResponseV338(
            headers={
                "Cache-Control": "private, no-store",
                "Content-Security-Policy-Report-Only": (
                    "default-src 'self'"
                ),
            }
        )
        opener = FakeOpenerV338(response=response)
        result = execute_csp_smoke_v338(plan, opener=opener)

        self.assertTrue(result["passed"])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["response_status"], 204)
        self.assertTrue(result["enforcement_absent"])
        self.assertTrue(result["cache_control_no_store"])
        self.assertEqual(result["reason_code"], "delivery_passed")
        self.assertEqual(len(opener.requests), 1)

        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, plan.target_url)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, plan.payload)
        self.assertEqual(timeout, 5.0)
        self.assertEqual(
            request.get_header("Content-type"),
            "application/csp-report",
        )

    def test_execute_rejects_status_enforcement_cache_and_body_failures(self):
        cases = (
            (
                FakeResponseV338(status=404),
                "unexpected_status",
            ),
            (
                FakeResponseV338(
                    headers={
                        "Cache-Control": "no-store",
                        "Content-Security-Policy": (
                            "default-src 'self'"
                        ),
                    }
                ),
                "enforcement_detected",
            ),
            (
                FakeResponseV338(headers={"Cache-Control": "private"}),
                "cache_control_missing",
            ),
            (
                FakeResponseV338(body=b"unexpected"),
                "unexpected_response_body",
            ),
        )

        for response, reason_code in cases:
            with self.subTest(reason_code=reason_code):
                result = execute_csp_smoke_v338(
                    self.build_plan(),
                    opener=FakeOpenerV338(response=response),
                )

                self.assertFalse(result["passed"])
                self.assertEqual(
                    result["reason_code"],
                    reason_code,
                )

    def test_network_errors_are_sanitized(self):
        result = execute_csp_smoke_v338(
            self.build_plan(),
            opener=FakeOpenerV338(
                error=URLError(
                    "network-secret-that-must-not-be-returned"
                )
            ),
        )

        self.assertEqual(
            result,
            {
                "status": "failed",
                "response_status": None,
                "enforcement_absent": None,
                "cache_control_no_store": None,
                "passed": False,
                "reason_code": "network_error",
            },
        )

    def test_log_verification_requires_one_exact_standalone_json_line(self):
        plan = self.build_plan()
        verified = verify_csp_smoke_log_v338(
            plan,
            "unrelated\n" + plan.expected_log + "\n",
        )
        prefixed = verify_csp_smoke_log_v338(
            plan,
            "web | " + plan.expected_log,
        )
        duplicate = verify_csp_smoke_log_v338(
            plan,
            plan.expected_log + "\n" + plan.expected_log,
        )
        oversized = verify_csp_smoke_log_v338(
            plan,
            "x" * (CSP_SMOKE_LOG_INPUT_MAX_BYTES_V338 + 1),
        )

        self.assertTrue(verified["passed"])
        self.assertEqual(verified["reason_code"], "log_verified")
        self.assertFalse(prefixed["passed"])
        self.assertFalse(duplicate["passed"])
        self.assertEqual(
            oversized["reason_code"],
            "log_input_unreadable",
        )

    def test_response_and_log_input_bounds_are_small(self):
        self.assertEqual(CSP_SMOKE_RESPONSE_MAX_BYTES_V338, 1024)
        self.assertEqual(
            CSP_SMOKE_LOG_INPUT_MAX_BYTES_V338,
            512 * 1024,
        )

    def test_redirects_are_never_followed(self):
        handler = _NoRedirectHandlerV338()

        self.assertIsNone(
            handler.redirect_request(
                None,
                None,
                302,
                "redirect",
                {},
                "https://other.invalid/__csp_reports__/",
            )
        )

    def test_source_has_no_environment_enforcement_cookie_or_write_path(self):
        source = (
            self.backend_dir
            / "scripts"
            / "run_csp_observation_smoke_v338.py"
        ).read_text(encoding="utf-8")

        for forbidden in (
            "os.environ",
            "subprocess",
            "CookieJar",
            "write_text(",
            "Path(",
            "CSP_REPORT_ONLY_ENABLED",
            "CSP_ENFORCEMENT_ENABLED",
            ".objects",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

        self.assertIn("ProxyHandler({})", source)
        self.assertIn("_NoRedirectHandlerV338()", source)

    def test_v338_adds_no_database_migration(self):
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
                    "*v338*.py"
                )
            )

        self.assertEqual(matches, [])


@override_settings(
    CSP_REPORT_INGESTION_ENABLED=True,
    CSP_REPORT_ONLY_ENABLED=False,
)
class CspObservationSyntheticDeliverySmokeV338LiveTests(
    LiveServerTestCase
):
    def test_real_loopback_http_delivery_reaches_v334_without_enforcement(
        self,
    ):
        plan = build_csp_smoke_plan_v338(
            target_url=self.live_server_url + CSP_SMOKE_PATH_V338,
            smoke_id=SMOKE_ID_V338,
            timeout_seconds=5.0,
        )

        with self.assertLogs(
            CSP_REPORT_LOGGER_NAME_V334,
            level="INFO",
        ) as captured:
            result = execute_csp_smoke_v338(plan)

        self.assertTrue(result["passed"])
        self.assertEqual(result["response_status"], 204)
        self.assertTrue(result["enforcement_absent"])
        rendered = "\n".join(captured.output)
        self.assertIn(
            f"https://v338-{SMOKE_ID_V338}.invalid",
            rendered,
        )

        for secret in (
            "private",
            "document-secret",
            "source-secret",
            "script-sample-secret",
        ):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, rendered)
