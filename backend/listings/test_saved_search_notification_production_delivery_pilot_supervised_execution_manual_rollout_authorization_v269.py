from __future__ import annotations

import ast
from dataclasses import dataclass
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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_contract_v268 import (
    MANUAL_ROLLOUT_AUTHORIZATION_COMPLETENESS_REASON_CODES,
    MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS,
    MANUAL_ROLLOUT_AUTHORIZATION_DECISION_PRECEDENCE,
    MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST,
    MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS,
    MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT,
    MANUAL_ROLLOUT_AUTHORIZATION_MAX_OWNER_COUNT,
    MANUAL_ROLLOUT_AUTHORIZATION_PREVIEW_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS,
    MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTION_REASON_CODES,
    MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS,
    MANUAL_ROLLOUT_AUTHORIZATION_PROVIDER_STATE_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_READINESS_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER,
    MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS,
    MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_ROLES,
    MANUAL_ROLLOUT_AUTHORIZATION_ROLE_SEPARATION_RULES,
    MANUAL_ROLLOUT_AUTHORIZATION_SCOPE_ROLE_REASON_CODES,
    MANUAL_ROLLOUT_AUTHORIZATION_SENSITIVE_INPUT_KEYS,
    MANUAL_ROLLOUT_AUTHORIZATION_SOURCE_REASON_CODES,
    MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS,
    V268_ACCEPTANCE_GATES,
    build_complete_manual_rollout_authorization_candidate,
    build_manual_rollout_authorization_contract_summary,
    manual_rollout_authorization_source_is_eligible,
)


V269_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION = (
    "V269_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION"
)

V268_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "contract_v268.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "contract_v268.md"
    ),
)

V269_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_v269.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_v269.md"
    ),
)

V270_PROPOSED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "closeout_audit_v270.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "closeout_audit_v270.md"
    ),
)

MANUAL_ROLLOUT_AUTHORIZATION_RESULT_FIELDS = (
    "decision",
    "authorized",
    "reason_codes",
    "sanitized_evidence",
    "immutable_snapshot",
    "single_execution_requirements",
    "owner_id",
    "approved_limit",
    "production_command",
    "production_delivery_performed",
    "authorization_consumed",
)

MANUAL_ROLLOUT_AUTHORIZATION_REVIEWER_FIELDS = (
    "decision_owner_identity",
    "evidence_reviewer_identity",
    "privacy_reviewer_identity",
    "incident_reviewer_identity",
    "rollback_reviewer_identity",
    "incident_commander_identity",
)

MANUAL_ROLLOUT_AUTHORIZATION_PAIRWISE_REVIEWER_FIELDS = (
    "evidence_reviewer_identity",
    "privacy_reviewer_identity",
    "incident_reviewer_identity",
    "rollback_reviewer_identity",
)

V269_REASON_REACHABILITY_CASES = (
    ({}, ("authorization_id",), {}, "missing_authorization_id"),
    ({}, ("source_consideration_id",), {}, "missing_source_consideration_id"),
    ({}, ("source_change_record_id",), {}, "missing_source_change_record_id"),
    (
        {},
        ("historical_source_authorization_id",),
        {},
        "missing_historical_source_authorization_id",
    ),
    ({}, ("owner_id",), {}, "missing_owner_id"),
    ({}, ("approved_limit",), {}, "missing_approved_limit"),
    (
        {},
        ("authorizing_operator_identity",),
        {},
        "missing_authorizing_operator_identity",
    ),
    (
        {},
        ("evidence_reviewer_identity",),
        {},
        "missing_required_reviewer_identity",
    ),
    (
        {},
        ("readiness_generated_at_utc",),
        {},
        "missing_readiness_evidence",
    ),
    (
        {},
        ("preview_generated_at_utc",),
        {},
        "missing_preview_evidence",
    ),
    (
        {},
        ("provider_state_fingerprint",),
        {},
        "missing_provider_state_evidence",
    ),
    (
        {},
        ("authorization_command_fingerprint",),
        {},
        "missing_command_fingerprint",
    ),
    (
        {},
        ("pre_send_freeze_fingerprint",),
        {},
        "missing_freeze_fingerprint",
    ),
    (
        {},
        ("authorization_created_at_utc",),
        {},
        "missing_authorization_window",
    ),
    (
        {"source_consideration_eligible": False},
        (),
        {},
        "source_consideration_not_eligible",
    ),
    (
        {"source_consideration_reason_codes": ("source-error",)},
        (),
        {},
        "source_consideration_reason_codes_nonempty",
    ),
    (
        {"source_evidence_sanitized": False},
        (),
        {},
        "source_evidence_not_sanitized",
    ),
    (
        {"source_immutable_snapshot_complete": False},
        (),
        {},
        "source_immutable_snapshot_incomplete",
    ),
    (
        {"authorization_id": "authorization-001"},
        (),
        {},
        "historical_authorization_reuse_attempted",
    ),
    (
        {"source_owner_id": 0},
        (),
        {},
        "source_owner_mismatch",
    ),
    (
        {
            "source_approved_limit": 2,
            "source_considered_limit": 3,
        },
        (),
        {},
        "source_limit_mismatch",
    ),
    (
        {"source_considered_owner_ids": (202,)},
        (),
        {},
        "source_considered_owner_scope_invalid",
    ),
    (
        {"source_considered_limit": 0},
        (),
        {},
        "source_considered_limit_invalid",
    ),
    (
        {"source_authorization_preconditions_complete": False},
        (),
        {},
        "source_preconditions_incomplete",
    ),
    (
        {"owner_id": 0},
        (),
        {},
        "invalid_owner_id",
    ),
    (
        {"approved_limit": 0},
        (),
        {},
        "invalid_approved_limit",
    ),
    (
        {"owner_id": 202},
        (),
        {},
        "owner_scope_expanded",
    ),
    (
        {
            "source_considered_limit": 2,
            "approved_limit": 3,
        },
        (),
        {},
        "limit_expanded",
    ),
    (
        {"authorizing_operator_identity": "decision-owner-a"},
        (),
        {},
        "authorizing_operator_role_overlap",
    ),
    (
        {"decision_owner_identity": "evidence-reviewer-a"},
        (),
        {},
        "decision_owner_role_overlap",
    ),
    (
        {"privacy_reviewer_identity": "evidence-reviewer-a"},
        (),
        {},
        "required_reviewer_identity_not_distinct",
    ),
    (
        {"readiness_generated_at_utc": 899},
        (),
        {},
        "readiness_evidence_stale_or_changed",
    ),
    (
        {"preview_generated_at_utc": 899},
        (),
        {},
        "preview_evidence_stale_or_changed",
    ),
    (
        {"provider_state_generated_at_utc": 899},
        (),
        {},
        "provider_state_stale_or_changed",
    ),
    (
        {"authorization_command_fingerprint": "changed"},
        (),
        {},
        "command_or_freeze_fingerprint_changed",
    ),
    (
        {"authorization_created_at_utc": 1201},
        (),
        {},
        "authorization_expired_or_future_dated",
    ),
    (
        {"production_delivery_performed": True},
        (),
        {},
        "production_delivery_performed_during_authorization",
    ),
    (
        {"authorization_consumption_count": 1},
        (),
        {},
        "authorization_consumed_before_execution",
    ),
    (
        {"retry_performed": True},
        (),
        {},
        "retry_performed_during_authorization",
    ),
    (
        {"scheduler_enabled": True},
        (),
        {},
        "scheduler_enabled_during_authorization",
    ),
    (
        {"automatic_promotion_performed": True},
        (),
        {},
        "automatic_promotion_performed_during_authorization",
    ),
)

V269_IMPLEMENTATION_GATES = (
    "v268 authorization contract remains packaged",
    "v268 committed scope remains exactly two files",
    "v269 scope remains exactly two implementation files",
    "v270 proposed scope remains exactly two closeout files",
    "implementation remains documentation and test only",
    "forty-six required fields remain exact",
    "forty-six required fields remain unique",
    "forty-one ordered reason codes remain exact",
    "forty-one ordered reason codes remain unique",
    "all forty-one reason codes remain reachable",
    "reason ordering remains deterministic",
    "four reason families remain disjoint",
    "two decisions remain exact",
    "not-authorized retains fail-closed precedence",
    "positive result permits preparation only",
    "positive result returns no production command",
    "positive result performs no production delivery",
    "positive result consumes no authorization",
    "positive result performs no retry",
    "positive result enables no scheduler",
    "positive result performs no automatic promotion",
    "source consideration decision remains mandatory",
    "source consideration eligibility remains mandatory",
    "source reason-code collection remains empty",
    "source evidence remains sanitized",
    "source immutable snapshot remains complete",
    "source preconditions remain complete",
    "historical authorization reuse remains prohibited",
    "source owner remains positive",
    "authorization owner remains positive",
    "source and authorization owners remain bound",
    "owner scope remains exactly one",
    "owner scope expansion fails closed",
    "source approved limit remains one through three",
    "source considered limit remains one through three",
    "authorization limit remains one through three",
    "source limit mismatch fails closed",
    "authorization limit expansion fails closed",
    "authorizing operator remains mandatory",
    "decision owner remains mandatory",
    "reviewer identities remain mandatory",
    "authorizing operator overlap fails closed",
    "decision owner overlap fails closed",
    "reviewer duplication fails closed",
    "readiness freshness remains inclusive at three hundred seconds",
    "preview freshness remains inclusive at three hundred seconds",
    "provider-state freshness remains inclusive at three hundred seconds",
    "authorization lifetime remains inclusive at six hundred seconds",
    "future readiness evidence fails closed",
    "future preview evidence fails closed",
    "future provider state fails closed",
    "future authorization creation fails closed",
    "stale readiness fails closed",
    "stale preview fails closed",
    "stale provider state fails closed",
    "expired authorization fails closed",
    "changed readiness fingerprint fails closed",
    "changed preview fingerprint fails closed",
    "changed provider fingerprint fails closed",
    "changed sender fingerprint fails closed",
    "changed backend fingerprint fails closed",
    "changed command fingerprint fails closed",
    "changed freeze fingerprint fails closed",
    "both production confirmations remain mandatory",
    "feature-gate expected state remains mandatory",
    "authorization begins prepared",
    "authorization begins unconsumed",
    "authorization begins with zero production invocations",
    "production delivery during preparation fails closed",
    "authorization consumption during preparation fails closed",
    "production invocation during preparation fails closed",
    "retry during preparation fails closed",
    "scheduler enablement during preparation fails closed",
    "automatic promotion during preparation fails closed",
    "strict sanitizer uses exact allowlist",
    "unknown evidence fields are discarded",
    "sensitive evidence fields are discarded",
    "sensitive values remain absent from output",
    "computed reason codes cannot be spoofed",
    "computed authorization state cannot be spoofed",
    "immutable snapshot remains exact",
    "immutable snapshot remains deterministic",
    "single-execution requirements remain exact",
    "evaluator remains pure and in-memory",
    "evaluator invokes no subprocess",
    "evaluator invokes no management command",
    "evaluator opens no email connection",
    "evaluator performs no database mutation",
    "default readiness remains not-ready",
    "production-like readiness remains ready",
    "readiness evaluation opens no email connection",
    "production command controls remain unchanged",
    "production batch maximum remains twenty-five",
    "scheduler remains nonautomatic",
    "runtime scheduler schema and UI remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "historical safety tests remain green",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v270: saved-search notification production delivery pilot supervised execution manual rollout authorization closeout audit"

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
        "pilot_supervised_execution_manual_rollout_authorization_"
        "contract_v268.py"
    ),
)


@dataclass(frozen=True)
class ManualRolloutAuthorizationEvaluationContext:
    current_timestamp_utc: int
    expected_readiness_evidence_fingerprint: str
    expected_preview_evidence_fingerprint: str
    expected_provider_state_fingerprint: str
    expected_sender_state_fingerprint: str
    expected_email_backend_state_fingerprint: str
    expected_authorization_command_fingerprint: str
    expected_pre_send_freeze_fingerprint: str


def build_manual_rollout_authorization_evaluation_context(
    **changes: Any,
) -> ManualRolloutAuthorizationEvaluationContext:
    values: dict[str, Any] = {
        "current_timestamp_utc": 1200,
        "expected_readiness_evidence_fingerprint": (
            "readiness-fingerprint-002"
        ),
        "expected_preview_evidence_fingerprint": (
            "preview-fingerprint-002"
        ),
        "expected_provider_state_fingerprint": (
            "provider-fingerprint-002"
        ),
        "expected_sender_state_fingerprint": (
            "sender-fingerprint-002"
        ),
        "expected_email_backend_state_fingerprint": (
            "backend-fingerprint-002"
        ),
        "expected_authorization_command_fingerprint": (
            "command-fingerprint-002"
        ),
        "expected_pre_send_freeze_fingerprint": (
            "freeze-fingerprint-002"
        ),
    }

    values.update(
        changes
    )

    return ManualRolloutAuthorizationEvaluationContext(
        **values
    )


def _is_positive_integer(
    value: Any,
) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value > 0
    )


def _is_bounded_limit(
    value: Any,
) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 1
        <= value
        <= MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT
    )


def _is_nonempty_text(
    value: Any,
) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
    )


def ordered_unique_manual_rollout_authorization_reasons(
    reasons: list[str] | tuple[str, ...],
) -> tuple[str, ...]:
    reason_set = set(
        reasons
    )

    return tuple(
        reason
        for reason in MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
        if reason in reason_set
    )


def collect_manual_rollout_authorization_completeness_reasons(
    candidate: dict[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if not _is_nonempty_text(
        candidate.get(
            "authorization_id"
        )
    ):
        reasons.append(
            "missing_authorization_id"
        )

    if not _is_nonempty_text(
        candidate.get(
            "source_consideration_id"
        )
    ):
        reasons.append(
            "missing_source_consideration_id"
        )

    if not _is_nonempty_text(
        candidate.get(
            "source_change_record_id"
        )
    ):
        reasons.append(
            "missing_source_change_record_id"
        )

    if not _is_nonempty_text(
        candidate.get(
            "historical_source_authorization_id"
        )
    ):
        reasons.append(
            "missing_historical_source_authorization_id"
        )

    if "owner_id" not in candidate:
        reasons.append(
            "missing_owner_id"
        )

    if "approved_limit" not in candidate:
        reasons.append(
            "missing_approved_limit"
        )

    if not _is_nonempty_text(
        candidate.get(
            "authorizing_operator_identity"
        )
    ):
        reasons.append(
            "missing_authorizing_operator_identity"
        )

    if any(
        not _is_nonempty_text(
            candidate.get(
                field
            )
        )
        for field in MANUAL_ROLLOUT_AUTHORIZATION_REVIEWER_FIELDS
    ):
        reasons.append(
            "missing_required_reviewer_identity"
        )

    if (
        "readiness_generated_at_utc" not in candidate
        or not _is_nonempty_text(
            candidate.get(
                "readiness_evidence_fingerprint"
            )
        )
    ):
        reasons.append(
            "missing_readiness_evidence"
        )

    if (
        "preview_generated_at_utc" not in candidate
        or not _is_nonempty_text(
            candidate.get(
                "preview_evidence_fingerprint"
            )
        )
    ):
        reasons.append(
            "missing_preview_evidence"
        )

    if (
        "provider_state_generated_at_utc" not in candidate
        or any(
            not _is_nonempty_text(
                candidate.get(
                    field
                )
            )
            for field in (
                "provider_state_fingerprint",
                "sender_state_fingerprint",
                "email_backend_state_fingerprint",
            )
        )
    ):
        reasons.append(
            "missing_provider_state_evidence"
        )

    if not _is_nonempty_text(
        candidate.get(
            "authorization_command_fingerprint"
        )
    ):
        reasons.append(
            "missing_command_fingerprint"
        )

    if not _is_nonempty_text(
        candidate.get(
            "pre_send_freeze_fingerprint"
        )
    ):
        reasons.append(
            "missing_freeze_fingerprint"
        )

    if (
        "authorization_created_at_utc" not in candidate
        or "authorization_expires_at_utc" not in candidate
    ):
        reasons.append(
            "missing_authorization_window"
        )

    return ordered_unique_manual_rollout_authorization_reasons(
        reasons
    )


def collect_manual_rollout_authorization_source_reasons(
    candidate: dict[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if (
        candidate.get(
            "source_consideration_decision"
        )
        != "eligible_to_prepare_future_authorization"
        or candidate.get(
            "source_consideration_eligible"
        )
        is not True
    ):
        reasons.append(
            "source_consideration_not_eligible"
        )

    if candidate.get(
        "source_consideration_reason_codes"
    ) != ():
        reasons.append(
            "source_consideration_reason_codes_nonempty"
        )

    if candidate.get(
        "source_evidence_sanitized"
    ) is not True:
        reasons.append(
            "source_evidence_not_sanitized"
        )

    if candidate.get(
        "source_immutable_snapshot_complete"
    ) is not True:
        reasons.append(
            "source_immutable_snapshot_incomplete"
        )

    if (
        _is_nonempty_text(
            candidate.get(
                "authorization_id"
            )
        )
        and candidate.get(
            "authorization_id"
        )
        == candidate.get(
            "historical_source_authorization_id"
        )
    ):
        reasons.append(
            "historical_authorization_reuse_attempted"
        )

    source_owner_id = candidate.get(
        "source_owner_id"
    )

    if not _is_positive_integer(
        source_owner_id
    ):
        reasons.append(
            "source_owner_mismatch"
        )

    source_approved_limit = candidate.get(
        "source_approved_limit"
    )

    source_considered_limit = candidate.get(
        "source_considered_limit"
    )

    if (
        not _is_bounded_limit(
            source_approved_limit
        )
        or (
            _is_bounded_limit(
                source_considered_limit
            )
            and _is_bounded_limit(
                source_approved_limit
            )
            and source_considered_limit
            > source_approved_limit
        )
    ):
        reasons.append(
            "source_limit_mismatch"
        )

    if (
        _is_positive_integer(
            source_owner_id
        )
        and candidate.get(
            "source_considered_owner_ids"
        )
        != (
            source_owner_id,
        )
    ):
        reasons.append(
            "source_considered_owner_scope_invalid"
        )

    if not _is_bounded_limit(
        source_considered_limit
    ):
        reasons.append(
            "source_considered_limit_invalid"
        )

    if (
        candidate.get(
            "source_authorization_preconditions_complete"
        )
        is not True
        or candidate.get(
            "production_confirmation_primary"
        )
        is not True
        or candidate.get(
            "production_confirmation_secondary"
        )
        is not True
        or candidate.get(
            "feature_gate_expected_enabled"
        )
        is not True
        or candidate.get(
            "authorization_state"
        )
        != "prepared"
    ):
        reasons.append(
            "source_preconditions_incomplete"
        )

    return ordered_unique_manual_rollout_authorization_reasons(
        reasons
    )


def _fresh_and_bound(
    *,
    current_timestamp_utc: Any,
    generated_at_utc: Any,
    maximum_age_seconds: int,
    actual_fingerprint: Any,
    expected_fingerprint: str,
) -> bool:
    if (
        not isinstance(
            current_timestamp_utc,
            int,
        )
        or isinstance(
            current_timestamp_utc,
            bool,
        )
        or not isinstance(
            generated_at_utc,
            int,
        )
        or isinstance(
            generated_at_utc,
            bool,
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
        and _is_nonempty_text(
            actual_fingerprint
        )
        and actual_fingerprint
        == expected_fingerprint
    )


def collect_manual_rollout_authorization_scope_role_reasons(
    candidate: dict[str, Any],
    context: ManualRolloutAuthorizationEvaluationContext,
) -> tuple[str, ...]:
    reasons: list[str] = []

    owner_id = candidate.get(
        "owner_id"
    )

    source_owner_id = candidate.get(
        "source_owner_id"
    )

    approved_limit = candidate.get(
        "approved_limit"
    )

    source_considered_limit = candidate.get(
        "source_considered_limit"
    )

    if (
        "owner_id" in candidate
        and not _is_positive_integer(
            owner_id
        )
    ):
        reasons.append(
            "invalid_owner_id"
        )

    if (
        "approved_limit" in candidate
        and not _is_bounded_limit(
            approved_limit
        )
    ):
        reasons.append(
            "invalid_approved_limit"
        )

    if (
        _is_positive_integer(
            owner_id
        )
        and _is_positive_integer(
            source_owner_id
        )
        and owner_id
        != source_owner_id
    ):
        reasons.append(
            "owner_scope_expanded"
        )

    if (
        _is_bounded_limit(
            approved_limit
        )
        and _is_bounded_limit(
            source_considered_limit
        )
        and approved_limit
        > source_considered_limit
    ):
        reasons.append(
            "limit_expanded"
        )

    authorizing_operator = candidate.get(
        "authorizing_operator_identity"
    )

    decision_owner = candidate.get(
        "decision_owner_identity"
    )

    reviewers = tuple(
        candidate.get(
            field
        )
        for field in MANUAL_ROLLOUT_AUTHORIZATION_PAIRWISE_REVIEWER_FIELDS
    )

    incident_commander = candidate.get(
        "incident_commander_identity"
    )

    if (
        _is_nonempty_text(
            authorizing_operator
        )
        and authorizing_operator
        in (
            decision_owner,
            *reviewers,
            incident_commander,
        )
    ):
        reasons.append(
            "authorizing_operator_role_overlap"
        )

    if (
        _is_nonempty_text(
            decision_owner
        )
        and decision_owner
        in (
            *reviewers,
            incident_commander,
        )
    ):
        reasons.append(
            "decision_owner_role_overlap"
        )

    populated_reviewers = tuple(
        value
        for value in reviewers
        if _is_nonempty_text(
            value
        )
    )

    if (
        len(
            populated_reviewers
        )
        != len(
            set(
                populated_reviewers
            )
        )
        or (
            _is_nonempty_text(
                incident_commander
            )
            and incident_commander
            == candidate.get(
                "rollback_reviewer_identity"
            )
        )
    ):
        reasons.append(
            "required_reviewer_identity_not_distinct"
        )

    if not _fresh_and_bound(
        current_timestamp_utc=(
            context.current_timestamp_utc
        ),
        generated_at_utc=candidate.get(
            "readiness_generated_at_utc"
        ),
        maximum_age_seconds=(
            MANUAL_ROLLOUT_AUTHORIZATION_READINESS_FRESHNESS_SECONDS
        ),
        actual_fingerprint=candidate.get(
            "readiness_evidence_fingerprint"
        ),
        expected_fingerprint=(
            context.expected_readiness_evidence_fingerprint
        ),
    ):
        reasons.append(
            "readiness_evidence_stale_or_changed"
        )

    if not _fresh_and_bound(
        current_timestamp_utc=(
            context.current_timestamp_utc
        ),
        generated_at_utc=candidate.get(
            "preview_generated_at_utc"
        ),
        maximum_age_seconds=(
            MANUAL_ROLLOUT_AUTHORIZATION_PREVIEW_FRESHNESS_SECONDS
        ),
        actual_fingerprint=candidate.get(
            "preview_evidence_fingerprint"
        ),
        expected_fingerprint=(
            context.expected_preview_evidence_fingerprint
        ),
    ):
        reasons.append(
            "preview_evidence_stale_or_changed"
        )

    provider_fresh = _fresh_and_bound(
        current_timestamp_utc=(
            context.current_timestamp_utc
        ),
        generated_at_utc=candidate.get(
            "provider_state_generated_at_utc"
        ),
        maximum_age_seconds=(
            MANUAL_ROLLOUT_AUTHORIZATION_PROVIDER_STATE_FRESHNESS_SECONDS
        ),
        actual_fingerprint=candidate.get(
            "provider_state_fingerprint"
        ),
        expected_fingerprint=(
            context.expected_provider_state_fingerprint
        ),
    )

    provider_fingerprints_match = all(
        (
            candidate.get(
                "sender_state_fingerprint"
            )
            == context.expected_sender_state_fingerprint,
            candidate.get(
                "email_backend_state_fingerprint"
            )
            == context.expected_email_backend_state_fingerprint,
        )
    )

    if not (
        provider_fresh
        and provider_fingerprints_match
    ):
        reasons.append(
            "provider_state_stale_or_changed"
        )

    if (
        candidate.get(
            "authorization_command_fingerprint"
        )
        != context.expected_authorization_command_fingerprint
        or candidate.get(
            "pre_send_freeze_fingerprint"
        )
        != context.expected_pre_send_freeze_fingerprint
    ):
        reasons.append(
            "command_or_freeze_fingerprint_changed"
        )

    created_at = candidate.get(
        "authorization_created_at_utc"
    )

    expires_at = candidate.get(
        "authorization_expires_at_utc"
    )

    current = context.current_timestamp_utc

    authorization_window_valid = (
        isinstance(
            current,
            int,
        )
        and not isinstance(
            current,
            bool,
        )
        and isinstance(
            created_at,
            int,
        )
        and not isinstance(
            created_at,
            bool,
        )
        and isinstance(
            expires_at,
            int,
        )
        and not isinstance(
            expires_at,
            bool,
        )
        and 0
        <= current
        - created_at
        <= MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS
        and created_at
        < expires_at
        and expires_at
        - created_at
        <= MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS
        and current
        <= expires_at
    )

    if not authorization_window_valid:
        reasons.append(
            "authorization_expired_or_future_dated"
        )

    return ordered_unique_manual_rollout_authorization_reasons(
        reasons
    )


def collect_manual_rollout_authorization_prohibited_action_reasons(
    candidate: dict[str, Any],
) -> tuple[str, ...]:
    reasons: list[str] = []

    if candidate.get(
        "production_delivery_performed"
    ) is not False:
        reasons.append(
            "production_delivery_performed_during_authorization"
        )

    if (
        candidate.get(
            "authorization_consumption_count"
        )
        != 0
        or candidate.get(
            "production_invocation_count"
        )
        != 0
    ):
        reasons.append(
            "authorization_consumed_before_execution"
        )

    if candidate.get(
        "retry_performed"
    ) is not False:
        reasons.append(
            "retry_performed_during_authorization"
        )

    if candidate.get(
        "scheduler_enabled"
    ) is not False:
        reasons.append(
            "scheduler_enabled_during_authorization"
        )

    if candidate.get(
        "automatic_promotion_performed"
    ) is not False:
        reasons.append(
            "automatic_promotion_performed_during_authorization"
        )

    return ordered_unique_manual_rollout_authorization_reasons(
        reasons
    )


def sanitize_manual_rollout_authorization_evidence(
    candidate: dict[str, Any],
    *,
    decision: str,
    reason_codes: tuple[str, ...],
) -> dict[str, Any]:
    sanitized = {
        field: candidate[field]
        for field in MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST
        if field in candidate
    }

    sanitized["authorization_state"] = (
        "prepared"
        if decision
        == "authorized_to_prepare_single_manual_execution"
        else "rejected"
    )

    sanitized["reason_codes"] = (
        reason_codes
    )

    return sanitized


def manual_rollout_authorization_immutable_snapshot(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    return {
        field: candidate[field]
        for field in MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS
        if field in candidate
    }


def evaluate_manual_rollout_authorization(
    candidate: dict[str, Any],
    *,
    context: ManualRolloutAuthorizationEvaluationContext | None = None,
) -> dict[str, Any]:
    active_context = (
        context
        or build_manual_rollout_authorization_evaluation_context()
    )

    reasons = (
        collect_manual_rollout_authorization_completeness_reasons(
            candidate
        )
        + collect_manual_rollout_authorization_source_reasons(
            candidate
        )
        + collect_manual_rollout_authorization_scope_role_reasons(
            candidate,
            active_context,
        )
        + collect_manual_rollout_authorization_prohibited_action_reasons(
            candidate
        )
    )

    reason_codes = (
        ordered_unique_manual_rollout_authorization_reasons(
            reasons
        )
    )

    authorized = not reason_codes

    decision = (
        "authorized_to_prepare_single_manual_execution"
        if authorized
        else "not_authorized"
    )

    return {
        "decision": decision,
        "authorized": authorized,
        "reason_codes": reason_codes,
        "sanitized_evidence": (
            sanitize_manual_rollout_authorization_evidence(
                candidate,
                decision=decision,
                reason_codes=reason_codes,
            )
        ),
        "immutable_snapshot": (
            manual_rollout_authorization_immutable_snapshot(
                candidate
            )
        ),
        "single_execution_requirements": (
            MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS
            if authorized
            else ()
        ),
        "owner_id": (
            candidate.get(
                "owner_id"
            )
            if authorized
            else None
        ),
        "approved_limit": (
            candidate.get(
                "approved_limit"
            )
            if authorized
            else None
        ),
        "production_command": None,
        "production_delivery_performed": False,
        "authorization_consumed": False,
    }


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionManualRolloutAuthorizationV269Tests(
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

    def test_v269_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V269_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION,
            (
                "V269_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_AUTHORIZATION"
            ),
        )

        self.assertEqual(
            len(V268_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V269_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V270_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v270: saved-search notification production delivery "
                "pilot supervised execution manual rollout "
                "authorization closeout audit"
            ),
        )

    def test_v269_and_v270_scopes_are_documentation_and_test_only(self):
        for scope in (
            V269_ALLOWED_SCOPE,
            V270_PROPOSED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v269_contract_packages_remain_exact(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS
            ),
            46,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS
            ),
            14,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS
            ),
            18,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS,
            (
                "not_authorized",
                "authorized_to_prepare_single_manual_execution",
            ),
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_DECISION_PRECEDENCE,
            MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS,
        )

    def test_v269_reason_packages_remain_exact(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_COMPLETENESS_REASON_CODES
            ),
            14,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_SOURCE_REASON_CODES
            ),
            10,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_SCOPE_ROLE_REASON_CODES
            ),
            12,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTION_REASON_CODES
            ),
            5,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
            ),
            41,
        )

        self.assertEqual(
            len(
                set(
                    MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
                )
            ),
            41,
        )

    def test_v269_default_result_is_preparation_only(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        self.assertEqual(
            tuple(result),
            MANUAL_ROLLOUT_AUTHORIZATION_RESULT_FIELDS,
        )

        self.assertEqual(
            result["decision"],
            "authorized_to_prepare_single_manual_execution",
        )

        self.assertTrue(
            result["authorized"]
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["owner_id"],
            101,
        )

        self.assertEqual(
            result["approved_limit"],
            3,
        )

        self.assertEqual(
            result["single_execution_requirements"],
            MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS,
        )

        self.assertIsNone(
            result["production_command"]
        )

        self.assertFalse(
            result["production_delivery_performed"]
        )

        self.assertFalse(
            result["authorization_consumed"]
        )

    def test_v269_contract_helper_and_evaluator_agree(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        self.assertTrue(
            manual_rollout_authorization_source_is_eligible(
                candidate
            )
        )

        contract_summary = (
            build_manual_rollout_authorization_contract_summary(
                candidate
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        self.assertEqual(
            contract_summary["decision"],
            result["decision"],
        )

        self.assertEqual(
            contract_summary["authorized"],
            result["authorized"],
        )

    def test_v269_all_reason_codes_are_reachable(self):
        reached: set[str] = set()

        for (
            changes,
            removed_fields,
            context_changes,
            expected_reason,
        ) in V269_REASON_REACHABILITY_CASES:
            with self.subTest(
                expected_reason=expected_reason
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                for field in removed_fields:
                    candidate.pop(
                        field
                    )

                context = (
                    build_manual_rollout_authorization_evaluation_context(
                        **context_changes
                    )
                )

                result = evaluate_manual_rollout_authorization(
                    candidate,
                    context=context,
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

                self.assertIn(
                    expected_reason,
                    result["reason_codes"],
                )

                reached.add(
                    expected_reason
                )

        self.assertEqual(
            reached,
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
            ),
        )

    def test_v269_reason_order_is_deterministic(self):
        reversed_reasons = tuple(
            reversed(
                MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
            )
        )

        self.assertEqual(
            ordered_unique_manual_rollout_authorization_reasons(
                reversed_reasons
                + MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER[:8]
            ),
            MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER,
        )

    def test_v269_collectors_are_empty_for_default_candidate(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        context = (
            build_manual_rollout_authorization_evaluation_context()
        )

        self.assertEqual(
            collect_manual_rollout_authorization_completeness_reasons(
                candidate
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_authorization_source_reasons(
                candidate
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_authorization_scope_role_reasons(
                candidate,
                context,
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_authorization_prohibited_action_reasons(
                candidate
            ),
            (),
        )

    def test_v269_not_authorized_has_fail_closed_precedence(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                source_consideration_eligible=False,
            )
        )

        self.assertEqual(
            result["decision"],
            "not_authorized",
        )

        self.assertFalse(
            result["authorized"]
        )

        self.assertEqual(
            result["single_execution_requirements"],
            (),
        )

        self.assertIsNone(
            result["owner_id"]
        )

        self.assertIsNone(
            result["approved_limit"]
        )

    def test_v269_missing_required_fields_fail_closed(self):
        for field in (
            "authorization_id",
            "source_consideration_id",
            "source_change_record_id",
            "historical_source_authorization_id",
            "owner_id",
            "approved_limit",
            "authorizing_operator_identity",
            "readiness_generated_at_utc",
            "preview_generated_at_utc",
            "provider_state_generated_at_utc",
            "authorization_command_fingerprint",
            "pre_send_freeze_fingerprint",
            "authorization_created_at_utc",
        ):
            with self.subTest(
                field=field
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate()
                )

                candidate.pop(
                    field
                )

                result = evaluate_manual_rollout_authorization(
                    candidate
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

                self.assertTrue(
                    result["reason_codes"]
                )

    def test_v269_required_roles_remain_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_ROLES,
            (
                "decision_owner",
                "authorizing_operator",
                "evidence_reviewer",
                "privacy_reviewer",
                "incident_reviewer",
                "rollback_reviewer",
                "incident_commander",
            ),
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_ROLE_SEPARATION_RULES
            ),
            7,
        )

    def test_v269_required_reviewer_identities_are_mandatory(self):
        for field in MANUAL_ROLLOUT_AUTHORIZATION_REVIEWER_FIELDS:
            with self.subTest(
                field=field
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate()
                )

                candidate.pop(
                    field
                )

                result = evaluate_manual_rollout_authorization(
                    candidate
                )

                self.assertIn(
                    "missing_required_reviewer_identity",
                    result["reason_codes"],
                )

    def test_v269_role_separation_fails_closed(self):
        cases = (
            (
                {
                    "authorizing_operator_identity": (
                        "decision-owner-a"
                    ),
                },
                "authorizing_operator_role_overlap",
            ),
            (
                {
                    "decision_owner_identity": (
                        "evidence-reviewer-a"
                    ),
                },
                "decision_owner_role_overlap",
            ),
            (
                {
                    "privacy_reviewer_identity": (
                        "evidence-reviewer-a"
                    ),
                },
                "required_reviewer_identity_not_distinct",
            ),
            (
                {
                    "incident_commander_identity": (
                        "rollback-reviewer-a"
                    ),
                },
                "required_reviewer_identity_not_distinct",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v269_owner_scope_remains_single_and_bound(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_MAX_OWNER_COUNT,
            1,
        )

        cases = (
            {
                "owner_id": 0,
            },
            {
                "source_owner_id": 0,
            },
            {
                "owner_id": 202,
            },
            {
                "source_considered_owner_ids": (
                    101,
                    202,
                ),
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

    def test_v269_limit_remains_one_through_three_without_expansion(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT,
            3,
        )

        cases = (
            {
                "approved_limit": 0,
            },
            {
                "approved_limit": 4,
            },
            {
                "source_approved_limit": 4,
            },
            {
                "source_considered_limit": 4,
            },
            {
                "source_considered_limit": 2,
                "approved_limit": 3,
            },
            {
                "source_approved_limit": 2,
                "source_considered_limit": 3,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

    def test_v269_freshness_boundaries_are_inclusive(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                readiness_generated_at_utc=1500,
                preview_generated_at_utc=1500,
                provider_state_generated_at_utc=1500,
            )
        )

        context = (
            build_manual_rollout_authorization_evaluation_context(
                current_timestamp_utc=1800,
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate,
            context=context,
        )

        self.assertEqual(
            result["decision"],
            "authorized_to_prepare_single_manual_execution",
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_READINESS_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_PREVIEW_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_PROVIDER_STATE_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS,
            600,
        )

    def test_v269_stale_evidence_fails_closed(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                readiness_generated_at_utc=899,
                preview_generated_at_utc=899,
                provider_state_generated_at_utc=899,
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        self.assertIn(
            "readiness_evidence_stale_or_changed",
            result["reason_codes"],
        )

        self.assertIn(
            "preview_evidence_stale_or_changed",
            result["reason_codes"],
        )

        self.assertIn(
            "provider_state_stale_or_changed",
            result["reason_codes"],
        )

    def test_v269_future_evidence_fails_closed(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                readiness_generated_at_utc=1201,
                preview_generated_at_utc=1201,
                provider_state_generated_at_utc=1201,
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        self.assertIn(
            "readiness_evidence_stale_or_changed",
            result["reason_codes"],
        )

        self.assertIn(
            "preview_evidence_stale_or_changed",
            result["reason_codes"],
        )

        self.assertIn(
            "provider_state_stale_or_changed",
            result["reason_codes"],
        )

    def test_v269_changed_fingerprints_fail_closed(self):
        cases = (
            (
                {
                    "readiness_evidence_fingerprint": "changed",
                },
                "readiness_evidence_stale_or_changed",
            ),
            (
                {
                    "preview_evidence_fingerprint": "changed",
                },
                "preview_evidence_stale_or_changed",
            ),
            (
                {
                    "provider_state_fingerprint": "changed",
                },
                "provider_state_stale_or_changed",
            ),
            (
                {
                    "sender_state_fingerprint": "changed",
                },
                "provider_state_stale_or_changed",
            ),
            (
                {
                    "email_backend_state_fingerprint": "changed",
                },
                "provider_state_stale_or_changed",
            ),
            (
                {
                    "authorization_command_fingerprint": "changed",
                },
                "command_or_freeze_fingerprint_changed",
            ),
            (
                {
                    "pre_send_freeze_fingerprint": "changed",
                },
                "command_or_freeze_fingerprint_changed",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v269_authorization_lifetime_boundary_is_inclusive(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                readiness_generated_at_utc=1500,
                preview_generated_at_utc=1500,
                provider_state_generated_at_utc=1500,
            )
        )

        context = (
            build_manual_rollout_authorization_evaluation_context(
                current_timestamp_utc=1800,
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate,
            context=context,
        )

        self.assertNotIn(
            "authorization_expired_or_future_dated",
            result["reason_codes"],
        )

    def test_v269_invalid_authorization_windows_fail_closed(self):
        cases = (
            {
                "authorization_created_at_utc": 1201,
            },
            {
                "authorization_created_at_utc": 500,
            },
            {
                "authorization_expires_at_utc": 1199,
            },
            {
                "authorization_created_at_utc": 1200,
                "authorization_expires_at_utc": 1801,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertIn(
                    "authorization_expired_or_future_dated",
                    result["reason_codes"],
                )

    def test_v269_both_confirmations_are_mandatory(self):
        for field in (
            "production_confirmation_primary",
            "production_confirmation_secondary",
        ):
            with self.subTest(
                field=field
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **{
                            field: False,
                        }
                    )
                )

                self.assertIn(
                    "source_preconditions_incomplete",
                    result["reason_codes"],
                )

    def test_v269_feature_gate_expectation_is_mandatory(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                feature_gate_expected_enabled=False,
            )
        )

        self.assertIn(
            "source_preconditions_incomplete",
            result["reason_codes"],
        )

    def test_v269_all_prohibited_actions_fail_closed(self):
        cases = (
            (
                {
                    "production_delivery_performed": True,
                },
                "production_delivery_performed_during_authorization",
            ),
            (
                {
                    "authorization_consumption_count": 1,
                },
                "authorization_consumed_before_execution",
            ),
            (
                {
                    "production_invocation_count": 1,
                },
                "authorization_consumed_before_execution",
            ),
            (
                {
                    "retry_performed": True,
                },
                "retry_performed_during_authorization",
            ),
            (
                {
                    "scheduler_enabled": True,
                },
                "scheduler_enabled_during_authorization",
            ),
            (
                {
                    "automatic_promotion_performed": True,
                },
                "automatic_promotion_performed_during_authorization",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v269_input_reason_codes_cannot_spoof_result(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                reason_codes=(
                    "production_delivery_performed_during_authorization",
                ),
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        self.assertEqual(
            result["decision"],
            "authorized_to_prepare_single_manual_execution",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["sanitized_evidence"]["reason_codes"],
            (),
        )

    def test_v269_input_authorization_state_cannot_spoof_result(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                authorization_state="authorized",
            )
        )

        self.assertEqual(
            result["decision"],
            "not_authorized",
        )

        self.assertEqual(
            result["sanitized_evidence"]["authorization_state"],
            "rejected",
        )

    def test_v269_sanitizer_is_strict_allowlist_based(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                unknown_field="discard-me",
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        sanitized = result[
            "sanitized_evidence"
        ]

        self.assertEqual(
            tuple(sanitized),
            MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST,
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        self.assertNotIn(
            "discard-me",
            repr(sanitized),
        )

    def test_v269_sensitive_values_are_discarded(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                smtp_password="secret-value",
                recipient_email="private@example.invalid",
                rendered_body="private-body",
                provider_response_body="provider-private",
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        rendered = repr(
            result
        )

        for value in (
            "secret-value",
            "private@example.invalid",
            "private-body",
            "provider-private",
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
                MANUAL_ROLLOUT_AUTHORIZATION_SENSITIVE_INPUT_KEYS
            )
        )

    def test_v269_privacy_and_prohibition_packages_remain_complete(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS
            ),
            13,
        )

        self.assertIn(
            "SMTP password",
            MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "raw exception traceback",
            MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "historical source authorization reuse",
            MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "automatic authorization renewal",
            MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS,
        )

    def test_v269_immutable_snapshot_is_exact_and_deterministic(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        first = (
            manual_rollout_authorization_immutable_snapshot(
                candidate
            )
        )

        second = (
            manual_rollout_authorization_immutable_snapshot(
                candidate
            )
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            tuple(first),
            MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS,
        )

    def test_v269_evaluator_performs_no_external_action(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
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
            result = evaluate_manual_rollout_authorization(
                candidate
            )

        subprocess_run.assert_not_called()
        get_connection.assert_not_called()
        call_command_mock.assert_not_called()

        self.assertTrue(
            result["authorized"]
        )

    def test_v269_acceptance_gate_packages_remain_present(self):
        self.assertGreaterEqual(
            len(V268_ACCEPTANCE_GATES),
            85,
        )

        self.assertGreaterEqual(
            len(V269_IMPLEMENTATION_GATES),
            95,
        )

        self.assertIn(
            "positive decision permits preparation only",
            V268_ACCEPTANCE_GATES,
        )

        self.assertIn(
            "all forty-one reason codes remain reachable",
            V269_IMPLEMENTATION_GATES,
        )

    def test_v269_default_readiness_remains_not_ready(self):
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
    def test_v269_production_like_readiness_remains_ready(self):
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

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v269_readiness_execution_opens_no_email_connection(self):
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

    def test_v269_command_surfaces_remain_unchanged(self):
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

    def test_v269_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v269_scheduler_remains_nonautomatic(self):
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

    def test_v269_v268_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_manual_rollout_authorization_"
            "contract_v268.py"
        )

        self.assertIn(
            (
                "V268_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_AUTHORIZATION_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v269: saved-search notification production delivery "
                "pilot supervised execution manual rollout "
                "authorization implementation"
            ),
            source,
        )

    def test_v269_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V269_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION
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

    def test_v269_no_migration_0017_exists(self):
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

    def test_v269_implementation_gate_matrix_is_complete(self):
        required = {
            "v268 authorization contract remains packaged",
            "v269 scope remains exactly two implementation files",
            "v270 proposed scope remains exactly two closeout files",
            "all forty-one reason codes remain reachable",
            "positive result permits preparation only",
            "positive result returns no production command",
            "positive result performs no production delivery",
            "positive result consumes no authorization",
            "owner scope remains exactly one",
            "authorization limit remains one through three",
            "authorization limit expansion fails closed",
            "readiness freshness remains inclusive at three hundred seconds",
            "preview freshness remains inclusive at three hundred seconds",
            "provider-state freshness remains inclusive at three hundred seconds",
            "authorization lifetime remains inclusive at six hundred seconds",
            "strict sanitizer uses exact allowlist",
            "sensitive values remain absent from output",
            "computed reason codes cannot be spoofed",
            "immutable snapshot remains deterministic",
            "evaluator invokes no subprocess",
            "evaluator invokes no management command",
            "evaluator opens no email connection",
            "production command controls remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertGreaterEqual(
            len(V269_IMPLEMENTATION_GATES),
            95,
        )

        self.assertTrue(
            required.issubset(
                set(V269_IMPLEMENTATION_GATES)
            )
        )
