import json
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from config.csp_observation_readiness_v335 import (
    CSP_OBSERVATION_BUILT_IN_REPORT_URI_V335,
    CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335,
    CSP_OBSERVATION_READINESS_CHECK_IDS_V335,
    CSP_OBSERVATION_READINESS_CHECK_KEYS_V335,
    CSP_OBSERVATION_READINESS_REASON_CODES_V335,
    CSP_OBSERVATION_READINESS_RESULT_KEYS_V335,
    _info_log_delivery_configured_v335,
    _synthetic_contract_packaged_v335,
    get_csp_observation_readiness_v335,
)


DEFAULT_OFF_SETTINGS_V335 = {
    "CSP_REPORT_ONLY_ENABLED": False,
    "CSP_REPORT_ONLY_REPORT_URI": "",
    "CSP_REPORT_INGESTION_ENABLED": False,
    "CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED": False,
    "CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED": False,
    "CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED": False,
}
PRODUCTION_READY_SETTINGS_V335 = {
    "CSP_REPORT_ONLY_ENABLED": True,
    "CSP_REPORT_ONLY_REPORT_URI": "/__csp_reports__/",
    "CSP_REPORT_INGESTION_ENABLED": True,
    "CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED": True,
    "CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED": True,
    "CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED": True,
}


@override_settings(**DEFAULT_OFF_SETTINGS_V335)
class CspObservationOperationalReadinessV335Tests(SimpleTestCase):
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

    def test_marker_and_sanitized_result_contract_are_exact(self):
        result = get_csp_observation_readiness_v335()

        self.assertEqual(
            CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335,
            "CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335",
        )
        self.assertEqual(
            CSP_OBSERVATION_BUILT_IN_REPORT_URI_V335,
            "/__csp_reports__/",
        )
        self.assertEqual(
            tuple(result),
            CSP_OBSERVATION_READINESS_RESULT_KEYS_V335,
        )
        self.assertEqual(
            tuple(result["checks"][0]),
            CSP_OBSERVATION_READINESS_CHECK_KEYS_V335,
        )
        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            CSP_OBSERVATION_READINESS_CHECK_IDS_V335,
        )
        self.assertTrue(
            {
                check["reason_code"]
                for check in result["checks"]
            }.issubset(
                set(CSP_OBSERVATION_READINESS_REASON_CODES_V335)
            )
        )

    def test_default_off_configuration_fails_closed_with_exact_blockers(self):
        result = get_csp_observation_readiness_v335()
        failed_ids = {
            check["check_id"]
            for check in result["checks"]
            if not check["passed"]
        }

        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "not_ready")
        self.assertTrue(result["read_only"])
        self.assertEqual(result["ready_count"], 7)
        self.assertEqual(result["not_ready_count"], 6)
        self.assertEqual(
            failed_ids,
            {
                "report_only_enabled",
                "ingestion_enabled",
                "built_in_report_uri_selected",
                "edge_rate_limit_approved",
                "log_governance_approved",
                "synthetic_delivery_verified",
            },
        )

    @override_settings(**PRODUCTION_READY_SETTINGS_V335)
    def test_reviewed_production_like_configuration_is_ready(self):
        result = get_csp_observation_readiness_v335()

        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(
            result["ready_count"],
            len(CSP_OBSERVATION_READINESS_CHECK_IDS_V335),
        )
        self.assertEqual(result["not_ready_count"], 0)
        self.assertTrue(
            all(check["passed"] for check in result["checks"])
        )

    def test_each_external_attestation_is_independently_required(self):
        attestation_checks = (
            (
                "CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED",
                "edge_rate_limit_approved",
                "edge_rate_limit_not_approved",
            ),
            (
                "CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED",
                "log_governance_approved",
                "log_governance_not_approved",
            ),
            (
                "CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED",
                "synthetic_delivery_verified",
                "synthetic_delivery_not_verified",
            ),
        )

        for setting_name, check_id, reason_code in attestation_checks:
            configured = {
                **PRODUCTION_READY_SETTINGS_V335,
                setting_name: False,
            }

            with self.subTest(setting_name=setting_name):
                with override_settings(**configured):
                    result = get_csp_observation_readiness_v335()

                check = self.checks_by_id(result)[check_id]
                self.assertFalse(result["ready"])
                self.assertFalse(check["passed"])
                self.assertEqual(check["reason_code"], reason_code)

    @override_settings(
        **{
            **PRODUCTION_READY_SETTINGS_V335,
            "CSP_REPORT_ONLY_REPORT_URI": (
                "https://collector.example.invalid/csp"
            ),
        }
    )
    def test_external_collector_does_not_claim_built_in_readiness(self):
        result = get_csp_observation_readiness_v335()
        check = self.checks_by_id(result)[
            "built_in_report_uri_selected"
        ]

        self.assertFalse(result["ready"])
        self.assertFalse(check["passed"])
        self.assertEqual(
            check["reason_code"],
            "built_in_report_uri_not_selected",
        )

    def test_info_log_delivery_check_rejects_dropped_info_events(self):
        warning_logging = {
            "version": 1,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": "WARNING",
            },
        }
        missing_handler_logging = {
            "version": 1,
            "handlers": {},
            "root": {
                "handlers": ["missing"],
                "level": "INFO",
            },
        }

        with override_settings(LOGGING=warning_logging):
            self.assertFalse(_info_log_delivery_configured_v335())

        with override_settings(LOGGING=missing_handler_logging):
            self.assertFalse(_info_log_delivery_configured_v335())

        self.assertTrue(_info_log_delivery_configured_v335())

    def test_synthetic_contract_discards_private_report_material(self):
        self.assertTrue(_synthetic_contract_packaged_v335())

        source = (
            self.backend_dir
            / "config"
            / "csp_observation_readiness_v335.py"
        ).read_text(encoding="utf-8")

        self.assertIn("synthetic-secret-sample", source)
        self.assertIn("secret not in serialized", source)

    def test_audit_source_has_no_network_database_or_report_emission(self):
        audit_source = (
            self.backend_dir
            / "config"
            / "csp_observation_readiness_v335.py"
        ).read_text(encoding="utf-8")
        command_source = (
            self.backend_dir
            / "pages"
            / "management"
            / "commands"
            / "check_csp_observation_readiness_v335.py"
        ).read_text(encoding="utf-8")
        combined = audit_source + command_source

        for forbidden in (
            ".objects",
            "requests.",
            "urllib.",
            "Client(",
            "logger.",
            "csp_report_ingestion_v334(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, combined)

        self.assertIn("read_only", audit_source)
        self.assertIn("without network access", command_source)

    def test_text_and_json_commands_are_deterministic_and_sanitized(self):
        text_output = StringIO()
        json_output = StringIO()

        call_command(
            "check_csp_observation_readiness_v335",
            stdout=text_output,
        )
        call_command(
            "check_csp_observation_readiness_v335",
            "--json",
            stdout=json_output,
        )

        rendered_text = text_output.getvalue()
        payload = json.loads(json_output.getvalue())

        self.assertIn(
            CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335,
            rendered_text,
        )
        self.assertIn("status=not_ready", rendered_text)
        self.assertIn("read_only=true", rendered_text)
        self.assertEqual(
            payload,
            get_csp_observation_readiness_v335(),
        )
        self.assertNotIn("document-secret", json_output.getvalue())
        self.assertNotIn("source-secret", json_output.getvalue())

    def test_strict_command_fails_closed_and_passes_when_ready(self):
        with self.assertRaisesMessage(
            CommandError,
            "CSP observation operational-readiness audit failed.",
        ):
            call_command(
                "check_csp_observation_readiness_v335",
                "--strict",
                stdout=StringIO(),
                stderr=StringIO(),
            )

        with override_settings(**PRODUCTION_READY_SETTINGS_V335):
            call_command(
                "check_csp_observation_readiness_v335",
                "--strict",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_environment_contracts_are_declared_default_off(self):
        settings_source = (
            self.backend_dir / "config" / "settings.py"
        ).read_text(encoding="utf-8")

        environment_names = (
            "DJANGO_CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED",
            "DJANGO_CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED",
            "DJANGO_CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED",
        )

        for name in environment_names:
            with self.subTest(name=name):
                self.assertIn(name, settings_source)

        self.assertFalse(
            settings.CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED
        )
        self.assertFalse(
            settings.CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED
        )
        self.assertFalse(
            settings.CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED
        )

    def test_v335_adds_no_database_migration(self):
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
                    "*v335*.py"
                )
            )

        self.assertEqual(matches, [])
