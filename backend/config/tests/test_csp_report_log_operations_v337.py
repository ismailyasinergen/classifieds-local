import json
import logging
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from config.csp_observation_readiness_v335 import (
    _info_log_delivery_configured_v335,
)
from config.csp_report_ingestion_v334 import (
    CSP_REPORT_LOGGER_NAME_V334,
    sanitize_csp_report_v334,
)
from config.csp_report_logging_v337 import (
    CSP_REPORT_EVIDENCE_EXTRA_V337,
    CSP_REPORT_EVIDENCE_KEYS_V337,
    CSP_REPORT_LOG_EVENT_V337,
    CSP_REPORT_LOG_OPERATIONS_BASELINE_V337,
    CSP_REPORT_LOG_REJECTED_EVENT_V337,
    CSP_REPORT_LOG_SCHEMA_VERSION_V337,
    SanitizedCspReportFormatterV337,
)
from scripts.check_csp_report_log_retention_v337 import (
    CSP_REPORT_COMPOSE_JSON_MAX_BYTES_V337,
    CSP_REPORT_LOG_RETENTION_CHECK_IDS_V337,
    CSP_REPORT_LOG_RETENTION_CHECK_KEYS_V337,
    CSP_REPORT_LOG_RETENTION_REASON_CODES_V337,
    CSP_REPORT_LOG_RETENTION_RESULT_KEYS_V337,
    CSP_REPORT_LOG_RETENTION_VALIDATOR_V337,
    _read_bounded_v337,
    audit_csp_report_log_retention_v337,
)


VALID_COMPOSE_PAYLOAD_V337 = {
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


def valid_evidence_v337():
    return {
        "media_type": "application/csp-report",
        "report_index": 1,
        **sanitize_csp_report_v334(
            {
                "document-uri": (
                    "https://testserver/private/page"
                    "?token=document-secret"
                ),
                "blocked-uri": "inline",
                "effective-directive": "script-src-attr",
                "violated-directive": "script-src-attr 'none'",
                "source-file": (
                    "https://testserver/private/source.js"
                    "?token=source-secret"
                ),
                "line-number": 17,
                "column-number": 4,
                "status-code": 200,
                "disposition": "report",
            }
        ),
    }


def log_record_v337(*, evidence=None, message="raw-message-secret"):
    record = logging.LogRecord(
        name=CSP_REPORT_LOGGER_NAME_V334,
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )

    if evidence is not None:
        setattr(
            record,
            CSP_REPORT_EVIDENCE_EXTRA_V337,
            evidence,
        )

    return record


class CspReportLogOperationsV337Tests(SimpleTestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.backend_dir = Path(settings.BASE_DIR)
        cls.formatter = SanitizedCspReportFormatterV337()

    def retention_checks_by_id(self, result):
        return {
            check["check_id"]: check
            for check in result["checks"]
        }

    def test_validated_evidence_formats_as_exact_bounded_json(self):
        evidence = valid_evidence_v337()
        rendered = self.formatter.format(
            log_record_v337(evidence=evidence)
        )
        payload = json.loads(rendered)

        self.assertTrue(CSP_REPORT_LOG_OPERATIONS_BASELINE_V337)
        self.assertEqual(
            tuple(evidence),
            CSP_REPORT_EVIDENCE_KEYS_V337,
        )
        self.assertEqual(
            payload,
            {
                "event": CSP_REPORT_LOG_EVENT_V337,
                "evidence": evidence,
                "schema_version": (
                    CSP_REPORT_LOG_SCHEMA_VERSION_V337
                ),
            },
        )
        self.assertLess(len(rendered.encode("utf-8")), 2048)

        for secret in (
            "raw-message-secret",
            "private",
            "document-secret",
            "source-secret",
        ):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, rendered)

    def test_missing_or_invalid_evidence_rejects_without_raw_fallback(self):
        invalid_cases = (
            None,
            {"unexpected": "raw-secret"},
            {
                **valid_evidence_v337(),
                "media_type": "application/json",
            },
            {
                **valid_evidence_v337(),
                "blocked_resource": (
                    "https://example.invalid/private?secret=yes"
                ),
            },
            {
                **valid_evidence_v337(),
                "effective_directive": "invalid directive",
            },
            {
                **valid_evidence_v337(),
                "report_index": 11,
            },
            {
                **valid_evidence_v337(),
                "status_code": 600,
            },
        )

        for evidence in invalid_cases:
            with self.subTest(evidence=evidence):
                rendered = self.formatter.format(
                    log_record_v337(
                        evidence=evidence,
                        message="never-log-this-raw-secret",
                    )
                )

                self.assertEqual(
                    json.loads(rendered),
                    {
                        "event": (
                            CSP_REPORT_LOG_REJECTED_EVENT_V337
                        ),
                        "schema_version": (
                            CSP_REPORT_LOG_SCHEMA_VERSION_V337
                        ),
                    },
                )
                self.assertNotIn("raw-secret", rendered)
                self.assertNotIn("never-log-this", rendered)

    def test_exception_and_format_arguments_are_not_rendered(self):
        evidence = valid_evidence_v337()
        record = logging.LogRecord(
            name=CSP_REPORT_LOGGER_NAME_V334,
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="raw %s",
            args=("argument-secret",),
            exc_info=(
                RuntimeError,
                RuntimeError("exception-secret"),
                None,
            ),
        )
        setattr(
            record,
            CSP_REPORT_EVIDENCE_EXTRA_V337,
            evidence,
        )
        rendered = self.formatter.format(record)

        self.assertNotIn("argument-secret", rendered)
        self.assertNotIn("exception-secret", rendered)
        self.assertEqual(
            json.loads(rendered)["evidence"],
            evidence,
        )

    def test_settings_route_csp_events_to_dedicated_stdout_only(self):
        formatter_config = settings.LOGGING["formatters"][
            "csp_report_v337"
        ]
        handler_config = settings.LOGGING["handlers"][
            "csp_report_console_v337"
        ]
        logger_config = settings.LOGGING["loggers"][
            CSP_REPORT_LOGGER_NAME_V334
        ]

        self.assertEqual(
            formatter_config["()"],
            (
                "config.csp_report_logging_v337."
                "SanitizedCspReportFormatterV337"
            ),
        )
        self.assertEqual(
            handler_config,
            {
                "class": "logging.StreamHandler",
                "formatter": "csp_report_v337",
                "level": "INFO",
                "stream": "ext://sys.stdout",
            },
        )
        self.assertEqual(
            logger_config,
            {
                "handlers": ["csp_report_console_v337"],
                "level": "INFO",
                "propagate": False,
            },
        )
        self.assertNotIn(
            "csp_report_console_v337",
            settings.LOGGING["root"]["handlers"],
        )
        self.assertTrue(_info_log_delivery_configured_v335())

    def test_ingestion_attaches_sanitized_evidence_to_log_record(self):
        source = (
            self.backend_dir
            / "config"
            / "csp_report_ingestion_v334.py"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "CSP_REPORT_EVIDENCE_EXTRA_V337: evidence",
            source,
        )
        self.assertNotIn("request.body", source)

    def test_retention_validator_ready_contract_is_exact(self):
        result = audit_csp_report_log_retention_v337(
            json.dumps(VALID_COMPOSE_PAYLOAD_V337)
        )

        self.assertEqual(
            CSP_REPORT_LOG_RETENTION_VALIDATOR_V337,
            "CSP_REPORT_LOG_RETENTION_VALIDATOR_V337",
        )
        self.assertEqual(
            tuple(result),
            CSP_REPORT_LOG_RETENTION_RESULT_KEYS_V337,
        )
        self.assertEqual(
            tuple(result["checks"][0]),
            CSP_REPORT_LOG_RETENTION_CHECK_KEYS_V337,
        )
        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            CSP_REPORT_LOG_RETENTION_CHECK_IDS_V337,
        )
        self.assertTrue(
            {
                check["reason_code"]
                for check in result["checks"]
            }.issubset(
                set(CSP_REPORT_LOG_RETENTION_REASON_CODES_V337)
            )
        )
        self.assertTrue(result["ready"])
        self.assertTrue(result["read_only"])
        self.assertEqual(result["ready_count"], 7)
        self.assertEqual(result["not_ready_count"], 0)

    def test_retention_validator_rejects_unreadable_or_invalid_json(self):
        unreadable = audit_csp_report_log_retention_v337(None)
        invalid = audit_csp_report_log_retention_v337("{")

        self.assertFalse(unreadable["ready"])
        self.assertEqual(
            self.retention_checks_by_id(unreadable)[
                "compose_json_readable"
            ]["reason_code"],
            "compose_json_unreadable",
        )
        self.assertFalse(invalid["ready"])
        self.assertEqual(
            self.retention_checks_by_id(invalid)[
                "compose_json_valid"
            ]["reason_code"],
            "compose_json_invalid",
        )

    def test_each_retention_control_is_required(self):
        cases = (
            (
                "driver",
                "json-file",
                "local_driver_selected",
                "local_driver_missing",
            ),
            (
                "max-size",
                "100m",
                "rotation_size_bounded",
                "rotation_size_missing",
            ),
            (
                "max-file",
                "10",
                "rotation_file_count_bounded",
                "rotation_file_count_missing",
            ),
            (
                "compress",
                "false",
                "rotation_compression_enabled",
                "rotation_compression_missing",
            ),
        )

        for key, value, check_id, reason in cases:
            with self.subTest(check_id=check_id):
                payload = json.loads(
                    json.dumps(VALID_COMPOSE_PAYLOAD_V337)
                )
                logging_config = payload["services"]["web"]["logging"]

                if key == "driver":
                    logging_config[key] = value
                else:
                    logging_config["options"][key] = value

                result = audit_csp_report_log_retention_v337(
                    json.dumps(payload)
                )
                check = self.retention_checks_by_id(result)[check_id]

                self.assertFalse(result["ready"])
                self.assertFalse(check["passed"])
                self.assertEqual(check["reason_code"], reason)

    def test_retention_reader_is_bounded_and_missing_path_is_safe(self):
        missing = self.backend_dir / "missing-v337-compose.json"

        self.assertEqual(
            CSP_REPORT_COMPOSE_JSON_MAX_BYTES_V337,
            1024 * 1024,
        )
        self.assertIsNone(_read_bounded_v337(missing))

    def test_v337_sources_have_no_network_write_or_docker_mutation(self):
        formatter_source = (
            self.backend_dir
            / "config"
            / "csp_report_logging_v337.py"
        ).read_text(encoding="utf-8")
        validator_source = (
            self.backend_dir
            / "scripts"
            / "check_csp_report_log_retention_v337.py"
        ).read_text(encoding="utf-8")
        combined = formatter_source + validator_source

        for forbidden in (
            "requests.",
            "urllib.",
            "write_text(",
            "open(",
            "subprocess",
            "docker compose",
            ".objects",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, combined)

        self.assertIn("read_bytes(", validator_source)
        self.assertNotIn("record.getMessage()", formatter_source)

    def test_v337_adds_no_database_migration(self):
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
                    "*v337*.py"
                )
            )

        self.assertEqual(matches, [])
