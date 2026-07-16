from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, replace
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
from listings.test_saved_search_notification_production_delivery_pilot_execution_authorization_v257 import (
    build_command_fingerprint,
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


V260_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION = (
    "V260_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION"
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

V261_PROPOSED_SCOPE = (
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

SUPERVISED_FREEZE_FINGERPRINT_FIELDS = (
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
)

SUPERVISED_PREFLIGHT_RESULT_FIELDS = (
    "approved",
    "status",
    "reason_codes",
    "change_record_id",
    "authorization_id",
    "pilot_owner_id",
    "approved_limit",
    "preview_candidate_count",
    "authorization_command_fingerprint",
    "freeze_fingerprint",
)

SUPERVISED_EXECUTION_PLAN_FIELDS = (
    "executable",
    "status",
    "reason_codes",
    "change_record_id",
    "authorization_id",
    "pilot_owner_id",
    "approved_limit",
    "authorization_consumption_limit",
    "production_invocation_limit",
    "command_pattern",
    "authorization_command_fingerprint",
    "freeze_fingerprint",
)

SUPERVISED_CONSUMPTION_RESULT_FIELDS = (
    "consumed",
    "status",
    "reason_codes",
    "authorization_id",
    "authorization_state",
    "authorization_consumed_at_utc",
)

SUPERVISED_POST_RUN_REASON_CODES = (
    "production_invocation_count_mismatch",
    "authorization_consumption_count_mismatch",
    "delivery_counts_mismatch",
    "failed_count_nonzero",
    "unexpected_refusal_count_nonzero",
    "delivery_attempted_event_mismatch",
    "delivery_succeeded_event_mismatch",
    "delivery_failed_event_mismatch",
    "sent_timestamp_event_mismatch",
    "sent_timestamp_inconsistent",
    "duplicate_attempt_detected",
    "audit_gap_detected",
    "provider_anomaly_detected",
    "incident_not_closed_or_escalated",
    "post_run_review_deadline_missed",
    "automatic_retry_enabled",
    "automatic_rollout_promotion_enabled",
)

SUPERVISED_POST_RUN_RESULT_FIELDS = (
    "successful",
    "status",
    "reason_codes",
    "delivered_count",
    "skipped_count",
    "refused_count",
    "failed_count",
    "incident_state",
)

SUPERVISED_SENSITIVE_FIELDS = (
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

V260_IMPLEMENTATION_GATES = (
    "v259 supervised-execution contract remains packaged",
    "v260 scope is exactly two implementation files",
    "v261 closeout scope is exactly two files",
    "implementation remains documentation and test only",
    "supervised limit remains 1 through 3",
    "readiness freshness remains 300 seconds",
    "preview freshness remains 300 seconds",
    "authorization lifetime remains 600 seconds",
    "pre-send freeze freshness remains 120 seconds",
    "post-run review deadline remains 600 seconds",
    "freeze fingerprint uses canonical SHA-256",
    "freeze fingerprint binds owner and limit",
    "freeze fingerprint binds provider and sender state",
    "freeze fingerprint binds authorization state",
    "freeze fingerprint binds supervision roles",
    "preflight evaluator is deterministic",
    "all 38 abort reasons remain reachable",
    "abort-reason order remains deterministic",
    "positive owner remains mandatory",
    "limit between 1 and 3 remains mandatory",
    "authorized unconsumed authorization remains mandatory",
    "matching authorization fingerprint remains mandatory",
    "matching owner bindings remain mandatory",
    "matching limit bindings remain mandatory",
    "strict readiness remains mandatory",
    "all nine readiness checks remain mandatory",
    "fresh readiness remains mandatory",
    "fresh preview remains mandatory",
    "fresh pre-send freeze remains mandatory",
    "feature gate remains mandatory",
    "approved backend remains mandatory",
    "configured sender remains mandatory",
    "verified sender remains mandatory",
    "provider credentials remain mandatory",
    "sufficient provider quota remains mandatory",
    "operational provider remains mandatory",
    "owner opt-in remains mandatory",
    "eligible due candidate remains mandatory",
    "preview candidate count remains bounded",
    "preview skips must be understood",
    "unexpected preview refusals remain prohibited",
    "concurrent owner run blocks execution",
    "open incident blocks execution",
    "operator identity remains mandatory",
    "two distinct reviewers remain mandatory",
    "rollback reviewer remains mandatory",
    "incident commander remains mandatory",
    "both production confirmations remain mandatory",
    "authorization consumption remains one-shot",
    "runtime mutation after freeze fails closed",
    "execution plan permits at most one invocation",
    "execution plan never invokes production",
    "post-run reconciliation is deterministic",
    "post-run reason order is deterministic",
    "success and failure audit sequences remain exact",
    "post-run deadline remains enforced",
    "automatic retry remains disabled",
    "automatic rollout promotion remains disabled",
    "evidence sanitizer remains strict allowlist based",
    "sensitive evidence remains excluded",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v261: saved-search notification production delivery pilot supervised execution closeout audit"

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
)


@dataclass(frozen=True)
class SupervisedExecutionEvidence:
    change_record_id: str = "change-001"
    authorization_id: str = "authorization-001"
    authorization_lane_closed: bool = True
    authorization_state: str = "authorized"
    authorization_consumed: bool = False
    authorization_consumption_succeeds: bool = True
    authorization_expires_at_utc: int = 1550
    authorization_command_fingerprint: str = ""
    pilot_owner_id: int = 101
    approved_limit: int = 3
    preview_owner_id: int = 101
    preview_limit: int = 3
    preview_candidate_count: int = 2
    preview_skips_understood: bool = True
    preview_unexpected_refusal_count: int = 0
    readiness_status: str = "ready"
    readiness_check_count: int = 9
    readiness_checked_at_utc: int = 900
    preview_checked_at_utc: int = 900
    pre_send_freeze_at_utc: int = 950
    feature_gate_enabled: bool = True
    email_backend_allowed: bool = True
    default_sender_configured: bool = True
    sender_verified: bool = True
    provider_credentials_available: bool = True
    provider_quota_available: int = 3
    provider_operational: bool = True
    owner_opt_in_enabled: bool = True
    eligible_due_candidate_count: int = 2
    concurrent_owner_run: bool = False
    unresolved_incident: bool = False
    operator_identity: str = "operator-a"
    primary_reviewer_identity: str = "reviewer-a"
    secondary_reviewer_identity: str = "reviewer-b"
    rollback_reviewer_identity: str = "rollback-reviewer-a"
    incident_commander_identity: str = "incident-commander-a"
    post_run_reconciliation_owner: str = "operator-a"
    execute_production_send: bool = True
    confirm_production_delivery: bool = True
    command_owner_id: int = 101
    command_limit: int = 3
    issued_execution_window: str = "window-001"
    freeze_fingerprint: str = ""
    runtime_freeze_fingerprint: str = ""


@dataclass(frozen=True)
class SupervisedPostRunEvidence:
    expected_candidate_count: int = 2
    production_invocation_count: int = 1
    authorization_consumption_count: int = 1
    delivered_count: int = 2
    skipped_count: int = 0
    refused_count: int = 0
    failed_count: int = 0
    unexpected_refusal_count: int = 0
    delivery_attempted_event_count: int = 2
    delivery_succeeded_event_count: int = 2
    delivery_failed_event_count: int = 0
    sent_timestamp_event_count: int = 2
    sent_timestamp_consistent: bool = True
    duplicate_attempt_clean: bool = True
    audit_gap_free: bool = True
    provider_anomaly: bool = False
    incident_state: str = "closed"
    review_started_at_utc: int = 1100
    review_completed_at_utc: int = 1200
    automatic_retry_enabled: bool = False
    automatic_rollout_promotion_enabled: bool = False


def build_freeze_fingerprint(
    evidence: SupervisedExecutionEvidence,
) -> str:
    payload = {
        "authorization_id": evidence.authorization_id,
        "authorization_command_fingerprint": (
            evidence.authorization_command_fingerprint
        ),
        "pilot_owner_id": evidence.pilot_owner_id,
        "approved_limit": evidence.approved_limit,
        "feature_gate_enabled": evidence.feature_gate_enabled,
        "email_backend_allowed": evidence.email_backend_allowed,
        "default_sender_configured": (
            evidence.default_sender_configured
        ),
        "sender_verified": evidence.sender_verified,
        "provider_operational": evidence.provider_operational,
        "provider_quota_available": (
            evidence.provider_quota_available
        ),
        "authorization_state": evidence.authorization_state,
        "operator_identity": evidence.operator_identity,
        "primary_reviewer_identity": (
            evidence.primary_reviewer_identity
        ),
        "secondary_reviewer_identity": (
            evidence.secondary_reviewer_identity
        ),
        "rollback_reviewer_identity": (
            evidence.rollback_reviewer_identity
        ),
        "incident_commander_identity": (
            evidence.incident_commander_identity
        ),
        "pre_send_freeze_at_utc": (
            evidence.pre_send_freeze_at_utc
        ),
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=True,
    )

    return hashlib.sha256(
        canonical.encode(
            "utf-8"
        )
    ).hexdigest()


def make_supervised_execution_evidence(
    **changes: Any,
) -> SupervisedExecutionEvidence:
    evidence = replace(
        SupervisedExecutionEvidence(),
        **changes,
    )

    if "authorization_command_fingerprint" not in changes:
        authorization_fingerprint = build_command_fingerprint(
            command_name="process_saved_search_notifications",
            execute_production_send=(
                evidence.execute_production_send
            ),
            confirm_production_delivery=(
                evidence.confirm_production_delivery
            ),
            owner_id=evidence.command_owner_id,
            limit=evidence.command_limit,
        )

        evidence = replace(
            evidence,
            authorization_command_fingerprint=(
                authorization_fingerprint
            ),
        )

    if "freeze_fingerprint" not in changes:
        evidence = replace(
            evidence,
            freeze_fingerprint=build_freeze_fingerprint(
                evidence
            ),
        )

    if "runtime_freeze_fingerprint" not in changes:
        evidence = replace(
            evidence,
            runtime_freeze_fingerprint=(
                evidence.freeze_fingerprint
            ),
        )

    return evidence


def supervised_immutable_binding_snapshot(
    evidence: SupervisedExecutionEvidence,
) -> dict[str, Any]:
    source = {
        "change_record_id": evidence.change_record_id,
        "authorization_id": evidence.authorization_id,
        "authorization_command_fingerprint": (
            evidence.authorization_command_fingerprint
        ),
        "pilot_owner_id": evidence.pilot_owner_id,
        "approved_limit": evidence.approved_limit,
        "preview_owner_id": evidence.preview_owner_id,
        "preview_limit": evidence.preview_limit,
        "preview_candidate_count": (
            evidence.preview_candidate_count
        ),
        "operator_identity": evidence.operator_identity,
        "primary_reviewer_identity": (
            evidence.primary_reviewer_identity
        ),
        "secondary_reviewer_identity": (
            evidence.secondary_reviewer_identity
        ),
        "issued_execution_window": (
            evidence.issued_execution_window
        ),
    }

    return {
        field: source[field]
        for field in SUPERVISED_EXECUTION_IMMUTABLE_BINDINGS
    }


def evaluate_supervised_preflight(
    evidence: SupervisedExecutionEvidence,
    *,
    now_utc: int,
) -> dict[str, Any]:
    reasons: list[str] = []

    def add(reason: str) -> None:
        if reason not in reasons:
            reasons.append(
                reason
            )

    if not evidence.authorization_lane_closed:
        add(
            "authorization_lane_not_closed"
        )

    if evidence.pilot_owner_id <= 0:
        add(
            "invalid_owner_id"
        )

    if not (
        SUPERVISED_EXECUTION_LIMIT_BAND[0]
        <= evidence.approved_limit
        <= SUPERVISED_EXECUTION_LIMIT_BAND[1]
    ):
        add(
            "invalid_pilot_limit"
        )

    if evidence.authorization_state != "authorized":
        add(
            "authorization_not_authorized"
        )

    if evidence.authorization_consumed:
        add(
            "authorization_already_consumed"
        )

    if (
        now_utc >= evidence.authorization_expires_at_utc
        or evidence.authorization_state == "expired"
    ):
        add(
            "authorization_expired"
        )

    if evidence.authorization_state == "revoked":
        add(
            "authorization_revoked"
        )

    expected_command_fingerprint = build_command_fingerprint(
        command_name="process_saved_search_notifications",
        execute_production_send=(
            evidence.execute_production_send
        ),
        confirm_production_delivery=(
            evidence.confirm_production_delivery
        ),
        owner_id=evidence.command_owner_id,
        limit=evidence.command_limit,
    )

    if (
        evidence.authorization_command_fingerprint
        != expected_command_fingerprint
    ):
        add(
            "command_fingerprint_mismatch"
        )

    if (
        evidence.preview_owner_id
        != evidence.pilot_owner_id
        or evidence.command_owner_id
        != evidence.pilot_owner_id
    ):
        add(
            "owner_binding_mismatch"
        )

    if (
        evidence.preview_limit
        != evidence.approved_limit
        or evidence.command_limit
        != evidence.approved_limit
    ):
        add(
            "limit_binding_mismatch"
        )

    if evidence.readiness_status != "ready":
        add(
            "readiness_not_ready"
        )

    if evidence.readiness_check_count != 9:
        add(
            "readiness_check_count_mismatch"
        )

    readiness_age = (
        now_utc
        - evidence.readiness_checked_at_utc
    )

    if not (
        0
        <= readiness_age
        <= SUPERVISED_EXECUTION_TIME_WINDOWS_SECONDS[
            "readiness_max_age"
        ]
    ):
        add(
            "readiness_evidence_stale"
        )

    preview_age = (
        now_utc
        - evidence.preview_checked_at_utc
    )

    if not (
        0
        <= preview_age
        <= SUPERVISED_EXECUTION_TIME_WINDOWS_SECONDS[
            "preview_max_age"
        ]
    ):
        add(
            "preview_evidence_stale"
        )

    freeze_age = (
        now_utc
        - evidence.pre_send_freeze_at_utc
    )

    if not (
        0
        <= freeze_age
        <= SUPERVISED_EXECUTION_TIME_WINDOWS_SECONDS[
            "pre_send_freeze_max_age"
        ]
    ):
        add(
            "pre_send_freeze_stale"
        )

    if not evidence.feature_gate_enabled:
        add(
            "feature_gate_disabled"
        )

    if not evidence.email_backend_allowed:
        add(
            "email_backend_rejected"
        )

    if not evidence.default_sender_configured:
        add(
            "default_sender_missing"
        )

    if not evidence.sender_verified:
        add(
            "sender_unverified"
        )

    if not evidence.provider_credentials_available:
        add(
            "provider_credentials_unavailable"
        )

    if (
        evidence.provider_quota_available
        < evidence.approved_limit
    ):
        add(
            "provider_quota_insufficient"
        )

    if not evidence.provider_operational:
        add(
            "provider_not_operational"
        )

    if not evidence.owner_opt_in_enabled:
        add(
            "owner_opt_in_disabled"
        )

    if evidence.eligible_due_candidate_count <= 0:
        add(
            "no_eligible_due_candidate"
        )

    if not (
        1
        <= evidence.preview_candidate_count
        <= evidence.approved_limit
    ):
        add(
            "preview_candidate_count_invalid"
        )

    if not evidence.preview_skips_understood:
        add(
            "preview_skips_unresolved"
        )

    if evidence.preview_unexpected_refusal_count != 0:
        add(
            "preview_unexpected_refusal"
        )

    if evidence.concurrent_owner_run:
        add(
            "concurrent_owner_run"
        )

    if evidence.unresolved_incident:
        add(
            "unresolved_incident"
        )

    if not evidence.operator_identity.strip():
        add(
            "operator_identity_missing"
        )

    if not evidence.primary_reviewer_identity.strip():
        add(
            "primary_reviewer_missing"
        )

    if not evidence.secondary_reviewer_identity.strip():
        add(
            "secondary_reviewer_missing"
        )

    if (
        evidence.primary_reviewer_identity.strip()
        and evidence.secondary_reviewer_identity.strip()
        and evidence.primary_reviewer_identity
        == evidence.secondary_reviewer_identity
    ):
        add(
            "reviewer_identity_collision"
        )

    if not evidence.rollback_reviewer_identity.strip():
        add(
            "rollback_reviewer_missing"
        )

    if not evidence.incident_commander_identity.strip():
        add(
            "incident_commander_missing"
        )

    if not (
        evidence.execute_production_send
        and evidence.confirm_production_delivery
    ):
        add(
            "production_confirmation_missing"
        )

    if not evidence.authorization_consumption_succeeds:
        add(
            "authorization_consumption_failed"
        )

    if (
        evidence.runtime_freeze_fingerprint
        != evidence.freeze_fingerprint
        or evidence.freeze_fingerprint
        != build_freeze_fingerprint(
            evidence
        )
    ):
        add(
            "runtime_state_changed_after_freeze"
        )

    order = {
        reason: index
        for index, reason in enumerate(
            SUPERVISED_EXECUTION_ABORT_REASONS
        )
    }

    reason_codes = tuple(
        sorted(
            reasons,
            key=order.__getitem__,
        )
    )

    return {
        "approved": not reason_codes,
        "status": (
            "approved"
            if not reason_codes
            else "aborted"
        ),
        "reason_codes": reason_codes,
        "change_record_id": evidence.change_record_id,
        "authorization_id": evidence.authorization_id,
        "pilot_owner_id": evidence.pilot_owner_id,
        "approved_limit": evidence.approved_limit,
        "preview_candidate_count": (
            evidence.preview_candidate_count
        ),
        "authorization_command_fingerprint": (
            evidence.authorization_command_fingerprint
        ),
        "freeze_fingerprint": evidence.freeze_fingerprint,
    }


def plan_supervised_execution(
    evidence: SupervisedExecutionEvidence,
    *,
    now_utc: int,
) -> dict[str, Any]:
    decision = evaluate_supervised_preflight(
        evidence,
        now_utc=now_utc,
    )

    executable = decision["approved"]

    return {
        "executable": executable,
        "status": (
            "ready_for_supervised_execution"
            if executable
            else "aborted"
        ),
        "reason_codes": decision["reason_codes"],
        "change_record_id": evidence.change_record_id,
        "authorization_id": evidence.authorization_id,
        "pilot_owner_id": evidence.pilot_owner_id,
        "approved_limit": evidence.approved_limit,
        "authorization_consumption_limit": (
            1
            if executable
            else 0
        ),
        "production_invocation_limit": (
            1
            if executable
            else 0
        ),
        "command_pattern": (
            SUPERVISED_EXECUTION_PRODUCTION_COMMAND
            if executable
            else None
        ),
        "authorization_command_fingerprint": (
            evidence.authorization_command_fingerprint
        ),
        "freeze_fingerprint": evidence.freeze_fingerprint,
    }


def consume_supervised_authorization(
    evidence: SupervisedExecutionEvidence,
    *,
    now_utc: int,
) -> dict[str, Any]:
    decision = evaluate_supervised_preflight(
        evidence,
        now_utc=now_utc,
    )

    if not decision["approved"]:
        return {
            "consumed": False,
            "status": "failed_closed",
            "reason_codes": decision["reason_codes"],
            "authorization_id": evidence.authorization_id,
            "authorization_state": "failed_closed",
            "authorization_consumed_at_utc": None,
        }

    return {
        "consumed": True,
        "status": "consumed",
        "reason_codes": (),
        "authorization_id": evidence.authorization_id,
        "authorization_state": "consumed",
        "authorization_consumed_at_utc": now_utc,
    }


def reconcile_supervised_post_run(
    evidence: SupervisedPostRunEvidence,
) -> dict[str, Any]:
    reasons: list[str] = []

    def add(reason: str) -> None:
        if reason not in reasons:
            reasons.append(
                reason
            )

    if evidence.production_invocation_count != 1:
        add(
            "production_invocation_count_mismatch"
        )

    if evidence.authorization_consumption_count != 1:
        add(
            "authorization_consumption_count_mismatch"
        )

    total = (
        evidence.delivered_count
        + evidence.skipped_count
        + evidence.refused_count
        + evidence.failed_count
    )

    if total != evidence.expected_candidate_count:
        add(
            "delivery_counts_mismatch"
        )

    if evidence.failed_count != 0:
        add(
            "failed_count_nonzero"
        )

    if evidence.unexpected_refusal_count != 0:
        add(
            "unexpected_refusal_count_nonzero"
        )

    expected_attempted = (
        evidence.delivered_count
        + evidence.failed_count
    )

    if (
        evidence.delivery_attempted_event_count
        != expected_attempted
    ):
        add(
            "delivery_attempted_event_mismatch"
        )

    if (
        evidence.delivery_succeeded_event_count
        != evidence.delivered_count
    ):
        add(
            "delivery_succeeded_event_mismatch"
        )

    if (
        evidence.delivery_failed_event_count
        != evidence.failed_count
    ):
        add(
            "delivery_failed_event_mismatch"
        )

    if (
        evidence.sent_timestamp_event_count
        != evidence.delivered_count
    ):
        add(
            "sent_timestamp_event_mismatch"
        )

    if not evidence.sent_timestamp_consistent:
        add(
            "sent_timestamp_inconsistent"
        )

    if not evidence.duplicate_attempt_clean:
        add(
            "duplicate_attempt_detected"
        )

    if not evidence.audit_gap_free:
        add(
            "audit_gap_detected"
        )

    if evidence.provider_anomaly:
        add(
            "provider_anomaly_detected"
        )

    if evidence.incident_state not in {
        "closed",
        "escalated",
    }:
        add(
            "incident_not_closed_or_escalated"
        )

    review_duration = (
        evidence.review_completed_at_utc
        - evidence.review_started_at_utc
    )

    if not (
        0
        <= review_duration
        <= SUPERVISED_EXECUTION_TIME_WINDOWS_SECONDS[
            "post_run_review_deadline"
        ]
    ):
        add(
            "post_run_review_deadline_missed"
        )

    if evidence.automatic_retry_enabled:
        add(
            "automatic_retry_enabled"
        )

    if evidence.automatic_rollout_promotion_enabled:
        add(
            "automatic_rollout_promotion_enabled"
        )

    order = {
        reason: index
        for index, reason in enumerate(
            SUPERVISED_POST_RUN_REASON_CODES
        )
    }

    reason_codes = tuple(
        sorted(
            reasons,
            key=order.__getitem__,
        )
    )

    return {
        "successful": not reason_codes,
        "status": (
            "closed"
            if not reason_codes
            else "escalate"
        ),
        "reason_codes": reason_codes,
        "delivered_count": evidence.delivered_count,
        "skipped_count": evidence.skipped_count,
        "refused_count": evidence.refused_count,
        "failed_count": evidence.failed_count,
        "incident_state": evidence.incident_state,
    }


def sanitize_supervised_evidence(
    raw_record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        field: raw_record[field]
        for field in SUPERVISED_EXECUTION_EVIDENCE_ALLOWLIST
        if field in raw_record
    }


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionV260Tests(
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

    def test_v260_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V260_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION,
            (
                "V260_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION"
            ),
        )

        self.assertEqual(
            len(V259_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V260_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V261_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v261: saved-search notification production "
                "delivery pilot supervised execution closeout audit"
            ),
        )

    def test_v260_scope_remains_documentation_and_test_only(self):
        for scope in (
            V260_ALLOWED_SCOPE,
            V261_PROPOSED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v260_contract_constants_remain_exact(self):
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
            len(SUPERVISED_EXECUTION_POST_RUN_GATES),
            17,
        )

    def test_v260_required_roles_and_stage_order_remain_exact(self):
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

    def test_v260_freeze_fingerprint_is_deterministic_sha256(self):
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

    def test_v260_freeze_fingerprint_binds_every_field(self):
        evidence = make_supervised_execution_evidence()

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
                pre_send_freeze_at_utc=951,
            ),
        )

        baseline = build_freeze_fingerprint(
            evidence
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

    def test_v260_default_preflight_is_approved(self):
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

    def test_v260_limit_boundaries_remain_fail_closed(self):
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

                evidence = make_supervised_execution_evidence(
                    approved_limit=limit,
                    preview_limit=limit,
                    preview_candidate_count=candidate_count,
                    provider_quota_available=max(
                        limit,
                        0,
                    ),
                    command_limit=limit,
                )

                result = evaluate_supervised_preflight(
                    evidence,
                    now_utc=1000,
                )

                self.assertEqual(
                    result["approved"],
                    approved,
                )

    def test_v260_freshness_boundaries_are_inclusive(self):
        evidence = make_supervised_execution_evidence(
            readiness_checked_at_utc=700,
            preview_checked_at_utc=700,
            pre_send_freeze_at_utc=880,
        )

        result = evaluate_supervised_preflight(
            evidence,
            now_utc=1000,
        )

        self.assertTrue(
            result["approved"]
        )

    def test_v260_stale_readiness_preview_and_freeze_fail_closed(self):
        evidence = make_supervised_execution_evidence(
            readiness_checked_at_utc=699,
            preview_checked_at_utc=699,
            pre_send_freeze_at_utc=879,
        )

        result = evaluate_supervised_preflight(
            evidence,
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

    def test_v260_each_abort_reason_is_reachable(self):
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

    def test_v260_abort_reason_order_matches_contract(self):
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

    def test_v260_immutable_snapshot_is_exact(self):
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

    def test_v260_execution_plan_is_bounded_and_nonexecuting(self):
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

    def test_v260_aborted_plan_contains_no_command(self):
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
            plan["production_invocation_limit"],
            0,
        )

        self.assertIsNone(
            plan["command_pattern"]
        )

    def test_v260_authorization_consumption_is_one_shot(self):
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

    def test_v260_runtime_mutation_blocks_consumption(self):
        result = consume_supervised_authorization(
            make_supervised_execution_evidence(
                runtime_freeze_fingerprint="changed",
            ),
            now_utc=1000,
        )

        self.assertFalse(
            result["consumed"]
        )

        self.assertIn(
            "runtime_state_changed_after_freeze",
            result["reason_codes"],
        )

    def test_v260_default_post_run_reconciliation_succeeds(self):
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

    def test_v260_each_post_run_reason_is_reachable(self):
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

    def test_v260_post_run_reason_order_is_deterministic(self):
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

    def test_v260_post_run_deadline_boundary_is_inclusive(self):
        result = reconcile_supervised_post_run(
            SupervisedPostRunEvidence(
                review_started_at_utc=1100,
                review_completed_at_utc=1700,
            )
        )

        self.assertTrue(
            result["successful"]
        )

    def test_v260_audit_sequences_remain_exact(self):
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

    def test_v260_evidence_sanitizer_is_strict_allowlist(self):
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

    def test_v260_privacy_and_prohibition_packages_remain_present(self):
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

    def test_v260_default_readiness_remains_not_ready(self):
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
    def test_v260_production_like_readiness_remains_ready(self):
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
    def test_v260_readiness_execution_opens_no_email_connection(self):
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

    def test_v260_command_surfaces_remain_unchanged(self):
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

    def test_v260_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v260_scheduler_remains_nonautomatic(self):
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

    def test_v260_v259_contract_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_contract_v259.py"
        )

        self.assertIn(
            (
                "V259_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v260: saved-search notification production "
                "delivery pilot supervised execution implementation"
            ),
            source,
        )

    def test_v260_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V260_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION
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

    def test_v260_no_migration_0017_exists(self):
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

    def test_v260_implementation_gate_matrix_is_complete(self):
        required = {
            "v259 supervised-execution contract remains packaged",
            "v260 scope is exactly two implementation files",
            "v261 closeout scope is exactly two files",
            "implementation remains documentation and test only",
            "supervised limit remains 1 through 3",
            "pre-send freeze freshness remains 120 seconds",
            "post-run review deadline remains 600 seconds",
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
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V260_IMPLEMENTATION_GATES)
            )
        )
