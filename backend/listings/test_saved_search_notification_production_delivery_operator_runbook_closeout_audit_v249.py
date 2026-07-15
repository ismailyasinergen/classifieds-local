from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import (
    SimpleTestCase,
    override_settings,
)

from listings.saved_search_notification_production_readiness import (
    READINESS_CHECK_IDS,
    READINESS_REASON_CODES,
    READINESS_STATUS_VALUES,
    get_saved_search_notification_production_readiness,
)


V249_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CLOSEOUT_AUDIT = (
    "V249_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CLOSEOUT_AUDIT"
)

V247_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_contract_v247.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "operator_runbook_contract_v247.md"
    ),
)

V248_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_v248.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "operator_runbook_v248.md"
    ),
)

V249_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_closeout_audit_v249.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "operator_runbook_closeout_audit_v249.md"
    ),
)

RUNBOOK_SECTION_ORDER = (
    "purpose and audience",
    "authority and change record",
    "preflight readiness",
    "environment and backend verification",
    "owner selection",
    "bounded preview",
    "production execution",
    "stop conditions",
    "result verification",
    "persistent audit verification",
    "failure isolation",
    "rollback and recovery",
    "incident escalation",
    "privacy and secret handling",
    "post-run evidence",
    "prohibited actions",
)

RUNBOOK_COMMAND_SEQUENCE = (
    (
        "docker compose exec -T web python manage.py "
        "check_saved_search_notification_production_readiness "
        "--strict"
    ),
    (
        "docker compose exec -T web python manage.py "
        "check_saved_search_notification_production_readiness "
        "--json"
    ),
    (
        "docker compose exec -T web python manage.py "
        "process_saved_search_notifications "
        "--owner-id <POSITIVE_OWNER_ID> "
        "--limit <1-25>"
    ),
    (
        "docker compose exec -T web python manage.py "
        "process_saved_search_notifications "
        "--execute-production-send "
        "--confirm-production-delivery "
        "--owner-id <POSITIVE_OWNER_ID> "
        "--limit <1-25>"
    ),
    (
        "docker compose exec -T web python manage.py "
        "process_saved_search_notifications --help"
    ),
)

MANDATORY_STOP_CONDITIONS = (
    "readiness status is not ready",
    "feature gate is disabled",
    "email backend is rejected",
    "default sender is missing",
    "owner identity is uncertain",
    "requested limit is outside 1 through 25",
    "another operator may be running the same owner scope",
    "unexpected configuration refusal is reported",
    "unexpected delivery failure is reported",
    "persistent audit evidence is incomplete",
    "sent timestamp evidence is inconsistent",
    "provider behavior is unexpected",
    "sanitized output cannot be reconciled",
)

POST_RUN_EVIDENCE = (
    "change record identifier",
    "operator identity",
    "reviewer identity when required",
    "UTC start timestamp",
    "UTC finish timestamp",
    "target owner identifier",
    "requested limit",
    "sanitized readiness result",
    "sanitized preview summary",
    "sanitized delivery summary",
    "persistent audit verification result",
    "sent timestamp verification result",
    "rollback decision",
    "incident reference when applicable",
)

PROHIBITED_CONTENT = (
    "SMTP password",
    "SMTP username when confidential",
    "API key",
    "access token",
    "recipient email address",
    "default sender value",
    "raw backend path",
    "saved-search name",
    "saved-search querystring",
    "rendered email subject",
    "rendered email body",
    "provider response body",
    "raw exception traceback",
)

PROHIBITED_ACTIONS = (
    "global all-owner production execution",
    "limit above 25",
    "readiness bypass",
    "production confirmation bypass",
    "owner-scope bypass",
    "manual sent timestamp edit",
    "manual audit-event deletion",
    "direct SQL repair",
    "Django shell timestamp repair",
    "credential logging",
    "recipient payload logging",
    "saved-search payload logging",
    "automatic scheduler enablement",
    "Celery enablement",
    "cron enablement",
    "startup-time delivery",
    "request-time delivery",
    "unreviewed repeated execution",
    "silent partial-failure handling",
)

EXPECTED_AUDIT_SEQUENCE = (
    "delivery_attempted",
    "delivery_succeeded or delivery_failed",
    "sent_timestamp_recorded when delivery succeeds",
)

RUNBOOK_CLOSEOUT_GATES = (
    "v247 runbook contract remains packaged",
    "v248 runbook implementation remains packaged",
    "v247 committed scope remains exactly two files",
    "v248 committed scope remains exactly two files",
    "v249 scope remains exactly two audit files",
    "all sixteen runbook sections remain packaged",
    "runbook sections remain in the contracted order",
    "authority is documented before execution",
    "strict readiness gate is documented before preview",
    "sanitized JSON readiness evidence is documented",
    "default development readiness remains not_ready",
    "production-like readiness remains ready",
    "readiness command remains read only",
    "readiness execution opens no email connection",
    "preview remains owner scoped",
    "preview remains explicitly limited",
    "preview contains no production confirmation flags",
    "production execution retains both confirmation flags",
    "production execution requires a positive owner identifier",
    "production execution requires an explicit limit",
    "production limit remains between 1 and 25",
    "production batch maximum remains 25",
    "global all-owner execution remains prohibited",
    "mandatory stop conditions remain explicit",
    "sanitized result reconciliation remains explicit",
    "persistent audit verification remains explicit",
    "sent timestamp verification remains explicit",
    "duplicate-attempt review remains explicit",
    "per-item failure isolation remains documented",
    "rollback begins with deployed command help verification",
    "rollback preview remains required before apply",
    "unsupported rollback syntax remains prohibited",
    "manual database repair remains prohibited",
    "incident escalation remains explicit",
    "privacy and secret exclusions remain explicit",
    "post-run evidence remains explicit",
    "production sender remains unchanged",
    "production delivery command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v250: saved-search notification production delivery controlled rollout contract"

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
    (
        "listings/"
        "saved_search_notification_production_readiness.py"
    ),
    (
        "listings/management/commands/"
        "check_saved_search_notification_production_readiness.py"
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
        "operator_runbook_contract_v247.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_v248.py"
    ),
)

HISTORICAL_SAFETY_TEST_PATHS = (
    (
        "listings/"
        "test_saved_search_notification_explicit_send_"
        "test_backend_v222.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_rollback_audit_"
        "hardening_v224.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "design_audit_v225.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_audit_runtime_"
        "integration_v232.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_persistent_audit_"
        "operator_shared_shell_integration_closeout_audit_v240.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_contract_v241.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_v242.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "closeout_audit_v243.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_contract_v244.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_v245.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_closeout_audit_v246.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_contract_v247.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_v248.py"
    ),
)


class SavedSearchNotificationProductionDeliveryOperatorRunbookCloseoutAuditV249Tests(
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

    def test_v249_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V249_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CLOSEOUT_AUDIT,
            (
                "V249_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATOR_RUNBOOK_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V247_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V248_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V249_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v250: saved-search notification production "
                "delivery controlled rollout contract"
            ),
        )

    def test_v249_runbook_section_order_remains_exact(self):
        self.assertEqual(
            len(RUNBOOK_SECTION_ORDER),
            16,
        )

        self.assertEqual(
            RUNBOOK_SECTION_ORDER[0],
            "purpose and audience",
        )

        self.assertEqual(
            RUNBOOK_SECTION_ORDER[2],
            "preflight readiness",
        )

        self.assertEqual(
            RUNBOOK_SECTION_ORDER[5],
            "bounded preview",
        )

        self.assertEqual(
            RUNBOOK_SECTION_ORDER[6],
            "production execution",
        )

        self.assertEqual(
            RUNBOOK_SECTION_ORDER[-1],
            "prohibited actions",
        )

    def test_v249_runbook_command_sequence_remains_safe(self):
        self.assertEqual(
            len(RUNBOOK_COMMAND_SEQUENCE),
            5,
        )

        self.assertIn(
            "--strict",
            RUNBOOK_COMMAND_SEQUENCE[0],
        )

        self.assertIn(
            "--json",
            RUNBOOK_COMMAND_SEQUENCE[1],
        )

        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            RUNBOOK_COMMAND_SEQUENCE[2],
        )

        self.assertIn(
            "--limit <1-25>",
            RUNBOOK_COMMAND_SEQUENCE[2],
        )

        self.assertNotIn(
            "--execute-production-send",
            RUNBOOK_COMMAND_SEQUENCE[2],
        )

        self.assertNotIn(
            "--confirm-production-delivery",
            RUNBOOK_COMMAND_SEQUENCE[2],
        )

        self.assertIn(
            "--execute-production-send",
            RUNBOOK_COMMAND_SEQUENCE[3],
        )

        self.assertIn(
            "--confirm-production-delivery",
            RUNBOOK_COMMAND_SEQUENCE[3],
        )

        self.assertTrue(
            RUNBOOK_COMMAND_SEQUENCE[4].endswith(
                "process_saved_search_notifications --help"
            )
        )

    def test_v249_default_readiness_remains_not_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        self.assertFalse(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "not_ready",
        )

        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            READINESS_CHECK_IDS,
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v249_production_like_readiness_remains_ready(self):
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

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v249_readiness_command_opens_no_email_connection(self):
        stdout = StringIO()

        with patch(
            "django.core.mail.get_connection"
        ) as get_connection:
            call_command(
                "check_saved_search_notification_production_readiness",
                stdout=stdout,
            )

        get_connection.assert_not_called()

        self.assertIn(
            "status=ready",
            stdout.getvalue(),
        )

    def test_v249_readiness_contract_values_remain_stable(self):
        self.assertEqual(
            READINESS_STATUS_VALUES,
            (
                "ready",
                "not_ready",
                "warning",
            ),
        )

        self.assertEqual(
            len(READINESS_CHECK_IDS),
            9,
        )

        self.assertEqual(
            READINESS_REASON_CODES[0],
            "ready",
        )

        self.assertIn(
            "feature_gate_disabled",
            READINESS_REASON_CODES,
        )

        self.assertIn(
            "email_backend_rejected",
            READINESS_REASON_CODES,
        )

    def test_v249_readiness_command_surface_remains_report_only(self):
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

        forbidden = (
            "--execute-production-send",
            "--confirm-production-delivery",
            "--owner-id",
            "--limit",
            "send_saved_search_notification_email_production",
            "SavedSearchNotificationAuditEvent",
            "get_connection(",
        )

        for term in forbidden:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v249_production_command_controls_remain_packaged(self):
        source = self._read_backend(
            "listings/management/commands/"
            "process_saved_search_notifications.py"
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

        required = {
            "--execute-production-send",
            "--confirm-production-delivery",
            "--owner-id",
            "--limit",
        }

        self.assertTrue(
            required.issubset(
                option_strings
            )
        )

        for term in (
            "Production delivery requires both",
            "Production delivery requires a positive",
            "configuration_refused",
            "failed_count",
        ):
            with self.subTest(
                term=term
            ):
                self.assertIn(
                    term,
                    source,
                )

    def test_v249_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

        self.assertIn(
            "nonproduction_delivery_backend",
            source,
        )

        self.assertIn(
            "send_saved_search_notification_email_production",
            source,
        )

    def test_v249_stop_conditions_remain_complete(self):
        required = {
            "readiness status is not ready",
            "feature gate is disabled",
            "email backend is rejected",
            "default sender is missing",
            "owner identity is uncertain",
            "requested limit is outside 1 through 25",
            "another operator may be running the same owner scope",
            "unexpected configuration refusal is reported",
            "unexpected delivery failure is reported",
            "persistent audit evidence is incomplete",
            "sent timestamp evidence is inconsistent",
            "provider behavior is unexpected",
            "sanitized output cannot be reconciled",
        }

        self.assertEqual(
            set(MANDATORY_STOP_CONDITIONS),
            required,
        )

    def test_v249_post_run_evidence_remains_complete(self):
        required = {
            "change record identifier",
            "operator identity",
            "reviewer identity when required",
            "UTC start timestamp",
            "UTC finish timestamp",
            "target owner identifier",
            "requested limit",
            "sanitized readiness result",
            "sanitized preview summary",
            "sanitized delivery summary",
            "persistent audit verification result",
            "sent timestamp verification result",
            "rollback decision",
            "incident reference when applicable",
        }

        self.assertEqual(
            set(POST_RUN_EVIDENCE),
            required,
        )

    def test_v249_privacy_exclusions_remain_complete(self):
        required = {
            "SMTP password",
            "SMTP username when confidential",
            "API key",
            "access token",
            "recipient email address",
            "default sender value",
            "raw backend path",
            "saved-search name",
            "saved-search querystring",
            "rendered email subject",
            "rendered email body",
            "provider response body",
            "raw exception traceback",
        }

        self.assertEqual(
            set(PROHIBITED_CONTENT),
            required,
        )

    def test_v249_prohibited_actions_remain_complete(self):
        required = {
            "global all-owner production execution",
            "limit above 25",
            "readiness bypass",
            "production confirmation bypass",
            "owner-scope bypass",
            "manual sent timestamp edit",
            "manual audit-event deletion",
            "direct SQL repair",
            "Django shell timestamp repair",
            "credential logging",
            "recipient payload logging",
            "saved-search payload logging",
            "automatic scheduler enablement",
            "Celery enablement",
            "cron enablement",
            "startup-time delivery",
            "request-time delivery",
            "unreviewed repeated execution",
            "silent partial-failure handling",
        }

        self.assertEqual(
            set(PROHIBITED_ACTIONS),
            required,
        )

    def test_v249_expected_audit_sequence_remains_stable(self):
        self.assertEqual(
            EXPECTED_AUDIT_SEQUENCE,
            (
                "delivery_attempted",
                "delivery_succeeded or delivery_failed",
                "sent_timestamp_recorded when delivery succeeds",
            ),
        )

    def test_v249_scheduler_remains_nonautomatic(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_scheduler.py"
        )

        forbidden = (
            "--execute-production-send",
            "--confirm-production-delivery",
            "send_saved_search_notification_email_production",
            "Celery",
            "celery",
            "cron",
            "startup",
            "ready(",
        )

        for term in forbidden:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v249_v247_and_v248_packages_remain_present(self):
        v247_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "operator_runbook_contract_v247.py"
        )

        v248_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "operator_runbook_v248.py"
        )

        self.assertIn(
            (
                "V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATOR_RUNBOOK_CONTRACT"
            ),
            v247_source,
        )

        self.assertIn(
            (
                "V248_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATOR_RUNBOOK"
            ),
            v248_source,
        )

        self.assertIn(
            (
                "v249: saved-search notification production "
                "delivery operator runbook closeout audit"
            ),
            v248_source,
        )

    def test_v249_historical_safety_package_is_present(self):
        for relative_path in HISTORICAL_SAFETY_TEST_PATHS:
            with self.subTest(
                relative_path=relative_path
            ):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file()
                )

    def test_v249_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V249_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CLOSEOUT_AUDIT
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

    def test_v249_no_migration_0017_exists(self):
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

    def test_v249_closeout_gate_matrix_is_complete(self):
        required = {
            "v247 runbook contract remains packaged",
            "v248 runbook implementation remains packaged",
            "v249 scope remains exactly two audit files",
            "all sixteen runbook sections remain packaged",
            "strict readiness gate is documented before preview",
            "default development readiness remains not_ready",
            "production-like readiness remains ready",
            "readiness command remains read only",
            "preview remains owner scoped",
            "preview remains explicitly limited",
            "preview contains no production confirmation flags",
            "production execution retains both confirmation flags",
            "production execution requires a positive owner identifier",
            "production execution requires an explicit limit",
            "production limit remains between 1 and 25",
            "production batch maximum remains 25",
            "global all-owner execution remains prohibited",
            "persistent audit verification remains explicit",
            "sent timestamp verification remains explicit",
            "rollback begins with deployed command help verification",
            "rollback preview remains required before apply",
            "unsupported rollback syntax remains prohibited",
            "manual database repair remains prohibited",
            "privacy and secret exclusions remain explicit",
            "production sender remains unchanged",
            "production delivery command remains unchanged",
            "readiness service and command remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(RUNBOOK_CLOSEOUT_GATES)
            )
        )
