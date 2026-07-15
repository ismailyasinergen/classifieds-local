from __future__ import annotations

import ast
import json
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import (
    SimpleTestCase,
    override_settings,
)

from listings.saved_search_notification_production_readiness import (
    READINESS_CHECK_IDS,
    READINESS_CHECK_RESULT_KEYS,
    READINESS_REASON_CODES,
    READINESS_RESULT_KEYS,
    READINESS_STATUS_VALUES,
    REJECTED_EMAIL_BACKEND_PREFIXES,
    V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS,
    get_saved_search_notification_production_readiness,
)


V245_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "saved_search_notification_production_readiness.py"
    ),
    (
        "backend/listings/management/commands/"
        "check_saved_search_notification_production_readiness.py"
    ),
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_v245.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "operational_readiness_v245.md"
    ),
)

NEXT_CHECKPOINT = "v246: saved-search notification production delivery operational readiness closeout audit"

PRODUCTION_LIKE_SETTINGS = {
    "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED": True,
    "EMAIL_BACKEND": (
        "project.production_mail."
        "ProductionEmailBackend"
    ),
    "DEFAULT_FROM_EMAIL": (
        "saved-search-alerts@example.invalid"
    ),
}

PROTECTED_RUNTIME_PATHS = (
    "config/settings.py",
    "listings/saved_search_notification_email_sender.py",
    (
        "listings/management/commands/"
        "process_saved_search_notifications.py"
    ),
    "listings/saved_search_notification_scheduler.py",
    "listings/saved_search_notifications.py",
    "listings/saved_search_notification_audit_runtime.py",
    "listings/saved_search_notification_audit_persistence.py",
    "listings/saved_search_notification_audit.py",
    "listings/saved_search_notification_email_renderer.py",
    "listings/models.py",
    "listings/admin.py",
    "listings/urls.py",
    "templates/base.html",
    (
        "listings/templates/listings/"
        "saved_search_notification_audit_events.html"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_contract_v244.py"
    ),
)


class SavedSearchNotificationProductionDeliveryOperationalReadinessV245Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _read_backend(
        self,
        relative_path: str,
    ) -> str:
        return (
            self._backend_root()
            / relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def _checks_by_id(
        self,
        result,
    ):
        return {
            check["check_id"]: check
            for check in result["checks"]
        }

    def test_v245_marker_scope_and_next_lane_are_stable(self):
        self.assertEqual(
            V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS,
            (
                "V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATIONAL_READINESS"
            ),
        )

        self.assertEqual(
            len(V245_ALLOWED_SCOPE),
            4,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v246: saved-search notification production "
                "delivery operational readiness closeout audit"
            ),
        )

    def test_v245_result_and_check_contracts_are_exact(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        self.assertEqual(
            tuple(result),
            READINESS_RESULT_KEYS,
        )

        self.assertEqual(
            tuple(
                result["checks"][0]
            ),
            READINESS_CHECK_RESULT_KEYS,
        )

        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            READINESS_CHECK_IDS,
        )

        self.assertTrue(
            {
                check["status"]
                for check in result["checks"]
            }.issubset(
                set(READINESS_STATUS_VALUES)
            )
        )

        self.assertTrue(
            {
                check["reason_code"]
                for check in result["checks"]
            }.issubset(
                set(READINESS_REASON_CODES)
            )
        )

    def test_v245_default_development_configuration_is_not_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        checks = self._checks_by_id(
            result
        )

        self.assertFalse(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "not_ready",
        )

        self.assertFalse(
            checks["feature_gate_enabled"]["passed"]
        )

        self.assertEqual(
            checks["feature_gate_enabled"]["reason_code"],
            "feature_gate_disabled",
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v245_production_like_configuration_is_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        self.assertTrue(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "ready",
        )

        self.assertEqual(
            result["ready_count"],
            len(READINESS_CHECK_IDS),
        )

        self.assertEqual(
            result["not_ready_count"],
            0,
        )

        self.assertEqual(
            result["warning_count"],
            0,
        )

        self.assertTrue(
            all(
                check["passed"]
                for check in result["checks"]
            )
        )

    def test_v245_known_nonproduction_backends_are_rejected(self):
        rejected_backends = (
            "django.core.mail.backends.locmem.EmailBackend",
            "django.core.mail.backends.dummy.EmailBackend",
            "django.core.mail.backends.console.EmailBackend",
            "django.core.mail.backends.filebased.EmailBackend",
        )

        self.assertEqual(
            len(REJECTED_EMAIL_BACKEND_PREFIXES),
            4,
        )

        for backend_path in rejected_backends:
            with self.subTest(
                backend_path=backend_path
            ):
                with override_settings(
                    SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
                    EMAIL_BACKEND=backend_path,
                    DEFAULT_FROM_EMAIL=(
                        "alerts@example.invalid"
                    ),
                ):
                    result = (
                        get_saved_search_notification_production_readiness()
                    )

                check = self._checks_by_id(
                    result
                )["email_backend_allowed"]

                self.assertFalse(
                    check["passed"]
                )

                self.assertEqual(
                    check["reason_code"],
                    "email_backend_rejected",
                )

    @override_settings(
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
        EMAIL_BACKEND=(
            "project.production_mail."
            "ProductionEmailBackend"
        ),
        DEFAULT_FROM_EMAIL="",
    )
    def test_v245_missing_default_sender_is_not_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        check = self._checks_by_id(
            result
        )["default_sender_configured"]

        self.assertFalse(
            result["ready"]
        )

        self.assertFalse(
            check["passed"]
        )

        self.assertEqual(
            check["reason_code"],
            "default_sender_missing",
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v245_readiness_result_is_deterministic(self):
        first = (
            get_saved_search_notification_production_readiness()
        )

        second = (
            get_saved_search_notification_production_readiness()
        )

        self.assertEqual(
            first,
            second,
        )

    @override_settings(
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
        EMAIL_BACKEND=(
            "private.provider."
            "SecretBackend"
        ),
        DEFAULT_FROM_EMAIL=(
            "private-sender@example.invalid"
        ),
    )
    def test_v245_human_command_output_is_sanitized(self):
        stdout = StringIO()

        call_command(
            "check_saved_search_notification_production_readiness",
            stdout=stdout,
        )

        output = stdout.getvalue()

        self.assertIn(
            "status=ready",
            output,
        )

        self.assertIn(
            "check=email_backend_allowed",
            output,
        )

        for forbidden in (
            "private.provider.SecretBackend",
            "private-sender@example.invalid",
            "EMAIL_HOST_PASSWORD",
            "SMTP_PASSWORD",
            "api_key",
            "token",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    output,
                )

    @override_settings(
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
        EMAIL_BACKEND=(
            "private.provider."
            "SecretBackend"
        ),
        DEFAULT_FROM_EMAIL=(
            "private-json-sender@example.invalid"
        ),
    )
    def test_v245_json_command_output_is_sanitized(self):
        stdout = StringIO()

        call_command(
            "check_saved_search_notification_production_readiness",
            "--json",
            stdout=stdout,
        )

        raw_output = stdout.getvalue().strip()

        payload = json.loads(
            raw_output
        )

        self.assertEqual(
            tuple(payload),
            tuple(
                sorted(
                    READINESS_RESULT_KEYS
                )
            ),
        )

        self.assertTrue(
            payload["ready"]
        )

        for forbidden in (
            "private.provider.SecretBackend",
            "private-json-sender@example.invalid",
            "password",
            "credential",
            "provider_response",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    raw_output.casefold(),
                )

    @override_settings(
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=False,
        EMAIL_BACKEND=(
            "project.production_mail."
            "ProductionEmailBackend"
        ),
        DEFAULT_FROM_EMAIL=(
            "alerts@example.invalid"
        ),
    )
    def test_v245_strict_mode_fails_closed_when_not_ready(self):
        stdout = StringIO()

        with self.assertRaises(
            CommandError
        ):
            call_command(
                "check_saved_search_notification_production_readiness",
                "--strict",
                stdout=stdout,
            )

        output = stdout.getvalue()

        self.assertIn(
            "status=not_ready",
            output,
        )

        self.assertNotIn(
            "alerts@example.invalid",
            output,
        )

    @override_settings(
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=False,
        EMAIL_BACKEND=(
            "project.production_mail."
            "ProductionEmailBackend"
        ),
        DEFAULT_FROM_EMAIL=(
            "alerts@example.invalid"
        ),
    )
    def test_v245_non_strict_mode_reports_without_failing(self):
        stdout = StringIO()

        result = call_command(
            "check_saved_search_notification_production_readiness",
            stdout=stdout,
        )

        self.assertIsNone(
            result
        )

        self.assertIn(
            "status=not_ready",
            stdout.getvalue(),
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v245_command_never_opens_email_connection(self):
        stdout = StringIO()

        with patch(
            "django.core.mail.get_connection"
        ) as get_connection:
            call_command(
                "check_saved_search_notification_production_readiness",
                stdout=stdout,
            )

        get_connection.assert_not_called()

    def test_v245_service_source_is_read_only(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_production_readiness.py"
        )

        forbidden_terms = (
            "from listings.models",
            "import listings.models",
            "from django.db",
            "import django.db",
            ".objects.",
            "get_connection(",
            "send_mail(",
            "EmailMessage(",
            "EmailMultiAlternatives(",
            "SavedSearchNotificationAuditEvent",
            "transaction.atomic",
        )

        for term in forbidden_terms:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

        credential_terms = (
            "EMAIL_HOST_PASSWORD",
            "EMAIL_HOST_USER",
            "SMTP_PASSWORD",
            "API_KEY",
            "ACCESS_TOKEN",
        )

        for term in credential_terms:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v245_command_source_has_only_report_options(self):
        source = self._read_backend(
            "listings/management/commands/"
            "check_saved_search_notification_production_readiness.py"
        )

        tree = ast.parse(
            source
        )

        option_strings = {
            argument.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        }

        self.assertEqual(
            option_strings,
            {
                "--strict",
                "--json",
            },
        )

        forbidden_terms = (
            "--execute-production-send",
            "--confirm-production-delivery",
            "--owner-id",
            "--limit",
            "send_saved_search_notification_email_production",
            "SavedSearchNotificationAuditEvent",
            "from listings.models",
            "from django.db",
        )

        for term in forbidden_terms:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v245_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS
        )

        for relative_path in PROTECTED_RUNTIME_PATHS:
            source = self._read_backend(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_v245_no_migration_0017_exists(self):
        migration_directory = (
            self._backend_root()
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )
