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
from listings.test_saved_search_notification_production_delivery_pilot_readiness_v254 import (
    PILOT_ALLOWED_RECORD_FIELDS,
    PILOT_DECISION_STAGE_ORDER,
    PILOT_IMPLEMENTATION_GATES,
    PILOT_LIMIT_BAND,
    PILOT_POST_RUN_REASON_ORDER,
    PILOT_PREFLIGHT_REASON_ORDER,
    PILOT_PREVIEW_COMMAND,
    PILOT_PRODUCTION_COMMAND,
    PILOT_SENSITIVE_RECORD_FIELDS,
    PilotPostRunEvidence,
    PilotPreflightEvidence,
    evaluate_pilot_post_run,
    evaluate_pilot_preflight,
    sanitize_pilot_evidence_record,
)


V255_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CLOSEOUT_AUDIT = (
    "V255_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CLOSEOUT_AUDIT"
)

V253_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_contract_v253.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_readiness_contract_v253.md"
    ),
)

V254_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_v254.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_readiness_v254.md"
    ),
)

V255_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_closeout_audit_v255.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_readiness_closeout_audit_v255.md"
    ),
)

V256_PROPOSED_SCOPE = (
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

PILOT_PREFLIGHT_RESULT_FIELDS = (
    "ready",
    "status",
    "reason_codes",
    "owner_id",
    "approved_limit",
    "preview_candidate_count",
)

PILOT_POST_RUN_RESULT_FIELDS = (
    "successful",
    "status",
    "reason_codes",
    "preview_candidate_count",
    "delivered_count",
    "skipped_count",
    "refused_count",
    "failed_count",
)

PILOT_EXECUTION_AUTHORIZATION_PRECONDITIONS = (
    "pilot-readiness lane is closed",
    "authorization checkpoint remains documentation and test only",
    "one positive owner identifier is approved",
    "pilot limit is between 1 and 3",
    "owner and limit approval is time bounded",
    "strict readiness is rerun immediately before authorization",
    "sanitized readiness JSON is retained",
    "matching owner-scoped preview is rerun",
    "preview candidate count is between 1 and approved limit",
    "provider and sender verification remain current",
    "no concurrent owner-scoped run exists",
    "no unresolved incident exists",
    "rollback reviewer remains available",
    "production requires both confirmation flags",
    "authorization permits at most one invocation",
    "authorization does not permit automatic phase promotion",
)

PILOT_CLOSEOUT_GATES = (
    "v253 pilot-readiness contract remains packaged",
    "v254 pilot-readiness implementation remains packaged",
    "v253 committed scope remains exactly two files",
    "v254 committed scope remains exactly two files",
    "v255 scope remains exactly two closeout files",
    "v256 authorization-contract scope is exactly two files",
    "v256 remains documentation and test only",
    "pilot limit band remains exactly 1 through 3",
    "decision-stage order remains deterministic",
    "authorization stage remains first",
    "post-run verification remains last",
    "preflight reason-code count remains 30",
    "preflight reason-code order remains deterministic",
    "post-run reason-code count remains 12",
    "post-run reason-code order remains deterministic",
    "positive owner identifier remains mandatory",
    "owner approval remains mandatory",
    "reviewer approval remains mandatory",
    "owner-scope isolation remains mandatory",
    "notification opt-in remains mandatory",
    "eligible due saved-search state remains mandatory",
    "usable recipient state remains mandatory",
    "concurrent owner run blocks readiness",
    "open incident blocks readiness",
    "feature gate must be enabled",
    "approved email backend remains mandatory",
    "default sender configuration remains mandatory",
    "sender verification remains mandatory",
    "provider credential availability remains mandatory",
    "provider quota remains mandatory",
    "provider operational state remains mandatory",
    "bounce and complaint ownership remains mandatory",
    "approved execution window remains mandatory",
    "rollback reviewer remains mandatory",
    "strict readiness must report ready",
    "all nine readiness checks remain present",
    "sanitized readiness JSON remains mandatory",
    "deployed command-help review remains mandatory",
    "rollback controls remain source verified",
    "preview owner must match approved owner",
    "preview limit must match approved limit",
    "preview candidate count must be between 1 and approved limit",
    "preview skip classifications must be understood",
    "preview unexpected refusal count must be zero",
    "preview command remains nonproduction",
    "production command retains both confirmation flags",
    "preflight result schema remains sanitized",
    "post-run result schema remains sanitized",
    "evidence sanitizer remains strict allowlist based",
    "sensitive evidence fields remain excluded",
    "post-run failed count must be zero",
    "post-run refusal count must be zero",
    "delivery counts must reconcile",
    "persistent audit-event counts must reconcile",
    "sent timestamp evidence must reconcile",
    "duplicate-attempt review must remain clean",
    "audit gaps block success",
    "provider anomaly blocks success",
    "open incident blocks success",
    "understood skips may reconcile successfully",
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

NEXT_CHECKPOINT = "v256: saved-search notification production delivery pilot execution authorization contract"

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
        "pilot_readiness_contract_v253.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_v254.py"
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
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_v251.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_closeout_audit_v252.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_contract_v253.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_v254.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotReadinessCloseoutAuditV255Tests(
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

    def test_v255_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V255_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CLOSEOUT_AUDIT,
            (
                "V255_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_READINESS_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V253_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V254_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V255_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V256_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v256: saved-search notification production "
                "delivery pilot execution authorization contract"
            ),
        )

    def test_v255_v256_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V256_PROPOSED_SCOPE,
            (
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
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V256_PROPOSED_SCOPE
            )
        )

    def test_v255_pilot_limit_and_stage_order_remain_exact(self):
        self.assertEqual(
            PILOT_LIMIT_BAND,
            (
                1,
                3,
            ),
        )

        self.assertEqual(
            PILOT_DECISION_STAGE_ORDER,
            (
                "authorization",
                "owner eligibility",
                "environment verification",
                "strict readiness",
                "matching preview",
                "reviewer go decision",
                "guarded production invocation",
                "post-run verification",
            ),
        )

    def test_v255_reason_code_packages_remain_exact(self):
        self.assertEqual(
            len(PILOT_PREFLIGHT_REASON_ORDER),
            30,
        )

        self.assertEqual(
            len(PILOT_POST_RUN_REASON_ORDER),
            12,
        )

        self.assertEqual(
            PILOT_PREFLIGHT_REASON_ORDER[0],
            "invalid_owner_id",
        )

        self.assertEqual(
            PILOT_PREFLIGHT_REASON_ORDER[-1],
            "preview_unexpected_refusal",
        )

        self.assertEqual(
            PILOT_POST_RUN_REASON_ORDER[0],
            "failed_count_nonzero",
        )

        self.assertEqual(
            PILOT_POST_RUN_REASON_ORDER[-1],
            "incident_open",
        )

    def test_v255_default_preflight_result_remains_ready_and_sanitized(self):
        result = evaluate_pilot_preflight(
            PilotPreflightEvidence()
        )

        self.assertTrue(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "ready",
        )

        self.assertEqual(
            tuple(result),
            PILOT_PREFLIGHT_RESULT_FIELDS,
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

    def test_v255_preflight_reason_order_remains_deterministic(self):
        evidence = PilotPreflightEvidence(
            owner_id=0,
            approved_limit=4,
            owner_approved=False,
            reviewer_approved=False,
            owner_scope_isolated=False,
            notification_opt_in_enabled=False,
            eligible_due_count=0,
            recipient_usable=False,
            concurrent_owner_run=True,
            unresolved_incident=True,
            feature_gate_enabled=False,
            email_backend_allowed=False,
            default_sender_configured=False,
            sender_verified=False,
            provider_credentials_available=False,
            provider_quota_available=0,
            provider_operational=False,
            bounce_complaint_owner_assigned=False,
            execution_window_approved=False,
            rollback_reviewer_available=False,
            strict_readiness_ready=False,
            readiness_check_count=8,
            readiness_json_retained=False,
            deployed_help_reviewed=False,
            rollback_controls_verified=False,
            preview_owner_id=999,
            preview_limit=2,
            preview_candidate_count=0,
            preview_skips_understood=False,
            preview_unexpected_refusal_count=1,
        )

        result = evaluate_pilot_preflight(
            evidence
        )

        self.assertFalse(
            result["ready"]
        )

        self.assertEqual(
            result["reason_codes"],
            PILOT_PREFLIGHT_REASON_ORDER,
        )

    def test_v255_pilot_limit_boundaries_remain_fail_closed(self):
        for limit, ready in (
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

                result = evaluate_pilot_preflight(
                    replace(
                        PilotPreflightEvidence(),
                        approved_limit=limit,
                        preview_limit=limit,
                        preview_candidate_count=candidate_count,
                        provider_quota_available=max(
                            limit,
                            0,
                        ),
                    )
                )

                self.assertEqual(
                    result["ready"],
                    ready,
                )

    def test_v255_default_post_run_result_remains_successful(self):
        result = evaluate_pilot_post_run(
            PilotPostRunEvidence()
        )

        self.assertTrue(
            result["successful"]
        )

        self.assertEqual(
            result["status"],
            "successful",
        )

        self.assertEqual(
            tuple(result),
            PILOT_POST_RUN_RESULT_FIELDS,
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

    def test_v255_post_run_reason_order_remains_deterministic(self):
        evidence = PilotPostRunEvidence(
            preview_candidate_count=5,
            delivered_count=1,
            skipped_count=0,
            refused_count=1,
            failed_count=1,
            attempted_event_count=0,
            succeeded_event_count=0,
            failed_event_count=0,
            timestamp_event_count=0,
            sent_timestamp_consistent=False,
            duplicate_attempt_clean=False,
            audit_gap_free=False,
            provider_anomaly=True,
            incident_open=True,
        )

        result = evaluate_pilot_post_run(
            evidence
        )

        self.assertFalse(
            result["successful"]
        )

        self.assertEqual(
            result["reason_codes"],
            PILOT_POST_RUN_REASON_ORDER,
        )

    def test_v255_understood_skips_remain_reconcilable(self):
        result = evaluate_pilot_post_run(
            PilotPostRunEvidence(
                preview_candidate_count=3,
                delivered_count=2,
                skipped_count=1,
                attempted_event_count=2,
                succeeded_event_count=2,
                timestamp_event_count=2,
            )
        )

        self.assertTrue(
            result["successful"]
        )

        self.assertEqual(
            result["skipped_count"],
            1,
        )

    def test_v255_evidence_allowlist_and_sensitive_fields_are_disjoint(self):
        self.assertTrue(
            set(PILOT_ALLOWED_RECORD_FIELDS)
            .isdisjoint(
                PILOT_SENSITIVE_RECORD_FIELDS
            )
        )

        self.assertIn(
            "pilot_owner_id",
            PILOT_ALLOWED_RECORD_FIELDS,
        )

        self.assertIn(
            "decision",
            PILOT_ALLOWED_RECORD_FIELDS,
        )

        self.assertIn(
            "smtp_password",
            PILOT_SENSITIVE_RECORD_FIELDS,
        )

        self.assertIn(
            "recipient_email",
            PILOT_SENSITIVE_RECORD_FIELDS,
        )

    def test_v255_evidence_sanitizer_remains_strict_allowlist_based(self):
        raw_record = {
            field: f"allowed-{index}"
            for index, field in enumerate(
                PILOT_ALLOWED_RECORD_FIELDS,
                start=1,
            )
        }

        raw_record.update(
            {
                field: f"sensitive-{index}"
                for index, field in enumerate(
                    PILOT_SENSITIVE_RECORD_FIELDS,
                    start=1,
                )
            }
        )

        raw_record["unknown_field"] = "discard-me"

        sanitized = sanitize_pilot_evidence_record(
            raw_record
        )

        self.assertEqual(
            tuple(sanitized),
            PILOT_ALLOWED_RECORD_FIELDS,
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        for field in PILOT_SENSITIVE_RECORD_FIELDS:
            with self.subTest(
                field=field
            ):
                self.assertNotIn(
                    field,
                    sanitized,
                )

    def test_v255_result_schemas_remain_free_of_sensitive_fields(self):
        preflight_result = evaluate_pilot_preflight(
            PilotPreflightEvidence()
        )

        post_run_result = evaluate_pilot_post_run(
            PilotPostRunEvidence()
        )

        serialized = (
            repr(preflight_result)
            + repr(post_run_result)
        ).lower()

        for term in (
            "smtp_password",
            "smtp_username",
            "api_key",
            "access_token",
            "recipient_email",
            "default_sender",
            "rendered_body",
            "provider_response_body",
        ):
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    serialized,
                )

    def test_v255_preview_command_remains_nonproduction(self):
        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            PILOT_PREVIEW_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            PILOT_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--execute-production-send",
            PILOT_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--confirm-production-delivery",
            PILOT_PREVIEW_COMMAND,
        )

    def test_v255_production_command_retains_all_controls(self):
        self.assertIn(
            "--execute-production-send",
            PILOT_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--confirm-production-delivery",
            PILOT_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            PILOT_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            PILOT_PRODUCTION_COMMAND,
        )

    def test_v255_v254_implementation_gate_package_remains_complete(self):
        required = {
            "v253 pilot-readiness contract remains packaged",
            "v254 scope is exactly two implementation files",
            "pilot limit band remains exactly 1 through 3",
            "decision-stage order is deterministic",
            "preflight reason-code order is deterministic",
            "post-run reason-code order is deterministic",
            "strict readiness must report ready",
            "all nine readiness checks must remain present",
            "preview owner must match approved owner",
            "preview limit must match approved limit",
            "preview command contains no production flags",
            "production command contains both confirmation flags",
            "pilot evidence record uses an allowlist",
            "sensitive evidence fields are excluded",
            "tests execute no production delivery",
            "scheduler remains nonautomatic",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(PILOT_IMPLEMENTATION_GATES)
            )
        )

    def test_v255_execution_authorization_preconditions_are_complete(self):
        required = {
            "pilot-readiness lane is closed",
            "authorization checkpoint remains documentation and test only",
            "one positive owner identifier is approved",
            "pilot limit is between 1 and 3",
            "owner and limit approval is time bounded",
            "strict readiness is rerun immediately before authorization",
            "sanitized readiness JSON is retained",
            "matching owner-scoped preview is rerun",
            "preview candidate count is between 1 and approved limit",
            "provider and sender verification remain current",
            "no concurrent owner-scoped run exists",
            "no unresolved incident exists",
            "rollback reviewer remains available",
            "production requires both confirmation flags",
            "authorization permits at most one invocation",
            "authorization does not permit automatic phase promotion",
        }

        self.assertEqual(
            set(PILOT_EXECUTION_AUTHORIZATION_PRECONDITIONS),
            required,
        )

    def test_v255_default_readiness_remains_not_ready(self):
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
    def test_v255_production_like_readiness_remains_ready(self):
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
    def test_v255_readiness_execution_opens_no_email_connection(self):
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

    def test_v255_command_surfaces_remain_unchanged(self):
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

    def test_v255_production_batch_cap_remains_25(self):
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

    def test_v255_scheduler_remains_nonautomatic(self):
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

    def test_v255_v253_and_v254_packages_remain_present(self):
        v253_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_readiness_contract_v253.py"
        )

        v254_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_readiness_v254.py"
        )

        self.assertIn(
            (
                "V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_READINESS_CONTRACT"
            ),
            v253_source,
        )

        self.assertIn(
            (
                "V254_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_READINESS"
            ),
            v254_source,
        )

        self.assertIn(
            (
                "v255: saved-search notification production "
                "delivery pilot readiness closeout audit"
            ),
            v254_source,
        )

    def test_v255_historical_safety_package_is_present(self):
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

    def test_v255_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V255_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CLOSEOUT_AUDIT
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

    def test_v255_no_migration_0017_exists(self):
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

    def test_v255_closeout_gate_matrix_is_complete(self):
        required = {
            "v253 pilot-readiness contract remains packaged",
            "v254 pilot-readiness implementation remains packaged",
            "v255 scope remains exactly two closeout files",
            "v256 authorization-contract scope is exactly two files",
            "v256 remains documentation and test only",
            "pilot limit band remains exactly 1 through 3",
            "decision-stage order remains deterministic",
            "preflight reason-code count remains 30",
            "post-run reason-code count remains 12",
            "strict readiness must report ready",
            "all nine readiness checks remain present",
            "preview owner must match approved owner",
            "preview limit must match approved limit",
            "preview command remains nonproduction",
            "production command retains both confirmation flags",
            "preflight result schema remains sanitized",
            "post-run result schema remains sanitized",
            "evidence sanitizer remains strict allowlist based",
            "sensitive evidence fields remain excluded",
            "post-run failed count must be zero",
            "post-run refusal count must be zero",
            "delivery counts must reconcile",
            "persistent audit-event counts must reconcile",
            "sent timestamp evidence must reconcile",
            "duplicate-attempt review must remain clean",
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
                set(PILOT_CLOSEOUT_GATES)
            )
        )
