from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase


V244_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CONTRACT = (
    "V244_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CONTRACT"
)

V243_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "closeout_audit_v243.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "closeout_audit_v243.md"
    ),
)

V244_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_contract_v244.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "operational_readiness_contract_v244.md"
    ),
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

READINESS_STATUS_VALUES = (
    "ready",
    "not_ready",
    "warning",
)

READINESS_CHECK_IDS = (
    "feature_gate_declared",
    "feature_gate_enabled",
    "email_backend_configured",
    "email_backend_allowed",
    "default_sender_configured",
    "double_confirmation_packaged",
    "owner_scope_packaged",
    "explicit_limit_packaged",
    "batch_cap_packaged",
)

READINESS_REASON_CODES = (
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
)

READINESS_RESULT_KEYS = (
    "marker",
    "status",
    "ready",
    "checks",
    "ready_count",
    "not_ready_count",
    "warning_count",
)

READINESS_CHECK_RESULT_KEYS = (
    "check_id",
    "status",
    "passed",
    "reason_code",
)

READINESS_COMMAND_OPTIONS = (
    "--strict",
    "--json",
)

V244_ACCEPTANCE_GATES = (
    "v243 closeout package remains unchanged",
    "v245 readiness service is read only",
    "v245 readiness command is read only",
    "default command invocation performs no delivery",
    "default command invocation performs no database mutation",
    "default command invocation performs no audit-event write",
    "default command invocation performs no provider connection",
    "readiness checks are deterministic",
    "readiness checks use stable check identifiers",
    "readiness checks use stable reason codes",
    "overall status is ready not_ready or warning",
    "feature-gate declaration is checked",
    "feature-gate enabled state is checked",
    "configured email backend is checked",
    "known nonproduction backends are rejected",
    "default sender presence is checked",
    "double production confirmation is checked",
    "positive owner scope is checked",
    "explicit bounded limit is checked",
    "production batch maximum 25 is checked",
    "human output is sanitized",
    "JSON output is sanitized",
    "strict mode fails when not ready",
    "non-strict mode reports without failing",
    "recipient addresses are never printed",
    "saved-search payload is never printed",
    "email bodies are never rendered",
    "provider credentials are never read or printed",
    "provider response bodies are never printed",
    "existing production sender remains unchanged",
    "existing delivery command remains unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "v245 implementation scope is exactly four files",
)

NEXT_CHECKPOINT = "v245: saved-search notification production delivery operational readiness implementation"

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
        "closeout_audit_v243.py"
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
)


class SavedSearchNotificationProductionDeliveryOperationalReadinessContractV244Tests(
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


    def test_v244_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V244_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CONTRACT,
            (
                "V244_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_OPERATIONAL_READINESS_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V243_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V244_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V245_ALLOWED_SCOPE),
            4,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v245: saved-search notification production "
                "delivery operational readiness implementation"
            ),
        )

    def test_v244_v243_closeout_package_remains_present(self):
        v243_test = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "closeout_audit_v243.py"
        )

        marker = (
            "V243_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
            "DELIVERY_CLOSEOUT_AUDIT"
        )

        self.assertIn(
            marker,
            v243_test,
        )

        self.assertIn(
            "v244: saved-search notification production delivery operational readiness contract",
            v243_test,
        )

        self.assertIn(
            (
                "docs/"
                "saved_search_notification_production_delivery_"
                "closeout_audit_v243.md"
            ),
            V243_COMMITTED_SCOPE,
        )

    def test_v244_v245_allowed_scope_is_exact(self):
        self.assertEqual(
            V245_ALLOWED_SCOPE,
            (
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
            ),
        )

    def test_v244_v245_scope_excludes_runtime_schema_ui_and_scheduler(self):
        forbidden = {
            "backend/config/settings.py",
            (
                "backend/listings/"
                "saved_search_notification_email_sender.py"
            ),
            (
                "backend/listings/management/commands/"
                "process_saved_search_notifications.py"
            ),
            (
                "backend/listings/"
                "saved_search_notification_scheduler.py"
            ),
            "backend/listings/models.py",
            "backend/listings/admin.py",
            "backend/listings/urls.py",
            "backend/templates/base.html",
        }

        self.assertTrue(
            forbidden.isdisjoint(
                set(V245_ALLOWED_SCOPE)
            )
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/templates/" in path
                for path in V245_ALLOWED_SCOPE
            )
        )

    def test_v244_readiness_status_and_result_contract_is_complete(self):
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

    def test_v244_required_readiness_checks_are_complete(self):
        required = {
            "feature_gate_declared",
            "feature_gate_enabled",
            "email_backend_configured",
            "email_backend_allowed",
            "default_sender_configured",
            "double_confirmation_packaged",
            "owner_scope_packaged",
            "explicit_limit_packaged",
            "batch_cap_packaged",
        }

        self.assertEqual(
            set(READINESS_CHECK_IDS),
            required,
        )

    def test_v244_reason_codes_are_stable_and_sanitized(self):
        required = {
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
        }

        self.assertEqual(
            set(READINESS_REASON_CODES),
            required,
        )

        serialized = repr(
            READINESS_REASON_CODES
        ).casefold()

        for forbidden in (
            "password",
            "secret",
            "token",
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

    def test_v244_command_contract_is_read_only_and_operator_safe(self):
        self.assertEqual(
            READINESS_COMMAND_OPTIONS,
            (
                "--strict",
                "--json",
            ),
        )

        required = {
            "v245 readiness command is read only",
            "default command invocation performs no delivery",
            "default command invocation performs no database mutation",
            "default command invocation performs no audit-event write",
            "default command invocation performs no provider connection",
            "human output is sanitized",
            "JSON output is sanitized",
            "strict mode fails when not ready",
            "non-strict mode reports without failing",
        }

        self.assertTrue(
            required.issubset(
                set(V244_ACCEPTANCE_GATES)
            )
        )

    def test_v244_privacy_and_secret_contract_is_complete(self):
        required = {
            "recipient addresses are never printed",
            "saved-search payload is never printed",
            "email bodies are never rendered",
            "provider credentials are never read or printed",
            "provider response bodies are never printed",
        }

        self.assertTrue(
            required.issubset(
                set(V244_ACCEPTANCE_GATES)
            )
        )

    def test_v244_existing_delivery_safety_boundary_is_preserved(self):
        required = {
            "existing production sender remains unchanged",
            "existing delivery command remains unchanged",
            "scheduler remains nonautomatic",
            "models admin URLs templates and migrations remain unchanged",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
        }

        self.assertTrue(
            required.issubset(
                set(V244_ACCEPTANCE_GATES)
            )
        )

    def test_v244_historical_safety_package_is_present(self):
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

    def test_v244_contract_is_deferred_until_v245(self):
        expected_scope = (
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

        self.assertEqual(
            V245_ALLOWED_SCOPE,
            expected_scope,
        )

        self.assertEqual(
            len(V245_ALLOWED_SCOPE),
            4,
        )

        self.assertTrue(
            set(V244_ALLOWED_SCOPE).isdisjoint(
                set(V245_ALLOWED_SCOPE)
            )
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/templates/" in path
                for path in V245_ALLOWED_SCOPE
            )
        )

    def test_v244_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V244_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS_CONTRACT
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

    def test_v244_no_migration_0017_exists(self):
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

    def test_v244_acceptance_gate_matrix_is_complete(self):
        required = {
            "v243 closeout package remains unchanged",
            "v245 readiness service is read only",
            "v245 readiness command is read only",
            "readiness checks are deterministic",
            "readiness checks use stable check identifiers",
            "readiness checks use stable reason codes",
            "overall status is ready not_ready or warning",
            "feature-gate declaration is checked",
            "feature-gate enabled state is checked",
            "configured email backend is checked",
            "known nonproduction backends are rejected",
            "default sender presence is checked",
            "double production confirmation is checked",
            "positive owner scope is checked",
            "explicit bounded limit is checked",
            "production batch maximum 25 is checked",
            "v245 implementation scope is exactly four files",
        }

        self.assertTrue(
            required.issubset(
                set(V244_ACCEPTANCE_GATES)
            )
        )
