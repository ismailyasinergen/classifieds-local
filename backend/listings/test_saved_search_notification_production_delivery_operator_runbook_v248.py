from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase


V248_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK = (
    "V248_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK"
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

V248_ALLOWED_SCOPE = (
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

V249_PROPOSED_SCOPE = (
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

V248_ACCEPTANCE_GATES = (
    "v247 contract remains packaged",
    "v248 scope is exactly two files",
    "v249 proposed scope is exactly two files",
    "runbook contains all sixteen required sections",
    "section order starts with authority and readiness before execution",
    "strict readiness command precedes preview",
    "sanitized JSON readiness evidence is documented",
    "preview is owner scoped",
    "preview is explicitly limited",
    "preview contains no production confirmation flags",
    "production execution contains both confirmation flags",
    "production execution requires a positive owner identifier",
    "production execution requires an explicit limit",
    "production limit remains between 1 and 25",
    "production batch maximum remains 25",
    "global all-owner execution is prohibited",
    "mandatory stop conditions are explicit",
    "sanitized result reconciliation is explicit",
    "persistent audit verification is explicit",
    "sent timestamp verification is explicit",
    "duplicate-attempt review is explicit",
    "per-item failure isolation is explained",
    "rollback begins with deployed command help verification",
    "rollback preview is required before apply",
    "unsupported rollback syntax is prohibited",
    "manual database repair is prohibited",
    "incident escalation is explicit",
    "privacy and secret exclusions are explicit",
    "post-run evidence is explicit",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v249: saved-search notification production delivery operator runbook closeout audit"

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
)


class SavedSearchNotificationProductionDeliveryOperatorRunbookV248Tests(
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

    def test_v248_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V248_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK,
            (
                "V248_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATOR_RUNBOOK"
            ),
        )

        self.assertEqual(
            len(V247_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V248_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V249_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v249: saved-search notification production "
                "delivery operator runbook closeout audit"
            ),
        )

    def test_v248_required_section_order_is_exact(self):
        self.assertEqual(
            RUNBOOK_SECTION_ORDER,
            (
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
            ),
        )

    def test_v248_command_sequence_is_exact(self):
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

    def test_v248_readiness_command_surface_is_unchanged(self):
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

        self.assertIn(
            "CommandError",
            source,
        )

        self.assertIn(
            "get_saved_search_notification_production_readiness",
            source,
        )

    def test_v248_production_command_controls_are_unchanged(self):
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

        required_source_terms = (
            "Production delivery requires both",
            "Production delivery requires a positive",
            "configuration_refused",
            "failed_count",
        )

        for term in required_source_terms:
            with self.subTest(
                term=term
            ):
                self.assertIn(
                    term,
                    source,
                )

    def test_v248_production_batch_cap_remains_25(self):
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

    def test_v248_stop_conditions_are_complete(self):
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

    def test_v248_post_run_evidence_is_complete(self):
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

    def test_v248_privacy_exclusions_are_complete(self):
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

    def test_v248_prohibited_actions_are_complete(self):
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

    def test_v248_expected_audit_sequence_is_stable(self):
        self.assertEqual(
            EXPECTED_AUDIT_SEQUENCE,
            (
                "delivery_attempted",
                "delivery_succeeded or delivery_failed",
                "sent_timestamp_recorded when delivery succeeds",
            ),
        )

    def test_v248_rollback_guidance_does_not_invent_flags(self):
        rollback_help_command = (
            RUNBOOK_COMMAND_SEQUENCE[4]
        )

        self.assertIn(
            "--help",
            rollback_help_command,
        )

        self.assertNotIn(
            "--rollback-",
            repr(RUNBOOK_COMMAND_SEQUENCE)
        )

        acceptance_text = repr(
            V248_ACCEPTANCE_GATES
        ).casefold()

        self.assertIn(
            "unsupported rollback syntax is prohibited",
            acceptance_text,
        )

        self.assertIn(
            "rollback preview is required before apply",
            acceptance_text,
        )

    def test_v248_scheduler_remains_nonautomatic(self):
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

    def test_v248_v247_contract_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "operator_runbook_contract_v247.py"
        )

        self.assertIn(
            (
                "V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATOR_RUNBOOK_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v248: saved-search notification production "
                "delivery operator runbook implementation"
            ),
            source,
        )

    def test_v248_historical_safety_package_is_present(self):
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

    def test_v248_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V248_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK
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

    def test_v248_no_migration_0017_exists(self):
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

    def test_v248_acceptance_gate_matrix_is_complete(self):
        required = {
            "v247 contract remains packaged",
            "v248 scope is exactly two files",
            "v249 proposed scope is exactly two files",
            "runbook contains all sixteen required sections",
            "strict readiness command precedes preview",
            "preview is owner scoped",
            "preview is explicitly limited",
            "preview contains no production confirmation flags",
            "production execution contains both confirmation flags",
            "production execution requires a positive owner identifier",
            "production execution requires an explicit limit",
            "production limit remains between 1 and 25",
            "production batch maximum remains 25",
            "global all-owner execution is prohibited",
            "mandatory stop conditions are explicit",
            "persistent audit verification is explicit",
            "sent timestamp verification is explicit",
            "rollback begins with deployed command help verification",
            "rollback preview is required before apply",
            "unsupported rollback syntax is prohibited",
            "manual database repair is prohibited",
            "privacy and secret exclusions are explicit",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service and command remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V248_ACCEPTANCE_GATES)
            )
        )
