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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_contract_v259 import (
    SUPERVISED_EXECUTION_ABORT_REASONS,
    SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
    SUPERVISED_EXECUTION_FAILURE_AUDIT_SEQUENCE,
    SUPERVISED_EXECUTION_IMMUTABLE_BINDINGS,
    SUPERVISED_EXECUTION_LIMIT_BAND,
    SUPERVISED_EXECUTION_POST_RUN_GATES,
    SUPERVISED_EXECUTION_PRIVACY_EXCLUSIONS,
    SUPERVISED_EXECUTION_PRODUCTION_COMMAND,
    SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
    SUPERVISED_EXECUTION_REQUIRED_ROLES,
    SUPERVISED_EXECUTION_STAGE_ORDER,
    SUPERVISED_EXECUTION_SUCCESS_AUDIT_SEQUENCE,
    SUPERVISED_EXECUTION_TIME_WINDOWS_SECONDS,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_v260 import (
    SUPERVISED_CONSUMPTION_RESULT_FIELDS,
    SUPERVISED_EXECUTION_PLAN_FIELDS,
    SUPERVISED_FREEZE_FINGERPRINT_FIELDS,
    SUPERVISED_POST_RUN_REASON_CODES,
    SUPERVISED_POST_RUN_RESULT_FIELDS,
    SUPERVISED_PREFLIGHT_RESULT_FIELDS,
    SUPERVISED_SENSITIVE_FIELDS,
    V260_IMPLEMENTATION_GATES,
    SupervisedPostRunEvidence,
    build_freeze_fingerprint,
    consume_supervised_authorization,
    evaluate_supervised_preflight,
    make_supervised_execution_evidence,
    plan_supervised_execution,
    reconcile_supervised_post_run,
    sanitize_supervised_evidence,
    supervised_immutable_binding_snapshot,
)


V261_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CLOSEOUT_AUDIT = (
    "V261_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CLOSEOUT_AUDIT"
)

V259_COMMITTED_SCOPE = (
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

V260_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_v260.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_v260.md"
    ),
)

V261_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_closeout_audit_v261.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_closeout_audit_v261.md"
    ),
)

V262_PROPOSED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_evidence_review_contract_v262.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_evidence_review_contract_v262.md"
    ),
)

EVIDENCE_REVIEW_PRECONDITIONS = (
    "supervised-execution lane is closed",
    "evidence-review checkpoint remains documentation and test only",
    "one change-record identifier is present",
    "one authorization identifier is present",
    "one positive owner identifier is present",
    "approved limit remains between 1 and 3",
    "freeze fingerprint is present",
    "authorization command fingerprint is present",
    "authorization consumption count is known",
    "production invocation count is known",
    "delivery outcome counts are known",
    "persistent audit counts are known",
    "sent-timestamp consistency is known",
    "duplicate-attempt status is known",
    "provider anomaly status is known",
    "incident state is known",
    "privacy sanitizer has been applied",
    "automatic retry remains disabled",
    "automatic rollout promotion remains disabled",
    "review does not perform production delivery",
)

V261_CLOSEOUT_GATES = (
    "v259 supervised-execution contract remains packaged",
    "v260 supervised-execution implementation remains packaged",
    "v259 committed scope remains exactly two files",
    "v260 committed scope remains exactly two files",
    "v261 scope remains exactly two closeout files",
    "v262 evidence-review contract scope is exactly two files",
    "v262 remains documentation and test only",
    "supervised owner scope remains exactly one owner",
    "supervised limit remains exactly 1 through 3",
    "readiness maximum age remains 300 seconds",
    "preview maximum age remains 300 seconds",
    "authorization lifetime remains 600 seconds",
    "pre-send freeze maximum age remains 120 seconds",
    "post-run review deadline remains 600 seconds",
    "required supervision roles remain exact",
    "supervised stage order remains deterministic",
    "freeze fingerprint remains canonical SHA-256",
    "freeze fingerprint fields remain exact",
    "freeze fingerprint binds authorization identifier",
    "freeze fingerprint binds authorization command fingerprint",
    "freeze fingerprint binds owner and limit",
    "freeze fingerprint binds feature-gate state",
    "freeze fingerprint binds backend and sender state",
    "freeze fingerprint binds provider state",
    "freeze fingerprint binds authorization state",
    "freeze fingerprint binds operator and reviewer roles",
    "freeze fingerprint binds freeze timestamp",
    "preflight evaluator remains deterministic",
    "preflight result schema remains sanitized",
    "all 38 abort reasons remain packaged",
    "all 38 abort reasons remain reachable",
    "abort-reason order remains deterministic",
    "positive owner identifier remains mandatory",
    "limit between 1 and 3 remains mandatory",
    "authorized unconsumed authorization remains mandatory",
    "authorization expiration remains enforced",
    "authorization revocation remains enforced",
    "authorization command fingerprint remains enforced",
    "owner bindings remain enforced",
    "limit bindings remain enforced",
    "strict readiness remains mandatory",
    "all nine readiness checks remain mandatory",
    "readiness freshness remains enforced",
    "preview freshness remains enforced",
    "pre-send freeze freshness remains enforced",
    "feature gate remains mandatory",
    "approved backend remains mandatory",
    "configured sender remains mandatory",
    "verified sender remains mandatory",
    "provider credentials remain mandatory",
    "provider quota remains mandatory",
    "operational provider remains mandatory",
    "owner opt-in remains mandatory",
    "eligible candidate remains mandatory",
    "preview count remains bounded",
    "preview skips must remain understood",
    "unexpected preview refusals remain prohibited",
    "concurrent owner run blocks execution",
    "open incident blocks execution",
    "operator identity remains mandatory",
    "two distinct reviewers remain mandatory",
    "rollback reviewer remains mandatory",
    "incident commander remains mandatory",
    "both production confirmations remain mandatory",
    "runtime mutation after freeze remains fail closed",
    "execution plan remains bounded to one authorization consumption",
    "execution plan remains bounded to one production invocation",
    "execution plan remains nonexecuting",
    "aborted plans contain no production command",
    "authorization consumption remains one-shot",
    "authorization reuse remains fail closed",
    "post-run reconciliation remains deterministic",
    "all 17 post-run reasons remain packaged",
    "all 17 post-run reasons remain reachable",
    "post-run reason order remains deterministic",
    "success audit sequence remains exact",
    "failure audit sequence remains exact",
    "post-run review deadline remains enforced",
    "automatic retry remains disabled",
    "automatic rollout promotion remains disabled",
    "evidence sanitizer remains strict allowlist based",
    "unknown evidence fields remain discarded",
    "sensitive evidence fields remain excluded",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "tests perform no production delivery",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v262: saved-search notification production delivery pilot supervised execution evidence review contract"

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
        "pilot_supervised_execution_contract_v259.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_v260.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionCloseoutAuditV261Tests(
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

    def test_v261_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V261_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CLOSEOUT_AUDIT,
            (
                "V261_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V259_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V260_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V261_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V262_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v262: saved-search notification production delivery "
                "pilot supervised execution evidence review contract"
            ),
        )

    def test_v261_v262_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V262_PROPOSED_SCOPE,
            (
                (
                    "backend/listings/"
                    "test_saved_search_notification_production_delivery_"
                    "pilot_supervised_execution_evidence_review_contract_v262.py"
                ),
                (
                    "docs/"
                    "saved_search_notification_production_delivery_"
                    "pilot_supervised_execution_evidence_review_contract_v262.md"
                ),
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V262_PROPOSED_SCOPE
            )
        )

    def test_v261_contract_boundaries_remain_exact(self):
        self.assertEqual(
            SUPERVISED_EXECUTION_LIMIT_BAND,
            (
                1,
                3,
            ),
        )

        self.assertEqual(
            SUPERVISED_EXECUTION_TIME_WINDOWS_SECONDS,
            {
                "readiness_max_age": 300,
                "preview_max_age": 300,
                "authorization_ttl": 600,
                "pre_send_freeze_max_age": 120,
                "post_run_review_deadline": 600,
            },
        )

        self.assertEqual(
            len(SUPERVISED_EXECUTION_ABORT_REASONS),
            38,
        )

        self.assertEqual(
            len(SUPERVISED_POST_RUN_REASON_CODES),
            17,
        )

    def test_v261_roles_and_stage_order_remain_exact(self):
        self.assertEqual(
            SUPERVISED_EXECUTION_REQUIRED_ROLES,
            (
                "operator",
                "primary_reviewer",
                "secondary_reviewer",
                "rollback_reviewer",
                "incident_commander",
            ),
        )

        self.assertEqual(
            len(SUPERVISED_EXECUTION_STAGE_ORDER),
            11,
        )

        self.assertEqual(
            SUPERVISED_EXECUTION_STAGE_ORDER[0],
            "open supervised change window",
        )

        self.assertEqual(
            SUPERVISED_EXECUTION_STAGE_ORDER[-1],
            "close or escalate the change window",
        )

    def test_v261_freeze_fingerprint_fields_remain_exact(self):
        self.assertEqual(
            SUPERVISED_FREEZE_FINGERPRINT_FIELDS,
            (
                "authorization_id",
                "authorization_command_fingerprint",
                "pilot_owner_id",
                "approved_limit",
                "feature_gate_enabled",
                "email_backend_allowed",
                "default_sender_configured",
                "sender_verified",
                "provider_operational",
                "provider_quota_available",
                "authorization_state",
                "operator_identity",
                "primary_reviewer_identity",
                "secondary_reviewer_identity",
                "rollback_reviewer_identity",
                "incident_commander_identity",
                "pre_send_freeze_at_utc",
            ),
        )

    def test_v261_freeze_fingerprint_remains_deterministic_sha256(self):
        evidence = make_supervised_execution_evidence()

        first = build_freeze_fingerprint(
            evidence
        )

        second = build_freeze_fingerprint(
            evidence
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

    def test_v261_freeze_fingerprint_remains_bound_to_state(self):
        evidence = make_supervised_execution_evidence()

        baseline = build_freeze_fingerprint(
            evidence
        )

        variants = (
            replace(
                evidence,
                authorization_id="authorization-002",
            ),
            replace(
                evidence,
                pilot_owner_id=102,
            ),
            replace(
                evidence,
                approved_limit=2,
            ),
            replace(
                evidence,
                feature_gate_enabled=False,
            ),
            replace(
                evidence,
                email_backend_allowed=False,
            ),
            replace(
                evidence,
                sender_verified=False,
            ),
            replace(
                evidence,
                provider_operational=False,
            ),
            replace(
                evidence,
                primary_reviewer_identity="reviewer-c",
            ),
            replace(
                evidence,
                rollback_reviewer_identity="rollback-reviewer-b",
            ),
            replace(
                evidence,
                incident_commander_identity="incident-commander-b",
            ),
            replace(
                evidence,
                pre_send_freeze_at_utc=951,
            ),
        )

        for variant in variants:
            with self.subTest(
                variant=variant
            ):
                self.assertNotEqual(
                    build_freeze_fingerprint(
                        variant
                    ),
                    baseline,
                )

    def test_v261_default_preflight_remains_approved(self):
        result = evaluate_supervised_preflight(
            make_supervised_execution_evidence(),
            now_utc=1000,
        )

        self.assertTrue(
            result["approved"]
        )

        self.assertEqual(
            result["status"],
            "approved",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            tuple(result),
            SUPERVISED_PREFLIGHT_RESULT_FIELDS,
        )

    def test_v261_limit_boundaries_remain_fail_closed(self):
        for limit, approved in (
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

                result = evaluate_supervised_preflight(
                    make_supervised_execution_evidence(
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
                    result["approved"],
                    approved,
                )

    def test_v261_freshness_boundaries_remain_inclusive(self):
        result = evaluate_supervised_preflight(
            make_supervised_execution_evidence(
                readiness_checked_at_utc=700,
                preview_checked_at_utc=700,
                pre_send_freeze_at_utc=880,
            ),
            now_utc=1000,
        )

        self.assertTrue(
            result["approved"]
        )

    def test_v261_stale_readiness_preview_and_freeze_remain_rejected(self):
        result = evaluate_supervised_preflight(
            make_supervised_execution_evidence(
                readiness_checked_at_utc=699,
                preview_checked_at_utc=699,
                pre_send_freeze_at_utc=879,
            ),
            now_utc=1000,
        )

        self.assertEqual(
            result["reason_codes"],
            (
                "readiness_evidence_stale",
                "preview_evidence_stale",
                "pre_send_freeze_stale",
            ),
        )

    def test_v261_all_abort_reasons_remain_reachable(self):
        cases = (
            (
                {
                    "authorization_lane_closed": False,
                },
                "authorization_lane_not_closed",
            ),
            (
                {
                    "pilot_owner_id": 0,
                },
                "invalid_owner_id",
            ),
            (
                {
                    "approved_limit": 4,
                    "preview_limit": 4,
                    "command_limit": 4,
                },
                "invalid_pilot_limit",
            ),
            (
                {
                    "authorization_state": "draft",
                },
                "authorization_not_authorized",
            ),
            (
                {
                    "authorization_consumed": True,
                },
                "authorization_already_consumed",
            ),
            (
                {
                    "authorization_expires_at_utc": 1000,
                },
                "authorization_expired",
            ),
            (
                {
                    "authorization_state": "revoked",
                },
                "authorization_revoked",
            ),
            (
                {
                    "authorization_command_fingerprint": "mismatch",
                },
                "command_fingerprint_mismatch",
            ),
            (
                {
                    "preview_owner_id": 999,
                },
                "owner_binding_mismatch",
            ),
            (
                {
                    "preview_limit": 2,
                },
                "limit_binding_mismatch",
            ),
            (
                {
                    "readiness_status": "not_ready",
                },
                "readiness_not_ready",
            ),
            (
                {
                    "readiness_check_count": 8,
                },
                "readiness_check_count_mismatch",
            ),
            (
                {
                    "readiness_checked_at_utc": 699,
                },
                "readiness_evidence_stale",
            ),
            (
                {
                    "preview_checked_at_utc": 699,
                },
                "preview_evidence_stale",
            ),
            (
                {
                    "pre_send_freeze_at_utc": 879,
                },
                "pre_send_freeze_stale",
            ),
            (
                {
                    "feature_gate_enabled": False,
                },
                "feature_gate_disabled",
            ),
            (
                {
                    "email_backend_allowed": False,
                },
                "email_backend_rejected",
            ),
            (
                {
                    "default_sender_configured": False,
                },
                "default_sender_missing",
            ),
            (
                {
                    "sender_verified": False,
                },
                "sender_unverified",
            ),
            (
                {
                    "provider_credentials_available": False,
                },
                "provider_credentials_unavailable",
            ),
            (
                {
                    "provider_quota_available": 2,
                },
                "provider_quota_insufficient",
            ),
            (
                {
                    "provider_operational": False,
                },
                "provider_not_operational",
            ),
            (
                {
                    "owner_opt_in_enabled": False,
                },
                "owner_opt_in_disabled",
            ),
            (
                {
                    "eligible_due_candidate_count": 0,
                },
                "no_eligible_due_candidate",
            ),
            (
                {
                    "preview_candidate_count": 0,
                },
                "preview_candidate_count_invalid",
            ),
            (
                {
                    "preview_skips_understood": False,
                },
                "preview_skips_unresolved",
            ),
            (
                {
                    "preview_unexpected_refusal_count": 1,
                },
                "preview_unexpected_refusal",
            ),
            (
                {
                    "concurrent_owner_run": True,
                },
                "concurrent_owner_run",
            ),
            (
                {
                    "unresolved_incident": True,
                },
                "unresolved_incident",
            ),
            (
                {
                    "operator_identity": "",
                },
                "operator_identity_missing",
            ),
            (
                {
                    "primary_reviewer_identity": "",
                },
                "primary_reviewer_missing",
            ),
            (
                {
                    "secondary_reviewer_identity": "",
                },
                "secondary_reviewer_missing",
            ),
            (
                {
                    "secondary_reviewer_identity": "reviewer-a",
                },
                "reviewer_identity_collision",
            ),
            (
                {
                    "rollback_reviewer_identity": "",
                },
                "rollback_reviewer_missing",
            ),
            (
                {
                    "incident_commander_identity": "",
                },
                "incident_commander_missing",
            ),
            (
                {
                    "execute_production_send": False,
                },
                "production_confirmation_missing",
            ),
            (
                {
                    "authorization_consumption_succeeds": False,
                },
                "authorization_consumption_failed",
            ),
            (
                {
                    "runtime_freeze_fingerprint": "changed",
                },
                "runtime_state_changed_after_freeze",
            ),
        )

        self.assertEqual(
            len(cases),
            len(SUPERVISED_EXECUTION_ABORT_REASONS),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_supervised_preflight(
                    make_supervised_execution_evidence(
                        **changes
                    ),
                    now_utc=1000,
                )

                self.assertFalse(
                    result["approved"]
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v261_abort_reason_order_remains_deterministic(self):
        result = evaluate_supervised_preflight(
            make_supervised_execution_evidence(
                authorization_lane_closed=False,
                pilot_owner_id=0,
                approved_limit=4,
                preview_owner_id=999,
                preview_limit=2,
                readiness_status="not_ready",
                readiness_check_count=8,
                readiness_checked_at_utc=699,
                preview_checked_at_utc=699,
                pre_send_freeze_at_utc=879,
                feature_gate_enabled=False,
                email_backend_allowed=False,
                default_sender_configured=False,
                sender_verified=False,
                provider_credentials_available=False,
                provider_quota_available=0,
                provider_operational=False,
                owner_opt_in_enabled=False,
                eligible_due_candidate_count=0,
                preview_candidate_count=0,
                preview_skips_understood=False,
                preview_unexpected_refusal_count=1,
                concurrent_owner_run=True,
                unresolved_incident=True,
                operator_identity="",
                primary_reviewer_identity="",
                secondary_reviewer_identity="",
                rollback_reviewer_identity="",
                incident_commander_identity="",
                execute_production_send=False,
                confirm_production_delivery=False,
                authorization_consumption_succeeds=False,
                runtime_freeze_fingerprint="changed",
            ),
            now_utc=1000,
        )

        order = {
            reason: index
            for index, reason in enumerate(
                SUPERVISED_EXECUTION_ABORT_REASONS
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

    def test_v261_immutable_binding_snapshot_remains_exact(self):
        snapshot = supervised_immutable_binding_snapshot(
            make_supervised_execution_evidence()
        )

        self.assertEqual(
            tuple(snapshot),
            SUPERVISED_EXECUTION_IMMUTABLE_BINDINGS,
        )

        self.assertEqual(
            snapshot["pilot_owner_id"],
            101,
        )

        self.assertEqual(
            snapshot["approved_limit"],
            3,
        )

    def test_v261_execution_plan_remains_bounded_and_nonexecuting(self):
        evidence = make_supervised_execution_evidence()

        with patch(
            "subprocess.run"
        ) as subprocess_run:
            plan = plan_supervised_execution(
                evidence,
                now_utc=1000,
            )

        subprocess_run.assert_not_called()

        self.assertEqual(
            tuple(plan),
            SUPERVISED_EXECUTION_PLAN_FIELDS,
        )

        self.assertTrue(
            plan["executable"]
        )

        self.assertEqual(
            plan["authorization_consumption_limit"],
            1,
        )

        self.assertEqual(
            plan["production_invocation_limit"],
            1,
        )

        self.assertEqual(
            plan["command_pattern"],
            SUPERVISED_EXECUTION_PRODUCTION_COMMAND,
        )

    def test_v261_aborted_plan_remains_command_free(self):
        plan = plan_supervised_execution(
            make_supervised_execution_evidence(
                feature_gate_enabled=False,
            ),
            now_utc=1000,
        )

        self.assertFalse(
            plan["executable"]
        )

        self.assertEqual(
            plan["authorization_consumption_limit"],
            0,
        )

        self.assertEqual(
            plan["production_invocation_limit"],
            0,
        )

        self.assertIsNone(
            plan["command_pattern"]
        )

    def test_v261_authorization_consumption_remains_one_shot(self):
        evidence = make_supervised_execution_evidence()

        first = consume_supervised_authorization(
            evidence,
            now_utc=1000,
        )

        self.assertEqual(
            tuple(first),
            SUPERVISED_CONSUMPTION_RESULT_FIELDS,
        )

        self.assertTrue(
            first["consumed"]
        )

        second = consume_supervised_authorization(
            replace(
                evidence,
                authorization_consumed=True,
                authorization_state="consumed",
            ),
            now_utc=1001,
        )

        self.assertFalse(
            second["consumed"]
        )

        self.assertIn(
            "authorization_already_consumed",
            second["reason_codes"],
        )

    def test_v261_runtime_mutation_remains_fail_closed(self):
        result = consume_supervised_authorization(
            make_supervised_execution_evidence(
                runtime_freeze_fingerprint="changed",
            ),
            now_utc=1000,
        )

        self.assertFalse(
            result["consumed"]
        )

        self.assertEqual(
            result["authorization_state"],
            "failed_closed",
        )

        self.assertIn(
            "runtime_state_changed_after_freeze",
            result["reason_codes"],
        )

    def test_v261_default_post_run_reconciliation_remains_closed(self):
        result = reconcile_supervised_post_run(
            SupervisedPostRunEvidence()
        )

        self.assertEqual(
            tuple(result),
            SUPERVISED_POST_RUN_RESULT_FIELDS,
        )

        self.assertTrue(
            result["successful"]
        )

        self.assertEqual(
            result["status"],
            "closed",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

    def test_v261_all_post_run_reasons_remain_reachable(self):
        cases = (
            (
                {
                    "production_invocation_count": 2,
                },
                "production_invocation_count_mismatch",
            ),
            (
                {
                    "authorization_consumption_count": 0,
                },
                "authorization_consumption_count_mismatch",
            ),
            (
                {
                    "expected_candidate_count": 3,
                },
                "delivery_counts_mismatch",
            ),
            (
                {
                    "delivered_count": 1,
                    "failed_count": 1,
                    "delivery_succeeded_event_count": 1,
                    "delivery_failed_event_count": 1,
                    "sent_timestamp_event_count": 1,
                },
                "failed_count_nonzero",
            ),
            (
                {
                    "unexpected_refusal_count": 1,
                },
                "unexpected_refusal_count_nonzero",
            ),
            (
                {
                    "delivery_attempted_event_count": 1,
                },
                "delivery_attempted_event_mismatch",
            ),
            (
                {
                    "delivery_succeeded_event_count": 1,
                },
                "delivery_succeeded_event_mismatch",
            ),
            (
                {
                    "delivery_failed_event_count": 1,
                },
                "delivery_failed_event_mismatch",
            ),
            (
                {
                    "sent_timestamp_event_count": 1,
                },
                "sent_timestamp_event_mismatch",
            ),
            (
                {
                    "sent_timestamp_consistent": False,
                },
                "sent_timestamp_inconsistent",
            ),
            (
                {
                    "duplicate_attempt_clean": False,
                },
                "duplicate_attempt_detected",
            ),
            (
                {
                    "audit_gap_free": False,
                },
                "audit_gap_detected",
            ),
            (
                {
                    "provider_anomaly": True,
                },
                "provider_anomaly_detected",
            ),
            (
                {
                    "incident_state": "open",
                },
                "incident_not_closed_or_escalated",
            ),
            (
                {
                    "review_completed_at_utc": 1701,
                },
                "post_run_review_deadline_missed",
            ),
            (
                {
                    "automatic_retry_enabled": True,
                },
                "automatic_retry_enabled",
            ),
            (
                {
                    "automatic_rollout_promotion_enabled": True,
                },
                "automatic_rollout_promotion_enabled",
            ),
        )

        self.assertEqual(
            len(cases),
            len(SUPERVISED_POST_RUN_REASON_CODES),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = reconcile_supervised_post_run(
                    replace(
                        SupervisedPostRunEvidence(),
                        **changes,
                    )
                )

                self.assertFalse(
                    result["successful"]
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v261_post_run_reason_order_remains_deterministic(self):
        result = reconcile_supervised_post_run(
            SupervisedPostRunEvidence(
                production_invocation_count=2,
                authorization_consumption_count=0,
                expected_candidate_count=3,
                failed_count=1,
                unexpected_refusal_count=1,
                delivery_attempted_event_count=0,
                delivery_succeeded_event_count=0,
                delivery_failed_event_count=0,
                sent_timestamp_event_count=0,
                sent_timestamp_consistent=False,
                duplicate_attempt_clean=False,
                audit_gap_free=False,
                provider_anomaly=True,
                incident_state="open",
                review_completed_at_utc=1701,
                automatic_retry_enabled=True,
                automatic_rollout_promotion_enabled=True,
            )
        )

        order = {
            reason: index
            for index, reason in enumerate(
                SUPERVISED_POST_RUN_REASON_CODES
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

    def test_v261_post_run_deadline_boundary_remains_inclusive(self):
        result = reconcile_supervised_post_run(
            SupervisedPostRunEvidence(
                review_started_at_utc=1100,
                review_completed_at_utc=1700,
            )
        )

        self.assertTrue(
            result["successful"]
        )

    def test_v261_audit_sequences_remain_exact(self):
        self.assertEqual(
            SUPERVISED_EXECUTION_SUCCESS_AUDIT_SEQUENCE,
            (
                "delivery_attempted",
                "delivery_succeeded",
                "sent_timestamp_recorded",
            ),
        )

        self.assertEqual(
            SUPERVISED_EXECUTION_FAILURE_AUDIT_SEQUENCE,
            (
                "delivery_attempted",
                "delivery_failed",
            ),
        )

    def test_v261_evidence_sanitizer_remains_strict(self):
        raw_record = {
            field: f"allowed-{index}"
            for index, field in enumerate(
                SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
                start=1,
            )
        }

        raw_record.update(
            {
                field: f"sensitive-{index}"
                for index, field in enumerate(
                    SUPERVISED_SENSITIVE_FIELDS,
                    start=1,
                )
            }
        )

        raw_record["unknown_field"] = "discard"

        sanitized = sanitize_supervised_evidence(
            raw_record
        )

        self.assertEqual(
            tuple(sanitized),
            SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        for field in SUPERVISED_SENSITIVE_FIELDS:
            with self.subTest(
                field=field
            ):
                self.assertNotIn(
                    field,
                    sanitized,
                )

    def test_v261_privacy_and_prohibition_packages_remain_complete(self):
        self.assertIn(
            "SMTP password",
            SUPERVISED_EXECUTION_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "automatic retry",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "global all-owner execution",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "multi-owner command execution",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "silent partial-failure handling",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

    def test_v261_v260_implementation_gate_package_remains_complete(self):
        required = {
            "v259 supervised-execution contract remains packaged",
            "v260 scope is exactly two implementation files",
            "v261 closeout scope is exactly two files",
            "freeze fingerprint uses canonical SHA-256",
            "preflight evaluator is deterministic",
            "all 38 abort reasons remain reachable",
            "abort-reason order remains deterministic",
            "authorization consumption remains one-shot",
            "runtime mutation after freeze fails closed",
            "execution plan permits at most one invocation",
            "execution plan never invokes production",
            "post-run reconciliation is deterministic",
            "post-run reason order is deterministic",
            "evidence sanitizer remains strict allowlist based",
            "sensitive evidence remains excluded",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service and command remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V260_IMPLEMENTATION_GATES)
            )
        )

    def test_v261_evidence_review_preconditions_are_complete(self):
        required = {
            "supervised-execution lane is closed",
            "evidence-review checkpoint remains documentation and test only",
            "one change-record identifier is present",
            "one authorization identifier is present",
            "one positive owner identifier is present",
            "approved limit remains between 1 and 3",
            "freeze fingerprint is present",
            "authorization command fingerprint is present",
            "authorization consumption count is known",
            "production invocation count is known",
            "delivery outcome counts are known",
            "persistent audit counts are known",
            "sent-timestamp consistency is known",
            "duplicate-attempt status is known",
            "provider anomaly status is known",
            "incident state is known",
            "privacy sanitizer has been applied",
            "automatic retry remains disabled",
            "automatic rollout promotion remains disabled",
            "review does not perform production delivery",
        }

        self.assertEqual(
            set(EVIDENCE_REVIEW_PRECONDITIONS),
            required,
        )

    def test_v261_default_readiness_remains_not_ready(self):
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
    def test_v261_production_like_readiness_remains_ready(self):
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
    def test_v261_readiness_execution_opens_no_email_connection(self):
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

    def test_v261_command_surfaces_remain_unchanged(self):
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

    def test_v261_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v261_scheduler_remains_nonautomatic(self):
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

    def test_v261_v259_and_v260_packages_remain_present(self):
        v259_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_contract_v259.py"
        )

        v260_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_v260.py"
        )

        self.assertIn(
            (
                "V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT"
            ),
            v259_source,
        )

        self.assertIn(
            (
                "V260_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION"
            ),
            v260_source,
        )

        self.assertIn(
            (
                "v261: saved-search notification production "
                "delivery pilot supervised execution closeout audit"
            ),
            v260_source,
        )

    def test_v261_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V261_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CLOSEOUT_AUDIT
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

    def test_v261_no_migration_0017_exists(self):
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

    def test_v261_closeout_gate_matrix_is_complete(self):
        required = {
            "v259 supervised-execution contract remains packaged",
            "v260 supervised-execution implementation remains packaged",
            "v261 scope remains exactly two closeout files",
            "v262 evidence-review contract scope is exactly two files",
            "v262 remains documentation and test only",
            "supervised limit remains exactly 1 through 3",
            "pre-send freeze maximum age remains 120 seconds",
            "post-run review deadline remains 600 seconds",
            "freeze fingerprint remains canonical SHA-256",
            "preflight evaluator remains deterministic",
            "all 38 abort reasons remain packaged",
            "all 38 abort reasons remain reachable",
            "abort-reason order remains deterministic",
            "runtime mutation after freeze remains fail closed",
            "execution plan remains bounded to one production invocation",
            "execution plan remains nonexecuting",
            "authorization consumption remains one-shot",
            "post-run reconciliation remains deterministic",
            "all 17 post-run reasons remain packaged",
            "all 17 post-run reasons remain reachable",
            "post-run reason order remains deterministic",
            "evidence sanitizer remains strict allowlist based",
            "sensitive evidence fields remain excluded",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service and command remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "tests perform no production delivery",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V261_CLOSEOUT_GATES)
            )
        )
