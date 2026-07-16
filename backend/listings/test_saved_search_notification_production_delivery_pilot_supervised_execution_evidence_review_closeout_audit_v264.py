from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
from typing import Any
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
    EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES,
    EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES,
    EVIDENCE_REVIEW_DECISIONS,
    EVIDENCE_REVIEW_DECISION_PRECEDENCE,
    EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST,
    EVIDENCE_REVIEW_IMMUTABLE_BINDINGS,
    EVIDENCE_REVIEW_INCIDENT_REASON_CODES,
    EVIDENCE_REVIEW_POLICY_REASON_CODES,
    EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS,
    EVIDENCE_REVIEW_PRIVACY_REASON_CODES,
    EVIDENCE_REVIEW_PROHIBITED_ACTIONS,
    EVIDENCE_REVIEW_REASON_ORDER,
    EVIDENCE_REVIEW_RECONCILIATION_RULES,
    EVIDENCE_REVIEW_REQUIRED_FIELDS,
    EVIDENCE_REVIEW_REQUIRED_REVIEW_ROLES,
    EVIDENCE_REVIEW_ROLLOUT_RECOMMENDATIONS,
    V262_ACCEPTANCE_GATES,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_evidence_review_v263 import (
    EVIDENCE_REVIEW_AUDIT_COUNT_FIELDS,
    EVIDENCE_REVIEW_DELIVERY_COUNT_FIELDS,
    EVIDENCE_REVIEW_RESULT_FIELDS,
    EVIDENCE_REVIEW_SENSITIVE_INPUT_KEYS,
    V263_IMPLEMENTATION_GATES,
    build_complete_evidence_review_record,
    collect_completeness_reason_codes,
    collect_consistency_reason_codes,
    collect_incident_reason_codes,
    collect_policy_reason_codes,
    collect_privacy_reason_codes,
    evaluate_evidence_review,
    immutable_evidence_review_snapshot,
    ordered_unique_reason_codes,
    sanitize_evidence_review_record,
)


V264_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CLOSEOUT_AUDIT = (
    "V264_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CLOSEOUT_AUDIT"
)

V262_COMMITTED_SCOPE = (
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

V263_COMMITTED_SCOPE = (
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

V264_ALLOWED_SCOPE = (
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

V265_PROPOSED_SCOPE = (
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

MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS = (
    "evidence-review lane is closed",
    "manual-rollout consideration remains documentation and test only",
    "evidence decision is complete_consistent",
    "rollout recommendation is eligible_for_manual_consideration",
    "reason-code collection is empty",
    "evidence completeness flag is true",
    "evidence consistency flag is true",
    "privacy-safe flag is true",
    "incident-clear flag is true",
    "policy-compliant flag is true",
    "one change-record identifier is present",
    "one authorization identifier is present",
    "one positive owner identifier is present",
    "approved limit remains between 1 and 3",
    "authorization consumption count equals one",
    "production invocation count equals one",
    "delivery outcome counts reconcile",
    "persistent audit counts reconcile",
    "sent timestamps are internally consistent",
    "duplicate-attempt review is clean",
    "persistent audit has no gaps",
    "provider anomaly is absent",
    "incident state is closed",
    "privacy sanitizer was applied",
    "automatic retry remains disabled",
    "automatic rollout promotion remains disabled",
    "manual rollout decision owner is present",
    "evidence reviewer is present",
    "privacy reviewer is present",
    "incident reviewer is present",
    "rollback reviewer is present",
    "incident commander is present",
    "review identities are distinct where required",
    "a separate future authorization is required",
    "consideration performs no production delivery",
    "consideration consumes no authorization",
    "consideration performs no retry",
    "consideration enables no scheduler",
    "consideration performs no automatic promotion",
)

V264_REASON_REACHABILITY_CASES = (
    (
        {},
        ("change_record_id",),
        "missing_change_record_id",
    ),
    (
        {},
        ("authorization_id",),
        "missing_authorization_id",
    ),
    (
        {},
        ("pilot_owner_id",),
        "missing_owner_id",
    ),
    (
        {},
        ("approved_limit",),
        "missing_approved_limit",
    ),
    (
        {},
        ("authorization_command_fingerprint",),
        "missing_authorization_command_fingerprint",
    ),
    (
        {},
        ("freeze_fingerprint",),
        "missing_freeze_fingerprint",
    ),
    (
        {},
        ("authorization_consumption_count",),
        "missing_authorization_consumption_count",
    ),
    (
        {},
        ("production_invocation_count",),
        "missing_production_invocation_count",
    ),
    (
        {},
        ("delivered_count",),
        "missing_delivery_outcome_counts",
    ),
    (
        {},
        ("delivery_attempted_event_count",),
        "missing_persistent_audit_counts",
    ),
    (
        {},
        ("sent_timestamp_consistent",),
        "missing_sent_timestamp_consistency",
    ),
    (
        {},
        ("duplicate_attempt_clean",),
        "missing_duplicate_attempt_status",
    ),
    (
        {},
        ("provider_anomaly",),
        "missing_provider_anomaly_status",
    ),
    (
        {},
        ("incident_state",),
        "missing_incident_state",
    ),
    (
        {},
        ("reviewer_identity",),
        "missing_reviewer_identity",
    ),
    (
        {},
        ("review_completed_at_utc",),
        "missing_review_timestamp",
    ),
    (
        {
            "pilot_owner_id": 0,
        },
        (),
        "invalid_owner_id",
    ),
    (
        {
            "approved_limit": 4,
        },
        (),
        "invalid_approved_limit",
    ),
    (
        {
            "authorization_consumption_count": 0,
        },
        (),
        "authorization_consumption_count_mismatch",
    ),
    (
        {
            "production_invocation_count": 2,
        },
        (),
        "production_invocation_count_mismatch",
    ),
    (
        {
            "delivered_count": 4,
            "delivery_attempted_event_count": 4,
            "delivery_succeeded_event_count": 4,
            "sent_timestamp_event_count": 4,
        },
        (),
        "delivery_counts_mismatch",
    ),
    (
        {
            "delivery_attempted_event_count": 1,
        },
        (),
        "delivery_attempted_event_mismatch",
    ),
    (
        {
            "delivery_succeeded_event_count": 1,
        },
        (),
        "delivery_succeeded_event_mismatch",
    ),
    (
        {
            "delivery_failed_event_count": 1,
        },
        (),
        "delivery_failed_event_mismatch",
    ),
    (
        {
            "sent_timestamp_event_count": 1,
        },
        (),
        "sent_timestamp_event_mismatch",
    ),
    (
        {
            "sent_timestamp_consistent": False,
        },
        (),
        "sent_timestamp_inconsistent",
    ),
    (
        {
            "duplicate_attempt_clean": False,
        },
        (),
        "duplicate_attempt_detected",
    ),
    (
        {
            "audit_gap_free": False,
        },
        (),
        "audit_gap_detected",
    ),
    (
        {
            "privacy_sanitizer_applied": False,
        },
        (),
        "privacy_sanitizer_not_applied",
    ),
    (
        {
            "smtp_password": "secret",
        },
        (),
        "sensitive_evidence_detected",
    ),
    (
        {
            "provider_anomaly": True,
        },
        (),
        "provider_anomaly_detected",
    ),
    (
        {
            "incident_state": "open",
        },
        (),
        "incident_open",
    ),
    (
        {
            "incident_state": "invalid",
        },
        (),
        "incident_state_invalid",
    ),
    (
        {
            "delivered_count": 1,
            "failed_count": 1,
            "delivery_attempted_event_count": 2,
            "delivery_succeeded_event_count": 1,
            "delivery_failed_event_count": 1,
            "sent_timestamp_event_count": 1,
        },
        (),
        "failed_delivery_present",
    ),
    (
        {
            "delivered_count": 1,
            "refused_count": 1,
            "delivery_attempted_event_count": 1,
            "delivery_succeeded_event_count": 1,
            "sent_timestamp_event_count": 1,
        },
        (),
        "unexpected_refusal_present",
    ),
    (
        {
            "automatic_retry_enabled": True,
        },
        (),
        "automatic_retry_enabled",
    ),
    (
        {
            "automatic_rollout_promotion_enabled": True,
        },
        (),
        "automatic_rollout_promotion_enabled",
    ),
    (
        {
            "production_delivery_attempted_during_review": True,
        },
        (),
        "production_delivery_attempted_during_review",
    ),
)

V264_CLOSEOUT_GATES = (
    "v262 evidence-review contract remains packaged",
    "v263 evidence-review implementation remains packaged",
    "v262 committed scope remains exactly two files",
    "v263 committed scope remains exactly two files",
    "v264 scope remains exactly two closeout files",
    "v265 proposed scope remains exactly two files",
    "v265 remains documentation and test only",
    "required evidence fields remain exactly twenty-eight",
    "immutable evidence bindings remain exact",
    "six decision classifications remain exact",
    "decision precedence remains deterministic",
    "two rollout recommendations remain exact",
    "complete-consistent permits manual consideration only",
    "complete-consistent does not authorize production delivery",
    "complete-consistent does not consume authorization",
    "complete-consistent does not authorize retry",
    "complete-consistent does not enable scheduler",
    "complete-consistent does not promote rollout automatically",
    "all thirty-eight reason codes remain unique",
    "all thirty-eight reason codes remain reachable",
    "reason-code order remains deterministic",
    "completeness reasons remain explicit",
    "consistency reasons remain explicit",
    "privacy reasons remain explicit",
    "incident reasons remain explicit",
    "policy reasons remain explicit",
    "privacy rejection remains highest precedence",
    "incident escalation remains second precedence",
    "incomplete remains before inconsistent",
    "inconsistent remains before policy ineligibility",
    "policy ineligibility remains before complete-consistent",
    "positive owner identifier remains mandatory",
    "approved limit remains between one and three",
    "authorization consumption count must equal one",
    "production invocation count must equal one",
    "delivery counts must be present",
    "delivery counts must be nonnegative integers",
    "delivery total must be at least one",
    "delivery total must not exceed approved limit",
    "delivery-attempted count must equal delivered plus failed",
    "delivery-succeeded count must equal delivered",
    "delivery-failed count must equal failed",
    "sent-timestamp count must equal delivered",
    "sent timestamps must remain consistent",
    "duplicate-attempt review must remain clean",
    "persistent audit must remain gap-free",
    "provider anomaly must escalate",
    "open incident must escalate",
    "invalid incident state must escalate",
    "failed delivery must escalate",
    "unexpected refusal must escalate",
    "privacy sanitizer remains mandatory",
    "sensitive key detection remains fail closed",
    "sensitive values remain excluded from results",
    "unknown fields remain discarded",
    "input final decision cannot spoof output",
    "input rollout recommendation cannot spoof output",
    "input reason codes cannot spoof output",
    "sanitizer remains strict allowlist based",
    "immutable snapshot remains deterministic",
    "review evaluator remains deterministic",
    "automatic retry remains policy-ineligible",
    "automatic rollout promotion remains policy-ineligible",
    "review-time delivery attempt remains policy-ineligible",
    "review performs no production delivery",
    "review consumes no authorization",
    "review performs no retry",
    "review invokes no management command",
    "review invokes no subprocess",
    "review opens no email connection",
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
    "manual rollout consideration requires separate future authorization",
    "manual rollout consideration remains nonexecuting",
    "historical safety tests remain green",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v265: saved-search notification production delivery pilot supervised execution manual rollout consideration contract"

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
        "pilot_supervised_execution_evidence_review_contract_v262.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_evidence_review_v263.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionEvidenceReviewCloseoutAuditV264Tests(
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

    def test_v264_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V264_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CLOSEOUT_AUDIT,
            (
                "V264_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "EVIDENCE_REVIEW_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V262_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V263_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V264_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V265_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v265: saved-search notification production delivery "
                "pilot supervised execution manual rollout consideration "
                "contract"
            ),
        )

    def test_v264_v265_scope_is_documentation_and_test_only(self):
        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V265_PROPOSED_SCOPE
            )
        )

    def test_v264_contract_packages_remain_exact(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_REQUIRED_FIELDS),
            28,
        )

        self.assertEqual(
            len(EVIDENCE_REVIEW_DECISIONS),
            6,
        )

        self.assertEqual(
            len(EVIDENCE_REVIEW_REASON_ORDER),
            38,
        )

        self.assertEqual(
            len(set(EVIDENCE_REVIEW_REASON_ORDER)),
            38,
        )

        self.assertEqual(
            EVIDENCE_REVIEW_ROLLOUT_RECOMMENDATIONS,
            (
                "not_eligible",
                "eligible_for_manual_consideration",
            ),
        )

    def test_v264_result_fields_remain_exact(self):
        self.assertEqual(
            EVIDENCE_REVIEW_RESULT_FIELDS,
            (
                "decision",
                "rollout_recommendation",
                "complete",
                "consistent",
                "privacy_safe",
                "incident_clear",
                "policy_compliant",
                "reason_codes",
                "sanitized_evidence",
            ),
        )

    def test_v264_delivery_and_audit_count_fields_remain_exact(self):
        self.assertEqual(
            EVIDENCE_REVIEW_DELIVERY_COUNT_FIELDS,
            (
                "delivered_count",
                "skipped_count",
                "refused_count",
                "failed_count",
            ),
        )

        self.assertEqual(
            EVIDENCE_REVIEW_AUDIT_COUNT_FIELDS,
            (
                "delivery_attempted_event_count",
                "delivery_succeeded_event_count",
                "delivery_failed_event_count",
                "sent_timestamp_event_count",
            ),
        )

    def test_v264_decision_precedence_remains_exact(self):
        self.assertEqual(
            EVIDENCE_REVIEW_DECISION_PRECEDENCE,
            (
                "privacy_rejected",
                "incident_escalated",
                "incomplete",
                "inconsistent",
                (
                    "not_eligible_for_"
                    "rollout_consideration"
                ),
                "complete_consistent",
            ),
        )

        cases = (
            (
                build_complete_evidence_review_record(
                    smtp_password="secret",
                    provider_anomaly=True,
                    change_record_id="",
                    pilot_owner_id=0,
                    automatic_retry_enabled=True,
                ),
                "privacy_rejected",
            ),
            (
                build_complete_evidence_review_record(
                    provider_anomaly=True,
                    change_record_id="",
                    pilot_owner_id=0,
                    automatic_retry_enabled=True,
                ),
                "incident_escalated",
            ),
            (
                build_complete_evidence_review_record(
                    change_record_id="",
                    pilot_owner_id=0,
                    automatic_retry_enabled=True,
                ),
                "incomplete",
            ),
            (
                build_complete_evidence_review_record(
                    pilot_owner_id=0,
                    automatic_retry_enabled=True,
                ),
                "inconsistent",
            ),
            (
                build_complete_evidence_review_record(
                    automatic_retry_enabled=True,
                ),
                (
                    "not_eligible_for_"
                    "rollout_consideration"
                ),
            ),
            (
                build_complete_evidence_review_record(),
                "complete_consistent",
            ),
        )

        for record, expected in cases:
            with self.subTest(
                expected=expected
            ):
                result = evaluate_evidence_review(
                    record
                )

                self.assertEqual(
                    result["decision"],
                    expected,
                )

    def test_v264_default_result_remains_manual_consideration_only(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record()
        )

        self.assertEqual(
            tuple(result),
            EVIDENCE_REVIEW_RESULT_FIELDS,
        )

        self.assertEqual(
            result["decision"],
            "complete_consistent",
        )

        self.assertEqual(
            result["rollout_recommendation"],
            "eligible_for_manual_consideration",
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

        self.assertEqual(
            result["reason_codes"],
            (),
        )

    def test_v264_all_reason_codes_remain_reachable(self):
        self.assertEqual(
            len(V264_REASON_REACHABILITY_CASES),
            38,
        )

        reached: set[str] = set()

        for changes, remove_fields, reason in (
            V264_REASON_REACHABILITY_CASES
        ):
            with self.subTest(
                reason=reason
            ):
                record = (
                    build_complete_evidence_review_record(
                        **changes
                    )
                )

                for field in remove_fields:
                    record.pop(
                        field
                    )

                result = evaluate_evidence_review(
                    record
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

                reached.add(
                    reason
                )

        self.assertEqual(
            reached,
            set(EVIDENCE_REVIEW_REASON_ORDER),
        )

    def test_v264_reason_order_remains_deterministic(self):
        record = (
            build_complete_evidence_review_record(
                change_record_id="",
                pilot_owner_id=0,
                approved_limit=4,
                authorization_consumption_count=0,
                production_invocation_count=2,
                delivered_count=5,
                failed_count=1,
                refused_count=1,
                delivery_attempted_event_count=0,
                delivery_succeeded_event_count=0,
                delivery_failed_event_count=0,
                sent_timestamp_event_count=0,
                sent_timestamp_consistent=False,
                duplicate_attempt_clean=False,
                audit_gap_free=False,
                privacy_sanitizer_applied=False,
                smtp_password="secret",
                provider_anomaly=True,
                incident_state="open",
                automatic_retry_enabled=True,
                automatic_rollout_promotion_enabled=True,
                production_delivery_attempted_during_review=True,
            )
        )

        result = evaluate_evidence_review(
            record
        )

        order = {
            reason: index
            for index, reason in enumerate(
                EVIDENCE_REVIEW_REASON_ORDER
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

        self.assertEqual(
            result["reason_codes"],
            ordered_unique_reason_codes(
                list(
                    reversed(
                        result["reason_codes"]
                    )
                )
            ),
        )

    def test_v264_reason_packages_remain_exact(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES),
            16,
        )

        self.assertEqual(
            len(EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES),
            12,
        )

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

        combined = (
            set(EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES)
            | set(EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES)
            | set(EVIDENCE_REVIEW_PRIVACY_REASON_CODES)
            | set(EVIDENCE_REVIEW_INCIDENT_REASON_CODES)
            | set(EVIDENCE_REVIEW_POLICY_REASON_CODES)
        )

        self.assertEqual(
            combined,
            set(EVIDENCE_REVIEW_REASON_ORDER),
        )

    def test_v264_collectors_remain_deterministic(self):
        record = (
            build_complete_evidence_review_record()
        )

        self.assertEqual(
            collect_completeness_reason_codes(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_consistency_reason_codes(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_privacy_reason_codes(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_incident_reason_codes(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_policy_reason_codes(
                record
            ),
            (),
        )

    def test_v264_input_decision_cannot_spoof_computed_result(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                final_decision="privacy_rejected",
                rollout_recommendation="not_eligible",
                reason_codes=(
                    "sensitive_evidence_detected",
                ),
            )
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

        self.assertEqual(
            result["sanitized_evidence"][
                "final_decision"
            ],
            "complete_consistent",
        )

    def test_v264_sensitive_evidence_remains_privacy_rejected(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                smtp_password="secret-value",
                recipient_email="private@example.invalid",
                rendered_subject="private-subject",
                rendered_body="private-body",
                provider_response_body="private-provider-body",
            )
        )

        self.assertEqual(
            result["decision"],
            "privacy_rejected",
        )

        self.assertEqual(
            result["rollout_recommendation"],
            "not_eligible",
        )

        rendered = repr(
            result
        )

        for value in (
            "secret-value",
            "private@example.invalid",
            "private-subject",
            "private-body",
            "private-provider-body",
        ):
            with self.subTest(
                value=value
            ):
                self.assertNotIn(
                    value,
                    rendered,
                )

    def test_v264_privacy_sanitizer_remains_mandatory(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                privacy_sanitizer_applied=False,
            )
        )

        self.assertEqual(
            result["decision"],
            "privacy_rejected",
        )

        self.assertIn(
            "privacy_sanitizer_not_applied",
            result["reason_codes"],
        )

    def test_v264_unknown_fields_remain_discarded(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                unknown_field="discard-me",
            )
        )

        self.assertNotIn(
            "unknown_field",
            result["sanitized_evidence"],
        )

        self.assertNotIn(
            "discard-me",
            repr(result),
        )

    def test_v264_sanitizer_remains_strict_allowlist_based(self):
        record = (
            build_complete_evidence_review_record()
        )

        sanitized = sanitize_evidence_review_record(
            record
        )

        self.assertTrue(
            set(sanitized).issubset(
                set(EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST)
            )
        )

        self.assertEqual(
            tuple(sanitized),
            tuple(
                field
                for field in EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST
                if field in sanitized
            ),
        )

        self.assertTrue(
            set(EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST)
            .isdisjoint(
                EVIDENCE_REVIEW_SENSITIVE_INPUT_KEYS
            )
        )

    def test_v264_immutable_snapshot_remains_exact(self):
        record = (
            build_complete_evidence_review_record()
        )

        first = immutable_evidence_review_snapshot(
            record
        )

        second = immutable_evidence_review_snapshot(
            record
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            tuple(first),
            EVIDENCE_REVIEW_IMMUTABLE_BINDINGS,
        )

        self.assertEqual(
            first["pilot_owner_id"],
            101,
        )

        self.assertEqual(
            first["approved_limit"],
            3,
        )

    def test_v264_owner_and_limit_boundaries_remain_fail_closed(self):
        cases = (
            (
                1,
                1,
                "complete_consistent",
            ),
            (
                101,
                3,
                "complete_consistent",
            ),
            (
                0,
                1,
                "inconsistent",
            ),
            (
                1,
                0,
                "inconsistent",
            ),
            (
                1,
                4,
                "inconsistent",
            ),
        )

        for owner_id, limit, expected in cases:
            with self.subTest(
                owner_id=owner_id,
                limit=limit,
            ):
                record = (
                    build_complete_evidence_review_record(
                        pilot_owner_id=owner_id,
                        approved_limit=limit,
                    )
                )

                if limit == 1:
                    record.update(
                        {
                            "delivered_count": 1,
                            "delivery_attempted_event_count": 1,
                            "delivery_succeeded_event_count": 1,
                            "sent_timestamp_event_count": 1,
                        }
                    )

                result = evaluate_evidence_review(
                    record
                )

                self.assertEqual(
                    result["decision"],
                    expected,
                )

    def test_v264_authorization_and_invocation_counts_remain_exact(self):
        authorization_result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                authorization_consumption_count=0,
            )
        )

        invocation_result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                production_invocation_count=2,
            )
        )

        self.assertEqual(
            authorization_result["decision"],
            "inconsistent",
        )

        self.assertIn(
            "authorization_consumption_count_mismatch",
            authorization_result["reason_codes"],
        )

        self.assertEqual(
            invocation_result["decision"],
            "inconsistent",
        )

        self.assertIn(
            "production_invocation_count_mismatch",
            invocation_result["reason_codes"],
        )

    def test_v264_delivery_counts_remain_bounded(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                approved_limit=1,
                delivered_count=2,
                delivery_attempted_event_count=2,
                delivery_succeeded_event_count=2,
                sent_timestamp_event_count=2,
            )
        )

        self.assertEqual(
            result["decision"],
            "inconsistent",
        )

        self.assertIn(
            "delivery_counts_mismatch",
            result["reason_codes"],
        )

    def test_v264_audit_counts_remain_reconciled(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                delivery_attempted_event_count=1,
                delivery_succeeded_event_count=1,
                delivery_failed_event_count=1,
                sent_timestamp_event_count=1,
            )
        )

        self.assertEqual(
            result["decision"],
            "inconsistent",
        )

        expected = {
            "delivery_attempted_event_mismatch",
            "delivery_succeeded_event_mismatch",
            "delivery_failed_event_mismatch",
            "sent_timestamp_event_mismatch",
        }

        self.assertTrue(
            expected.issubset(
                set(result["reason_codes"])
            )
        )

    def test_v264_sent_timestamp_duplicate_and_gap_safety_remain(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                sent_timestamp_consistent=False,
                duplicate_attempt_clean=False,
                audit_gap_free=False,
            )
        )

        self.assertEqual(
            result["decision"],
            "inconsistent",
        )

        self.assertIn(
            "sent_timestamp_inconsistent",
            result["reason_codes"],
        )

        self.assertIn(
            "duplicate_attempt_detected",
            result["reason_codes"],
        )

        self.assertIn(
            "audit_gap_detected",
            result["reason_codes"],
        )

    def test_v264_incident_conditions_remain_escalated(self):
        cases = (
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
                "incident_open",
            ),
            (
                {
                    "incident_state": "invalid",
                },
                "incident_state_invalid",
            ),
            (
                {
                    "delivered_count": 1,
                    "failed_count": 1,
                    "delivery_attempted_event_count": 2,
                    "delivery_succeeded_event_count": 1,
                    "delivery_failed_event_count": 1,
                    "sent_timestamp_event_count": 1,
                },
                "failed_delivery_present",
            ),
            (
                {
                    "delivered_count": 1,
                    "refused_count": 1,
                    "delivery_attempted_event_count": 1,
                    "delivery_succeeded_event_count": 1,
                    "sent_timestamp_event_count": 1,
                },
                "unexpected_refusal_present",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_evidence_review(
                    build_complete_evidence_review_record(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "incident_escalated",
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v264_policy_conditions_remain_not_eligible(self):
        cases = (
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
            (
                {
                    "production_delivery_attempted_during_review": True,
                },
                "production_delivery_attempted_during_review",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_evidence_review(
                    build_complete_evidence_review_record(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    (
                        "not_eligible_for_"
                        "rollout_consideration"
                    ),
                )

                self.assertEqual(
                    result["rollout_recommendation"],
                    "not_eligible",
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v264_review_functions_remain_nonexecuting(self):
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

    def test_v264_review_roles_remain_exact(self):
        self.assertEqual(
            EVIDENCE_REVIEW_REQUIRED_REVIEW_ROLES,
            (
                "evidence_reviewer",
                "privacy_reviewer",
                "incident_reviewer",
            ),
        )

    def test_v264_reconciliation_rules_remain_complete(self):
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

    def test_v264_privacy_and_prohibition_packages_remain_complete(self):
        self.assertIn(
            "SMTP password",
            EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "raw exception traceback",
            EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS,
        )

        required = {
            "production delivery during evidence-review checkpoint",
            "authorization consumption during evidence review",
            "delivery retry during evidence review",
            "automatic rollout promotion",
            "automatic retry",
            "global all-owner execution",
            "multi-owner execution",
            "direct SQL repair",
            "Django shell timestamp repair",
            "privacy sanitizer bypass",
            "silent inconsistency acceptance",
        }

        self.assertTrue(
            required.issubset(
                set(EVIDENCE_REVIEW_PROHIBITED_ACTIONS)
            )
        )

    def test_v264_v262_and_v263_gate_packages_remain_present(self):
        v262_required = {
            "decision precedence is deterministic",
            "all reason codes are unique",
            "privacy sanitizer remains mandatory",
            "sensitive evidence triggers privacy rejection",
            "automatic retry remains prohibited",
            "automatic rollout promotion remains prohibited",
            "evidence review performs no production delivery",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        v263_required = {
            "all thirty-eight reason codes remain reachable",
            "reason-code order remains deterministic",
            "privacy rejection has highest precedence",
            "complete-consistent permits manual consideration only",
            "sensitive values never appear in results",
            "unknown fields are discarded",
            "production command is not invoked during review",
            "email connection is not opened during review",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            v262_required.issubset(
                set(V262_ACCEPTANCE_GATES)
            )
        )

        self.assertTrue(
            v263_required.issubset(
                set(V263_IMPLEMENTATION_GATES)
            )
        )

    def test_v264_manual_rollout_preconditions_are_complete(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS),
            39,
        )

        required = {
            "evidence-review lane is closed",
            "manual-rollout consideration remains documentation and test only",
            "evidence decision is complete_consistent",
            "rollout recommendation is eligible_for_manual_consideration",
            "reason-code collection is empty",
            "authorization consumption count equals one",
            "production invocation count equals one",
            "delivery outcome counts reconcile",
            "persistent audit counts reconcile",
            "provider anomaly is absent",
            "incident state is closed",
            "automatic retry remains disabled",
            "automatic rollout promotion remains disabled",
            "a separate future authorization is required",
            "consideration performs no production delivery",
            "consideration consumes no authorization",
            "consideration performs no retry",
            "consideration enables no scheduler",
            "consideration performs no automatic promotion",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_CONSIDERATION_PRECONDITIONS
                )
            )
        )

    def test_v264_default_readiness_remains_not_ready(self):
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
    def test_v264_production_like_readiness_remains_ready(self):
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
    def test_v264_readiness_execution_opens_no_email_connection(self):
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

    def test_v264_command_surfaces_remain_unchanged(self):
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

    def test_v264_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v264_scheduler_remains_nonautomatic(self):
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

    def test_v264_v262_and_v263_packages_remain_present(self):
        v262_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_evidence_review_contract_v262.py"
        )

        v263_source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_evidence_review_v263.py"
        )

        self.assertIn(
            (
                "V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "EVIDENCE_REVIEW_CONTRACT"
            ),
            v262_source,
        )

        self.assertIn(
            (
                "V263_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "EVIDENCE_REVIEW"
            ),
            v263_source,
        )

        self.assertIn(
            (
                "v264: saved-search notification production delivery "
                "pilot supervised execution evidence review closeout audit"
            ),
            v263_source,
        )

    def test_v264_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V264_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW_CLOSEOUT_AUDIT
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

    def test_v264_no_migration_0017_exists(self):
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

    def test_v264_closeout_gate_matrix_is_complete(self):
        required = {
            "v262 evidence-review contract remains packaged",
            "v263 evidence-review implementation remains packaged",
            "v264 scope remains exactly two closeout files",
            "v265 proposed scope remains exactly two files",
            "complete-consistent permits manual consideration only",
            "all thirty-eight reason codes remain reachable",
            "reason-code order remains deterministic",
            "privacy rejection remains highest precedence",
            "delivery-attempted count must equal delivered plus failed",
            "sent timestamps must remain consistent",
            "provider anomaly must escalate",
            "open incident must escalate",
            "privacy sanitizer remains mandatory",
            "sensitive values remain excluded from results",
            "input final decision cannot spoof output",
            "automatic retry remains policy-ineligible",
            "automatic rollout promotion remains policy-ineligible",
            "review performs no production delivery",
            "review consumes no authorization",
            "review performs no retry",
            "review invokes no subprocess",
            "review opens no email connection",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service remains unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "manual rollout consideration requires separate future authorization",
            "historical safety tests remain green",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V264_CLOSEOUT_GATES)
            )
        )
