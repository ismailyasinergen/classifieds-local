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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_contract_v265 import (
    MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES,
    MANUAL_ROLLOUT_CONSIDERATION_LIFETIME_SECONDS,
    MANUAL_ROLLOUT_DECISIONS,
    MANUAL_ROLLOUT_DECISION_PRECEDENCE,
    MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST,
    MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS,
    MANUAL_ROLLOUT_IMMUTABLE_BINDINGS,
    MANUAL_ROLLOUT_MAX_LIMIT,
    MANUAL_ROLLOUT_MAX_OWNER_COUNT,
    MANUAL_ROLLOUT_PREVIEW_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS,
    MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES,
    MANUAL_ROLLOUT_PROHIBITED_ACTIONS,
    MANUAL_ROLLOUT_READINESS_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_REASON_ORDER,
    MANUAL_ROLLOUT_REQUIRED_FIELDS,
    MANUAL_ROLLOUT_REQUIRED_ROLES,
    MANUAL_ROLLOUT_ROLE_SEPARATION_RULES,
    MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES,
    MANUAL_ROLLOUT_SENSITIVE_INPUT_KEYS,
    MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES,
    V265_ACCEPTANCE_GATES,
)


V266_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION = (
    "V266_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION"
)

V265_COMMITTED_SCOPE = (
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

V266_ALLOWED_SCOPE = (
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

V267_PROPOSED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_closeout_audit_v267.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_closeout_audit_v267.md"
    ),
)

MANUAL_ROLLOUT_RESULT_FIELDS = (
    "decision",
    "eligible",
    "reason_codes",
    "sanitized_evidence",
    "immutable_snapshot",
    "future_authorization_requirements",
)

MANUAL_ROLLOUT_REVIEWER_FIELDS = (
    "evidence_reviewer_identity",
    "privacy_reviewer_identity",
    "incident_reviewer_identity",
    "rollback_reviewer_identity",
    "incident_commander_identity",
)

MANUAL_ROLLOUT_PAIRWISE_REVIEWER_FIELDS = (
    "evidence_reviewer_identity",
    "privacy_reviewer_identity",
    "incident_reviewer_identity",
    "rollback_reviewer_identity",
)

MANUAL_ROLLOUT_SOURCE_DELIVERY_COUNT_FIELDS = (
    "source_delivered_count",
    "source_skipped_count",
    "source_refused_count",
    "source_failed_count",
)

V266_IMPLEMENTATION_GATES = (
    "v265 manual-rollout consideration contract remains packaged",
    "v265 committed scope remains exactly two files",
    "v266 scope remains exactly two implementation files",
    "v267 proposed scope remains exactly two files",
    "v267 remains documentation and test only",
    "implementation remains documentation and test only",
    "required fields remain exactly forty-seven",
    "two decisions remain exact",
    "not-eligible remains fail-closed precedence",
    "forty-eight reason codes remain explicit",
    "forty-eight reason codes remain unique",
    "all forty-eight reason codes remain reachable",
    "reason ordering remains deterministic",
    "completeness reasons remain deterministic",
    "source-eligibility reasons remain deterministic",
    "scope role and freshness reasons remain deterministic",
    "prohibited-action reasons remain deterministic",
    "source decision must be complete-consistent",
    "source recommendation must permit manual consideration",
    "source reasons must be empty",
    "source complete flag must be true",
    "source consistent flag must be true",
    "source privacy-safe flag must be true",
    "source incident-clear flag must be true",
    "source policy-compliant flag must be true",
    "source authorization consumption count must equal one",
    "source production invocation count must equal one",
    "source delivery counts must reconcile",
    "source failed count must remain zero",
    "source refused count must remain zero",
    "source audit must be gap-free",
    "source duplicate-attempt review must be clean",
    "source provider anomaly must be absent",
    "source incident state must be closed",
    "source privacy sanitizer must be applied",
    "source automatic retry must remain disabled",
    "source automatic rollout promotion must remain disabled",
    "source owner identifier must be positive",
    "source approved limit must be between one and three",
    "considered owner scope must contain exactly one owner",
    "considered owner scope must match source owner",
    "considered limit must be between one and three",
    "considered limit cannot exceed source approved limit",
    "decision owner must differ from every required reviewer role",
    "evidence privacy incident and rollback reviewers must be pairwise distinct",
    "readiness freshness boundary remains inclusive",
    "preview freshness boundary remains inclusive",
    "consideration lifetime boundary remains inclusive",
    "changed readiness fingerprint fails closed",
    "changed preview fingerprint fails closed",
    "expired consideration fails closed",
    "future authorization requirement remains mandatory",
    "eligible result permits future-authorization preparation only",
    "eligible result does not create an authorization identifier",
    "eligible result does not produce a production command",
    "eligible result does not reuse source authorization",
    "eligible result does not consume authorization",
    "eligible result does not perform retry",
    "eligible result does not enable scheduler",
    "eligible result does not perform automatic promotion",
    "production delivery during consideration fails closed",
    "authorization consumption during consideration fails closed",
    "retry during consideration fails closed",
    "scheduler enablement during consideration fails closed",
    "automatic promotion during consideration fails closed",
    "input decision cannot spoof computed result",
    "input reason codes cannot spoof computed result",
    "strict evidence allowlist remains enforced",
    "unknown evidence fields are discarded",
    "sensitive evidence fields are discarded",
    "sensitive values do not appear in results",
    "immutable snapshot remains exact",
    "immutable snapshot remains deterministic",
    "evaluator remains pure and in-memory",
    "evaluator invokes no subprocess",
    "evaluator invokes no management command",
    "evaluator opens no email connection",
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

NEXT_CHECKPOINT = "v267: saved-search notification production delivery pilot supervised execution manual rollout consideration closeout audit"

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
        "pilot_supervised_execution_manual_rollout_consideration_contract_v265.py"
    ),
)


@dataclass(frozen=True)
class ManualRolloutConsiderationRecord:
    consideration_id: str = "consideration-001"
    source_change_record_id: str = "change-001"
    source_authorization_id: str = "authorization-001"
    source_owner_id: int = 101
    source_approved_limit: int = 3
    source_authorization_command_fingerprint: str = (
        "source-command-fingerprint-001"
    )
    source_freeze_fingerprint: str = (
        "source-freeze-fingerprint-001"
    )
    source_evidence_decision: str = "complete_consistent"
    source_rollout_recommendation: str = (
        "eligible_for_manual_consideration"
    )
    source_reason_codes: tuple[str, ...] = ()
    source_complete: bool = True
    source_consistent: bool = True
    source_privacy_safe: bool = True
    source_incident_clear: bool = True
    source_policy_compliant: bool = True
    source_authorization_consumption_count: int = 1
    source_production_invocation_count: int = 1
    source_delivered_count: int = 2
    source_skipped_count: int = 0
    source_refused_count: int = 0
    source_failed_count: int = 0
    source_audit_gap_free: bool = True
    source_duplicate_attempt_clean: bool = True
    source_provider_anomaly: bool = False
    source_incident_state: str = "closed"
    source_privacy_sanitizer_applied: bool = True
    source_automatic_retry_enabled: bool = False
    source_automatic_rollout_promotion_enabled: bool = False
    decision_owner_identity: str = "decision-owner-a"
    evidence_reviewer_identity: str = "evidence-reviewer-a"
    privacy_reviewer_identity: str = "privacy-reviewer-a"
    incident_reviewer_identity: str = "incident-reviewer-a"
    rollback_reviewer_identity: str = "rollback-reviewer-a"
    incident_commander_identity: str = "incident-commander-a"
    considered_owner_ids: tuple[int, ...] = (101,)
    considered_limit: int = 3
    readiness_evidence_fingerprint: str = (
        "readiness-fingerprint-001"
    )
    preview_evidence_fingerprint: str = (
        "preview-fingerprint-001"
    )
    consideration_completed_at_utc: int = 1200
    final_decision: str = "pending"
    reason_codes: tuple[str, ...] = ()
    future_authorization_required: bool = True
    production_delivery_performed: bool = False
    authorization_consumed: bool = False
    retry_performed: bool = False
    scheduler_enabled: bool = False
    automatic_promotion_performed: bool = False


@dataclass(frozen=True)
class ManualRolloutEvaluationContext:
    current_timestamp_utc: int = 1200
    readiness_generated_at_utc: int = 900
    preview_generated_at_utc: int = 900
    consideration_started_at_utc: int = 300
    expected_readiness_evidence_fingerprint: str = (
        "readiness-fingerprint-001"
    )
    expected_preview_evidence_fingerprint: str = (
        "preview-fingerprint-001"
    )


def build_complete_manual_rollout_consideration(
    **changes: Any,
) -> dict[str, Any]:
    record = asdict(
        ManualRolloutConsiderationRecord()
    )

    record.update(
        changes
    )

    return record


def build_manual_rollout_evaluation_context(
    **changes: Any,
) -> ManualRolloutEvaluationContext:
    values = asdict(
        ManualRolloutEvaluationContext()
    )

    values.update(
        changes
    )

    return ManualRolloutEvaluationContext(
        **values
    )


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


def _is_fresh(
    *,
    current_timestamp_utc: int,
    generated_at_utc: int,
    maximum_age_seconds: int,
) -> bool:
    if not all(
        _is_integer(value)
        for value in (
            current_timestamp_utc,
            generated_at_utc,
            maximum_age_seconds,
        )
    ):
        return False

    age = (
        current_timestamp_utc
        - generated_at_utc
    )

    return (
        0
        <= age
        <= maximum_age_seconds
    )


def ordered_unique_manual_rollout_reasons(
    reasons: list[str],
) -> tuple[str, ...]:
    seen: set[str] = set()
    unique: list[str] = []

    for reason in reasons:
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
            MANUAL_ROLLOUT_REASON_ORDER
        )
    }

    return tuple(
        sorted(
            unique,
            key=order.__getitem__,
        )
    )


def collect_manual_rollout_completeness_reasons(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    scalar_fields = (
        (
            "consideration_id",
            "missing_consideration_id",
        ),
        (
            "source_change_record_id",
            "missing_source_change_record_id",
        ),
        (
            "source_authorization_id",
            "missing_source_authorization_id",
        ),
        (
            "source_owner_id",
            "missing_source_owner_id",
        ),
        (
            "source_approved_limit",
            "missing_source_approved_limit",
        ),
        (
            "source_authorization_command_fingerprint",
            "missing_source_authorization_command_fingerprint",
        ),
        (
            "source_freeze_fingerprint",
            "missing_source_freeze_fingerprint",
        ),
        (
            "decision_owner_identity",
            "missing_decision_owner_identity",
        ),
        (
            "considered_owner_ids",
            "missing_considered_owner_ids",
        ),
        (
            "considered_limit",
            "missing_considered_limit",
        ),
        (
            "readiness_evidence_fingerprint",
            "missing_readiness_evidence_fingerprint",
        ),
        (
            "preview_evidence_fingerprint",
            "missing_preview_evidence_fingerprint",
        ),
        (
            "consideration_completed_at_utc",
            "missing_consideration_timestamp",
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
        for field in MANUAL_ROLLOUT_REVIEWER_FIELDS
    ):
        reasons.append(
            "missing_required_reviewer_identity"
        )

    return ordered_unique_manual_rollout_reasons(
        reasons
    )


def collect_manual_rollout_source_eligibility_reasons(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if (
        record.get(
            "source_evidence_decision"
        )
        != "complete_consistent"
    ):
        reasons.append(
            "source_decision_not_complete_consistent"
        )

    if (
        record.get(
            "source_rollout_recommendation"
        )
        != "eligible_for_manual_consideration"
    ):
        reasons.append(
            "source_rollout_recommendation_not_manual_consideration"
        )

    source_reason_codes = record.get(
        "source_reason_codes"
    )

    if (
        source_reason_codes is None
        or bool(source_reason_codes)
    ):
        reasons.append(
            "source_reason_codes_nonempty"
        )

    flag_rules = (
        (
            "source_complete",
            "source_not_complete",
        ),
        (
            "source_consistent",
            "source_not_consistent",
        ),
        (
            "source_privacy_safe",
            "source_not_privacy_safe",
        ),
        (
            "source_incident_clear",
            "source_incident_not_clear",
        ),
        (
            "source_policy_compliant",
            "source_not_policy_compliant",
        ),
    )

    for field, reason in flag_rules:
        if record.get(field) is not True:
            reasons.append(
                reason
            )

    if (
        record.get(
            "source_authorization_consumption_count"
        )
        != 1
    ):
        reasons.append(
            "source_authorization_consumption_count_mismatch"
        )

    if (
        record.get(
            "source_production_invocation_count"
        )
        != 1
    ):
        reasons.append(
            "source_production_invocation_count_mismatch"
        )

    delivery_values = {
        field: record.get(field)
        for field in MANUAL_ROLLOUT_SOURCE_DELIVERY_COUNT_FIELDS
    }

    delivery_valid = all(
        _is_integer(value)
        and value >= 0
        for value in delivery_values.values()
    )

    source_limit = record.get(
        "source_approved_limit"
    )

    source_limit_valid = (
        _is_integer(source_limit)
        and 1
        <= source_limit
        <= MANUAL_ROLLOUT_MAX_LIMIT
    )

    if delivery_valid:
        total = sum(
            delivery_values.values()
        )

        delivery_valid = (
            total >= 1
            and (
                not source_limit_valid
                or total <= source_limit
            )
            and delivery_values[
                "source_refused_count"
            ] == 0
            and delivery_values[
                "source_failed_count"
            ] == 0
        )

    if not delivery_valid:
        reasons.append(
            "source_delivery_counts_not_reconciled"
        )

    if record.get(
        "source_audit_gap_free"
    ) is not True:
        reasons.append(
            "source_audit_not_gap_free"
        )

    if record.get(
        "source_duplicate_attempt_clean"
    ) is not True:
        reasons.append(
            "source_duplicate_attempt_not_clean"
        )

    if record.get(
        "source_provider_anomaly"
    ) is not False:
        reasons.append(
            "source_provider_anomaly_present"
        )

    if record.get(
        "source_incident_state"
    ) != "closed":
        reasons.append(
            "source_incident_state_not_closed"
        )

    if record.get(
        "source_privacy_sanitizer_applied"
    ) is not True:
        reasons.append(
            "source_privacy_sanitizer_not_applied"
        )

    if record.get(
        "source_automatic_retry_enabled"
    ) is not False:
        reasons.append(
            "source_automatic_retry_enabled"
        )

    if record.get(
        "source_automatic_rollout_promotion_enabled"
    ) is not False:
        reasons.append(
            "source_automatic_rollout_promotion_enabled"
        )

    return ordered_unique_manual_rollout_reasons(
        reasons
    )


def collect_manual_rollout_scope_role_reasons(
    record: Mapping[str, Any],
    context: ManualRolloutEvaluationContext,
) -> tuple[str, ...]:
    reasons: list[str] = []

    source_owner_id = record.get(
        "source_owner_id"
    )

    if (
        not _is_missing(
            record,
            "source_owner_id",
        )
        and (
            not _is_integer(source_owner_id)
            or source_owner_id <= 0
        )
    ):
        reasons.append(
            "invalid_source_owner_id"
        )

    source_limit = record.get(
        "source_approved_limit"
    )

    source_limit_valid = (
        _is_integer(source_limit)
        and 1
        <= source_limit
        <= MANUAL_ROLLOUT_MAX_LIMIT
    )

    if (
        not _is_missing(
            record,
            "source_approved_limit",
        )
        and not source_limit_valid
    ):
        reasons.append(
            "invalid_source_approved_limit"
        )

    if not _is_missing(
        record,
        "considered_owner_ids",
    ):
        considered_owner_ids = record.get(
            "considered_owner_ids"
        )

        valid_sequence = (
            isinstance(
                considered_owner_ids,
                (tuple, list),
            )
            and all(
                _is_integer(owner_id)
                and owner_id > 0
                for owner_id in considered_owner_ids
            )
        )

        if (
            not valid_sequence
            or len(considered_owner_ids) == 0
        ):
            reasons.append(
                "considered_owner_scope_empty"
            )
        elif (
            len(considered_owner_ids)
            != MANUAL_ROLLOUT_MAX_OWNER_COUNT
            or considered_owner_ids[0]
            != source_owner_id
        ):
            reasons.append(
                "considered_owner_scope_expanded"
            )

    considered_limit = record.get(
        "considered_limit"
    )

    considered_limit_valid = (
        _is_integer(considered_limit)
        and 1
        <= considered_limit
        <= MANUAL_ROLLOUT_MAX_LIMIT
    )

    if (
        not _is_missing(
            record,
            "considered_limit",
        )
        and not considered_limit_valid
    ):
        reasons.append(
            "considered_limit_invalid"
        )

    if (
        considered_limit_valid
        and source_limit_valid
        and considered_limit > source_limit
    ):
        reasons.append(
            "considered_limit_expanded"
        )

    decision_owner = record.get(
        "decision_owner_identity"
    )

    reviewer_values = [
        record.get(field)
        for field in MANUAL_ROLLOUT_REVIEWER_FIELDS
        if not _is_missing(
            record,
            field,
        )
    ]

    if (
        not _is_missing(
            record,
            "decision_owner_identity",
        )
        and decision_owner in reviewer_values
    ):
        reasons.append(
            "decision_owner_role_overlap"
        )

    pairwise_values = [
        record.get(field)
        for field in MANUAL_ROLLOUT_PAIRWISE_REVIEWER_FIELDS
        if not _is_missing(
            record,
            field,
        )
    ]

    if (
        len(pairwise_values)
        != len(set(pairwise_values))
    ):
        reasons.append(
            "required_reviewer_identity_not_distinct"
        )

    consideration_lifetime_valid = _is_fresh(
        current_timestamp_utc=(
            context.current_timestamp_utc
        ),
        generated_at_utc=(
            context.consideration_started_at_utc
        ),
        maximum_age_seconds=(
            MANUAL_ROLLOUT_CONSIDERATION_LIFETIME_SECONDS
        ),
    )

    readiness_fresh = _is_fresh(
        current_timestamp_utc=(
            context.current_timestamp_utc
        ),
        generated_at_utc=(
            context.readiness_generated_at_utc
        ),
        maximum_age_seconds=(
            MANUAL_ROLLOUT_READINESS_FRESHNESS_SECONDS
        ),
    )

    readiness_matches = (
        record.get(
            "readiness_evidence_fingerprint"
        )
        == context.expected_readiness_evidence_fingerprint
    )

    if (
        not readiness_fresh
        or not readiness_matches
        or not consideration_lifetime_valid
    ):
        reasons.append(
            "readiness_evidence_stale_or_changed"
        )

    preview_fresh = _is_fresh(
        current_timestamp_utc=(
            context.current_timestamp_utc
        ),
        generated_at_utc=(
            context.preview_generated_at_utc
        ),
        maximum_age_seconds=(
            MANUAL_ROLLOUT_PREVIEW_FRESHNESS_SECONDS
        ),
    )

    preview_matches = (
        record.get(
            "preview_evidence_fingerprint"
        )
        == context.expected_preview_evidence_fingerprint
    )

    if (
        not preview_fresh
        or not preview_matches
        or not consideration_lifetime_valid
    ):
        reasons.append(
            "preview_evidence_stale_or_changed"
        )

    if record.get(
        "future_authorization_required"
    ) is not True:
        reasons.append(
            "future_authorization_not_required"
        )

    return ordered_unique_manual_rollout_reasons(
        reasons
    )


def collect_manual_rollout_prohibited_action_reasons(
    record: Mapping[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    rules = (
        (
            "production_delivery_performed",
            "production_delivery_performed_during_consideration",
        ),
        (
            "authorization_consumed",
            "authorization_consumed_during_consideration",
        ),
        (
            "retry_performed",
            "retry_performed_during_consideration",
        ),
        (
            "scheduler_enabled",
            "scheduler_enabled_during_consideration",
        ),
        (
            "automatic_promotion_performed",
            "automatic_promotion_performed_during_consideration",
        ),
    )

    for field, reason in rules:
        if record.get(field) is not False:
            reasons.append(
                reason
            )

    return ordered_unique_manual_rollout_reasons(
        reasons
    )


def manual_rollout_immutable_snapshot(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        field: record.get(field)
        for field in MANUAL_ROLLOUT_IMMUTABLE_BINDINGS
    }


def sanitize_manual_rollout_evidence(
    record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        field: record[field]
        for field in MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST
        if field in record
    }


def evaluate_manual_rollout_consideration(
    record: Mapping[str, Any],
    *,
    context: ManualRolloutEvaluationContext | None = None,
) -> dict[str, Any]:
    resolved_context = (
        context
        if context is not None
        else ManualRolloutEvaluationContext()
    )

    completeness_reasons = (
        collect_manual_rollout_completeness_reasons(
            record
        )
    )

    source_reasons = (
        collect_manual_rollout_source_eligibility_reasons(
            record
        )
    )

    scope_role_reasons = (
        collect_manual_rollout_scope_role_reasons(
            record,
            resolved_context,
        )
    )

    prohibited_action_reasons = (
        collect_manual_rollout_prohibited_action_reasons(
            record
        )
    )

    reasons = ordered_unique_manual_rollout_reasons(
        [
            *completeness_reasons,
            *source_reasons,
            *scope_role_reasons,
            *prohibited_action_reasons,
        ]
    )

    decision = (
        "not_eligible"
        if reasons
        else "eligible_to_prepare_future_authorization"
    )

    computed_record = dict(
        record
    )

    computed_record.update(
        {
            "final_decision": decision,
            "reason_codes": reasons,
        }
    )

    sanitized_evidence = (
        sanitize_manual_rollout_evidence(
            computed_record
        )
    )

    eligible = (
        decision
        == "eligible_to_prepare_future_authorization"
    )

    return {
        "decision": decision,
        "eligible": eligible,
        "reason_codes": reasons,
        "sanitized_evidence": sanitized_evidence,
        "immutable_snapshot": (
            manual_rollout_immutable_snapshot(
                computed_record
            )
        ),
        "future_authorization_requirements": (
            MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS
            if eligible
            else ()
        ),
    }


V266_REASON_REACHABILITY_CASES = (
    (
        {},
        ("consideration_id",),
        {},
        "missing_consideration_id",
    ),
    (
        {},
        ("source_change_record_id",),
        {},
        "missing_source_change_record_id",
    ),
    (
        {},
        ("source_authorization_id",),
        {},
        "missing_source_authorization_id",
    ),
    (
        {},
        ("source_owner_id",),
        {},
        "missing_source_owner_id",
    ),
    (
        {},
        ("source_approved_limit",),
        {},
        "missing_source_approved_limit",
    ),
    (
        {},
        ("source_authorization_command_fingerprint",),
        {},
        "missing_source_authorization_command_fingerprint",
    ),
    (
        {},
        ("source_freeze_fingerprint",),
        {},
        "missing_source_freeze_fingerprint",
    ),
    (
        {},
        ("decision_owner_identity",),
        {},
        "missing_decision_owner_identity",
    ),
    (
        {},
        ("evidence_reviewer_identity",),
        {},
        "missing_required_reviewer_identity",
    ),
    (
        {},
        ("considered_owner_ids",),
        {},
        "missing_considered_owner_ids",
    ),
    (
        {},
        ("considered_limit",),
        {},
        "missing_considered_limit",
    ),
    (
        {},
        ("readiness_evidence_fingerprint",),
        {},
        "missing_readiness_evidence_fingerprint",
    ),
    (
        {},
        ("preview_evidence_fingerprint",),
        {},
        "missing_preview_evidence_fingerprint",
    ),
    (
        {},
        ("consideration_completed_at_utc",),
        {},
        "missing_consideration_timestamp",
    ),
    (
        {
            "source_evidence_decision": "incomplete",
        },
        (),
        {},
        "source_decision_not_complete_consistent",
    ),
    (
        {
            "source_rollout_recommendation": "not_eligible",
        },
        (),
        {},
        "source_rollout_recommendation_not_manual_consideration",
    ),
    (
        {
            "source_reason_codes": (
                "source-error",
            ),
        },
        (),
        {},
        "source_reason_codes_nonempty",
    ),
    (
        {
            "source_complete": False,
        },
        (),
        {},
        "source_not_complete",
    ),
    (
        {
            "source_consistent": False,
        },
        (),
        {},
        "source_not_consistent",
    ),
    (
        {
            "source_privacy_safe": False,
        },
        (),
        {},
        "source_not_privacy_safe",
    ),
    (
        {
            "source_incident_clear": False,
        },
        (),
        {},
        "source_incident_not_clear",
    ),
    (
        {
            "source_policy_compliant": False,
        },
        (),
        {},
        "source_not_policy_compliant",
    ),
    (
        {
            "source_authorization_consumption_count": 0,
        },
        (),
        {},
        "source_authorization_consumption_count_mismatch",
    ),
    (
        {
            "source_production_invocation_count": 2,
        },
        (),
        {},
        "source_production_invocation_count_mismatch",
    ),
    (
        {
            "source_delivered_count": 4,
        },
        (),
        {},
        "source_delivery_counts_not_reconciled",
    ),
    (
        {
            "source_audit_gap_free": False,
        },
        (),
        {},
        "source_audit_not_gap_free",
    ),
    (
        {
            "source_duplicate_attempt_clean": False,
        },
        (),
        {},
        "source_duplicate_attempt_not_clean",
    ),
    (
        {
            "source_provider_anomaly": True,
        },
        (),
        {},
        "source_provider_anomaly_present",
    ),
    (
        {
            "source_incident_state": "open",
        },
        (),
        {},
        "source_incident_state_not_closed",
    ),
    (
        {
            "source_privacy_sanitizer_applied": False,
        },
        (),
        {},
        "source_privacy_sanitizer_not_applied",
    ),
    (
        {
            "source_automatic_retry_enabled": True,
        },
        (),
        {},
        "source_automatic_retry_enabled",
    ),
    (
        {
            "source_automatic_rollout_promotion_enabled": True,
        },
        (),
        {},
        "source_automatic_rollout_promotion_enabled",
    ),
    (
        {
            "source_owner_id": 0,
        },
        (),
        {},
        "invalid_source_owner_id",
    ),
    (
        {
            "source_approved_limit": 4,
        },
        (),
        {},
        "invalid_source_approved_limit",
    ),
    (
        {
            "considered_owner_ids": (),
        },
        (),
        {},
        "considered_owner_scope_empty",
    ),
    (
        {
            "considered_owner_ids": (
                101,
                202,
            ),
        },
        (),
        {},
        "considered_owner_scope_expanded",
    ),
    (
        {
            "considered_limit": 0,
        },
        (),
        {},
        "considered_limit_invalid",
    ),
    (
        {
            "source_approved_limit": 2,
            "considered_limit": 3,
            "source_delivered_count": 2,
        },
        (),
        {},
        "considered_limit_expanded",
    ),
    (
        {
            "decision_owner_identity": (
                "evidence-reviewer-a"
            ),
        },
        (),
        {},
        "decision_owner_role_overlap",
    ),
    (
        {
            "privacy_reviewer_identity": (
                "evidence-reviewer-a"
            ),
        },
        (),
        {},
        "required_reviewer_identity_not_distinct",
    ),
    (
        {},
        (),
        {
            "readiness_generated_at_utc": 899,
        },
        "readiness_evidence_stale_or_changed",
    ),
    (
        {},
        (),
        {
            "preview_generated_at_utc": 899,
        },
        "preview_evidence_stale_or_changed",
    ),
    (
        {
            "future_authorization_required": False,
        },
        (),
        {},
        "future_authorization_not_required",
    ),
    (
        {
            "production_delivery_performed": True,
        },
        (),
        {},
        "production_delivery_performed_during_consideration",
    ),
    (
        {
            "authorization_consumed": True,
        },
        (),
        {},
        "authorization_consumed_during_consideration",
    ),
    (
        {
            "retry_performed": True,
        },
        (),
        {},
        "retry_performed_during_consideration",
    ),
    (
        {
            "scheduler_enabled": True,
        },
        (),
        {},
        "scheduler_enabled_during_consideration",
    ),
    (
        {
            "automatic_promotion_performed": True,
        },
        (),
        {},
        "automatic_promotion_performed_during_consideration",
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionManualRolloutConsiderationV266Tests(
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

    def test_v266_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V266_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION,
            (
                "V266_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_CONSIDERATION"
            ),
        )

        self.assertEqual(
            len(V265_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V266_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V267_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v267: saved-search notification production delivery "
                "pilot supervised execution manual rollout consideration "
                "closeout audit"
            ),
        )

    def test_v266_and_v267_scopes_are_documentation_and_test_only(self):
        for scope in (
            V266_ALLOWED_SCOPE,
            V267_PROPOSED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v266_contract_packages_remain_exact(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_REQUIRED_FIELDS),
            47,
        )

        self.assertEqual(
            len(MANUAL_ROLLOUT_REASON_ORDER),
            48,
        )

        self.assertEqual(
            len(set(MANUAL_ROLLOUT_REASON_ORDER)),
            48,
        )

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

    def test_v266_default_result_is_eligible_for_preparation_only(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration()
        )

        self.assertEqual(
            tuple(result),
            MANUAL_ROLLOUT_RESULT_FIELDS,
        )

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

        self.assertTrue(
            result["eligible"]
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["future_authorization_requirements"],
            MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS,
        )

        self.assertNotIn(
            "command",
            result,
        )

        self.assertNotIn(
            "authorization_id",
            result,
        )

    def test_v266_not_eligible_has_fail_closed_precedence(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_complete=False,
                production_delivery_performed=True,
            )
        )

        self.assertEqual(
            result["decision"],
            "not_eligible",
        )

        self.assertFalse(
            result["eligible"]
        )

        self.assertEqual(
            result["future_authorization_requirements"],
            (),
        )

        self.assertIn(
            "source_not_complete",
            result["reason_codes"],
        )

        self.assertIn(
            "production_delivery_performed_during_consideration",
            result["reason_codes"],
        )

    def test_v266_all_reason_codes_are_reachable(self):
        self.assertEqual(
            len(V266_REASON_REACHABILITY_CASES),
            48,
        )

        reached: set[str] = set()

        for (
            changes,
            removed_fields,
            context_changes,
            reason,
        ) in V266_REASON_REACHABILITY_CASES:
            with self.subTest(
                reason=reason
            ):
                record = (
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                for field in removed_fields:
                    record.pop(
                        field
                    )

                context = (
                    build_manual_rollout_evaluation_context(
                        **context_changes
                    )
                )

                result = evaluate_manual_rollout_consideration(
                    record,
                    context=context,
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

                self.assertEqual(
                    result["decision"],
                    "not_eligible",
                )

                reached.add(
                    reason
                )

        self.assertEqual(
            reached,
            set(MANUAL_ROLLOUT_REASON_ORDER),
        )

    def test_v266_reason_order_is_deterministic(self):
        record = (
            build_complete_manual_rollout_consideration(
                consideration_id="",
                source_owner_id=0,
                source_approved_limit=4,
                source_evidence_decision="incomplete",
                source_rollout_recommendation="not_eligible",
                source_reason_codes=("error",),
                source_complete=False,
                source_consistent=False,
                source_privacy_safe=False,
                source_incident_clear=False,
                source_policy_compliant=False,
                source_authorization_consumption_count=0,
                source_production_invocation_count=2,
                source_delivered_count=4,
                source_audit_gap_free=False,
                source_duplicate_attempt_clean=False,
                source_provider_anomaly=True,
                source_incident_state="open",
                source_privacy_sanitizer_applied=False,
                source_automatic_retry_enabled=True,
                source_automatic_rollout_promotion_enabled=True,
                decision_owner_identity="evidence-reviewer-a",
                privacy_reviewer_identity="evidence-reviewer-a",
                considered_owner_ids=(101, 202),
                considered_limit=4,
                future_authorization_required=False,
                production_delivery_performed=True,
                authorization_consumed=True,
                retry_performed=True,
                scheduler_enabled=True,
                automatic_promotion_performed=True,
            )
        )

        context = build_manual_rollout_evaluation_context(
            readiness_generated_at_utc=899,
            preview_generated_at_utc=899,
        )

        result = evaluate_manual_rollout_consideration(
            record,
            context=context,
        )

        order = {
            reason: index
            for index, reason in enumerate(
                MANUAL_ROLLOUT_REASON_ORDER
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
            ordered_unique_manual_rollout_reasons(
                list(
                    reversed(
                        result["reason_codes"]
                    )
                )
            ),
        )

    def test_v266_reason_families_remain_exact(self):
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
            combined,
            set(MANUAL_ROLLOUT_REASON_ORDER),
        )

    def test_v266_collectors_are_empty_for_default_record(self):
        record = (
            build_complete_manual_rollout_consideration()
        )

        context = (
            build_manual_rollout_evaluation_context()
        )

        self.assertEqual(
            collect_manual_rollout_completeness_reasons(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_source_eligibility_reasons(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_scope_role_reasons(
                record,
                context,
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_prohibited_action_reasons(
                record
            ),
            (),
        )

    def test_v266_input_decision_and_reasons_cannot_spoof_result(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                final_decision="not_eligible",
                reason_codes=(
                    "production_delivery_performed_during_consideration",
                ),
            )
        )

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["sanitized_evidence"][
                "final_decision"
            ],
            "eligible_to_prepare_future_authorization",
        )

        self.assertEqual(
            result["sanitized_evidence"][
                "reason_codes"
            ],
            (),
        )

    def test_v266_source_decision_and_recommendation_are_mandatory(self):
        decision_result = (
            evaluate_manual_rollout_consideration(
                build_complete_manual_rollout_consideration(
                    source_evidence_decision="incomplete",
                )
            )
        )

        recommendation_result = (
            evaluate_manual_rollout_consideration(
                build_complete_manual_rollout_consideration(
                    source_rollout_recommendation="not_eligible",
                )
            )
        )

        self.assertIn(
            "source_decision_not_complete_consistent",
            decision_result["reason_codes"],
        )

        self.assertIn(
            "source_rollout_recommendation_not_manual_consideration",
            recommendation_result["reason_codes"],
        )

    def test_v266_source_reason_codes_must_be_empty(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_reason_codes=(
                    "source-error",
                ),
            )
        )

        self.assertEqual(
            result["decision"],
            "not_eligible",
        )

        self.assertIn(
            "source_reason_codes_nonempty",
            result["reason_codes"],
        )

    def test_v266_source_flags_remain_fail_closed(self):
        cases = (
            (
                "source_complete",
                "source_not_complete",
            ),
            (
                "source_consistent",
                "source_not_consistent",
            ),
            (
                "source_privacy_safe",
                "source_not_privacy_safe",
            ),
            (
                "source_incident_clear",
                "source_incident_not_clear",
            ),
            (
                "source_policy_compliant",
                "source_not_policy_compliant",
            ),
        )

        for field, reason in cases:
            with self.subTest(
                field=field
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **{
                            field: False,
                        }
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v266_source_consumption_and_invocation_counts_are_exact(self):
        consumption = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_authorization_consumption_count=0,
            )
        )

        invocation = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_production_invocation_count=2,
            )
        )

        self.assertIn(
            "source_authorization_consumption_count_mismatch",
            consumption["reason_codes"],
        )

        self.assertIn(
            "source_production_invocation_count_mismatch",
            invocation["reason_codes"],
        )

    def test_v266_source_delivery_counts_remain_reconciled(self):
        cases = (
            {
                "source_delivered_count": -1,
            },
            {
                "source_delivered_count": 0,
            },
            {
                "source_delivered_count": 4,
            },
            {
                "source_refused_count": 1,
            },
            {
                "source_failed_count": 1,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                self.assertIn(
                    "source_delivery_counts_not_reconciled",
                    result["reason_codes"],
                )

    def test_v266_source_audit_incident_and_policy_states_fail_closed(self):
        cases = (
            (
                {
                    "source_audit_gap_free": False,
                },
                "source_audit_not_gap_free",
            ),
            (
                {
                    "source_duplicate_attempt_clean": False,
                },
                "source_duplicate_attempt_not_clean",
            ),
            (
                {
                    "source_provider_anomaly": True,
                },
                "source_provider_anomaly_present",
            ),
            (
                {
                    "source_incident_state": "open",
                },
                "source_incident_state_not_closed",
            ),
            (
                {
                    "source_privacy_sanitizer_applied": False,
                },
                "source_privacy_sanitizer_not_applied",
            ),
            (
                {
                    "source_automatic_retry_enabled": True,
                },
                "source_automatic_retry_enabled",
            ),
            (
                {
                    "source_automatic_rollout_promotion_enabled": True,
                },
                "source_automatic_rollout_promotion_enabled",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v266_owner_scope_is_single_and_source_bound(self):
        cases = (
            (
                {
                    "source_owner_id": 0,
                },
                "invalid_source_owner_id",
            ),
            (
                {
                    "considered_owner_ids": (),
                },
                "considered_owner_scope_empty",
            ),
            (
                {
                    "considered_owner_ids": (
                        202,
                    ),
                },
                "considered_owner_scope_expanded",
            ),
            (
                {
                    "considered_owner_ids": (
                        101,
                        202,
                    ),
                },
                "considered_owner_scope_expanded",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v266_considered_limit_cannot_expand(self):
        invalid = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                considered_limit=0,
            )
        )

        expanded = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_approved_limit=2,
                considered_limit=3,
                source_delivered_count=2,
            )
        )

        self.assertIn(
            "considered_limit_invalid",
            invalid["reason_codes"],
        )

        self.assertIn(
            "considered_limit_expanded",
            expanded["reason_codes"],
        )

    def test_v266_role_separation_remains_fail_closed(self):
        decision_overlap = (
            evaluate_manual_rollout_consideration(
                build_complete_manual_rollout_consideration(
                    decision_owner_identity=(
                        "evidence-reviewer-a"
                    ),
                )
            )
        )

        reviewer_overlap = (
            evaluate_manual_rollout_consideration(
                build_complete_manual_rollout_consideration(
                    privacy_reviewer_identity=(
                        "evidence-reviewer-a"
                    ),
                )
            )
        )

        self.assertIn(
            "decision_owner_role_overlap",
            decision_overlap["reason_codes"],
        )

        self.assertIn(
            "required_reviewer_identity_not_distinct",
            reviewer_overlap["reason_codes"],
        )

    def test_v266_freshness_boundaries_are_inclusive(self):
        record = (
            build_complete_manual_rollout_consideration()
        )

        at_boundary = (
            build_manual_rollout_evaluation_context(
                current_timestamp_utc=1200,
                readiness_generated_at_utc=900,
                preview_generated_at_utc=900,
                consideration_started_at_utc=300,
            )
        )

        result = evaluate_manual_rollout_consideration(
            record,
            context=at_boundary,
        )

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

        outside_boundary = (
            build_manual_rollout_evaluation_context(
                current_timestamp_utc=1200,
                readiness_generated_at_utc=899,
                preview_generated_at_utc=899,
                consideration_started_at_utc=299,
            )
        )

        stale = evaluate_manual_rollout_consideration(
            record,
            context=outside_boundary,
        )

        self.assertIn(
            "readiness_evidence_stale_or_changed",
            stale["reason_codes"],
        )

        self.assertIn(
            "preview_evidence_stale_or_changed",
            stale["reason_codes"],
        )

    def test_v266_fingerprint_changes_fail_closed(self):
        readiness = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                readiness_evidence_fingerprint="changed",
            )
        )

        preview = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                preview_evidence_fingerprint="changed",
            )
        )

        self.assertIn(
            "readiness_evidence_stale_or_changed",
            readiness["reason_codes"],
        )

        self.assertIn(
            "preview_evidence_stale_or_changed",
            preview["reason_codes"],
        )

    def test_v266_future_authorization_requirement_is_mandatory(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                future_authorization_required=False,
            )
        )

        self.assertEqual(
            result["decision"],
            "not_eligible",
        )

        self.assertIn(
            "future_authorization_not_required",
            result["reason_codes"],
        )

    def test_v266_all_prohibited_actions_fail_closed(self):
        cases = (
            (
                "production_delivery_performed",
                "production_delivery_performed_during_consideration",
            ),
            (
                "authorization_consumed",
                "authorization_consumed_during_consideration",
            ),
            (
                "retry_performed",
                "retry_performed_during_consideration",
            ),
            (
                "scheduler_enabled",
                "scheduler_enabled_during_consideration",
            ),
            (
                "automatic_promotion_performed",
                "automatic_promotion_performed_during_consideration",
            ),
        )

        for field, reason in cases:
            with self.subTest(
                field=field
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **{
                            field: True,
                        }
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_eligible",
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v266_sanitizer_is_strict_allowlist_based(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                unknown_field="discard-me",
            )
        )

        sanitized = result[
            "sanitized_evidence"
        ]

        self.assertEqual(
            tuple(sanitized),
            tuple(
                field
                for field in MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST
                if field in sanitized
            ),
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        self.assertNotIn(
            "discard-me",
            repr(result),
        )

    def test_v266_sensitive_values_are_discarded(self):
        record = (
            build_complete_manual_rollout_consideration(
                smtp_password="secret-value",
                recipient_email="private@example.invalid",
                rendered_body="private-body",
                provider_response_body="private-provider-body",
            )
        )

        result = evaluate_manual_rollout_consideration(
            record
        )

        rendered = repr(
            result
        )

        for value in (
            "secret-value",
            "private@example.invalid",
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

        self.assertTrue(
            set(
                result["sanitized_evidence"]
            ).isdisjoint(
                MANUAL_ROLLOUT_SENSITIVE_INPUT_KEYS
            )
        )

    def test_v266_immutable_snapshot_is_exact_and_deterministic(self):
        record = (
            build_complete_manual_rollout_consideration()
        )

        first = manual_rollout_immutable_snapshot(
            record
        )

        second = manual_rollout_immutable_snapshot(
            record
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            tuple(first),
            MANUAL_ROLLOUT_IMMUTABLE_BINDINGS,
        )

        self.assertEqual(
            first["source_owner_id"],
            101,
        )

        self.assertEqual(
            first["source_approved_limit"],
            3,
        )

    def test_v266_evaluator_performs_no_external_action(self):
        record = (
            build_complete_manual_rollout_consideration()
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
            result = evaluate_manual_rollout_consideration(
                record
            )

        subprocess_run.assert_not_called()
        get_connection.assert_not_called()
        call_command_mock.assert_not_called()

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

    def test_v266_role_and_privacy_packages_remain_exact(self):
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

        self.assertEqual(
            len(MANUAL_ROLLOUT_ROLE_SEPARATION_RULES),
            6,
        )

        self.assertEqual(
            len(MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS),
            13,
        )

        self.assertIn(
            "SMTP password",
            MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS,
        )

    def test_v266_future_authorization_package_remains_separate(self):
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

    def test_v266_prohibited_action_package_remains_complete(self):
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
            "direct SQL repair",
            "Django shell timestamp repair",
            "privacy sanitizer bypass",
            "computed decision spoofing",
            "silent inconsistency acceptance",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_PROHIBITED_ACTIONS
                )
            )
        )

    def test_v266_v265_acceptance_gates_remain_packaged(self):
        required = {
            "forty-eight reason codes remain unique",
            "source evidence decision must be complete-consistent",
            "source authorization consumption count must equal one",
            "considered owner scope cannot expand source owner scope",
            "considered limit cannot exceed source approved limit",
            "future authorization remains mandatory",
            "future authorization must have a new identifier",
            "manual consideration performs no production delivery",
            "manual consideration consumes no authorization",
            "manual consideration performs no retry",
            "manual consideration enables no scheduler",
            "manual consideration performs no automatic promotion",
            "source authorization cannot be reused",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V265_ACCEPTANCE_GATES)
            )
        )

    def test_v266_default_readiness_remains_not_ready(self):
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
    def test_v266_production_like_readiness_remains_ready(self):
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
    def test_v266_readiness_execution_opens_no_email_connection(self):
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

    def test_v266_command_surfaces_remain_unchanged(self):
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

    def test_v266_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v266_scheduler_remains_nonautomatic(self):
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

    def test_v266_v265_contract_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_manual_rollout_consideration_contract_v265.py"
        )

        self.assertIn(
            (
                "V265_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_CONSIDERATION_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v266: saved-search notification production delivery "
                "pilot supervised execution manual rollout consideration "
                "implementation"
            ),
            source,
        )

    def test_v266_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V266_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION
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

    def test_v266_no_migration_0017_exists(self):
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

    def test_v266_implementation_gate_matrix_is_complete(self):
        required = {
            "v265 manual-rollout consideration contract remains packaged",
            "v266 scope remains exactly two implementation files",
            "v267 proposed scope remains exactly two files",
            "all forty-eight reason codes remain reachable",
            "reason ordering remains deterministic",
            "source decision must be complete-consistent",
            "considered owner scope must match source owner",
            "considered limit cannot exceed source approved limit",
            "readiness freshness boundary remains inclusive",
            "preview freshness boundary remains inclusive",
            "consideration lifetime boundary remains inclusive",
            "eligible result permits future-authorization preparation only",
            "eligible result does not produce a production command",
            "production delivery during consideration fails closed",
            "authorization consumption during consideration fails closed",
            "retry during consideration fails closed",
            "scheduler enablement during consideration fails closed",
            "automatic promotion during consideration fails closed",
            "strict evidence allowlist remains enforced",
            "sensitive values do not appear in results",
            "evaluator invokes no subprocess",
            "evaluator invokes no management command",
            "evaluator opens no email connection",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service remains unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertGreaterEqual(
            len(V266_IMPLEMENTATION_GATES),
            85,
        )

        self.assertTrue(
            required.issubset(
                set(V266_IMPLEMENTATION_GATES)
            )
        )
