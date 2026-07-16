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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_contract_v262 import (
    EVIDENCE_REVIEW_DECISIONS,
    EVIDENCE_REVIEW_REASON_ORDER,
    EVIDENCE_REVIEW_ROLLOUT_RECOMMENDATIONS,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_v263 import (
    build_complete_evidence_review_record,
    evaluate_evidence_review,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_closeout_audit_v264 import (
    MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS,
    V264_CLOSEOUT_GATES,
)


V265_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CONTRACT = (
    "V265_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CONTRACT"
)

V264_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_evidence_review_closeout_audit_v264.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_evidence_review_closeout_audit_v264.md"
    ),
)

V265_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_contract_v265.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_contract_v265.md"
    ),
)

V266_PROPOSED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_v266.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_v266.md"
    ),
)

MANUAL_ROLLOUT_REQUIRED_FIELDS = (
    "consideration_id",
    "source_change_record_id",
    "source_authorization_id",
    "source_owner_id",
    "source_approved_limit",
    "source_authorization_command_fingerprint",
    "source_freeze_fingerprint",
    "source_evidence_decision",
    "source_rollout_recommendation",
    "source_reason_codes",
    "source_complete",
    "source_consistent",
    "source_privacy_safe",
    "source_incident_clear",
    "source_policy_compliant",
    "source_authorization_consumption_count",
    "source_production_invocation_count",
    "source_delivered_count",
    "source_skipped_count",
    "source_refused_count",
    "source_failed_count",
    "source_audit_gap_free",
    "source_duplicate_attempt_clean",
    "source_provider_anomaly",
    "source_incident_state",
    "source_privacy_sanitizer_applied",
    "source_automatic_retry_enabled",
    "source_automatic_rollout_promotion_enabled",
    "decision_owner_identity",
    "evidence_reviewer_identity",
    "privacy_reviewer_identity",
    "incident_reviewer_identity",
    "rollback_reviewer_identity",
    "incident_commander_identity",
    "considered_owner_ids",
    "considered_limit",
    "readiness_evidence_fingerprint",
    "preview_evidence_fingerprint",
    "consideration_completed_at_utc",
    "final_decision",
    "reason_codes",
    "future_authorization_required",
    "production_delivery_performed",
    "authorization_consumed",
    "retry_performed",
    "scheduler_enabled",
    "automatic_promotion_performed",
)

MANUAL_ROLLOUT_IMMUTABLE_BINDINGS = (
    "consideration_id",
    "source_change_record_id",
    "source_authorization_id",
    "source_owner_id",
    "source_approved_limit",
    "source_authorization_command_fingerprint",
    "source_freeze_fingerprint",
    "readiness_evidence_fingerprint",
    "preview_evidence_fingerprint",
)

MANUAL_ROLLOUT_DECISIONS = (
    "not_eligible",
    "eligible_to_prepare_future_authorization",
)

MANUAL_ROLLOUT_DECISION_PRECEDENCE = (
    "not_eligible",
    "eligible_to_prepare_future_authorization",
)

MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES = (
    "missing_consideration_id",
    "missing_source_change_record_id",
    "missing_source_authorization_id",
    "missing_source_owner_id",
    "missing_source_approved_limit",
    "missing_source_authorization_command_fingerprint",
    "missing_source_freeze_fingerprint",
    "missing_decision_owner_identity",
    "missing_required_reviewer_identity",
    "missing_considered_owner_ids",
    "missing_considered_limit",
    "missing_readiness_evidence_fingerprint",
    "missing_preview_evidence_fingerprint",
    "missing_consideration_timestamp",
)

MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES = (
    "source_decision_not_complete_consistent",
    "source_rollout_recommendation_not_manual_consideration",
    "source_reason_codes_nonempty",
    "source_not_complete",
    "source_not_consistent",
    "source_not_privacy_safe",
    "source_incident_not_clear",
    "source_not_policy_compliant",
    "source_authorization_consumption_count_mismatch",
    "source_production_invocation_count_mismatch",
    "source_delivery_counts_not_reconciled",
    "source_audit_not_gap_free",
    "source_duplicate_attempt_not_clean",
    "source_provider_anomaly_present",
    "source_incident_state_not_closed",
    "source_privacy_sanitizer_not_applied",
    "source_automatic_retry_enabled",
    "source_automatic_rollout_promotion_enabled",
)

MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES = (
    "invalid_source_owner_id",
    "invalid_source_approved_limit",
    "considered_owner_scope_empty",
    "considered_owner_scope_expanded",
    "considered_limit_invalid",
    "considered_limit_expanded",
    "decision_owner_role_overlap",
    "required_reviewer_identity_not_distinct",
    "readiness_evidence_stale_or_changed",
    "preview_evidence_stale_or_changed",
    "future_authorization_not_required",
)

MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES = (
    "production_delivery_performed_during_consideration",
    "authorization_consumed_during_consideration",
    "retry_performed_during_consideration",
    "scheduler_enabled_during_consideration",
    "automatic_promotion_performed_during_consideration",
)

MANUAL_ROLLOUT_REASON_ORDER = (
    "missing_consideration_id",
    "missing_source_change_record_id",
    "missing_source_authorization_id",
    "missing_source_owner_id",
    "missing_source_approved_limit",
    "missing_source_authorization_command_fingerprint",
    "missing_source_freeze_fingerprint",
    "missing_decision_owner_identity",
    "missing_required_reviewer_identity",
    "missing_considered_owner_ids",
    "missing_considered_limit",
    "missing_readiness_evidence_fingerprint",
    "missing_preview_evidence_fingerprint",
    "missing_consideration_timestamp",
    "source_decision_not_complete_consistent",
    "source_rollout_recommendation_not_manual_consideration",
    "source_reason_codes_nonempty",
    "source_not_complete",
    "source_not_consistent",
    "source_not_privacy_safe",
    "source_incident_not_clear",
    "source_not_policy_compliant",
    "source_authorization_consumption_count_mismatch",
    "source_production_invocation_count_mismatch",
    "source_delivery_counts_not_reconciled",
    "source_audit_not_gap_free",
    "source_duplicate_attempt_not_clean",
    "source_provider_anomaly_present",
    "source_incident_state_not_closed",
    "source_privacy_sanitizer_not_applied",
    "source_automatic_retry_enabled",
    "source_automatic_rollout_promotion_enabled",
    "invalid_source_owner_id",
    "invalid_source_approved_limit",
    "considered_owner_scope_empty",
    "considered_owner_scope_expanded",
    "considered_limit_invalid",
    "considered_limit_expanded",
    "decision_owner_role_overlap",
    "required_reviewer_identity_not_distinct",
    "readiness_evidence_stale_or_changed",
    "preview_evidence_stale_or_changed",
    "future_authorization_not_required",
    "production_delivery_performed_during_consideration",
    "authorization_consumed_during_consideration",
    "retry_performed_during_consideration",
    "scheduler_enabled_during_consideration",
    "automatic_promotion_performed_during_consideration",
)

MANUAL_ROLLOUT_REQUIRED_ROLES = (
    "decision_owner",
    "evidence_reviewer",
    "privacy_reviewer",
    "incident_reviewer",
    "rollback_reviewer",
    "incident_commander",
)

MANUAL_ROLLOUT_ROLE_SEPARATION_RULES = (
    "decision owner differs from evidence reviewer",
    "decision owner differs from privacy reviewer",
    "decision owner differs from incident reviewer",
    "decision owner differs from rollback reviewer",
    "decision owner differs from incident commander",
    "evidence privacy incident and rollback reviewers are pairwise distinct",
)

MANUAL_ROLLOUT_MAX_OWNER_COUNT = 1
MANUAL_ROLLOUT_MAX_LIMIT = 3
MANUAL_ROLLOUT_READINESS_FRESHNESS_SECONDS = 300
MANUAL_ROLLOUT_PREVIEW_FRESHNESS_SECONDS = 300
MANUAL_ROLLOUT_CONSIDERATION_LIFETIME_SECONDS = 900

MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS = (
    "new authorization identifier",
    "one explicit positive owner identifier",
    "explicit limit between one and three",
    "current readiness evidence",
    "current preview evidence",
    "current provider sender and backend state",
    "current authorization command fingerprint",
    "current pre-send freeze fingerprint",
    "current operator and reviewer identities",
    "both production confirmations",
    "explicit authorization expiration",
    "one-shot authorization consumption",
    "automatic retry and automatic promotion remain disabled",
)

MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST = MANUAL_ROLLOUT_REQUIRED_FIELDS

MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS = (
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

MANUAL_ROLLOUT_SENSITIVE_INPUT_KEYS = (
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
)

MANUAL_ROLLOUT_PROHIBITED_ACTIONS = (
    "production delivery during consideration",
    "authorization consumption during consideration",
    "delivery retry during consideration",
    "scheduler enablement",
    "automatic rollout promotion",
    "production feature-gate mutation",
    "owner-scope expansion",
    "limit expansion",
    "source authorization reuse",
    "evidence review reused as execution authorization",
    "global all-owner execution",
    "multi-owner execution",
    "blind retry",
    "manual sent-timestamp edit",
    "manual audit-event deletion",
    "direct SQL repair",
    "Django shell timestamp repair",
    "credential logging",
    "recipient-payload logging",
    "saved-search-payload logging",
    "rendered email-payload logging",
    "provider response-body logging",
    "privacy sanitizer bypass",
    "computed decision spoofing",
    "silent inconsistency acceptance",
)

V265_ACCEPTANCE_GATES = (
    "v264 evidence-review closeout remains packaged",
    "v264 committed scope remains exactly two files",
    "v265 scope remains exactly two contract files",
    "v266 proposed scope remains exactly two files",
    "v266 remains documentation and test only",
    "manual consideration remains documentation and test only",
    "v264 manual-rollout preconditions remain exactly thirty-nine",
    "required fields remain exactly forty-seven",
    "required fields remain unique",
    "immutable bindings remain exact",
    "two final decisions remain exact",
    "not-eligible decision has precedence",
    "eligible decision only permits future authorization preparation",
    "forty-eight reason codes remain explicit",
    "forty-eight reason codes remain unique",
    "reason-code order remains deterministic",
    "completeness reasons remain explicit",
    "source eligibility reasons remain explicit",
    "scope and role reasons remain explicit",
    "prohibited-action reasons remain explicit",
    "source evidence decision must be complete-consistent",
    "source rollout recommendation must permit manual consideration",
    "source reason-code collection must be empty",
    "source complete flag must be true",
    "source consistent flag must be true",
    "source privacy-safe flag must be true",
    "source incident-clear flag must be true",
    "source policy-compliant flag must be true",
    "source authorization consumption count must equal one",
    "source production invocation count must equal one",
    "source delivery counts must reconcile",
    "source audit must be gap-free",
    "source duplicate-attempt review must be clean",
    "source provider anomaly must be absent",
    "source incident state must be closed",
    "source privacy sanitizer must be applied",
    "source automatic retry must remain disabled",
    "source automatic rollout promotion must remain disabled",
    "source owner identifier must be positive",
    "source approved limit must remain between one and three",
    "considered owner scope must contain exactly one owner",
    "considered owner scope cannot expand source owner scope",
    "considered limit must remain between one and three",
    "considered limit cannot exceed source approved limit",
    "decision owner remains mandatory",
    "six required roles remain explicit",
    "decision owner remains separated from reviewers",
    "required reviewers remain separated",
    "readiness evidence fingerprint remains mandatory",
    "preview evidence fingerprint remains mandatory",
    "readiness evidence freshness remains five minutes",
    "preview evidence freshness remains five minutes",
    "consideration lifetime remains fifteen minutes",
    "future authorization remains mandatory",
    "future authorization must have a new identifier",
    "future authorization remains owner scoped",
    "future authorization remains limit bounded",
    "future authorization requires current readiness evidence",
    "future authorization requires current preview evidence",
    "future authorization requires current provider and sender state",
    "future authorization requires current command fingerprint",
    "future authorization requires current freeze fingerprint",
    "future authorization requires both confirmations",
    "future authorization remains one shot",
    "manual consideration performs no production delivery",
    "manual consideration consumes no authorization",
    "manual consideration performs no retry",
    "manual consideration enables no scheduler",
    "manual consideration performs no automatic promotion",
    "manual consideration mutates no feature gate",
    "source authorization cannot be reused",
    "evidence review cannot be reused as authorization",
    "strict evidence allowlist remains explicit",
    "unknown evidence fields must be discarded",
    "privacy exclusions remain explicit",
    "sensitive fields remain prohibited",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service remains unchanged",
    "readiness command remains unchanged",
    "scheduler remains nonautomatic",
    "matcher and renderer remain unchanged",
    "audit runtime and persistence remain unchanged",
    "models admin URLs templates and UI remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "historical safety tests remain green",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v266: saved-search notification production delivery pilot supervised execution manual rollout consideration implementation"

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
        "pilot_supervised_execution_evidence_review_closeout_audit_v264.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionManualRolloutConsiderationContractV265Tests(
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

    def test_v265_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V265_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CONTRACT,
            (
                "V265_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_CONSIDERATION_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V264_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V265_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V266_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v266: saved-search notification production delivery "
                "pilot supervised execution manual rollout consideration "
                "implementation"
            ),
        )

    def test_v265_and_v266_scopes_are_documentation_and_test_only(self):
        for scope in (
            V265_ALLOWED_SCOPE,
            V266_PROPOSED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v265_v264_preconditions_remain_exact(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS
            ),
            39,
        )

        self.assertIn(
            "evidence-review lane is closed",
            MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS,
        )

        self.assertIn(
            "a separate future authorization is required",
            MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS,
        )

        self.assertIn(
            "consideration performs no production delivery",
            MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS,
        )

    def test_v265_required_fields_are_exact_and_unique(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_REQUIRED_FIELDS),
            47,
        )

        self.assertEqual(
            len(set(MANUAL_ROLLOUT_REQUIRED_FIELDS)),
            47,
        )

        required = {
            "consideration_id",
            "source_evidence_decision",
            "source_rollout_recommendation",
            "decision_owner_identity",
            "considered_owner_ids",
            "considered_limit",
            "future_authorization_required",
            "production_delivery_performed",
            "authorization_consumed",
            "retry_performed",
            "scheduler_enabled",
            "automatic_promotion_performed",
        }

        self.assertTrue(
            required.issubset(
                set(MANUAL_ROLLOUT_REQUIRED_FIELDS)
            )
        )

    def test_v265_immutable_bindings_are_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_IMMUTABLE_BINDINGS,
            (
                "consideration_id",
                "source_change_record_id",
                "source_authorization_id",
                "source_owner_id",
                "source_approved_limit",
                "source_authorization_command_fingerprint",
                "source_freeze_fingerprint",
                "readiness_evidence_fingerprint",
                "preview_evidence_fingerprint",
            ),
        )

    def test_v265_decisions_are_exact_and_fail_closed(self):
        self.assertEqual(
            MANUAL_ROLLOUT_DECISIONS,
            (
                "not_eligible",
                "eligible_to_prepare_future_authorization",
            ),
        )

        self.assertEqual(
            MANUAL_ROLLOUT_DECISION_PRECEDENCE,
            MANUAL_ROLLOUT_DECISIONS,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_DECISION_PRECEDENCE[0],
            "not_eligible",
        )

    def test_v265_reason_families_are_exact_and_unique(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES),
            14,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES
            ),
            18,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES
            ),
            11,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES
            ),
            5,
        )

        combined = (
            set(MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES)
            | set(
                MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES
            )
            | set(
                MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES
            )
            | set(
                MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES
            )
        )

        self.assertEqual(
            len(combined),
            48,
        )

    def test_v265_global_reason_order_is_exact_and_unique(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_REASON_ORDER),
            48,
        )

        self.assertEqual(
            len(set(MANUAL_ROLLOUT_REASON_ORDER)),
            48,
        )

        expected = (
            set(MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES)
            | set(
                MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES
            )
            | set(
                MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES
            )
            | set(
                MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES
            )
        )

        self.assertEqual(
            set(MANUAL_ROLLOUT_REASON_ORDER),
            expected,
        )

    def test_v265_source_evidence_contract_remains_stable(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_DECISIONS),
            6,
        )

        self.assertEqual(
            len(EVIDENCE_REVIEW_REASON_ORDER),
            38,
        )

        self.assertEqual(
            EVIDENCE_REVIEW_ROLLOUT_RECOMMENDATIONS,
            (
                "not_eligible",
                "eligible_for_manual_consideration",
            ),
        )

    def test_v265_complete_consistent_source_is_considerable_only(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record()
        )

        self.assertEqual(
            result["decision"],
            "complete_consistent",
        )

        self.assertEqual(
            result["rollout_recommendation"],
            "eligible_for_manual_consideration",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertTrue(
            result["complete"]
        )

        self.assertTrue(
            result["consistent"]
        )

        self.assertTrue(
            result["privacy_safe"]
        )

        self.assertTrue(
            result["incident_clear"]
        )

        self.assertTrue(
            result["policy_compliant"]
        )

    def test_v265_nonqualifying_source_results_remain_not_considerable(self):
        cases = (
            build_complete_evidence_review_record(
                privacy_sanitizer_applied=False,
            ),
            build_complete_evidence_review_record(
                provider_anomaly=True,
            ),
            build_complete_evidence_review_record(
                change_record_id="",
            ),
            build_complete_evidence_review_record(
                pilot_owner_id=0,
            ),
            build_complete_evidence_review_record(
                automatic_retry_enabled=True,
            ),
        )

        for record in cases:
            with self.subTest(
                record=record
            ):
                result = evaluate_evidence_review(
                    record
                )

                self.assertNotEqual(
                    result["decision"],
                    "complete_consistent",
                )

                self.assertEqual(
                    result["rollout_recommendation"],
                    "not_eligible",
                )

                self.assertTrue(
                    result["reason_codes"]
                )

    def test_v265_owner_limit_and_time_boundaries_are_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_MAX_OWNER_COUNT,
            1,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_MAX_LIMIT,
            3,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_READINESS_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_PREVIEW_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_CONSIDERATION_LIFETIME_SECONDS,
            900,
        )

    def test_v265_required_roles_are_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_REQUIRED_ROLES,
            (
                "decision_owner",
                "evidence_reviewer",
                "privacy_reviewer",
                "incident_reviewer",
                "rollback_reviewer",
                "incident_commander",
            ),
        )

    def test_v265_role_separation_rules_are_complete(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_ROLE_SEPARATION_RULES),
            6,
        )

        self.assertIn(
            "decision owner differs from rollback reviewer",
            MANUAL_ROLLOUT_ROLE_SEPARATION_RULES,
        )

        self.assertIn(
            (
                "evidence privacy incident and rollback "
                "reviewers are pairwise distinct"
            ),
            MANUAL_ROLLOUT_ROLE_SEPARATION_RULES,
        )

    def test_v265_future_authorization_requirements_are_complete(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS
            ),
            13,
        )

        required = {
            "new authorization identifier",
            "one explicit positive owner identifier",
            "explicit limit between one and three",
            "current readiness evidence",
            "current preview evidence",
            "current provider sender and backend state",
            "current authorization command fingerprint",
            "current pre-send freeze fingerprint",
            "both production confirmations",
            "explicit authorization expiration",
            "one-shot authorization consumption",
            "automatic retry and automatic promotion remain disabled",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS
                )
            )
        )

    def test_v265_evidence_allowlist_is_exact_and_unique(self):
        self.assertEqual(
            MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST,
            MANUAL_ROLLOUT_REQUIRED_FIELDS,
        )

        self.assertEqual(
            len(set(MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST)),
            len(MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST),
        )

    def test_v265_allowlist_excludes_sensitive_fields(self):
        self.assertTrue(
            set(MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST)
            .isdisjoint(
                MANUAL_ROLLOUT_SENSITIVE_INPUT_KEYS
            )
        )

        self.assertNotIn(
            "recipient_email",
            MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST,
        )

        self.assertNotIn(
            "rendered_body",
            MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST,
        )

    def test_v265_privacy_exclusions_are_complete(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS),
            13,
        )

        self.assertIn(
            "SMTP password",
            MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "raw exception traceback",
            MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS,
        )

    def test_v265_prohibited_actions_are_complete(self):
        required = {
            "production delivery during consideration",
            "authorization consumption during consideration",
            "delivery retry during consideration",
            "scheduler enablement",
            "automatic rollout promotion",
            "production feature-gate mutation",
            "owner-scope expansion",
            "limit expansion",
            "source authorization reuse",
            "evidence review reused as execution authorization",
            "global all-owner execution",
            "multi-owner execution",
            "blind retry",
            "manual sent-timestamp edit",
            "manual audit-event deletion",
            "direct SQL repair",
            "Django shell timestamp repair",
            "credential logging",
            "privacy sanitizer bypass",
            "computed decision spoofing",
            "silent inconsistency acceptance",
        }

        self.assertTrue(
            required.issubset(
                set(MANUAL_ROLLOUT_PROHIBITED_ACTIONS)
            )
        )

    def test_v265_consideration_contract_performs_no_external_action(self):
        record = (
            build_complete_evidence_review_record()
        )

        with (
            patch(
                "subprocess.run"
            ) as subprocess_run,
            patch(
                "django.core.mail.get_connection"
            ) as get_connection,
            patch(
                "django.core.management.call_command"
            ) as call_command_mock,
        ):
            result = evaluate_evidence_review(
                record
            )

        subprocess_run.assert_not_called()
        get_connection.assert_not_called()
        call_command_mock.assert_not_called()

        self.assertEqual(
            result["decision"],
            "complete_consistent",
        )

    def test_v265_v264_closeout_gates_remain_packaged(self):
        required = {
            "complete-consistent permits manual consideration only",
            "manual rollout consideration requires separate future authorization",
            "manual rollout consideration remains nonexecuting",
            "review performs no production delivery",
            "review consumes no authorization",
            "review performs no retry",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V264_CLOSEOUT_GATES)
            )
        )

    def test_v265_default_readiness_remains_not_ready(self):
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
    def test_v265_production_like_readiness_remains_ready(self):
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
    def test_v265_readiness_execution_opens_no_email_connection(self):
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

    def test_v265_command_surfaces_remain_unchanged(self):
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

    def test_v265_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v265_scheduler_remains_nonautomatic(self):
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

    def test_v265_v264_closeout_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_evidence_review_closeout_audit_v264.py"
        )

        self.assertIn(
            (
                "V264_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "EVIDENCE_REVIEW_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            (
                "v265: saved-search notification production delivery "
                "pilot supervised execution manual rollout consideration "
                "contract"
            ),
            source,
        )

    def test_v265_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V265_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CONTRACT
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

    def test_v265_no_migration_0017_exists(self):
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

    def test_v265_acceptance_gate_matrix_is_complete(self):
        required = {
            "v264 evidence-review closeout remains packaged",
            "v265 scope remains exactly two contract files",
            "v266 proposed scope remains exactly two files",
            "manual consideration remains documentation and test only",
            "required fields remain exactly forty-seven",
            "forty-eight reason codes remain unique",
            "source evidence decision must be complete-consistent",
            "source rollout recommendation must permit manual consideration",
            "source reason-code collection must be empty",
            "source authorization consumption count must equal one",
            "source production invocation count must equal one",
            "considered owner scope cannot expand source owner scope",
            "considered limit cannot exceed source approved limit",
            "decision owner remains separated from reviewers",
            "future authorization remains mandatory",
            "future authorization must have a new identifier",
            "future authorization requires both confirmations",
            "manual consideration performs no production delivery",
            "manual consideration consumes no authorization",
            "manual consideration performs no retry",
            "manual consideration enables no scheduler",
            "manual consideration performs no automatic promotion",
            "source authorization cannot be reused",
            "evidence review cannot be reused as authorization",
            "strict evidence allowlist remains explicit",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service remains unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertGreaterEqual(
            len(V265_ACCEPTANCE_GATES),
            80,
        )

        self.assertTrue(
            required.issubset(
                set(V265_ACCEPTANCE_GATES)
            )
        )
