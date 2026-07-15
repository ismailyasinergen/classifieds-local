from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase


V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CONTRACT = (
    "V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CONTRACT"
)

V246_COMMITTED_SCOPE = (
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

V247_ALLOWED_SCOPE = (
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

RUNBOOK_REQUIRED_SECTIONS = (
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

RUNBOOK_REQUIRED_COMMAND_REFERENCES = (
    "check_saved_search_notification_production_readiness",
    "--strict",
    "--json",
    "process_saved_search_notifications",
    "--execute-production-send",
    "--confirm-production-delivery",
    "--owner-id",
    "--limit",
)

RUNBOOK_REQUIRED_STOP_CONDITIONS = (
    "readiness status is not ready",
    "feature gate is disabled",
    "email backend is rejected",
    "default sender is missing",
    "owner identity is uncertain",
    "requested limit is outside 1 through 25",
    "unexpected refusal is reported",
    "unexpected delivery failure is reported",
    "audit evidence is incomplete",
    "timestamp evidence is inconsistent",
    "provider behavior is unexpected",
)

RUNBOOK_REQUIRED_EVIDENCE = (
    "change record identifier",
    "operator identity",
    "UTC start timestamp",
    "UTC finish timestamp",
    "target owner identifier",
    "requested limit",
    "sanitized readiness result",
    "sanitized delivery summary",
    "audit verification result",
    "rollback decision",
    "incident reference when applicable",
)

RUNBOOK_PROHIBITED_CONTENT = (
    "SMTP password",
    "API key",
    "access token",
    "recipient email address",
    "saved-search querystring",
    "rendered email body",
    "provider response body",
    "raw exception traceback",
)

RUNBOOK_PROHIBITED_ACTIONS = (
    "global all-owner execution",
    "limit above 25",
    "manual notification timestamp edit",
    "manual audit-event deletion",
    "bypass of readiness checks",
    "bypass of production confirmations",
    "automatic scheduler enablement",
    "request-time delivery",
    "background-worker enablement",
    "credential logging",
)

V247_ACCEPTANCE_GATES = (
    "v246 readiness closeout remains packaged",
    "v247 scope is exactly two contract files",
    "v248 implementation scope is exactly two files",
    "v248 implementation is documentation and test only",
    "v247 is forward compatible with v248 files",
    "runbook identifies operator audience",
    "runbook requires an authority or change record",
    "runbook begins with readiness preflight",
    "strict readiness mode is documented",
    "JSON readiness mode is documented",
    "default not_ready result is handled as stop",
    "production execution remains owner scoped",
    "production execution remains explicitly confirmed",
    "production execution remains explicitly limited",
    "production batch maximum remains 25",
    "global all-owner execution is prohibited",
    "stop conditions are explicit",
    "sanitized output is required",
    "persistent audit verification is required",
    "timestamp verification is required",
    "per-item failure isolation is explained",
    "rollback uses existing audited controls",
    "manual database repair is prohibited",
    "incident escalation is defined",
    "post-run evidence is defined",
    "credentials are never included",
    "recipient and saved-search payloads are never included",
    "provider response bodies are never included",
    "production sender remains unchanged",
    "production delivery command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v248: saved-search notification production delivery operator runbook implementation"

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
        "operational_readiness_closeout_audit_v246.py"
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
)


class SavedSearchNotificationProductionDeliveryOperatorRunbookContractV247Tests(
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

    def test_v247_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CONTRACT,
            (
                "V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATOR_RUNBOOK_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V246_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V247_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V248_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v248: saved-search notification production "
                "delivery operator runbook implementation"
            ),
        )

    def test_v247_v248_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V248_ALLOWED_SCOPE,
            (
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
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/templates/" in path
                or "/management/commands/" in path
                for path in V248_ALLOWED_SCOPE
            )
        )

        self.assertTrue(
            set(V247_ALLOWED_SCOPE).isdisjoint(
                set(V248_ALLOWED_SCOPE)
            )
        )

    def test_v247_contract_is_forward_compatible_with_v248(self):
        expected_scope = {
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
        }

        self.assertEqual(
            set(V248_ALLOWED_SCOPE),
            expected_scope,
        )

        self.assertNotIn(
            "file must not exist",
            repr(V247_ACCEPTANCE_GATES).casefold(),
        )

        self.assertNotIn(
            "v248 files remain absent",
            repr(V247_ACCEPTANCE_GATES).casefold(),
        )

    def test_v247_required_runbook_sections_are_complete(self):
        required = {
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
        }

        self.assertEqual(
            set(RUNBOOK_REQUIRED_SECTIONS),
            required,
        )

    def test_v247_required_command_references_are_complete(self):
        self.assertEqual(
            RUNBOOK_REQUIRED_COMMAND_REFERENCES,
            (
                "check_saved_search_notification_production_readiness",
                "--strict",
                "--json",
                "process_saved_search_notifications",
                "--execute-production-send",
                "--confirm-production-delivery",
                "--owner-id",
                "--limit",
            ),
        )

    def test_v247_readiness_command_contract_remains_packaged(self):
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
            "get_saved_search_notification_production_readiness",
            source,
        )

        self.assertIn(
            "CommandError",
            source,
        )

    def test_v247_production_command_safety_controls_remain_packaged(self):
        source = self._read_backend(
            "listings/management/commands/"
            "process_saved_search_notifications.py"
        )

        required_options = {
            "--execute-production-send",
            "--confirm-production-delivery",
            "--owner-id",
            "--limit",
        }

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

        self.assertTrue(
            required_options.issubset(
                option_strings
            )
        )

        required_source_terms = (
            "Production delivery requires both",
            "Production delivery requires a positive",
            "V242_LEGACY_LIMIT_DEFAULT",
            "configuration_refused",
            "failed_count",
        )

        for term in required_source_terms:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

    def test_v247_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

        self.assertIn(
            "send_saved_search_notification_email_production",
            source,
        )

        self.assertIn(
            "nonproduction_delivery_backend",
            source,
        )

    def test_v247_stop_condition_contract_is_complete(self):
        required = {
            "readiness status is not ready",
            "feature gate is disabled",
            "email backend is rejected",
            "default sender is missing",
            "owner identity is uncertain",
            "requested limit is outside 1 through 25",
            "unexpected refusal is reported",
            "unexpected delivery failure is reported",
            "audit evidence is incomplete",
            "timestamp evidence is inconsistent",
            "provider behavior is unexpected",
        }

        self.assertEqual(
            set(RUNBOOK_REQUIRED_STOP_CONDITIONS),
            required,
        )

    def test_v247_post_run_evidence_contract_is_complete(self):
        required = {
            "change record identifier",
            "operator identity",
            "UTC start timestamp",
            "UTC finish timestamp",
            "target owner identifier",
            "requested limit",
            "sanitized readiness result",
            "sanitized delivery summary",
            "audit verification result",
            "rollback decision",
            "incident reference when applicable",
        }

        self.assertEqual(
            set(RUNBOOK_REQUIRED_EVIDENCE),
            required,
        )

    def test_v247_privacy_contract_is_sanitized(self):
        required = {
            "SMTP password",
            "API key",
            "access token",
            "recipient email address",
            "saved-search querystring",
            "rendered email body",
            "provider response body",
            "raw exception traceback",
        }

        self.assertEqual(
            set(RUNBOOK_PROHIBITED_CONTENT),
            required,
        )

        acceptance_text = repr(
            V247_ACCEPTANCE_GATES
        ).casefold()

        self.assertIn(
            "credentials are never included",
            acceptance_text,
        )

        self.assertIn(
            "provider response bodies are never included",
            acceptance_text,
        )

    def test_v247_prohibited_action_contract_is_complete(self):
        required = {
            "global all-owner execution",
            "limit above 25",
            "manual notification timestamp edit",
            "manual audit-event deletion",
            "bypass of readiness checks",
            "bypass of production confirmations",
            "automatic scheduler enablement",
            "request-time delivery",
            "background-worker enablement",
            "credential logging",
        }

        self.assertEqual(
            set(RUNBOOK_PROHIBITED_ACTIONS),
            required,
        )

    def test_v247_scheduler_remains_nonautomatic(self):
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
            with self.subTest(term=term):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v247_v246_closeout_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "operational_readiness_closeout_audit_v246.py"
        )

        self.assertIn(
            (
                "V246_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATIONAL_READINESS_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            "v247: saved-search notification production delivery operator runbook contract",
            source,
        )

    def test_v247_historical_safety_package_is_present(self):
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

    def test_v247_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V247_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATOR_RUNBOOK_CONTRACT
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

    def test_v247_no_migration_0017_exists(self):
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

    def test_v247_acceptance_gate_matrix_is_complete(self):
        required = {
            "v246 readiness closeout remains packaged",
            "v247 scope is exactly two contract files",
            "v248 implementation scope is exactly two files",
            "v248 implementation is documentation and test only",
            "v247 is forward compatible with v248 files",
            "runbook begins with readiness preflight",
            "strict readiness mode is documented",
            "production execution remains owner scoped",
            "production execution remains explicitly confirmed",
            "production execution remains explicitly limited",
            "production batch maximum remains 25",
            "global all-owner execution is prohibited",
            "persistent audit verification is required",
            "timestamp verification is required",
            "rollback uses existing audited controls",
            "manual database repair is prohibited",
            "incident escalation is defined",
            "credentials are never included",
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
                set(V247_ACCEPTANCE_GATES)
            )
        )
