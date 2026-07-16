from __future__ import annotations

import ast
from collections.abc import Mapping
from dataclasses import asdict, dataclass
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
    V262_ACCEPTANCE_GATES,
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
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_v260 import (
    SUPERVISED_SENSITIVE_FIELDS,
)


V263_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW = (
    "V263_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW"
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

V264_PROPOSED_SCOPE = (
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

EVIDENCE_REVIEW_RESULT_FIELDS = (
    "decision",
    "rollout_recommendation",
    "complete",
    "consistent",
    "privacy_safe",
    "incident_clear",
    "policy_compliant",
    "reason_codes",
    "sanitized_evidence",
)

EVIDENCE_REVIEW_DELIVERY_COUNT_FIELDS = (
    "delivered_count",
    "skipped_count",
    "refused_count",
    "failed_count",
)

EVIDENCE_REVIEW_AUDIT_COUNT_FIELDS = (
    "delivery_attempted_event_count",
    "delivery_succeeded_event_count",
    "delivery_failed_event_count",
    "sent_timestamp_event_count",
)

EVIDENCE_REVIEW_SENSITIVE_INPUT_KEYS = (
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

V263_IMPLEMENTATION_GATES = (
    "v262 evidence-review contract remains packaged",
    "v262 committed scope remains exactly two files",
    "v263 scope remains exactly two implementation files",
    "v264 closeout scope remains exactly two files",
    "v264 remains documentation and test only",
    "implementation remains documentation and test only",
    "required evidence fields remain exactly twenty-eight",
    "immutable bindings remain exact",
    "six decision classifications remain exact",
    "decision precedence remains deterministic",
    "two rollout recommendations remain exact",
    "all thirty-eight reason codes remain unique",
    "all thirty-eight reason codes remain reachable",
    "reason-code order remains deterministic",
    "complete evidence evaluates deterministically",
    "consistent evidence evaluates deterministically",
    "privacy rejection has highest precedence",
    "incident escalation precedes completeness",
    "incomplete precedes inconsistent",
    "inconsistent precedes policy ineligibility",
    "policy ineligibility precedes complete-consistent",
    "complete-consistent permits manual consideration only",
    "complete-consistent never promotes rollout",
    "privacy sanitizer remains mandatory",
    "sensitive keys trigger privacy rejection",
    "sensitive values never appear in results",
    "unknown fields are discarded",
    "final decision input cannot spoof computed decision",
    "reason-code input cannot spoof computed reasons",
    "positive owner identifier remains mandatory",
    "approved limit remains between one and three",
    "authorization consumption count must equal one",
    "production invocation count must equal one",
    "delivery outcome counts must be present",
    "delivery outcome counts must be nonnegative",
    "delivery outcome total must be between one and approved limit",
    "attempted audit count must equal delivered plus failed",
    "succeeded audit count must equal delivered",
    "failed audit count must equal failed",
    "sent-timestamp audit count must equal delivered",
    "sent timestamps must be consistent",
    "duplicate-attempt review must be clean",
    "persistent audit must have no gaps",
    "provider anomaly causes escalation",
    "open incident causes escalation",
    "invalid incident state causes escalation",
    "failed delivery causes escalation",
    "unexpected refusal causes escalation",
    "automatic retry causes policy ineligibility",
    "automatic rollout promotion causes policy ineligibility",
    "production delivery attempted during review causes policy ineligibility",
    "authorization is not consumed during review",
    "delivery is not retried during review",
    "production command is not invoked during review",
    "email connection is not opened during review",
    "immutable snapshot is deterministic",
    "evidence sanitizer is strict allowlist based",
    "reviewer identities remain sanitized",
    "incident reference remains sanitized",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v264: saved-search notification production delivery pilot supervised execution evidence review closeout audit"

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
)


@dataclass(frozen=True)
class EvidenceReviewRecord:
    change_record_id: str = "change-001"
    authorization_id: str = "authorization-001"
    pilot_owner_id: int = 101
    approved_limit: int = 3
    authorization_command_fingerprint: str = (
        "authorization-command-fingerprint-001"
    )
    freeze_fingerprint: str = (
        "freeze-fingerprint-001"
    )
    authorization_consumption_count: int = 1
    production_invocation_count: int = 1
    delivered_count: int = 2
    skipped_count: int = 0
    refused_count: int = 0
    failed_count: int = 0
    delivery_attempted_event_count: int = 2
    delivery_succeeded_event_count: int = 2
    delivery_failed_event_count: int = 0
    sent_timestamp_event_count: int = 2
    sent_timestamp_consistent: bool = True
    duplicate_attempt_clean: bool = True
    audit_gap_free: bool = True
    provider_anomaly: bool = False
    incident_state: str = "closed"
    privacy_sanitizer_applied: bool = True
    automatic_retry_enabled: bool = False
    automatic_rollout_promotion_enabled: bool = False
    reviewer_identity: str = "evidence-reviewer-a"
    privacy_reviewer_identity: str = "privacy-reviewer-a"
    incident_reviewer_identity: str = "incident-reviewer-a"
    review_completed_at_utc: int = 1200
    final_decision: str = "pending"
    rollout_recommendation: str = "not_eligible"
    reason_codes: tuple[str, ...] = ()
    incident_reference: str = ""
    production_delivery_attempted_during_review: bool = False


def build_complete_evidence_review_record(
    **changes: Any,
) -> dict[str, Any]:
    record = asdict(
        EvidenceReviewRecord()
    )

    record.update(
        changes
    )

    return record


def _is_missing(
    record: Mapping[str, Any],
    field: str,
) -> bool:
    if field not in record:
        return True

    value = record[field]

    if value is None:
        return True

    if isinstance(
        value,
        str,
    ):
        return not value.strip()

    return False


def _is_integer(
    value: Any,
) -> bool:
    return (
        isinstance(
            value,
            int,
        )
        and not isinstance(
            value,
            bool,
        )
    )


def ordered_unique_reason_codes(
    reason_codes: list[str],
) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []

    for reason in reason_codes:
        if reason in seen:
            continue

        seen.add(
            reason
        )

        unique.append(
            reason
        )

    order = {
        reason: index
        for index, reason in enumerate(
            EVIDENCE_REVIEW_REASON_ORDER
        )
    }

    return tuple(
        sorted(
            unique,
            key=order.__getitem__,
        )
    )


def collect_completeness_reason_codes(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    scalar_fields = (
        (
            "change_record_id",
            "missing_change_record_id",
        ),
        (
            "authorization_id",
            "missing_authorization_id",
        ),
        (
            "pilot_owner_id",
            "missing_owner_id",
        ),
        (
            "approved_limit",
            "missing_approved_limit",
        ),
        (
            "authorization_command_fingerprint",
            "missing_authorization_command_fingerprint",
        ),
        (
            "freeze_fingerprint",
            "missing_freeze_fingerprint",
        ),
        (
            "authorization_consumption_count",
            "missing_authorization_consumption_count",
        ),
        (
            "production_invocation_count",
            "missing_production_invocation_count",
        ),
        (
            "sent_timestamp_consistent",
            "missing_sent_timestamp_consistency",
        ),
        (
            "duplicate_attempt_clean",
            "missing_duplicate_attempt_status",
        ),
        (
            "provider_anomaly",
            "missing_provider_anomaly_status",
        ),
        (
            "incident_state",
            "missing_incident_state",
        ),
        (
            "reviewer_identity",
            "missing_reviewer_identity",
        ),
        (
            "review_completed_at_utc",
            "missing_review_timestamp",
        ),
    )

    for field, reason in scalar_fields:
        if _is_missing(
            record,
            field,
        ):
            reasons.append(
                reason
            )

    if any(
        _is_missing(
            record,
            field,
        )
        for field in EVIDENCE_REVIEW_DELIVERY_COUNT_FIELDS
    ):
        reasons.append(
            "missing_delivery_outcome_counts"
        )

    if any(
        _is_missing(
            record,
            field,
        )
        for field in EVIDENCE_REVIEW_AUDIT_COUNT_FIELDS
    ):
        reasons.append(
            "missing_persistent_audit_counts"
        )

    return ordered_unique_reason_codes(
        reasons
    )


def collect_consistency_reason_codes(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    owner = record.get(
        "pilot_owner_id"
    )

    if not _is_missing(
        record,
        "pilot_owner_id",
    ):
        if not _is_integer(
            owner
        ) or owner <= 0:
            reasons.append(
                "invalid_owner_id"
            )

    approved_limit = record.get(
        "approved_limit"
    )

    if not _is_missing(
        record,
        "approved_limit",
    ):
        if (
            not _is_integer(
                approved_limit
            )
            or not 1 <= approved_limit <= 3
        ):
            reasons.append(
                "invalid_approved_limit"
            )

    authorization_consumption_count = record.get(
        "authorization_consumption_count"
    )

    if not _is_missing(
        record,
        "authorization_consumption_count",
    ):
        if authorization_consumption_count != 1:
            reasons.append(
                "authorization_consumption_count_mismatch"
            )

    production_invocation_count = record.get(
        "production_invocation_count"
    )

    if not _is_missing(
        record,
        "production_invocation_count",
    ):
        if production_invocation_count != 1:
            reasons.append(
                "production_invocation_count_mismatch"
            )

    delivery_counts_available = not any(
        _is_missing(
            record,
            field,
        )
        for field in EVIDENCE_REVIEW_DELIVERY_COUNT_FIELDS
    )

    audit_counts_available = not any(
        _is_missing(
            record,
            field,
        )
        for field in EVIDENCE_REVIEW_AUDIT_COUNT_FIELDS
    )

    delivery_values: dict[str, Any] = {
        field: record.get(
            field
        )
        for field in EVIDENCE_REVIEW_DELIVERY_COUNT_FIELDS
    }

    audit_values: dict[str, Any] = {
        field: record.get(
            field
        )
        for field in EVIDENCE_REVIEW_AUDIT_COUNT_FIELDS
    }

    delivery_counts_are_integers = (
        delivery_counts_available
        and all(
            _is_integer(
                value
            )
            for value in delivery_values.values()
        )
    )

    audit_counts_are_integers = (
        audit_counts_available
        and all(
            _is_integer(
                value
            )
            for value in audit_values.values()
        )
    )

    if delivery_counts_available:
        if not delivery_counts_are_integers:
            reasons.append(
                "delivery_counts_mismatch"
            )
        else:
            delivery_total = sum(
                delivery_values.values()
            )

            valid_limit = (
                _is_integer(
                    approved_limit
                )
                and 1 <= approved_limit <= 3
            )

            if (
                any(
                    value < 0
                    for value in delivery_values.values()
                )
                or delivery_total < 1
                or (
                    valid_limit
                    and delivery_total > approved_limit
                )
            ):
                reasons.append(
                    "delivery_counts_mismatch"
                )

    if (
        delivery_counts_are_integers
        and audit_counts_are_integers
    ):
        delivered_count = delivery_values[
            "delivered_count"
        ]

        failed_count = delivery_values[
            "failed_count"
        ]

        if (
            audit_values[
                "delivery_attempted_event_count"
            ]
            != delivered_count + failed_count
        ):
            reasons.append(
                "delivery_attempted_event_mismatch"
            )

        if (
            audit_values[
                "delivery_succeeded_event_count"
            ]
            != delivered_count
        ):
            reasons.append(
                "delivery_succeeded_event_mismatch"
            )

        if (
            audit_values[
                "delivery_failed_event_count"
            ]
            != failed_count
        ):
            reasons.append(
                "delivery_failed_event_mismatch"
            )

        if (
            audit_values[
                "sent_timestamp_event_count"
            ]
            != delivered_count
        ):
            reasons.append(
                "sent_timestamp_event_mismatch"
            )

    if not _is_missing(
        record,
        "sent_timestamp_consistent",
    ):
        if record.get(
            "sent_timestamp_consistent"
        ) is not True:
            reasons.append(
                "sent_timestamp_inconsistent"
            )

    if not _is_missing(
        record,
        "duplicate_attempt_clean",
    ):
        if record.get(
            "duplicate_attempt_clean"
        ) is not True:
            reasons.append(
                "duplicate_attempt_detected"
            )

    if record.get(
        "audit_gap_free"
    ) is not True:
        reasons.append(
            "audit_gap_detected"
        )

    return ordered_unique_reason_codes(
        reasons
    )


def collect_privacy_reason_codes(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if record.get(
        "privacy_sanitizer_applied"
    ) is not True:
        reasons.append(
            "privacy_sanitizer_not_applied"
        )

    sensitive_keys = (
        set(
            SUPERVISED_SENSITIVE_FIELDS
        )
        | set(
            EVIDENCE_REVIEW_SENSITIVE_INPUT_KEYS
        )
    )

    if any(
        key in record
        for key in sensitive_keys
    ):
        reasons.append(
            "sensitive_evidence_detected"
        )

    return ordered_unique_reason_codes(
        reasons
    )


def collect_incident_reason_codes(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if not _is_missing(
        record,
        "provider_anomaly",
    ):
        if record.get(
            "provider_anomaly"
        ) is True:
            reasons.append(
                "provider_anomaly_detected"
            )

    if not _is_missing(
        record,
        "incident_state",
    ):
        incident_state = record.get(
            "incident_state"
        )

        if incident_state == "open":
            reasons.append(
                "incident_open"
            )
        elif incident_state not in {
            "closed",
            "escalated",
        }:
            reasons.append(
                "incident_state_invalid"
            )

    failed_count = record.get(
        "failed_count"
    )

    if (
        _is_integer(
            failed_count
        )
        and failed_count > 0
    ):
        reasons.append(
            "failed_delivery_present"
        )

    refused_count = record.get(
        "refused_count"
    )

    if (
        _is_integer(
            refused_count
        )
        and refused_count > 0
    ):
        reasons.append(
            "unexpected_refusal_present"
        )

    return ordered_unique_reason_codes(
        reasons
    )


def collect_policy_reason_codes(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if record.get(
        "automatic_retry_enabled"
    ) is not False:
        reasons.append(
            "automatic_retry_enabled"
        )

    if record.get(
        "automatic_rollout_promotion_enabled"
    ) is not False:
        reasons.append(
            "automatic_rollout_promotion_enabled"
        )

    if record.get(
        "production_delivery_attempted_during_review",
        False,
    ) is True:
        reasons.append(
            "production_delivery_attempted_during_review"
        )

    return ordered_unique_reason_codes(
        reasons
    )


def immutable_evidence_review_snapshot(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        field: record.get(
            field
        )
        for field in EVIDENCE_REVIEW_IMMUTABLE_BINDINGS
    }


def sanitize_evidence_review_record(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        field: record[field]
        for field in EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST
        if field in record
    }


def evaluate_evidence_review(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    completeness_reasons = (
        collect_completeness_reason_codes(
            record
        )
    )

    consistency_reasons = (
        collect_consistency_reason_codes(
            record
        )
    )

    privacy_reasons = (
        collect_privacy_reason_codes(
            record
        )
    )

    incident_reasons = (
        collect_incident_reason_codes(
            record
        )
    )

    policy_reasons = (
        collect_policy_reason_codes(
            record
        )
    )

    all_reasons = ordered_unique_reason_codes(
        [
            *completeness_reasons,
            *consistency_reasons,
            *privacy_reasons,
            *incident_reasons,
            *policy_reasons,
        ]
    )

    if privacy_reasons:
        decision = "privacy_rejected"
    elif incident_reasons:
        decision = "incident_escalated"
    elif completeness_reasons:
        decision = "incomplete"
    elif consistency_reasons:
        decision = "inconsistent"
    elif policy_reasons:
        decision = (
            "not_eligible_for_rollout_consideration"
        )
    else:
        decision = "complete_consistent"

    rollout_recommendation = (
        "eligible_for_manual_consideration"
        if decision == "complete_consistent"
        else "not_eligible"
    )

    computed_record = dict(
        record
    )

    computed_record.update(
        {
            "final_decision": decision,
            "rollout_recommendation": (
                rollout_recommendation
            ),
            "reason_codes": all_reasons,
        }
    )

    sanitized_evidence = (
        sanitize_evidence_review_record(
            computed_record
        )
    )

    return {
        "decision": decision,
        "rollout_recommendation": (
            rollout_recommendation
        ),
        "complete": not completeness_reasons,
        "consistent": not consistency_reasons,
        "privacy_safe": not privacy_reasons,
        "incident_clear": not incident_reasons,
        "policy_compliant": not policy_reasons,
        "reason_codes": all_reasons,
        "sanitized_evidence": sanitized_evidence,
    }


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionEvidenceReviewV263Tests(
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

    def test_v263_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V263_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW,
            (
                "V263_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "EVIDENCE_REVIEW"
            ),
        )

        self.assertEqual(
            len(V262_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V263_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V264_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v264: saved-search notification production delivery "
                "pilot supervised execution evidence review closeout audit"
            ),
        )

    def test_v263_and_v264_scopes_are_documentation_and_test_only(self):
        for scope in (
            V263_ALLOWED_SCOPE,
            V264_PROPOSED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v263_contract_packages_remain_exact(self):
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

    def test_v263_default_record_is_complete_consistent(self):
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

    def test_v263_default_result_decision_is_allowlisted(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record()
        )

        self.assertIn(
            result["decision"],
            EVIDENCE_REVIEW_DECISIONS,
        )

        self.assertIn(
            result["rollout_recommendation"],
            EVIDENCE_REVIEW_ROLLOUT_RECOMMENDATIONS,
        )

    def test_v263_input_decision_and_reason_codes_cannot_spoof_result(self):
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
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["sanitized_evidence"][
                "final_decision"
            ],
            "complete_consistent",
        )

    def test_v263_decision_precedence_is_exact(self):
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

        for record, expected in cases:
            with self.subTest(
                expected=expected
            ):
                self.assertEqual(
                    evaluate_evidence_review(
                        record
                    )["decision"],
                    expected,
                )

    def test_v263_each_reason_code_is_reachable(self):
        cases: tuple[
            tuple[
                dict[str, Any],
                tuple[str, ...],
                str,
            ],
            ...,
        ] = (
            (
                {},
                (
                    "change_record_id",
                ),
                "missing_change_record_id",
            ),
            (
                {},
                (
                    "authorization_id",
                ),
                "missing_authorization_id",
            ),
            (
                {},
                (
                    "pilot_owner_id",
                ),
                "missing_owner_id",
            ),
            (
                {},
                (
                    "approved_limit",
                ),
                "missing_approved_limit",
            ),
            (
                {},
                (
                    "authorization_command_fingerprint",
                ),
                "missing_authorization_command_fingerprint",
            ),
            (
                {},
                (
                    "freeze_fingerprint",
                ),
                "missing_freeze_fingerprint",
            ),
            (
                {},
                (
                    "authorization_consumption_count",
                ),
                "missing_authorization_consumption_count",
            ),
            (
                {},
                (
                    "production_invocation_count",
                ),
                "missing_production_invocation_count",
            ),
            (
                {},
                (
                    "delivered_count",
                ),
                "missing_delivery_outcome_counts",
            ),
            (
                {},
                (
                    "delivery_attempted_event_count",
                ),
                "missing_persistent_audit_counts",
            ),
            (
                {},
                (
                    "sent_timestamp_consistent",
                ),
                "missing_sent_timestamp_consistency",
            ),
            (
                {},
                (
                    "duplicate_attempt_clean",
                ),
                "missing_duplicate_attempt_status",
            ),
            (
                {},
                (
                    "provider_anomaly",
                ),
                "missing_provider_anomaly_status",
            ),
            (
                {},
                (
                    "incident_state",
                ),
                "missing_incident_state",
            ),
            (
                {},
                (
                    "reviewer_identity",
                ),
                "missing_reviewer_identity",
            ),
            (
                {},
                (
                    "review_completed_at_utc",
                ),
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
                    "incident_state": "unknown",
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

        self.assertEqual(
            len(cases),
            len(EVIDENCE_REVIEW_REASON_ORDER),
        )

        reached: set[str] = set()

        for changes, remove_fields, reason in cases:
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

    def test_v263_reason_order_is_deterministic(self):
        record = (
            build_complete_evidence_review_record(
                change_record_id="",
                pilot_owner_id=0,
                approved_limit=4,
                authorization_consumption_count=0,
                production_invocation_count=2,
                delivered_count=5,
                delivery_attempted_event_count=0,
                delivery_succeeded_event_count=0,
                delivery_failed_event_count=1,
                sent_timestamp_event_count=0,
                sent_timestamp_consistent=False,
                duplicate_attempt_clean=False,
                audit_gap_free=False,
                privacy_sanitizer_applied=False,
                smtp_password="secret",
                provider_anomaly=True,
                incident_state="open",
                failed_count=1,
                refused_count=1,
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

    def test_v263_completeness_reason_package_is_preserved(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES),
            16,
        )

        result = evaluate_evidence_review(
            {
                "privacy_sanitizer_applied": True,
                "automatic_retry_enabled": False,
                "automatic_rollout_promotion_enabled": False,
            }
        )

        self.assertEqual(
            result["decision"],
            "incomplete",
        )

        self.assertTrue(
            set(
                EVIDENCE_REVIEW_COMPLETENESS_REASON_CODES
            ).issubset(
                set(
                    result["reason_codes"]
                )
            )
        )

    def test_v263_consistency_reason_package_is_preserved(self):
        self.assertEqual(
            len(EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES),
            12,
        )

        self.assertIn(
            "authorization_consumption_count_mismatch",
            EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES,
        )

        self.assertIn(
            "audit_gap_detected",
            EVIDENCE_REVIEW_CONSISTENCY_REASON_CODES,
        )

    def test_v263_privacy_rejection_removes_sensitive_values(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                smtp_password="secret-value",
                recipient_email="private@example.invalid",
                rendered_body="private-body",
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

        self.assertNotIn(
            "secret-value",
            rendered,
        )

        self.assertNotIn(
            "private@example.invalid",
            rendered,
        )

        self.assertNotIn(
            "private-body",
            rendered,
        )

        self.assertNotIn(
            "smtp_password",
            result["sanitized_evidence"],
        )

    def test_v263_privacy_sanitizer_missing_is_rejected(self):
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

    def test_v263_provider_anomaly_requires_escalation(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                provider_anomaly=True,
                incident_reference="incident-001",
            )
        )

        self.assertEqual(
            result["decision"],
            "incident_escalated",
        )

        self.assertIn(
            "provider_anomaly_detected",
            result["reason_codes"],
        )

        self.assertEqual(
            result["sanitized_evidence"][
                "incident_reference"
            ],
            "incident-001",
        )

    def test_v263_open_incident_requires_escalation(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                incident_state="open",
            )
        )

        self.assertEqual(
            result["decision"],
            "incident_escalated",
        )

        self.assertIn(
            "incident_open",
            result["reason_codes"],
        )

    def test_v263_failed_delivery_requires_escalation(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                delivered_count=1,
                failed_count=1,
                delivery_attempted_event_count=2,
                delivery_succeeded_event_count=1,
                delivery_failed_event_count=1,
                sent_timestamp_event_count=1,
            )
        )

        self.assertEqual(
            result["decision"],
            "incident_escalated",
        )

        self.assertIn(
            "failed_delivery_present",
            result["reason_codes"],
        )

    def test_v263_unexpected_refusal_requires_escalation(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                delivered_count=1,
                refused_count=1,
                delivery_attempted_event_count=1,
                delivery_succeeded_event_count=1,
                sent_timestamp_event_count=1,
            )
        )

        self.assertEqual(
            result["decision"],
            "incident_escalated",
        )

        self.assertIn(
            "unexpected_refusal_present",
            result["reason_codes"],
        )

    def test_v263_automatic_retry_is_not_eligible(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                automatic_retry_enabled=True,
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

    def test_v263_automatic_promotion_is_not_eligible(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                automatic_rollout_promotion_enabled=True,
            )
        )

        self.assertEqual(
            result["decision"],
            (
                "not_eligible_for_"
                "rollout_consideration"
            ),
        )

        self.assertIn(
            "automatic_rollout_promotion_enabled",
            result["reason_codes"],
        )

    def test_v263_delivery_attempt_during_review_is_not_eligible(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record(
                production_delivery_attempted_during_review=True,
            )
        )

        self.assertEqual(
            result["decision"],
            (
                "not_eligible_for_"
                "rollout_consideration"
            ),
        )

        self.assertIn(
            "production_delivery_attempted_during_review",
            result["reason_codes"],
        )

        self.assertNotIn(
            "production_delivery_attempted_during_review",
            result["sanitized_evidence"],
        )

    def test_v263_unknown_fields_are_discarded(self):
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

    def test_v263_sanitized_evidence_uses_contract_allowlist(self):
        result = evaluate_evidence_review(
            build_complete_evidence_review_record()
        )

        self.assertTrue(
            set(
                result["sanitized_evidence"]
            ).issubset(
                set(
                    EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST
                )
            )
        )

        self.assertEqual(
            tuple(
                result["sanitized_evidence"]
            ),
            tuple(
                field
                for field in EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST
                if field
                in result["sanitized_evidence"]
            ),
        )

    def test_v263_allowlist_excludes_all_sensitive_keys(self):
        sensitive_keys = (
            set(
                SUPERVISED_SENSITIVE_FIELDS
            )
            | set(
                EVIDENCE_REVIEW_SENSITIVE_INPUT_KEYS
            )
        )

        self.assertTrue(
            set(
                EVIDENCE_REVIEW_EVIDENCE_ALLOWLIST
            ).isdisjoint(
                sensitive_keys
            )
        )

    def test_v263_immutable_snapshot_is_exact_and_deterministic(self):
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

    def test_v263_owner_and_limit_boundaries_are_fail_closed(self):
        for owner_id, limit, decision in (
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
        ):
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
                    decision,
                )

    def test_v263_delivery_counts_must_fit_approved_limit(self):
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

    def test_v263_audit_counts_must_reconcile(self):
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

        self.assertIn(
            "delivery_attempted_event_mismatch",
            result["reason_codes"],
        )

        self.assertIn(
            "delivery_succeeded_event_mismatch",
            result["reason_codes"],
        )

        self.assertIn(
            "delivery_failed_event_mismatch",
            result["reason_codes"],
        )

        self.assertIn(
            "sent_timestamp_event_mismatch",
            result["reason_codes"],
        )

    def test_v263_review_functions_perform_no_external_actions(self):
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

    def test_v263_required_review_roles_remain_exact(self):
        self.assertEqual(
            EVIDENCE_REVIEW_REQUIRED_REVIEW_ROLES,
            (
                "evidence_reviewer",
                "privacy_reviewer",
                "incident_reviewer",
            ),
        )

    def test_v263_reconciliation_rules_remain_complete(self):
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
                set(
                    EVIDENCE_REVIEW_RECONCILIATION_RULES
                )
            )
        )

    def test_v263_privacy_and_prohibition_packages_remain_complete(self):
        self.assertIn(
            "SMTP password",
            EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "raw exception traceback",
            EVIDENCE_REVIEW_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "production delivery during evidence-review checkpoint",
            EVIDENCE_REVIEW_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "authorization consumption during evidence review",
            EVIDENCE_REVIEW_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "delivery retry during evidence review",
            EVIDENCE_REVIEW_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "automatic rollout promotion",
            EVIDENCE_REVIEW_PROHIBITED_ACTIONS,
        )

    def test_v263_v262_acceptance_gates_remain_packaged(self):
        required = {
            "decision precedence is deterministic",
            "all reason codes are unique",
            "authorization consumption count must equal one",
            "production invocation count must equal one",
            "delivery outcome counts must reconcile",
            "persistent audit counts must reconcile",
            "privacy sanitizer remains mandatory",
            "sensitive evidence triggers privacy rejection",
            "automatic retry remains prohibited",
            "automatic rollout promotion remains prohibited",
            "evidence review performs no production delivery",
            "evidence review consumes no authorization",
            "evidence review performs no retry",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(
                    V262_ACCEPTANCE_GATES
                )
            )
        )

    def test_v263_default_readiness_remains_not_ready(self):
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
    def test_v263_production_like_readiness_remains_ready(self):
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
    def test_v263_readiness_execution_opens_no_email_connection(self):
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

    def test_v263_command_surfaces_remain_unchanged(self):
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

    def test_v263_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v263_scheduler_remains_nonautomatic(self):
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

    def test_v263_v262_contract_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_evidence_review_contract_v262.py"
        )

        self.assertIn(
            (
                "V262_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "EVIDENCE_REVIEW_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v263: saved-search notification production delivery "
                "pilot supervised execution evidence review implementation"
            ),
            source,
        )

    def test_v263_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V263_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_EVIDENCE_REVIEW
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

    def test_v263_no_migration_0017_exists(self):
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

    def test_v263_implementation_gate_matrix_is_complete(self):
        required = {
            "v262 evidence-review contract remains packaged",
            "v263 scope remains exactly two implementation files",
            "v264 closeout scope remains exactly two files",
            "implementation remains documentation and test only",
            "all thirty-eight reason codes remain reachable",
            "reason-code order remains deterministic",
            "privacy rejection has highest precedence",
            "complete-consistent permits manual consideration only",
            "sensitive values never appear in results",
            "unknown fields are discarded",
            "authorization consumption count must equal one",
            "production invocation count must equal one",
            "delivery outcome total must be between one and approved limit",
            "persistent audit must have no gaps",
            "provider anomaly causes escalation",
            "automatic retry causes policy ineligibility",
            "automatic rollout promotion causes policy ineligibility",
            "authorization is not consumed during review",
            "delivery is not retried during review",
            "production command is not invoked during review",
            "email connection is not opened during review",
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
                set(
                    V263_IMPLEMENTATION_GATES
                )
            )
        )
