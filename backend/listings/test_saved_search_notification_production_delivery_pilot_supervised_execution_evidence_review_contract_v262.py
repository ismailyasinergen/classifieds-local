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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_closeout_audit_v261 import (
    EVIDENCE_REVIEW_PRECONDITIONS,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_contract_v259 import (
    SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
    SUPERVISED_EXECUTION_PRIVACY_EXCLUSIONS,
    SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_v260 import (
    SUPERVISED_SENSITIVE_FIELDS,
)


V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CONTRACT = (
    "V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CONTRACT"
)

V261_COMMITTED_SCOPE = (
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

V262_ALLOWED_SCOPE = (
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

V263_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_evidence_review_v263.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_evidence_review_v263.md"
    ),
)

EVIDENCE_REVIEW_REQUIRED_FIELDS = (
    "change_record_id",
    "authorization_id",
    "pilot_owner_id",
    "approved_limit",
    "authorization_command_fingerprint",
    "freeze_fingerprint",
    "authorization_consumption_count",
    "production_invocation_count",
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
    "incident_state",
    "privacy_sanitizer_applied",
    "automatic_retry_enabled",
    "automatic_rollout_promotion_enabled",
    "reviewer_identity",
    "review_completed_at_utc",
    "final_decision",
    "reason_codes",
)

EVIDENCE_REVIEW_IMMUTABLE_BINDINGS = (
    "change_record_id",
    "authorization_id",
    "pilot_owner_id",
    "approved_limit",
    "authorization_command_fingerprint",
    "freeze_fingerprint",
)

EVIDENCE_REVIEW_DECISIONS = (
    "privacy_rejected",
    "incident_escalated",
    "incomplete",
    "inconsistent",
    "complete_consistent",
    "not_eligible_for_rollout_consideration",
)

EVIDENCE_REVIEW_DECISION_PRECEDENCE = (
    "privacy_rejected",
    "incident_escalated",
    "incomplete",
    "inconsistent",
    "not_eligible_for_rollout_consideration",
    "complete_consistent",
)

EVIDENCE_REVIEW_ROLLOUT_RECOMMENDATIONS = (
    "not_eligible",
    "eligible_for_manual_consideration",
)

EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES = (
    "missing_change_record_id",
    "missing_authorization_id",
    "missing_owner_id",
    "missing_approved_limit",
    "missing_authorization_command_fingerprint",
    "missing_freeze_fingerprint",
    "missing_authorization_consumption_count",
    "missing_production_invocation_count",
    "missing_delivery_outcome_counts",
    "missing_persistent_audit_counts",
    "missing_sent_timestamp_consistency",
    "missing_duplicate_attempt_status",
    "missing_provider_anomaly_status",
    "missing_incident_state",
    "missing_reviewer_identity",
    "missing_review_timestamp",
)

EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES = (
    "invalid_owner_id",
    "invalid_approved_limit",
    "authorization_consumption_count_mismatch",
    "production_invocation_count_mismatch",
    "delivery_counts_mismatch",
    "delivery_attempted_event_mismatch",
    "delivery_succeeded_event_mismatch",
    "delivery_failed_event_mismatch",
    "sent_timestamp_event_mismatch",
    "sent_timestamp_inconsistent",
    "duplicate_attempt_detected",
    "audit_gap_detected",
)

EVIDENCE_REVIEW_PRIVACY_REASON_CODES = (
    "privacy_sanitizer_not_applied",
    "sensitive_evidence_detected",
)

EVIDENCE_REVIEW_INCIDENT_REASON_CODES = (
    "provider_anomaly_detected",
    "incident_open",
    "incident_state_invalid",
    "failed_delivery_present",
    "unexpected_refusal_present",
)

EVIDENCE_REVIEW_POLICY_REASON_CODES = (
    "automatic_retry_enabled",
    "automatic_rollout_promotion_enabled",
    "production_delivery_attempted_during_review",
)

EVIDENCE_REVIEW_REASON_ORDER = (
    "missing_change_record_id",
    "missing_authorization_id",
    "missing_owner_id",
    "missing_approved_limit",
    "missing_authorization_command_fingerprint",
    "missing_freeze_fingerprint",
    "missing_authorization_consumption_count",
    "missing_production_invocation_count",
    "missing_delivery_outcome_counts",
    "missing_persistent_audit_counts",
    "missing_sent_timestamp_consistency",
    "missing_duplicate_attempt_status",
    "missing_provider_anomaly_status",
    "missing_incident_state",
    "missing_reviewer_identity",
    "missing_review_timestamp",
    "invalid_owner_id",
    "invalid_approved_limit",
    "authorization_consumption_count_mismatch",
    "production_invocation_count_mismatch",
    "delivery_counts_mismatch",
    "delivery_attempted_event_mismatch",
    "delivery_succeeded_event_mismatch",
    "delivery_failed_event_mismatch",
    "sent_timestamp_event_mismatch",
    "sent_timestamp_inconsistent",
    "duplicate_attempt_detected",
    "audit_gap_detected",
    "privacy_sanitizer_not_applied",
    "sensitive_evidence_detected",
    "provider_anomaly_detected",
    "incident_open",
    "incident_state_invalid",
    "failed_delivery_present",
    "unexpected_refusal_present",
    "automatic_retry_enabled",
    "automatic_rollout_promotion_enabled",
    "production_delivery_attempted_during_review",
)

EVIDENCE_REVIEW_RECONCILIATION_RULES = (
    "authorization consumption count equals one",
    "production invocation count equals one",
    "delivery outcome counts reconcile to reviewed candidate count",
    "failed count equals zero for complete-consistent classification",
    "unexpected refusal count equals zero",
    "delivery-attempted events equal delivered plus failed",
    "delivery-succeeded events equal delivered count",
    "delivery-failed events equal failed count",
    "sent-timestamp events equal delivered count",
    "sent timestamps are internally consistent",
    "duplicate-attempt review is clean",
    "persistent audit has no gaps",
    "provider anomaly is absent",
    "incident state is closed or explicitly escalated",
    "automatic retry remains disabled",
    "automatic rollout promotion remains disabled",
)

EVIDENCE_REVIEW_REQUIRED_REVIEW_ROLES = (
    "evidence_reviewer",
    "privacy_reviewer",
    "incident_reviewer",
)

EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST = (
    "change_record_id",
    "authorization_id",
    "pilot_owner_id",
    "approved_limit",
    "authorization_command_fingerprint",
    "freeze_fingerprint",
    "authorization_consumption_count",
    "production_invocation_count",
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
    "incident_state",
    "privacy_sanitizer_applied",
    "automatic_retry_enabled",
    "automatic_rollout_promotion_enabled",
    "reviewer_identity",
    "privacy_reviewer_identity",
    "incident_reviewer_identity",
    "review_completed_at_utc",
    "final_decision",
    "rollout_recommendation",
    "reason_codes",
    "incident_reference",
)

EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS = (
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

EVIDENCE_REVIEW_PROHIBITED_ACTIONS = (
    "production delivery during evidence-review checkpoint",
    "authorization consumption during evidence review",
    "delivery retry during evidence review",
    "automatic rollout promotion",
    "automatic retry",
    "global all-owner execution",
    "multi-owner execution",
    "manual sent-timestamp edit",
    "manual audit-event deletion",
    "direct SQL repair",
    "Django shell timestamp repair",
    "credential logging",
    "recipient payload logging",
    "saved-search payload logging",
    "rendered email payload logging",
    "provider response-body logging",
    "privacy sanitizer bypass",
    "classification without required evidence",
    "rollout recommendation without manual reviewer decision",
    "silent inconsistency acceptance",
)

V262_ACCEPTANCE_GATES = (
    "v261 supervised-execution closeout remains packaged",
    "v261 committed scope remains exactly two files",
    "v262 scope is exactly two contract files",
    "v263 evidence-review implementation scope is exactly two files",
    "v263 remains documentation and test only",
    "evidence review remains documentation and test only",
    "evidence-review preconditions remain exactly twenty",
    "required evidence fields are explicit",
    "immutable evidence bindings are explicit",
    "decision values are explicit",
    "decision precedence is deterministic",
    "rollout recommendations are explicit",
    "complete-consistent does not automatically promote rollout",
    "completeness reason codes are explicit",
    "consistency reason codes are explicit",
    "privacy reason codes are explicit",
    "incident reason codes are explicit",
    "policy reason codes are explicit",
    "global reason order is deterministic",
    "all reason codes are unique",
    "authorization consumption count must be known",
    "production invocation count must be known",
    "delivery counts must be known",
    "persistent audit counts must be known",
    "sent-timestamp consistency must be known",
    "duplicate-attempt status must be known",
    "provider anomaly status must be known",
    "incident state must be known",
    "positive owner identifier remains mandatory",
    "approved limit remains between 1 and 3",
    "authorization command fingerprint remains mandatory",
    "freeze fingerprint remains mandatory",
    "authorization consumption count must equal one",
    "production invocation count must equal one",
    "delivery outcome counts must reconcile",
    "persistent audit counts must reconcile",
    "sent timestamps must remain consistent",
    "duplicate-attempt review must remain clean",
    "audit-gap review must remain clean",
    "provider anomaly requires escalation",
    "open incident requires escalation",
    "failed delivery prevents complete-consistent classification",
    "unexpected refusal prevents complete-consistent classification",
    "privacy sanitizer remains mandatory",
    "sensitive evidence triggers privacy rejection",
    "automatic retry remains prohibited",
    "automatic rollout promotion remains prohibited",
    "evidence review performs no production delivery",
    "evidence review consumes no authorization",
    "evidence review performs no retry",
    "evidence allowlist is explicit",
    "privacy exclusions are explicit",
    "unknown fields must be discarded",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v263: saved-search notification production delivery pilot supervised execution evidence review implementation"

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
        "pilot_supervised_execution_closeout_audit_v261.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionEvidenceReviewContractV262Tests(
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

    def test_v262_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CONTRACT,
            (
                "V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "EVIDENCE_REVIEW_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V261_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V262_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V263_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v263: saved-search notification production delivery "
                "pilot supervised execution evidence review implementation"
            ),
        )

    def test_v262_and_v263_scopes_are_documentation_and_test_only(self):
        for scope in (
            V262_ALLOWED_SCOPE,
            V263_ALLOWED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v262_v261_preconditions_remain_exact(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_PRECONDITIONS),
            20,
        )

        self.assertIn(
            "supervised-execution lane is closed",
            EVIDENCE_REVIEW_PRECONDITIONS,
        )

        self.assertIn(
            "review does not perform production delivery",
            EVIDENCE_REVIEW_PRECONDITIONS,
        )

    def test_v262_required_fields_are_exact_and_unique(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_REQUIRED_FIELDS),
            28,
        )

        self.assertEqual(
            len(set(EVIDENCE_REVIEW_REQUIRED_FIELDS)),
            len(EVIDENCE_REVIEW_REQUIRED_FIELDS),
        )

        self.assertIn(
            "authorization_consumption_count",
            EVIDENCE_REVIEW_REQUIRED_FIELDS,
        )

        self.assertIn(
            "production_invocation_count",
            EVIDENCE_REVIEW_REQUIRED_FIELDS,
        )

        self.assertIn(
            "final_decision",
            EVIDENCE_REVIEW_REQUIRED_FIELDS,
        )

    def test_v262_immutable_bindings_are_exact(self):
        self.assertEqual(
            EVIDENCE_REVIEW_IMMUTABLE_BINDINGS,
            (
                "change_record_id",
                "authorization_id",
                "pilot_owner_id",
                "approved_limit",
                "authorization_command_fingerprint",
                "freeze_fingerprint",
            ),
        )

    def test_v262_decisions_and_precedence_are_deterministic(self):
        self.assertEqual(
            set(EVIDENCE_REVIEW_DECISIONS),
            set(EVIDENCE_REVIEW_DECISION_PRECEDENCE),
        )

        self.assertEqual(
            EVIDENCE_REVIEW_DECISION_PRECEDENCE[0],
            "privacy_rejected",
        )

        self.assertEqual(
            EVIDENCE_REVIEW_DECISION_PRECEDENCE[-1],
            "complete_consistent",
        )

        self.assertEqual(
            EVIDENCE_REVIEW_ROLLOUT_RECOMMENDATIONS,
            (
                "not_eligible",
                "eligible_for_manual_consideration",
            ),
        )

    def test_v262_completeness_reasons_are_exact_and_unique(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES),
            16,
        )

        self.assertEqual(
            len(set(EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES)),
            16,
        )

        self.assertIn(
            "missing_delivery_outcome_counts",
            EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES,
        )

        self.assertIn(
            "missing_persistent_audit_counts",
            EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES,
        )

    def test_v262_consistency_reasons_are_exact_and_unique(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES),
            12,
        )

        self.assertEqual(
            len(set(EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES)),
            12,
        )

        self.assertIn(
            "authorization_consumption_count_mismatch",
            EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES,
        )

        self.assertIn(
            "production_invocation_count_mismatch",
            EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES,
        )

    def test_v262_privacy_incident_and_policy_reasons_are_exact(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_PRIVACY_REASON_CODES),
            2,
        )

        self.assertEqual(
            len(EVIDENCE_REVIEW_INCIDENT_REASON_CODES),
            5,
        )

        self.assertEqual(
            len(EVIDENCE_REVIEW_POLICY_REASON_CODES),
            3,
        )

        self.assertIn(
            "sensitive_evidence_detected",
            EVIDENCE_REVIEW_PRIVACY_REASON_CODES,
        )

        self.assertIn(
            "provider_anomaly_detected",
            EVIDENCE_REVIEW_INCIDENT_REASON_CODES,
        )

        self.assertIn(
            "automatic_rollout_promotion_enabled",
            EVIDENCE_REVIEW_POLICY_REASON_CODES,
        )

    def test_v262_global_reason_order_is_exact_and_unique(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_REASON_ORDER),
            38,
        )

        self.assertEqual(
            len(set(EVIDENCE_REVIEW_REASON_ORDER)),
            38,
        )

        expected = (
            set(EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES)
            | set(EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES)
            | set(EVIDENCE_REVIEW_PRIVACY_REASON_CODES)
            | set(EVIDENCE_REVIEW_INCIDENT_REASON_CODES)
            | set(EVIDENCE_REVIEW_POLICY_REASON_CODES)
        )

        self.assertEqual(
            set(EVIDENCE_REVIEW_REASON_ORDER),
            expected,
        )

    def test_v262_reconciliation_rules_are_complete(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_RECONCILIATION_RULES),
            16,
        )

        required = {
            "authorization consumption count equals one",
            "production invocation count equals one",
            "delivery outcome counts reconcile to reviewed candidate count",
            "delivery-attempted events equal delivered plus failed",
            "delivery-succeeded events equal delivered count",
            "delivery-failed events equal failed count",
            "sent-timestamp events equal delivered count",
            "sent timestamps are internally consistent",
            "duplicate-attempt review is clean",
            "persistent audit has no gaps",
            "provider anomaly is absent",
            "automatic retry remains disabled",
            "automatic rollout promotion remains disabled",
        }

        self.assertTrue(
            required.issubset(
                set(EVIDENCE_REVIEW_RECONCILIATION_RULES)
            )
        )

    def test_v262_required_review_roles_are_exact(self):
        self.assertEqual(
            EVIDENCE_REVIEW_REQUIRED_REVIEW_ROLES,
            (
                "evidence_reviewer",
                "privacy_reviewer",
                "incident_reviewer",
            ),
        )

    def test_v262_evidence_allowlist_is_explicit_and_unique(self):
        self.assertEqual(
            len(set(EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST)),
            len(EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST),
        )

        self.assertIn(
            "rollout_recommendation",
            EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST,
        )

        self.assertIn(
            "reason_codes",
            EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST,
        )

        self.assertIn(
            "incident_reference",
            EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST,
        )

    def test_v262_allowlist_excludes_sensitive_fields(self):
        self.assertTrue(
            set(EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST)
            .isdisjoint(
                SUPERVISED_SENSITIVE_FIELDS
            )
        )

        self.assertTrue(
            set(EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST)
            .isdisjoint(
                {
                    "smtp_password",
                    "smtp_username",
                    "api_key",
                    "access_token",
                    "recipient_email",
                    "rendered_subject",
                    "rendered_body",
                    "provider_response_body",
                }
            )
        )

    def test_v262_privacy_exclusions_match_supervised_boundary(self):
        self.assertEqual(
            set(EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS),
            set(SUPERVISED_EXECUTION_PRIVACY_EXCLUSIONS),
        )

        self.assertIn(
            "SMTP password",
            EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "raw exception traceback",
            EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS,
        )

    def test_v262_prohibited_actions_are_complete(self):
        required = {
            "production delivery during evidence-review checkpoint",
            "authorization consumption during evidence review",
            "delivery retry during evidence review",
            "automatic rollout promotion",
            "automatic retry",
            "global all-owner execution",
            "multi-owner execution",
            "manual sent-timestamp edit",
            "manual audit-event deletion",
            "direct SQL repair",
            "Django shell timestamp repair",
            "privacy sanitizer bypass",
            "classification without required evidence",
            "rollout recommendation without manual reviewer decision",
            "silent inconsistency acceptance",
        }

        self.assertTrue(
            required.issubset(
                set(EVIDENCE_REVIEW_PROHIBITED_ACTIONS)
            )
        )

    def test_v262_supervised_prohibitions_remain_packaged(self):
        self.assertIn(
            "automatic retry",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "automatic rollout promotion",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "direct SQL repair",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "Django shell timestamp repair",
            SUPERVISED_EXECUTION_PROHIBITED_ACTIONS,
        )

    def test_v262_existing_supervised_allowlist_remains_packaged(self):
        self.assertIn(
            "change_record_id",
            SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
        )

        self.assertIn(
            "authorization_id",
            SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
        )

        self.assertIn(
            "final_decision",
            SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST,
        )

    def test_v262_default_readiness_remains_not_ready(self):
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
    def test_v262_production_like_readiness_remains_ready(self):
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
    def test_v262_readiness_execution_opens_no_email_connection(self):
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

    def test_v262_command_surfaces_remain_unchanged(self):
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

    def test_v262_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v262_scheduler_remains_nonautomatic(self):
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

    def test_v262_v261_closeout_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_closeout_audit_v261.py"
        )

        self.assertIn(
            (
                "V261_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            (
                "v262: saved-search notification production delivery "
                "pilot supervised execution evidence review contract"
            ),
            source,
        )

    def test_v262_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CONTRACT
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

    def test_v262_no_migration_0017_exists(self):
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

    def test_v262_acceptance_gate_matrix_is_complete(self):
        required = {
            "v261 supervised-execution closeout remains packaged",
            "v262 scope is exactly two contract files",
            "v263 evidence-review implementation scope is exactly two files",
            "evidence review remains documentation and test only",
            "decision precedence is deterministic",
            "all reason codes are unique",
            "authorization consumption count must equal one",
            "production invocation count must equal one",
            "delivery outcome counts must reconcile",
            "persistent audit counts must reconcile",
            "sent timestamps must remain consistent",
            "duplicate-attempt review must remain clean",
            "provider anomaly requires escalation",
            "open incident requires escalation",
            "privacy sanitizer remains mandatory",
            "sensitive evidence triggers privacy rejection",
            "automatic retry remains prohibited",
            "automatic rollout promotion remains prohibited",
            "evidence review performs no production delivery",
            "evidence review consumes no authorization",
            "evidence review performs no retry",
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
                set(V262_ACCEPTANCE_GATES)
            )
        )
