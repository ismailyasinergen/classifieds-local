import copy
import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from config.csp_observation_readiness_v335 import (
    CSP_OBSERVATION_READINESS_CHECK_IDS_V335,
    get_csp_observation_readiness_v335,
)
from config.csp_report_ingestion_v334 import (
    CSP_REPORT_LOGGER_NAME_V334,
    CSP_REPORT_MAX_BODY_BYTES_V334,
    CSP_REPORT_PATH_V334,
)
from config.csp_report_logging_v337 import (
    CSP_REPORT_LOG_OPERATIONS_BASELINE_V337,
)
from config.csp_report_only_v333 import (
    CSP_ENFORCEMENT_HEADER_V333,
    CSP_REPORT_ONLY_HEADER_ROLLOUT_V333,
)
from scripts.check_csp_observation_evidence_closeout_v339 import (
    CSP_CLOSEOUT_CHECK_IDS_V339,
    CSP_CLOSEOUT_CHECK_KEYS_V339,
    CSP_CLOSEOUT_EVIDENCE_MAX_BYTES_V339,
    CSP_CLOSEOUT_REASON_CODES_V339,
    CSP_CLOSEOUT_RESULT_KEYS_V339,
    CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339,
    _EDGE_CHECK_IDS_V339,
    _READINESS_CHECK_IDS_V339,
    _RETENTION_CHECK_IDS_V339,
    _read_evidence_v339,
    audit_csp_observation_evidence_closeout_v339,
    main,
)
from scripts.check_csp_report_edge_config_v336 import (
    CSP_REPORT_EDGE_CHECK_IDS_V336,
    audit_csp_report_edge_config_v336,
)
from scripts.check_csp_report_log_retention_v337 import (
    CSP_REPORT_LOG_RETENTION_CHECK_IDS_V337,
    audit_csp_report_log_retention_v337,
)
from scripts.run_csp_observation_smoke_v338 import (
    CSP_SMOKE_MEDIA_TYPE_V338,
    CSP_SMOKE_PATH_V338,
    build_csp_smoke_plan_v338,
    build_csp_smoke_result_v338,
)


SMOKE_ID_V339 = "0123456789abcdef"
EXPECTED_ORIGIN_V339 = "https://reports.example.invalid"
PRODUCTION_READY_SETTINGS_V339 = {
    "CSP_REPORT_ONLY_ENABLED": True,
    "CSP_REPORT_ONLY_REPORT_URI": "/__csp_reports__/",
    "CSP_REPORT_INGESTION_ENABLED": True,
    "CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED": True,
    "CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED": True,
    "CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED": True,
}
VALID_EDGE_SOURCE_V339 = """
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
VALID_RETENTION_PAYLOAD_V339 = {
    "services": {
        "web": {
            "logging": {
                "driver": "local",
                "options": {
                    "max-size": "10m",
                    "max-file": "5",
                    "compress": "true",
                },
            },
        },
    },
}


class FakeResponseV339:
    status = 204
    headers = {"Cache-Control": "no-store"}

    def read(self, limit):
        return b""

    def getcode(self):
        return self.status

    def close(self):
        pass


class FakeOpenerV339:
    def open(self, request, timeout):
        return FakeResponseV339()


def json_artifact_v339(value):
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


class CspObservationEvidenceCloseoutAuditV339Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)

    def build_evidence(self):
        with override_settings(**PRODUCTION_READY_SETTINGS_V339):
            readiness = get_csp_observation_readiness_v335()

        edge = audit_csp_report_edge_config_v336(
            VALID_EDGE_SOURCE_V339
        )
        retention = audit_csp_report_log_retention_v337(
            json.dumps(VALID_RETENTION_PAYLOAD_V339)
        )
        plan = build_csp_smoke_plan_v338(
            target_url=(
                EXPECTED_ORIGIN_V339
                + "/__csp_reports__/"
            ),
            confirmed_remote_host="reports.example.invalid",
            smoke_id=SMOKE_ID_V339,
            timeout_seconds=5.0,
        )
        delivery = build_csp_smoke_result_v338(
            plan=plan,
            execute=True,
            verify_log=False,
            opener=FakeOpenerV339(),
        )
        log_evidence = build_csp_smoke_result_v338(
            plan=plan,
            execute=False,
            verify_log=True,
            observed_log=plan.expected_log,
        )

        return {
            "readiness_evidence": json_artifact_v339(readiness),
            "edge_evidence": json_artifact_v339(edge),
            "retention_evidence": json_artifact_v339(retention),
            "delivery_evidence": json_artifact_v339(delivery),
            "log_evidence": json_artifact_v339(log_evidence),
            "expected_origin": EXPECTED_ORIGIN_V339,
        }

    def checks_by_id(self, result):
        return {
            check["check_id"]: check
            for check in result["checks"]
        }

    def test_linked_reviewed_evidence_closes_all_checks(self):
        evidence = self.build_evidence()
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )

        self.assertEqual(
            CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339,
            "CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339",
        )
        self.assertEqual(
            tuple(result),
            CSP_CLOSEOUT_RESULT_KEYS_V339,
        )
        self.assertEqual(
            tuple(result["checks"][0]),
            CSP_CLOSEOUT_CHECK_KEYS_V339,
        )
        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            CSP_CLOSEOUT_CHECK_IDS_V339,
        )
        self.assertTrue(
            {
                check["reason_code"]
                for check in result["checks"]
            }.issubset(set(CSP_CLOSEOUT_REASON_CODES_V339))
        )
        self.assertTrue(result["ready"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["ready_count"], 8)
        self.assertEqual(result["not_ready_count"], 0)

    def test_component_contracts_are_bound_to_v335_v336_and_v337(self):
        self.assertEqual(
            _READINESS_CHECK_IDS_V339,
            CSP_OBSERVATION_READINESS_CHECK_IDS_V335,
        )
        self.assertEqual(
            _EDGE_CHECK_IDS_V339,
            CSP_REPORT_EDGE_CHECK_IDS_V336,
        )
        self.assertEqual(
            _RETENTION_CHECK_IDS_V339,
            CSP_REPORT_LOG_RETENTION_CHECK_IDS_V337,
        )
        self.assertTrue(CSP_REPORT_ONLY_HEADER_ROLLOUT_V333)
        self.assertTrue(CSP_REPORT_LOG_OPERATIONS_BASELINE_V337)
        self.assertEqual(
            CSP_ENFORCEMENT_HEADER_V333,
            "Content-Security-Policy",
        )

    def test_cross_version_path_payload_media_and_logger_are_aligned(self):
        self.assertEqual(
            f"/{CSP_REPORT_PATH_V334}",
            CSP_SMOKE_PATH_V338,
        )
        self.assertEqual(
            CSP_SMOKE_MEDIA_TYPE_V338,
            "application/csp-report",
        )
        self.assertEqual(
            CSP_REPORT_MAX_BODY_BYTES_V334,
            16 * 1024,
        )
        self.assertIn(
            "client_max_body_size 16k;",
            VALID_EDGE_SOURCE_V339,
        )
        self.assertEqual(
            CSP_REPORT_LOGGER_NAME_V334,
            "security.csp_report_v334",
        )

    def test_not_ready_v335_evidence_cannot_be_closed(self):
        evidence = self.build_evidence()
        evidence["readiness_evidence"] = json_artifact_v339(
            get_csp_observation_readiness_v335()
        )
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )
        checks = self.checks_by_id(result)

        self.assertFalse(result["ready"])
        self.assertFalse(
            checks["readiness_evidence_valid"]["passed"]
        )
        self.assertTrue(checks["enforcement_absent"]["passed"])
        self.assertEqual(
            checks["readiness_evidence_valid"]["reason_code"],
            "readiness_evidence_invalid",
        )

    def test_each_component_marker_and_nested_check_fail_closed(self):
        component_cases = (
            (
                "readiness_evidence",
                "readiness_evidence_valid",
            ),
            ("edge_evidence", "edge_evidence_valid"),
            ("retention_evidence", "retention_evidence_valid"),
        )

        for evidence_name, check_id in component_cases:
            with self.subTest(evidence_name=evidence_name):
                evidence = self.build_evidence()
                evidence[evidence_name]["marker"] = "forged"
                result = audit_csp_observation_evidence_closeout_v339(
                    **evidence
                )

                self.assertFalse(
                    self.checks_by_id(result)[check_id]["passed"]
                )

        evidence = self.build_evidence()
        evidence["edge_evidence"]["checks"][0]["reason_code"] = (
            "forged"
        )
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )

        self.assertFalse(
            self.checks_by_id(result)[
                "edge_evidence_valid"
            ]["passed"]
        )

    def test_extra_keys_and_forged_counts_are_rejected(self):
        evidence = self.build_evidence()
        evidence["retention_evidence"]["raw_config"] = "secret"
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )

        self.assertFalse(
            self.checks_by_id(result)[
                "retention_evidence_valid"
            ]["passed"]
        )

        evidence = self.build_evidence()
        evidence["readiness_evidence"]["ready_count"] = True
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )

        self.assertFalse(
            self.checks_by_id(result)[
                "readiness_evidence_valid"
            ]["passed"]
        )

    def test_delivery_contract_rejects_unsafe_success_claims(self):
        mutations = (
            ("mode", "plan"),
            ("response_status", 200),
            ("enforcement_absent", False),
            ("cache_control_no_store", False),
            ("log_status", "verified"),
            ("passed", 1),
        )

        for key, value in mutations:
            with self.subTest(key=key):
                evidence = self.build_evidence()
                evidence["delivery_evidence"][key] = value
                result = audit_csp_observation_evidence_closeout_v339(
                    **evidence
                )

                self.assertFalse(
                    self.checks_by_id(result)[
                        "delivery_evidence_valid"
                    ]["passed"]
                )

    def test_valid_component_evidence_reports_detected_enforcement(self):
        evidence = self.build_evidence()
        readiness = evidence["readiness_evidence"]
        enforcement_check = readiness["checks"][-1]
        enforcement_check.update(
            {
                "status": "not_ready",
                "passed": False,
                "reason_code": "enforcement_detected",
            }
        )
        readiness.update(
            {
                "status": "not_ready",
                "ready": False,
                "ready_count": 12,
                "not_ready_count": 1,
            }
        )
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )
        check = self.checks_by_id(result)["enforcement_absent"]

        self.assertFalse(check["passed"])
        self.assertEqual(
            check["reason_code"],
            "enforcement_detected",
        )

    def test_log_contract_and_smoke_linkage_are_independently_required(self):
        evidence = self.build_evidence()
        evidence["log_evidence"]["log_status"] = "not_checked"
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )

        self.assertFalse(
            self.checks_by_id(result)[
                "log_evidence_valid"
            ]["passed"]
        )

        evidence = self.build_evidence()
        alternate_plan = build_csp_smoke_plan_v338(
            target_url=(
                EXPECTED_ORIGIN_V339
                + "/__csp_reports__/"
            ),
            confirmed_remote_host="reports.example.invalid",
            smoke_id="fedcba9876543210",
            timeout_seconds=5.0,
        )
        evidence["log_evidence"]["smoke_id"] = alternate_plan.smoke_id
        evidence["log_evidence"]["expected_log_sha256"] = (
            alternate_plan.expected_log_sha256
        )
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )
        checks = self.checks_by_id(result)

        self.assertTrue(checks["log_evidence_valid"]["passed"])
        self.assertFalse(checks["smoke_evidence_linked"]["passed"])
        self.assertEqual(
            checks["smoke_evidence_linked"]["reason_code"],
            "smoke_evidence_mismatch",
        )

        evidence = self.build_evidence()
        forged_digest = "f" * 64
        evidence["delivery_evidence"][
            "expected_log_sha256"
        ] = forged_digest
        evidence["log_evidence"][
            "expected_log_sha256"
        ] = forged_digest
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )
        checks = self.checks_by_id(result)

        self.assertFalse(
            checks["delivery_evidence_valid"]["passed"]
        )
        self.assertFalse(checks["log_evidence_valid"]["passed"])

    def test_expected_origin_is_exact_https_or_loopback_http(self):
        invalid_origins = (
            "http://reports.example.invalid",
            "https://user:pass@reports.example.invalid",
            "https://reports.example.invalid/path",
            "https://reports.example.invalid?query=1",
            "https://reports.example.invalid#fragment",
            " https://reports.example.invalid",
        )

        for origin in invalid_origins:
            with self.subTest(origin=origin):
                evidence = self.build_evidence()
                evidence["expected_origin"] = origin
                result = audit_csp_observation_evidence_closeout_v339(
                    **evidence
                )

                self.assertFalse(
                    self.checks_by_id(result)[
                        "expected_origin_valid"
                    ]["passed"]
                )

        evidence = self.build_evidence()
        evidence["expected_origin"] = "http://127.0.0.1:8000"
        evidence["delivery_evidence"]["target_origin"] = (
            "http://127.0.0.1:8000"
        )
        evidence["log_evidence"]["target_origin"] = (
            "http://127.0.0.1:8000"
        )
        result = audit_csp_observation_evidence_closeout_v339(
            **evidence
        )

        self.assertTrue(result["ready"])

    def write_evidence_files(self, directory, evidence):
        paths = {}

        for argument, evidence_name in (
            ("--readiness-json", "readiness_evidence"),
            ("--edge-json", "edge_evidence"),
            ("--retention-json", "retention_evidence"),
            ("--delivery-json", "delivery_evidence"),
            ("--log-json", "log_evidence"),
        ):
            path = directory / f"{evidence_name}.json"
            path.write_text(
                json.dumps(evidence[evidence_name]),
                encoding="utf-8",
            )
            paths[argument] = path

        return paths

    def cli_arguments(self, paths, *, expected_origin):
        arguments = []

        for option, path in paths.items():
            arguments.extend((option, str(path)))

        arguments.extend(
            (
                "--expected-origin",
                expected_origin,
                "--json",
                "--strict",
            )
        )

        return arguments

    def test_strict_json_cli_accepts_only_sanitized_linked_evidence(self):
        evidence = self.build_evidence()

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths = self.write_evidence_files(directory, evidence)
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    self.cli_arguments(
                        paths,
                        expected_origin=EXPECTED_ORIGIN_V339,
                    )
                )

        rendered = stdout.getvalue()
        payload = json.loads(rendered)

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ready"])

        for forbidden in (
            EXPECTED_ORIGIN_V339,
            SMOKE_ID_V339,
            evidence["delivery_evidence"][
                "expected_log_sha256"
            ],
            "target_origin",
            "smoke_id",
            "expected_log_sha256",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, rendered)

    def test_unreadable_and_oversized_evidence_fail_without_echo(self):
        evidence = self.build_evidence()

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            paths = self.write_evidence_files(directory, evidence)
            secret = "raw-secret-that-must-not-be-echoed"
            paths["--edge-json"].write_text(
                "{invalid-" + secret,
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    self.cli_arguments(
                        paths,
                        expected_origin=EXPECTED_ORIGIN_V339,
                    )
                )

            oversized = directory / "oversized.json"
            oversized.write_bytes(
                b"x" * (CSP_CLOSEOUT_EVIDENCE_MAX_BYTES_V339 + 1)
            )

            self.assertIsNone(_read_evidence_v339(oversized))

        self.assertEqual(exit_code, 1)
        self.assertNotIn(secret, stdout.getvalue())
        self.assertIn(
            "edge_evidence_invalid",
            stdout.getvalue(),
        )

    def test_audit_source_has_no_network_write_database_or_mutation_path(self):
        source = (
            self.backend_dir
            / "scripts"
            / "check_csp_observation_evidence_closeout_v339.py"
        ).read_text(encoding="utf-8")

        for forbidden in (
            "requests.",
            "urllib.request",
            "socket.",
            "subprocess",
            "os.environ",
            "write_text(",
            "write_bytes(",
            ".objects",
            "CSP_REPORT_ONLY_ENABLED =",
            "CSP_REPORT_INGESTION_ENABLED =",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

        self.assertIn("read_only", source)
        self.assertIn('path.open("rb")', source)
        self.assertIn(
            "CSP_CLOSEOUT_EVIDENCE_MAX_BYTES_V339 + 1",
            source,
        )
        self.assertNotIn("target_origin", json.dumps(
            audit_csp_observation_evidence_closeout_v339(
                **self.build_evidence()
            )
        ))

    def test_v339_adds_no_database_migration(self):
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
                    "*v339*.py"
                )
            )

        self.assertEqual(matches, [])
