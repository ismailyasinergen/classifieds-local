from __future__ import annotations

import ast
from dataclasses import replace
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
from listings.test_saved_search_notification_production_delivery_pilot_execution_authorization_contract_v256 import (
    AUTHORIZATION_COMMAND_FINGERPRINT_FIELDS,
    AUTHORIZATION_EVIDENCE_FIELDS,
    AUTHORIZATION_IMMUTABLE_BINDINGS,
    AUTHORIZATION_LIFECYCLE_STATES,
    AUTHORIZATION_LIMIT_BAND,
    AUTHORIZATION_PRIVACY_EXCLUSIONS,
    AUTHORIZATION_PROHIBITED_ACTIONS,
    AUTHORIZATION_STAGE_ORDER,
    AUTHORIZATION_STOP_REASONS,
    AUTHORIZATION_TERMINAL_STATES,
    AUTHORIZATION_TIME_WINDOWS_SECONDS,
)
from listings.test_saved_search_notification_production_delivery_pilot_execution_authorization_v257 import (
    AUTHORIZATION_CONSUMPTION_RESULT_FIELDS,
    AUTHORIZATION_EVIDENCE_ALLOWLIST,
    AUTHORIZATION_RESULT_FIELDS,
    AUTHORIZATION_SENSITIVE_FIELDS,
    AUTHORIZATION_STATE_ACTIONS,
    V257_IMPLEMENTATION_GATES,
    build_command_fingerprint,
    consume_authorization,
    evaluate_authorization,
    immutable_binding_snapshot,
    make_authorization_evidence,
    sanitize_authorization_evidence,
    transition_authorization_state,
)


V258_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CLOSEOUT_AUDIT = (
    "V258_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CLOSEOUT_AUDIT"
)

V256_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_contract_v256.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_execution_authorization_contract_v256.md"
    ),
)

V257_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_v257.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_execution_authorization_v257.md"
    ),
)

V258_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_closeout_audit_v258.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_execution_authorization_closeout_audit_v258.md"
    ),
)

V259_PROPOSED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_contract_v259.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_contract_v259.md"
    ),
)

SUPERVISED_EXECUTION_PRECONDITIONS = (
    "authorization lane is closed",
    "supervised-execution checkpoint remains documentation and test only",
    "one positive owner identifier is approved",
    "approved limit remains between 1 and 3",
    "fresh readiness evidence is present",
    "fresh matching preview evidence is present",
    "one unconsumed authorization is present",
    "authorization fingerprint matches command",
    "authorization owner matches preview and command owner",
    "authorization limit matches preview and command limit",
    "two distinct reviewer approvals remain current",
    "provider and sender evidence remain current",
    "no concurrent owner-scoped run exists",
    "no unresolved incident exists",
    "rollback reviewer remains available",
    "production command retains both confirmation flags",
    "authorization consumption occurs at most once",
    "post-run reconciliation is mandatory",
    "no automatic retry is permitted",
    "no automatic rollout promotion is permitted",
)

V258_CLOSEOUT_GATES = (
    "v256 authorization contract remains packaged",
    "v257 authorization implementation remains packaged",
    "v256 committed scope remains exactly two files",
    "v257 committed scope remains exactly two files",
    "v258 scope remains exactly two closeout files",
    "v259 supervised-execution contract scope is exactly two files",
    "v259 remains documentation and test only",
    "authorization limit remains exactly 1 through 3",
    "readiness evidence maximum age remains 300 seconds",
    "preview evidence maximum age remains 300 seconds",
    "authorization lifetime remains 600 seconds",
    "authorization stage order remains deterministic",
    "canonical fingerprint remains SHA-256",
    "fingerprint binds command identity",
    "fingerprint binds execute-production flag",
    "fingerprint binds confirmation flag",
    "fingerprint binds owner identifier",
    "fingerprint binds approved limit",
    "authorization evaluation remains deterministic",
    "all 31 stop reasons remain packaged",
    "stop-reason order remains deterministic",
    "owner identifier must remain positive",
    "preview owner must match approved owner",
    "preview limit must match approved limit",
    "preview candidate count remains bounded",
    "strict readiness must report ready",
    "all nine readiness checks remain required",
    "readiness freshness remains enforced",
    "preview freshness remains enforced",
    "authorization lifetime remains enforced",
    "expired authorization remains rejected",
    "consumed authorization remains rejected",
    "revoked authorization remains rejected",
    "failed-closed authorization remains rejected",
    "provider and sender controls remain required",
    "concurrent owner run blocks authorization",
    "open incident blocks authorization",
    "rollback reviewer remains mandatory",
    "primary reviewer remains mandatory",
    "secondary reviewer remains mandatory",
    "reviewer identities remain distinct",
    "operator identity remains mandatory",
    "command fingerprint mismatch fails closed",
    "both production confirmations remain mandatory",
    "immutable binding snapshot remains deterministic",
    "lifecycle transitions remain deterministic",
    "terminal states cannot reopen",
    "authorization consumption succeeds exactly once",
    "authorization reuse fails closed",
    "presented fingerprint mismatch fails closed",
    "authorization result schema remains sanitized",
    "consumption result schema remains sanitized",
    "evidence sanitizer remains strict allowlist based",
    "sensitive evidence fields remain excluded",
    "tests perform no production delivery",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v259: saved-search notification production delivery pilot supervised execution contract"

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
        "pilot_execution_authorization_contract_v256.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_v257.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotExecutionAuthorizationCloseoutAuditV258Tests(
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

    def test_v258_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V258_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CLOSEOUT_AUDIT,
            (
                "V258_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V256_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V257_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V258_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V259_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v259: saved-search notification production "
                "delivery pilot supervised execution contract"
            ),
        )

    def test_v258_v259_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V259_PROPOSED_SCOPE,
            (
                (
                    "backend/listings/"
                    "test_saved_search_notification_production_delivery_"
                    "pilot_supervised_execution_contract_v259.py"
                ),
                (
                    "docs/"
                    "saved_search_notification_production_delivery_"
                    "pilot_supervised_execution_contract_v259.md"
                ),
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V259_PROPOSED_SCOPE
            )
        )

    def test_v258_contract_boundaries_remain_exact(self):
        self.assertEqual(
            AUTHORIZATION_LIMIT_BAND,
            (
                1,
                3,
            ),
        )

        self.assertEqual(
            AUTHORIZATION_TIME_WINDOWS_SECONDS,
            {
                "readiness_max_age": 300,
                "preview_max_age": 300,
                "authorization_ttl": 600,
            },
        )

        self.assertEqual(
            len(AUTHORIZATION_STAGE_ORDER),
            8,
        )

        self.assertEqual(
            len(AUTHORIZATION_STOP_REASONS),
            31,
        )

    def test_v258_fingerprint_fields_remain_exact(self):
        self.assertEqual(
            AUTHORIZATION_COMMAND_FINGERPRINT_FIELDS,
            (
                "command_name",
                "execute_production_send",
                "confirm_production_delivery",
                "owner_id",
                "limit",
            ),
        )

    def test_v258_fingerprint_remains_deterministic_sha256(self):
        first = build_command_fingerprint(
            command_name="process_saved_search_notifications",
            execute_production_send=True,
            confirm_production_delivery=True,
            owner_id=101,
            limit=3,
        )

        second = build_command_fingerprint(
            command_name="process_saved_search_notifications",
            execute_production_send=True,
            confirm_production_delivery=True,
            owner_id=101,
            limit=3,
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            len(first),
            64,
        )

        self.assertTrue(
            all(
                character in "0123456789abcdef"
                for character in first
            )
        )

    def test_v258_fingerprint_remains_bound_to_every_field(self):
        base = {
            "command_name": "process_saved_search_notifications",
            "execute_production_send": True,
            "confirm_production_delivery": True,
            "owner_id": 101,
            "limit": 3,
        }

        baseline = build_command_fingerprint(
            **base
        )

        variants = (
            {
                **base,
                "command_name": "other",
            },
            {
                **base,
                "execute_production_send": False,
            },
            {
                **base,
                "confirm_production_delivery": False,
            },
            {
                **base,
                "owner_id": 102,
            },
            {
                **base,
                "limit": 2,
            },
        )

        for variant in variants:
            with self.subTest(
                variant=variant
            ):
                self.assertNotEqual(
                    build_command_fingerprint(
                        **variant
                    ),
                    baseline,
                )

    def test_v258_default_authorization_remains_authorized(self):
        evidence = make_authorization_evidence()

        result = evaluate_authorization(
            evidence,
            now_utc=1000,
        )

        self.assertTrue(
            result["authorized"]
        )

        self.assertEqual(
            result["status"],
            "authorized",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            tuple(result),
            AUTHORIZATION_RESULT_FIELDS,
        )

    def test_v258_limit_boundaries_remain_fail_closed(self):
        for limit, authorized in (
            (
                1,
                True,
            ),
            (
                3,
                True,
            ),
            (
                0,
                False,
            ),
            (
                4,
                False,
            ),
        ):
            with self.subTest(
                limit=limit
            ):
                candidate_count = (
                    1
                    if limit <= 1
                    else min(
                        limit,
                        2,
                    )
                )

                result = evaluate_authorization(
                    make_authorization_evidence(
                        approved_limit=limit,
                        preview_limit=limit,
                        preview_candidate_count=candidate_count,
                        provider_quota_available=max(
                            limit,
                            0,
                        ),
                        command_limit=limit,
                    ),
                    now_utc=1000,
                )

                self.assertEqual(
                    result["authorized"],
                    authorized,
                )

    def test_v258_freshness_boundaries_remain_inclusive(self):
        result = evaluate_authorization(
            make_authorization_evidence(
                readiness_checked_at_utc=700,
                preview_checked_at_utc=700,
            ),
            now_utc=1000,
        )

        self.assertTrue(
            result["authorized"]
        )

    def test_v258_stale_evidence_remains_rejected(self):
        result = evaluate_authorization(
            make_authorization_evidence(
                readiness_checked_at_utc=699,
                preview_checked_at_utc=699,
            ),
            now_utc=1000,
        )

        self.assertEqual(
            result["reason_codes"],
            (
                "readiness_evidence_stale",
                "preview_evidence_stale",
            ),
        )

    def test_v258_authorization_lifetime_boundary_remains_enforced(self):
        valid = evaluate_authorization(
            make_authorization_evidence(
                issued_at_utc=950,
                expires_at_utc=1550,
            ),
            now_utc=1000,
        )

        invalid = evaluate_authorization(
            make_authorization_evidence(
                issued_at_utc=950,
                expires_at_utc=1551,
            ),
            now_utc=1000,
        )

        self.assertTrue(
            valid["authorized"]
        )

        self.assertIn(
            "authorization_ttl_invalid",
            invalid["reason_codes"],
        )

    def test_v258_stop_reason_order_remains_deterministic(self):
        result = evaluate_authorization(
            make_authorization_evidence(
                pilot_readiness_lane_closed=False,
                pilot_owner_id=0,
                approved_limit=4,
                preview_owner_id=999,
                preview_limit=2,
                preview_candidate_count=0,
                readiness_status="not_ready",
                readiness_check_count=8,
                readiness_checked_at_utc=699,
                preview_checked_at_utc=699,
                feature_gate_enabled=False,
                email_backend_allowed=False,
                default_sender_configured=False,
                sender_verified=False,
                provider_credentials_available=False,
                provider_quota_available=0,
                provider_operational=False,
                concurrent_owner_run=True,
                unresolved_incident=True,
                rollback_reviewer_available=False,
                primary_reviewer_identity="",
                secondary_reviewer_identity="",
                operator_identity="",
                command_owner_id=999,
                command_limit=2,
                execute_production_send=False,
                confirm_production_delivery=False,
            ),
            now_utc=1000,
        )

        order = {
            reason: index
            for index, reason in enumerate(
                AUTHORIZATION_STOP_REASONS
            )
        }

        self.assertEqual(
            result["reason_codes"],
            tuple(
                sorted(
                    result["reason_codes"],
                    key=order.__getitem__,
                )
            ),
        )

    def test_v258_all_terminal_states_remain_locked(self):
        for state in AUTHORIZATION_TERMINAL_STATES:
            with self.subTest(
                state=state
            ):
                transition = transition_authorization_state(
                    current_state=state,
                    action="authorize",
                )

                self.assertFalse(
                    transition["applied"]
                )

                self.assertEqual(
                    transition["state"],
                    state,
                )

                self.assertEqual(
                    transition["reason_code"],
                    "terminal_state_locked",
                )

    def test_v258_valid_lifecycle_sequence_remains_deterministic(self):
        state = "draft"

        for action, expected in (
            (
                "submit",
                "ready_for_review",
            ),
            (
                "authorize",
                "authorized",
            ),
            (
                "consume",
                "consumed",
            ),
        ):
            transition = transition_authorization_state(
                current_state=state,
                action=action,
            )

            self.assertTrue(
                transition["applied"]
            )

            self.assertEqual(
                transition["state"],
                expected,
            )

            state = transition["state"]

    def test_v258_invalid_transition_remains_fail_closed(self):
        self.assertEqual(
            transition_authorization_state(
                current_state="draft",
                action="consume",
            ),
            {
                "applied": False,
                "state": "failed_closed",
                "reason_code": "invalid_state_transition",
            },
        )

    def test_v258_authorization_consumption_remains_one_shot(self):
        evidence = make_authorization_evidence()

        first = consume_authorization(
            evidence,
            now_utc=1000,
            presented_fingerprint=(
                evidence.command_fingerprint
            ),
        )

        self.assertTrue(
            first["consumed"]
        )

        self.assertEqual(
            tuple(first),
            AUTHORIZATION_CONSUMPTION_RESULT_FIELDS,
        )

        second = consume_authorization(
            replace(
                evidence,
                authorization_state="consumed",
                consumed_at_utc=1000,
            ),
            now_utc=1001,
            presented_fingerprint=(
                evidence.command_fingerprint
            ),
        )

        self.assertFalse(
            second["consumed"]
        )

        self.assertIn(
            "authorization_already_consumed",
            second["reason_codes"],
        )

    def test_v258_presented_fingerprint_mismatch_remains_fail_closed(self):
        result = consume_authorization(
            make_authorization_evidence(),
            now_utc=1000,
            presented_fingerprint="mismatch",
        )

        self.assertFalse(
            result["consumed"]
        )

        self.assertEqual(
            result["authorization_state"],
            "failed_closed",
        )

        self.assertEqual(
            result["reason_codes"],
            (
                "command_fingerprint_mismatch",
            ),
        )

    def test_v258_immutable_binding_snapshot_remains_exact(self):
        snapshot = immutable_binding_snapshot(
            make_authorization_evidence()
        )

        self.assertEqual(
            tuple(snapshot),
            AUTHORIZATION_IMMUTABLE_BINDINGS,
        )

        self.assertEqual(
            snapshot["pilot_owner_id"],
            101,
        )

        self.assertEqual(
            snapshot["approved_limit"],
            3,
        )

    def test_v258_evidence_allowlist_matches_contract(self):
        self.assertEqual(
            AUTHORIZATION_EVIDENCE_ALLOWLIST,
            AUTHORIZATION_EVIDENCE_FIELDS,
        )

        self.assertTrue(
            set(AUTHORIZATION_EVIDENCE_ALLOWLIST)
            .isdisjoint(
                AUTHORIZATION_SENSITIVE_FIELDS
            )
        )

    def test_v258_evidence_sanitizer_remains_strict(self):
        raw_record = {
            field: f"allowed-{index}"
            for index, field in enumerate(
                AUTHORIZATION_EVIDENCE_ALLOWLIST,
                start=1,
            )
        }

        raw_record.update(
            {
                field: f"sensitive-{index}"
                for index, field in enumerate(
                    AUTHORIZATION_SENSITIVE_FIELDS,
                    start=1,
                )
            }
        )

        raw_record["unknown_field"] = "discard"

        sanitized = sanitize_authorization_evidence(
            raw_record
        )

        self.assertEqual(
            tuple(sanitized),
            AUTHORIZATION_EVIDENCE_ALLOWLIST,
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        for field in AUTHORIZATION_SENSITIVE_FIELDS:
            with self.subTest(
                field=field
            ):
                self.assertNotIn(
                    field,
                    sanitized,
                )

    def test_v258_privacy_and_prohibition_packages_remain_complete(self):
        self.assertIn(
            "SMTP password",
            AUTHORIZATION_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "authorization reuse",
            AUTHORIZATION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "global all-owner execution",
            AUTHORIZATION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "multi-owner command execution",
            AUTHORIZATION_PROHIBITED_ACTIONS,
        )

    def test_v258_state_contract_remains_exact(self):
        self.assertEqual(
            AUTHORIZATION_LIFECYCLE_STATES,
            (
                "draft",
                "ready_for_review",
                "authorized",
                "consumed",
                "expired",
                "revoked",
                "failed_closed",
            ),
        )

        self.assertEqual(
            AUTHORIZATION_TERMINAL_STATES,
            (
                "consumed",
                "expired",
                "revoked",
                "failed_closed",
            ),
        )

        self.assertEqual(
            AUTHORIZATION_STATE_ACTIONS["consume"],
            {
                "authorized": "consumed",
            },
        )

    def test_v258_v257_implementation_gate_package_remains_complete(self):
        required = {
            "v256 authorization contract remains packaged",
            "v257 scope is exactly two implementation files",
            "v258 closeout scope is exactly two files",
            "authorization limit remains 1 through 3",
            "readiness maximum age remains 300 seconds",
            "preview maximum age remains 300 seconds",
            "authorization lifetime remains 600 seconds",
            "command fingerprint uses canonical SHA-256",
            "authorization evaluation is deterministic",
            "authorization stop-reason order is deterministic",
            "terminal states cannot reopen",
            "authorization is consumed exactly once",
            "authorization reuse fails closed",
            "evidence sanitizer is allowlist based",
            "sensitive evidence fields are excluded",
            "tests perform no production delivery",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V257_IMPLEMENTATION_GATES)
            )
        )

    def test_v258_supervised_execution_preconditions_are_complete(self):
        required = {
            "authorization lane is closed",
            "supervised-execution checkpoint remains documentation and test only",
            "one positive owner identifier is approved",
            "approved limit remains between 1 and 3",
            "fresh readiness evidence is present",
            "fresh matching preview evidence is present",
            "one unconsumed authorization is present",
            "authorization fingerprint matches command",
            "authorization owner matches preview and command owner",
            "authorization limit matches preview and command limit",
            "two distinct reviewer approvals remain current",
            "provider and sender evidence remain current",
            "no concurrent owner-scoped run exists",
            "no unresolved incident exists",
            "rollback reviewer remains available",
            "production command retains both confirmation flags",
            "authorization consumption occurs at most once",
            "post-run reconciliation is mandatory",
            "no automatic retry is permitted",
            "no automatic rollout promotion is permitted",
        }

        self.assertEqual(
            set(SUPERVISED_EXECUTION_PRECONDITIONS),
            required,
        )

    def test_v258_default_readiness_remains_not_ready(self):
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
    def test_v258_production_like_readiness_remains_ready(self):
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
    def test_v258_readiness_execution_opens_no_email_connection(self):
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

    def test_v258_command_surfaces_remain_unchanged(self):
        readiness_source = self._read_backend(
            "listings/management/commands/"
            "check_saved_search_notification_production_readiness.py"
        )

        production_source = self._read_backend(
            "listings/management/commands/"
            "process_saved_search_notifications.py"
        )

        readiness_tree = ast.parse(
            readiness_source
        )

        production_tree = ast.parse(
            production_source
        )

        readiness_options = {
            argument.value
            for node in ast.walk(readiness_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        }

        production_options = {
            argument.value
            for node in ast.walk(production_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        }

        self.assertEqual(
            readiness_options,
            {
                "--strict",
                "--json",
            },
        )

        self.assertTrue(
            {
                "--execute-production-send",
                "--confirm-production-delivery",
                "--owner-id",
                "--limit",
            }.issubset(
                production_options
            )
        )

    def test_v258_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v258_scheduler_remains_nonautomatic(self):
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

    def test_v258_v256_and_v257_packages_remain_present(self):
        v256_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_execution_authorization_contract_v256.py"
        )

        v257_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_execution_authorization_v257.py"
        )

        self.assertIn(
            (
                "V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT"
            ),
            v256_source,
        )

        self.assertIn(
            (
                "V257_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_EXECUTION_AUTHORIZATION"
            ),
            v257_source,
        )

        self.assertIn(
            (
                "v258: saved-search notification production "
                "delivery pilot execution authorization closeout audit"
            ),
            v257_source,
        )

    def test_v258_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V258_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CLOSEOUT_AUDIT
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

    def test_v258_no_migration_0017_exists(self):
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

    def test_v258_closeout_gate_matrix_is_complete(self):
        required = {
            "v256 authorization contract remains packaged",
            "v257 authorization implementation remains packaged",
            "v258 scope remains exactly two closeout files",
            "v259 supervised-execution contract scope is exactly two files",
            "v259 remains documentation and test only",
            "authorization limit remains exactly 1 through 3",
            "readiness evidence maximum age remains 300 seconds",
            "preview evidence maximum age remains 300 seconds",
            "authorization lifetime remains 600 seconds",
            "canonical fingerprint remains SHA-256",
            "all 31 stop reasons remain packaged",
            "stop-reason order remains deterministic",
            "terminal states cannot reopen",
            "authorization consumption succeeds exactly once",
            "authorization reuse fails closed",
            "evidence sanitizer remains strict allowlist based",
            "sensitive evidence fields remain excluded",
            "tests perform no production delivery",
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
                set(V258_CLOSEOUT_GATES)
            )
        )
