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


V246_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CLOSEOUT_AUDIT = (
    "V246_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CLOSEOUT_AUDIT"
)

V245_COMMITTED_SCOPE = (
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

V246_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_closeout_audit_v246.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "operational_readiness_closeout_audit_v246.md"
    ),
)

CLOSEOUT_GATES = (
    "v244 readiness contract remains packaged",
    "v245 readiness implementation remains packaged",
    "v245 implementation scope remains exactly four files",
    "v246 scope remains exactly two audit files",
    "default development configuration reports not_ready",
    "production-like configuration reports ready",
    "readiness result keys remain stable",
    "readiness check keys remain stable",
    "nine stable readiness check identifiers remain packaged",
    "stable sanitized reason codes remain packaged",
    "known nonproduction email backends remain rejected",
    "missing default sender remains not_ready",
    "readiness results remain deterministic",
    "human command output remains sanitized",
    "JSON command output remains sanitized",
    "strict mode remains fail closed",
    "non-strict mode remains report only",
    "readiness service remains read only",
    "readiness command remains read only",
    "readiness execution performs no database access",
    "readiness execution performs no database mutation",
    "readiness execution writes no audit event",
    "readiness execution renders no email",
    "readiness execution sends no email",
    "readiness execution opens no provider connection",
    "provider credentials are never read or printed",
    "raw backend paths and sender values are never printed",
    "production sender remains unchanged",
    "production delivery command remains unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v247: saved-search notification production delivery operator runbook contract"

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

PROTECTED_BACKEND_PATHS = (
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
        "saved_search_notification_production_readiness.py"
    ),
    (
        "listings/management/commands/"
        "check_saved_search_notification_production_readiness.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_v245.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_contract_v244.py"
    ),
)


class SavedSearchNotificationProductionDeliveryOperationalReadinessCloseoutAuditV246Tests(
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

    def test_v246_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V246_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CLOSEOUT_AUDIT,
            (
                "V246_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATIONAL_READINESS_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V245_COMMITTED_SCOPE),
            4,
        )

        self.assertEqual(
            len(V246_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v247: saved-search notification production "
                "delivery operator runbook contract"
            ),
        )

    def test_v246_public_contract_values_remain_exact(self):
        self.assertEqual(
            V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS,
            (
                "V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATIONAL_READINESS"
            ),
        )

        self.assertEqual(
            READINESS_STATUS_VALUES,
            (
                "ready",
                "not_ready",
                "warning",
            ),
        )

        self.assertEqual(
            READINESS_RESULT_KEYS,
            (
                "marker",
                "status",
                "ready",
                "checks",
                "ready_count",
                "not_ready_count",
                "warning_count",
            ),
        )

        self.assertEqual(
            READINESS_CHECK_RESULT_KEYS,
            (
                "check_id",
                "status",
                "passed",
                "reason_code",
            ),
        )

    def test_v246_nine_stable_check_identifiers_remain_packaged(self):
        self.assertEqual(
            READINESS_CHECK_IDS,
            (
                "feature_gate_declared",
                "feature_gate_enabled",
                "email_backend_configured",
                "email_backend_allowed",
                "default_sender_configured",
                "double_confirmation_packaged",
                "owner_scope_packaged",
                "explicit_limit_packaged",
                "batch_cap_packaged",
            ),
        )

    def test_v246_stable_reason_codes_remain_sanitized(self):
        self.assertEqual(
            READINESS_REASON_CODES,
            (
                "ready",
                "feature_gate_missing",
                "feature_gate_disabled",
                "email_backend_missing",
                "email_backend_rejected",
                "default_sender_missing",
                "delivery_confirmation_missing",
                "owner_scope_missing",
                "explicit_limit_missing",
                "batch_cap_mismatch",
            ),
        )

        serialized = repr(
            READINESS_REASON_CODES
        ).casefold()

        for forbidden in (
            "password",
            "secret",
            "credential",
            "recipient",
            "querystring",
            "email_body",
            "provider_response",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden,
                    serialized,
                )

    def test_v246_default_configuration_reports_not_ready_safely(self):
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

        self.assertEqual(
            result["ready_count"]
            + result["not_ready_count"]
            + result["warning_count"],
            len(READINESS_CHECK_IDS),
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v246_production_like_configuration_reports_ready(self):
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

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v246_readiness_result_is_deterministic(self):
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

        self.assertEqual(
            tuple(first),
            READINESS_RESULT_KEYS,
        )

        self.assertEqual(
            tuple(first["checks"][0]),
            READINESS_CHECK_RESULT_KEYS,
        )

    def test_v246_known_nonproduction_backends_remain_rejected(self):
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
                    result["ready"]
                )

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
    def test_v246_missing_default_sender_remains_not_ready(self):
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
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
        EMAIL_BACKEND=(
            "private.provider."
            "PrivateBackend"
        ),
        DEFAULT_FROM_EMAIL=(
            "private-sender@example.invalid"
        ),
    )
    def test_v246_human_output_remains_sanitized(self):
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
            "private.provider.PrivateBackend",
            "private-sender@example.invalid",
            "EMAIL_HOST_PASSWORD",
            "SMTP_PASSWORD",
            "API_KEY",
            "ACCESS_TOKEN",
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
            "PrivateBackend"
        ),
        DEFAULT_FROM_EMAIL=(
            "private-json-sender@example.invalid"
        ),
    )
    def test_v246_json_output_remains_sanitized(self):
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
            set(payload),
            set(READINESS_RESULT_KEYS),
        )

        self.assertTrue(
            payload["ready"]
        )

        self.assertEqual(
            len(payload["checks"]),
            len(READINESS_CHECK_IDS),
        )

        for forbidden in (
            "private.provider.PrivateBackend",
            "private-json-sender@example.invalid",
            "password",
            "credential",
            "provider_response",
        ):
            with self.subTest(
                forbidden=forbidden
            ):
                self.assertNotIn(
                    forbidden.casefold(),
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
    def test_v246_strict_mode_remains_fail_closed(self):
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
    def test_v246_non_strict_mode_remains_report_only(self):
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
    def test_v246_command_opens_no_email_connection(self):
        stdout = StringIO()

        with patch(
            "django.core.mail.get_connection"
        ) as get_connection:
            call_command(
                "check_saved_search_notification_production_readiness",
                stdout=stdout,
            )

        get_connection.assert_not_called()

    def test_v246_service_source_remains_read_only(self):
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
            "render_to_string(",
            "send_saved_search_notification_email_production(",
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

    def test_v246_command_source_remains_report_only(self):
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
            "get_connection(",
        )

        for term in forbidden_terms:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v246_v244_and_v245_transition_package_remains_present(self):
        v244_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "operational_readiness_contract_v244.py"
        )

        v245_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "operational_readiness_v245.py"
        )

        self.assertIn(
            (
                "V244_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATIONAL_READINESS_CONTRACT"
            ),
            v244_source,
        )

        self.assertIn(
            (
                "V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATIONAL_READINESS"
            ),
            v245_source,
        )

        self.assertIn(
            "v246: saved-search notification production delivery operational readiness closeout audit",
            v245_source,
        )

    def test_v246_marker_does_not_leak_into_protected_backend(self):
        marker = (
            V246_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CLOSEOUT_AUDIT
        )

        for relative_path in PROTECTED_BACKEND_PATHS:
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

    def test_v246_no_migration_0017_exists(self):
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

    def test_v246_closeout_gate_matrix_is_complete(self):
        required = {
            "v244 readiness contract remains packaged",
            "v245 readiness implementation remains packaged",
            "v245 implementation scope remains exactly four files",
            "v246 scope remains exactly two audit files",
            "default development configuration reports not_ready",
            "production-like configuration reports ready",
            "readiness execution performs no database access",
            "readiness execution performs no database mutation",
            "readiness execution writes no audit event",
            "readiness execution renders no email",
            "readiness execution sends no email",
            "readiness execution opens no provider connection",
            "provider credentials are never read or printed",
            "production sender remains unchanged",
            "production delivery command remains unchanged",
            "scheduler remains nonautomatic",
            "models admin URLs templates and migrations remain unchanged",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(CLOSEOUT_GATES)
            )
        )
