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
from listings.test_saved_search_notification_production_delivery_pilot_execution_authorization_closeout_audit_v258 import (
    SUPERVISED_EXECUTION_PRECONDITIONS,
)


V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT = (
    "V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT"
)

V258_COMMITTED_SCOPE = (
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

V259_ALLOWED_SCOPE = (
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

V260_ALLOWED_SCOPE = (
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

SUPERVISED_EXECUTION_LIMIT_BAND = (
    1,
    3,
)

SUPERVISED_EXECUTION_TIME_WINDOWS_SECONDS = {
    "readiness_max_age": 300,
    "preview_max_age": 300,
    "authorization_ttl": 600,
    "pre_send_freeze_max_age": 120,
    "post_run_review_deadline": 600,
}

SUPERVISED_EXECUTION_REQUIRED_ROLES = (
    "operator",
    "primary_reviewer",
    "secondary_reviewer",
    "rollback_reviewer",
    "incident_commander",
)

SUPERVISED_EXECUTION_STAGE_ORDER = (
    "open supervised change window",
    "verify immutable authorization bindings",
    "rerun strict readiness",
    "rerun matching preview",
    "freeze provider sender owner and limit state",
    "record final reviewer go decision",
    "consume authorization exactly once",
    "invoke one guarded production command",
    "capture persistent audit and timestamp evidence",
    "perform mandatory post-run reconciliation",
    "close or escalate the change window",
)

SUPERVISED_EXECUTION_REQUIRED_EVIDENCE = (
    "change_record_id",
    "authorization_id",
    "authorization_state",
    "authorization_command_fingerprint",
    "pilot_owner_id",
    "approved_limit",
    "preview_owner_id",
    "preview_limit",
    "preview_candidate_count",
    "readiness_status",
    "readiness_ready_count",
    "readiness_not_ready_count",
    "readiness_warning_count",
    "readiness_checked_at_utc",
    "preview_checked_at_utc",
    "pre_send_freeze_at_utc",
    "authorization_consumed_at_utc",
    "production_started_at_utc",
    "production_finished_at_utc",
    "operator_identity",
    "primary_reviewer_identity",
    "secondary_reviewer_identity",
    "rollback_reviewer_identity",
    "incident_commander_identity",
    "provider_status",
    "provider_quota_verified",
    "sender_verification_status",
    "feature_gate_verified",
    "backend_policy_verified",
    "delivered_count",
    "skipped_count",
    "refused_count",
    "failed_count",
    "delivery_attempted_event_count",
    "delivery_succeeded_event_count",
    "delivery_failed_event_count",
    "sent_timestamp_event_count",
    "sent_timestamp_consistent",
    "duplicate_attempt_clean",
    "audit_gap_free",
    "provider_anomaly",
    "incident_reference",
    "final_decision",
    "reason_codes",
)

SUPERVISED_EXECUTION_IMMUTABLE_BINDINGS = (
    "change_record_id",
    "authorization_id",
    "authorization_command_fingerprint",
    "pilot_owner_id",
    "approved_limit",
    "preview_owner_id",
    "preview_limit",
    "preview_candidate_count",
    "operator_identity",
    "primary_reviewer_identity",
    "secondary_reviewer_identity",
    "issued_execution_window",
)

SUPERVISED_EXECUTION_PREFLIGHT_GATES = (
    "authorization lane is closed",
    "positive owner identifier is approved",
    "approved limit is between 1 and 3",
    "authorization state is authorized and unconsumed",
    "authorization is not expired or revoked",
    "authorization fingerprint matches production command",
    "authorization owner matches preview and command owner",
    "authorization limit matches preview and command limit",
    "strict readiness status is ready",
    "all nine readiness checks are present",
    "readiness evidence age is at most 300 seconds",
    "preview evidence age is at most 300 seconds",
    "pre-send freeze evidence age is at most 120 seconds",
    "feature gate remains enabled",
    "approved backend remains configured",
    "default sender remains configured",
    "sender identity or domain remains verified",
    "provider credentials remain available",
    "provider quota covers approved limit",
    "provider status remains operational",
    "owner notification opt-in remains enabled",
    "eligible due candidate count is positive",
    "preview candidate count is between 1 and approved limit",
    "preview skips are understood",
    "preview unexpected refusal count is zero",
    "no concurrent owner-scoped run exists",
    "no unresolved incident exists",
    "operator identity is recorded",
    "primary reviewer approval is current",
    "secondary reviewer approval is current",
    "primary and secondary reviewers are distinct",
    "rollback reviewer is present",
    "incident commander is present",
    "both production confirmation flags remain present",
    "post-run reconciliation owner is assigned",
)

SUPERVISED_EXECUTION_ABORT_REASONS = (
    "authorization_lane_not_closed",
    "invalid_owner_id",
    "invalid_pilot_limit",
    "authorization_not_authorized",
    "authorization_already_consumed",
    "authorization_expired",
    "authorization_revoked",
    "command_fingerprint_mismatch",
    "owner_binding_mismatch",
    "limit_binding_mismatch",
    "readiness_not_ready",
    "readiness_check_count_mismatch",
    "readiness_evidence_stale",
    "preview_evidence_stale",
    "pre_send_freeze_stale",
    "feature_gate_disabled",
    "email_backend_rejected",
    "default_sender_missing",
    "sender_unverified",
    "provider_credentials_unavailable",
    "provider_quota_insufficient",
    "provider_not_operational",
    "owner_opt_in_disabled",
    "no_eligible_due_candidate",
    "preview_candidate_count_invalid",
    "preview_skips_unresolved",
    "preview_unexpected_refusal",
    "concurrent_owner_run",
    "unresolved_incident",
    "operator_identity_missing",
    "primary_reviewer_missing",
    "secondary_reviewer_missing",
    "reviewer_identity_collision",
    "rollback_reviewer_missing",
    "incident_commander_missing",
    "production_confirmation_missing",
    "authorization_consumption_failed",
    "runtime_state_changed_after_freeze",
)

SUPERVISED_EXECUTION_POST_RUN_GATES = (
    "production invocation count equals one",
    "authorization consumption count equals one",
    "delivered skipped refused and failed counts reconcile",
    "failed count is zero",
    "unexpected refusal count is zero",
    "delivery-attempted event count reconciles",
    "delivery-succeeded event count reconciles",
    "delivery-failed event count reconciles",
    "sent-timestamp event count reconciles",
    "sent timestamps are consistent",
    "duplicate-attempt review is clean",
    "persistent audit has no gaps",
    "provider has no unexplained anomaly",
    "incident state is closed or explicitly escalated",
    "post-run review completes within 600 seconds",
    "automatic retry remains disabled",
    "automatic rollout promotion remains disabled",
)

SUPERVISED_EXECUTION_SUCCESS_AUDIT_SEQUENCE = (
    "delivery_attempted",
    "delivery_succeeded",
    "sent_timestamp_recorded",
)

SUPERVISED_EXECUTION_FAILURE_AUDIT_SEQUENCE = (
    "delivery_attempted",
    "delivery_failed",
)

SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST = (
    "change_record_id",
    "authorization_id",
    "pilot_owner_id",
    "approved_limit",
    "preview_candidate_count",
    "readiness_status",
    "readiness_ready_count",
    "readiness_not_ready_count",
    "readiness_warning_count",
    "readiness_checked_at_utc",
    "preview_checked_at_utc",
    "pre_send_freeze_at_utc",
    "authorization_consumed_at_utc",
    "production_started_at_utc",
    "production_finished_at_utc",
    "operator_identity",
    "primary_reviewer_identity",
    "secondary_reviewer_identity",
    "rollback_reviewer_identity",
    "incident_commander_identity",
    "provider_status",
    "provider_quota_verified",
    "sender_verification_status",
    "feature_gate_verified",
    "backend_policy_verified",
    "delivered_count",
    "skipped_count",
    "refused_count",
    "failed_count",
    "delivery_attempted_event_count",
    "delivery_succeeded_event_count",
    "delivery_failed_event_count",
    "sent_timestamp_event_count",
    "sent_timestamp_consistent",
    "duplicate_attempt_clean",
    "audit_gap_free",
    "provider_anomaly",
    "final_decision",
    "reason_codes",
    "incident_reference",
)

SUPERVISED_EXECUTION_PRIVACY_EXCLUSIONS = (
    "SMTP password",
    "confidential SMTP username",
    "API key",
    "access token",
    "recipient email address",
    "default sender value",
    "raw email-backend path",
    "saved-search name",
    "saved-search querystring",
    "rendered email subject",
    "rendered email body",
    "provider response body",
    "raw exception traceback",
)

SUPERVISED_EXECUTION_PREVIEW_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

SUPERVISED_EXECUTION_PRODUCTION_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--execute-production-send "
    "--confirm-production-delivery "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

SUPERVISED_EXECUTION_PROHIBITED_ACTIONS = (
    "production delivery during contract checkpoint",
    "execution without a positive owner identifier",
    "execution without an explicit pilot limit",
    "execution with limit below 1",
    "execution with limit above 3",
    "execution without fresh readiness",
    "execution without fresh matching preview",
    "execution without valid unconsumed authorization",
    "execution without matching command fingerprint",
    "execution after authorization expiration",
    "execution after authorization revocation",
    "authorization reuse",
    "owner change after pre-send freeze",
    "limit change after pre-send freeze",
    "provider change after pre-send freeze",
    "sender change after pre-send freeze",
    "execution without two distinct reviewer approvals",
    "execution without rollback reviewer",
    "execution without incident commander",
    "global all-owner execution",
    "multi-owner command execution",
    "readiness bypass",
    "preview bypass",
    "production confirmation bypass",
    "provider verification bypass",
    "blind retry",
    "automatic retry",
    "automatic authorization renewal",
    "automatic rollout promotion",
    "automatic scheduler enablement",
    "Celery enablement",
    "cron enablement",
    "startup-time delivery",
    "request-time delivery",
    "manual sent-timestamp edit",
    "manual audit-event deletion",
    "direct SQL repair",
    "Django shell timestamp repair",
    "credential logging",
    "recipient payload logging",
    "saved-search payload logging",
    "silent partial-failure handling",
)

V259_ACCEPTANCE_GATES = (
    "v258 authorization closeout remains packaged",
    "v259 scope is exactly two contract files",
    "v260 implementation scope is exactly two files",
    "v260 remains documentation and test only",
    "supervised limit band is exactly 1 through 3",
    "readiness maximum age is 300 seconds",
    "preview maximum age is 300 seconds",
    "authorization lifetime is 600 seconds",
    "pre-send freeze maximum age is 120 seconds",
    "post-run review deadline is 600 seconds",
    "all supervision roles are explicit",
    "supervised stage order is deterministic",
    "required evidence fields are explicit",
    "immutable bindings are explicit",
    "preflight gates are explicit",
    "abort reasons are explicit",
    "post-run gates are explicit",
    "success audit sequence is explicit",
    "failure audit sequence is explicit",
    "one owner remains mandatory",
    "limit between 1 and 3 remains mandatory",
    "fresh strict readiness remains mandatory",
    "fresh matching preview remains mandatory",
    "unconsumed authorization remains mandatory",
    "command fingerprint remains mandatory",
    "authorization consumption remains one-shot",
    "pre-send freeze is mandatory",
    "runtime-state mutation after freeze aborts execution",
    "two distinct reviewers remain mandatory",
    "rollback reviewer remains mandatory",
    "incident commander remains mandatory",
    "provider and sender evidence remain current",
    "concurrent owner run blocks execution",
    "open incident blocks execution",
    "both production confirmation flags remain mandatory",
    "post-run reconciliation remains mandatory",
    "automatic retry remains prohibited",
    "automatic promotion remains prohibited",
    "evidence allowlist is explicit",
    "privacy exclusions are explicit",
    "contract checkpoint performs no delivery",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v260: saved-search notification production delivery pilot supervised execution implementation"

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
        "pilot_execution_authorization_closeout_audit_v258.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionContractV259Tests(
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

    def test_v259_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT,
            (
                "V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V258_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V259_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V260_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v260: saved-search notification production "
                "delivery pilot supervised execution implementation"
            ),
        )

    def test_v259_v260_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V260_ALLOWED_SCOPE,
            (
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
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V260_ALLOWED_SCOPE
            )
        )

    def test_v259_limit_and_time_windows_are_exact(self):
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

    def test_v259_required_roles_are_exact(self):
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

    def test_v259_stage_order_is_exact(self):
        self.assertEqual(
            SUPERVISED_EXECUTION_STAGE_ORDER,
            (
                "open supervised change window",
                "verify immutable authorization bindings",
                "rerun strict readiness",
                "rerun matching preview",
                "freeze provider sender owner and limit state",
                "record final reviewer go decision",
                "consume authorization exactly once",
                "invoke one guarded production command",
                "capture persistent audit and timestamp evidence",
                "perform mandatory post-run reconciliation",
                "close or escalate the change window",
            ),
        )

    def test_v259_required_evidence_is_complete(self):
        required = {
            "change_record_id",
            "authorization_id",
            "authorization_state",
            "authorization_command_fingerprint",
            "pilot_owner_id",
            "approved_limit",
            "preview_owner_id",
            "preview_limit",
            "preview_candidate_count",
            "readiness_status",
            "readiness_ready_count",
            "readiness_not_ready_count",
            "readiness_warning_count",
            "readiness_checked_at_utc",
            "preview_checked_at_utc",
            "pre_send_freeze_at_utc",
            "authorization_consumed_at_utc",
            "production_started_at_utc",
            "production_finished_at_utc",
            "operator_identity",
            "primary_reviewer_identity",
            "secondary_reviewer_identity",
            "rollback_reviewer_identity",
            "incident_commander_identity",
            "provider_status",
            "provider_quota_verified",
            "sender_verification_status",
            "feature_gate_verified",
            "backend_policy_verified",
            "delivered_count",
            "skipped_count",
            "refused_count",
            "failed_count",
            "delivery_attempted_event_count",
            "delivery_succeeded_event_count",
            "delivery_failed_event_count",
            "sent_timestamp_event_count",
            "sent_timestamp_consistent",
            "duplicate_attempt_clean",
            "audit_gap_free",
            "provider_anomaly",
            "incident_reference",
            "final_decision",
            "reason_codes",
        }

        self.assertEqual(
            set(SUPERVISED_EXECUTION_REQUIRED_EVIDENCE),
            required,
        )

    def test_v259_immutable_bindings_are_complete(self):
        required = {
            "change_record_id",
            "authorization_id",
            "authorization_command_fingerprint",
            "pilot_owner_id",
            "approved_limit",
            "preview_owner_id",
            "preview_limit",
            "preview_candidate_count",
            "operator_identity",
            "primary_reviewer_identity",
            "secondary_reviewer_identity",
            "issued_execution_window",
        }

        self.assertEqual(
            set(SUPERVISED_EXECUTION_IMMUTABLE_BINDINGS),
            required,
        )

    def test_v259_preflight_gate_package_is_complete(self):
        self.assertEqual(
            len(SUPERVISED_EXECUTION_PREFLIGHT_GATES),
            35,
        )

        required = {
            "authorization lane is closed",
            "positive owner identifier is approved",
            "approved limit is between 1 and 3",
            "authorization state is authorized and unconsumed",
            "authorization fingerprint matches production command",
            "strict readiness status is ready",
            "all nine readiness checks are present",
            "pre-send freeze evidence age is at most 120 seconds",
            "provider quota covers approved limit",
            "no concurrent owner-scoped run exists",
            "no unresolved incident exists",
            "primary and secondary reviewers are distinct",
            "rollback reviewer is present",
            "incident commander is present",
            "both production confirmation flags remain present",
            "post-run reconciliation owner is assigned",
        }

        self.assertTrue(
            required.issubset(
                set(SUPERVISED_EXECUTION_PREFLIGHT_GATES)
            )
        )

    def test_v259_abort_reasons_are_explicit_and_ordered(self):
        self.assertEqual(
            len(SUPERVISED_EXECUTION_ABORT_REASONS),
            38,
        )

        self.assertEqual(
            SUPERVISED_EXECUTION_ABORT_REASONS[0],
            "authorization_lane_not_closed",
        )

        self.assertEqual(
            SUPERVISED_EXECUTION_ABORT_REASONS[-1],
            "runtime_state_changed_after_freeze",
        )

        self.assertEqual(
            len(set(SUPERVISED_EXECUTION_ABORT_REASONS)),
            len(SUPERVISED_EXECUTION_ABORT_REASONS),
        )

    def test_v259_post_run_gate_package_is_complete(self):
        self.assertEqual(
            len(SUPERVISED_EXECUTION_POST_RUN_GATES),
            17,
        )

        required = {
            "production invocation count equals one",
            "authorization consumption count equals one",
            "delivered skipped refused and failed counts reconcile",
            "failed count is zero",
            "unexpected refusal count is zero",
            "sent timestamps are consistent",
            "duplicate-attempt review is clean",
            "persistent audit has no gaps",
            "post-run review completes within 600 seconds",
            "automatic retry remains disabled",
            "automatic rollout promotion remains disabled",
        }

        self.assertTrue(
            required.issubset(
                set(SUPERVISED_EXECUTION_POST_RUN_GATES)
            )
        )

    def test_v259_audit_sequences_are_exact(self):
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

    def test_v259_evidence_allowlist_excludes_sensitive_payloads(self):
        self.assertTrue(
            set(SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST)
            .isdisjoint(
                {
                    "smtp_password",
                    "smtp_username",
                    "api_key",
                    "access_token",
                    "recipient_email",
                    "default_sender",
                    "email_backend",
                    "saved_search_name",
                    "saved_search_querystring",
                    "rendered_subject",
                    "rendered_body",
                    "provider_response_body",
                    "raw_exception_traceback",
                }
            )
        )

        self.assertIn(
            "authorization_id",
            SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
        )

        self.assertIn(
            "final_decision",
            SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
        )

    def test_v259_privacy_exclusions_are_complete(self):
        required = {
            "SMTP password",
            "confidential SMTP username",
            "API key",
            "access token",
            "recipient email address",
            "default sender value",
            "raw email-backend path",
            "saved-search name",
            "saved-search querystring",
            "rendered email subject",
            "rendered email body",
            "provider response body",
            "raw exception traceback",
        }

        self.assertEqual(
            set(SUPERVISED_EXECUTION_PRIVACY_EXCLUSIONS),
            required,
        )

    def test_v259_preview_command_is_nonproduction(self):
        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            SUPERVISED_EXECUTION_PREVIEW_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            SUPERVISED_EXECUTION_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--execute-production-send",
            SUPERVISED_EXECUTION_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--confirm-production-delivery",
            SUPERVISED_EXECUTION_PREVIEW_COMMAND,
        )

    def test_v259_production_command_retains_all_controls(self):
        self.assertIn(
            "--execute-production-send",
            SUPERVISED_EXECUTION_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--confirm-production-delivery",
            SUPERVISED_EXECUTION_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            SUPERVISED_EXECUTION_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            SUPERVISED_EXECUTION_PRODUCTION_COMMAND,
        )

    def test_v259_prohibited_actions_are_complete(self):
        required = {
            "production delivery during contract checkpoint",
            "execution without a positive owner identifier",
            "execution without fresh readiness",
            "execution without fresh matching preview",
            "execution without valid unconsumed authorization",
            "execution without matching command fingerprint",
            "authorization reuse",
            "owner change after pre-send freeze",
            "limit change after pre-send freeze",
            "provider change after pre-send freeze",
            "sender change after pre-send freeze",
            "execution without two distinct reviewer approvals",
            "execution without rollback reviewer",
            "execution without incident commander",
            "global all-owner execution",
            "multi-owner command execution",
            "blind retry",
            "automatic retry",
            "automatic authorization renewal",
            "automatic rollout promotion",
            "automatic scheduler enablement",
            "direct SQL repair",
            "Django shell timestamp repair",
            "silent partial-failure handling",
        }

        self.assertTrue(
            required.issubset(
                set(SUPERVISED_EXECUTION_PROHIBITED_ACTIONS)
            )
        )

    def test_v259_v258_preconditions_remain_included(self):
        self.assertEqual(
            len(SUPERVISED_EXECUTION_PRECONDITIONS),
            20,
        )

        self.assertIn(
            "authorization lane is closed",
            SUPERVISED_EXECUTION_PRECONDITIONS,
        )

        self.assertIn(
            "authorization consumption occurs at most once",
            SUPERVISED_EXECUTION_PRECONDITIONS,
        )

        self.assertIn(
            "post-run reconciliation is mandatory",
            SUPERVISED_EXECUTION_PRECONDITIONS,
        )

    def test_v259_default_readiness_remains_not_ready(self):
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
    def test_v259_production_like_readiness_remains_ready(self):
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
    def test_v259_readiness_execution_opens_no_email_connection(self):
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

    def test_v259_command_surfaces_remain_unchanged(self):
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

    def test_v259_production_batch_cap_remains_25(self):
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

    def test_v259_scheduler_remains_nonautomatic(self):
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

    def test_v259_v258_closeout_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_execution_authorization_closeout_audit_v258.py"
        )

        self.assertIn(
            (
                "V258_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            (
                "v259: saved-search notification production "
                "delivery pilot supervised execution contract"
            ),
            source,
        )

    def test_v259_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT
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

    def test_v259_no_migration_0017_exists(self):
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

    def test_v259_acceptance_gate_matrix_is_complete(self):
        required = {
            "v258 authorization closeout remains packaged",
            "v259 scope is exactly two contract files",
            "v260 implementation scope is exactly two files",
            "v260 remains documentation and test only",
            "supervised limit band is exactly 1 through 3",
            "readiness maximum age is 300 seconds",
            "preview maximum age is 300 seconds",
            "authorization lifetime is 600 seconds",
            "pre-send freeze maximum age is 120 seconds",
            "post-run review deadline is 600 seconds",
            "all supervision roles are explicit",
            "supervised stage order is deterministic",
            "preflight gates are explicit",
            "abort reasons are explicit",
            "post-run gates are explicit",
            "one owner remains mandatory",
            "unconsumed authorization remains mandatory",
            "authorization consumption remains one-shot",
            "pre-send freeze is mandatory",
            "runtime-state mutation after freeze aborts execution",
            "two distinct reviewers remain mandatory",
            "rollback reviewer remains mandatory",
            "incident commander remains mandatory",
            "post-run reconciliation remains mandatory",
            "automatic retry remains prohibited",
            "automatic promotion remains prohibited",
            "contract checkpoint performs no delivery",
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
                set(V259_ACCEPTANCE_GATES)
            )
        )
