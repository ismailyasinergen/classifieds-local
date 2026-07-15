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
    get_saved_search_notification_production_readiness,
)


V250_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT_CONTRACT = (
    "V250_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT_CONTRACT"
)

V249_COMMITTED_SCOPE = (
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

V250_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.md"
    ),
)

V251_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_v251.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "controlled_rollout_v251.md"
    ),
)

ROLLOUT_PHASE_ORDER = (
    "phase 0 preflight and authorization",
    "phase 1 single-owner pilot",
    "phase 2 limited owner-scoped expansion",
    "phase 3 expanded owner-scoped validation",
    "phase 4 stabilization and closeout review",
)

ROLLOUT_LIMIT_BANDS = (
    (
        "single-owner pilot",
        1,
        3,
    ),
    (
        "limited owner-scoped expansion",
        4,
        10,
    ),
    (
        "expanded owner-scoped validation",
        11,
        25,
    ),
)

ROLLOUT_GO_GATES = (
    "strict readiness passes",
    "sanitized readiness JSON is retained",
    "authorized owner scope is documented",
    "bounded preview matches approved owner and limit",
    "production uses both explicit confirmation flags",
    "failed count is zero",
    "unexpected refusal count is zero",
    "delivery counts reconcile",
    "persistent audit sequence is complete",
    "sent timestamp evidence is consistent",
    "duplicate-attempt review is clean",
    "no provider anomaly is present",
    "no privacy or secret incident is open",
    "previous phase evidence is approved",
)

ROLLOUT_STOP_CONDITIONS = (
    "readiness status is not ready",
    "feature gate is disabled",
    "email backend is rejected",
    "default sender is missing",
    "owner identity is uncertain",
    "owner authorization is missing",
    "another operator may be running the same owner scope",
    "preview differs from the approved scope",
    "requested limit is outside the approved phase band",
    "configuration refusal is reported",
    "delivery failure is reported",
    "persistent audit evidence is incomplete",
    "sent timestamp evidence is inconsistent",
    "duplicate-attempt protection activates unexpectedly",
    "provider behavior is unexpected",
    "sanitized counts cannot be reconciled",
    "an unknown reason code appears",
    "private data or a secret may have appeared",
    "an incident remains open",
)

ROLLOUT_EVIDENCE = (
    "change record identifier",
    "rollout phase",
    "operator identity",
    "reviewer identity",
    "UTC start timestamp",
    "UTC finish timestamp",
    "target owner identifier",
    "approved phase limit",
    "sanitized readiness result",
    "sanitized preview summary",
    "sanitized delivery summary",
    "persistent audit verification result",
    "sent timestamp verification result",
    "duplicate-attempt verification result",
    "go or stop decision",
    "rollback decision",
    "incident reference when applicable",
)

ROLLOUT_PROHIBITED_ACTIONS = (
    "automatic phase promotion",
    "global all-owner execution",
    "multi-owner command execution",
    "limit above 25",
    "limit outside the approved phase band",
    "owner change without new approval",
    "limit increase without new approval",
    "readiness bypass",
    "preview bypass",
    "production confirmation bypass",
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
    "blind retry",
    "silent partial-failure handling",
)

V250_ACCEPTANCE_GATES = (
    "v249 operator-runbook closeout remains packaged",
    "v250 scope is exactly two contract files",
    "v251 implementation scope is exactly two files",
    "v251 implementation is documentation and test only",
    "v250 is forward compatible with v251 files",
    "five rollout phases are defined",
    "phase progression is manual",
    "each production invocation remains single-owner scoped",
    "pilot limit band is 1 through 3",
    "limited expansion band is 4 through 10",
    "expanded validation band is 11 through 25",
    "production batch maximum remains 25",
    "strict readiness is required before every phase",
    "sanitized readiness JSON evidence is required",
    "owner-scoped bounded preview is required",
    "preview and production owner must match",
    "preview and production limit must match",
    "both production confirmation flags remain mandatory",
    "go gates are explicit",
    "stop conditions are explicit",
    "failed count must be zero for progression",
    "unexpected refusal count must be zero for progression",
    "persistent audit verification is required",
    "sent timestamp verification is required",
    "duplicate-attempt review is required",
    "open incidents block progression",
    "rollback decision is recorded",
    "phase evidence requires reviewer approval",
    "privacy and secret exclusions remain enforced",
    "automatic phase promotion is prohibited",
    "global all-owner execution is prohibited",
    "multi-owner command execution is prohibited",
    "manual database repair is prohibited",
    "production sender remains unchanged",
    "production delivery command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v251: saved-search notification production delivery controlled rollout implementation"

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
        "operator_runbook_closeout_audit_v249.py"
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
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_closeout_audit_v249.py"
    ),
)


class SavedSearchNotificationProductionDeliveryControlledRolloutContractV250Tests(
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

    def test_v250_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V250_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT_CONTRACT,
            (
                "V250_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_CONTROLLED_ROLLOUT_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V249_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V250_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V251_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v251: saved-search notification production "
                "delivery controlled rollout implementation"
            ),
        )

    def test_v250_v251_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V251_ALLOWED_SCOPE,
            (
                (
                    "backend/listings/"
                    "test_saved_search_notification_production_delivery_"
                    "controlled_rollout_v251.py"
                ),
                (
                    "docs/"
                    "saved_search_notification_production_delivery_"
                    "controlled_rollout_v251.md"
                ),
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/templates/" in path
                or "/management/commands/" in path
                for path in V251_ALLOWED_SCOPE
            )
        )

        self.assertTrue(
            set(V250_ALLOWED_SCOPE).isdisjoint(
                set(V251_ALLOWED_SCOPE)
            )
        )

    def test_v250_contract_is_forward_compatible_with_v251(self):
        contract_text = repr(
            V250_ACCEPTANCE_GATES
        ).casefold()

        self.assertNotIn(
            "v251 files remain absent",
            contract_text,
        )

        self.assertNotIn(
            "file must not exist",
            contract_text,
        )

    def test_v250_rollout_phase_order_is_exact(self):
        self.assertEqual(
            ROLLOUT_PHASE_ORDER,
            (
                "phase 0 preflight and authorization",
                "phase 1 single-owner pilot",
                "phase 2 limited owner-scoped expansion",
                "phase 3 expanded owner-scoped validation",
                "phase 4 stabilization and closeout review",
            ),
        )

    def test_v250_rollout_limit_bands_are_exact_and_contiguous(self):
        self.assertEqual(
            ROLLOUT_LIMIT_BANDS,
            (
                (
                    "single-owner pilot",
                    1,
                    3,
                ),
                (
                    "limited owner-scoped expansion",
                    4,
                    10,
                ),
                (
                    "expanded owner-scoped validation",
                    11,
                    25,
                ),
            ),
        )

        previous_maximum = 0

        for (
            phase_name,
            minimum,
            maximum,
        ) in ROLLOUT_LIMIT_BANDS:
            with self.subTest(
                phase_name=phase_name
            ):
                self.assertEqual(
                    minimum,
                    previous_maximum + 1,
                )

                self.assertLessEqual(
                    minimum,
                    maximum,
                )

                previous_maximum = maximum

        self.assertEqual(
            previous_maximum,
            25,
        )

    def test_v250_rollout_go_gates_are_complete(self):
        required = {
            "strict readiness passes",
            "sanitized readiness JSON is retained",
            "authorized owner scope is documented",
            "bounded preview matches approved owner and limit",
            "production uses both explicit confirmation flags",
            "failed count is zero",
            "unexpected refusal count is zero",
            "delivery counts reconcile",
            "persistent audit sequence is complete",
            "sent timestamp evidence is consistent",
            "duplicate-attempt review is clean",
            "no provider anomaly is present",
            "no privacy or secret incident is open",
            "previous phase evidence is approved",
        }

        self.assertEqual(
            set(ROLLOUT_GO_GATES),
            required,
        )

    def test_v250_rollout_stop_conditions_are_complete(self):
        required = {
            "readiness status is not ready",
            "feature gate is disabled",
            "email backend is rejected",
            "default sender is missing",
            "owner identity is uncertain",
            "owner authorization is missing",
            "another operator may be running the same owner scope",
            "preview differs from the approved scope",
            "requested limit is outside the approved phase band",
            "configuration refusal is reported",
            "delivery failure is reported",
            "persistent audit evidence is incomplete",
            "sent timestamp evidence is inconsistent",
            "duplicate-attempt protection activates unexpectedly",
            "provider behavior is unexpected",
            "sanitized counts cannot be reconciled",
            "an unknown reason code appears",
            "private data or a secret may have appeared",
            "an incident remains open",
        }

        self.assertEqual(
            set(ROLLOUT_STOP_CONDITIONS),
            required,
        )

    def test_v250_rollout_evidence_is_complete(self):
        required = {
            "change record identifier",
            "rollout phase",
            "operator identity",
            "reviewer identity",
            "UTC start timestamp",
            "UTC finish timestamp",
            "target owner identifier",
            "approved phase limit",
            "sanitized readiness result",
            "sanitized preview summary",
            "sanitized delivery summary",
            "persistent audit verification result",
            "sent timestamp verification result",
            "duplicate-attempt verification result",
            "go or stop decision",
            "rollback decision",
            "incident reference when applicable",
        }

        self.assertEqual(
            set(ROLLOUT_EVIDENCE),
            required,
        )

    def test_v250_prohibited_actions_are_complete(self):
        required = {
            "automatic phase promotion",
            "global all-owner execution",
            "multi-owner command execution",
            "limit above 25",
            "limit outside the approved phase band",
            "owner change without new approval",
            "limit increase without new approval",
            "readiness bypass",
            "preview bypass",
            "production confirmation bypass",
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
            "blind retry",
            "silent partial-failure handling",
        }

        self.assertEqual(
            set(ROLLOUT_PROHIBITED_ACTIONS),
            required,
        )

    def test_v250_default_readiness_remains_not_ready(self):
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
    def test_v250_production_like_readiness_remains_ready(self):
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
    def test_v250_readiness_execution_opens_no_email_connection(self):
        stdout = StringIO()

        with patch(
            "django.core.mail.get_connection"
        ) as get_connection:
            call_command(
                "check_saved_search_notification_production_readiness",
                "--strict",
                stdout=stdout,
            )

        get_connection.assert_not_called()

        self.assertIn(
            "status=ready",
            stdout.getvalue(),
        )

    def test_v250_readiness_command_surface_remains_report_only(self):
        source = self._read_backend(
            "listings/management/commands/"
            "check_saved_search_notification_production_readiness.py"
        )

        tree = ast.parse(
            source
        )

        options = {
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
            options,
            {
                "--strict",
                "--json",
            },
        )

    def test_v250_production_command_controls_remain_packaged(self):
        source = self._read_backend(
            "listings/management/commands/"
            "process_saved_search_notifications.py"
        )

        tree = ast.parse(
            source
        )

        options = {
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
                options
            )
        )

    def test_v250_production_batch_cap_remains_25(self):
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

    def test_v250_scheduler_remains_nonautomatic(self):
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

    def test_v250_v249_closeout_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "operator_runbook_closeout_audit_v249.py"
        )

        self.assertIn(
            (
                "V249_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATOR_RUNBOOK_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            (
                "v250: saved-search notification production "
                "delivery controlled rollout contract"
            ),
            source,
        )

    def test_v250_historical_safety_package_is_present(self):
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

    def test_v250_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V250_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT_CONTRACT
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

    def test_v250_no_migration_0017_exists(self):
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

    def test_v250_acceptance_gate_matrix_is_complete(self):
        required = {
            "v249 operator-runbook closeout remains packaged",
            "v250 scope is exactly two contract files",
            "v251 implementation scope is exactly two files",
            "v251 implementation is documentation and test only",
            "v250 is forward compatible with v251 files",
            "five rollout phases are defined",
            "phase progression is manual",
            "each production invocation remains single-owner scoped",
            "pilot limit band is 1 through 3",
            "limited expansion band is 4 through 10",
            "expanded validation band is 11 through 25",
            "production batch maximum remains 25",
            "strict readiness is required before every phase",
            "owner-scoped bounded preview is required",
            "both production confirmation flags remain mandatory",
            "go gates are explicit",
            "stop conditions are explicit",
            "failed count must be zero for progression",
            "unexpected refusal count must be zero for progression",
            "persistent audit verification is required",
            "sent timestamp verification is required",
            "duplicate-attempt review is required",
            "open incidents block progression",
            "automatic phase promotion is prohibited",
            "global all-owner execution is prohibited",
            "multi-owner command execution is prohibited",
            "manual database repair is prohibited",
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
                set(V250_ACCEPTANCE_GATES)
            )
        )
