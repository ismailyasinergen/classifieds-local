from __future__ import annotations

import ast
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


V254_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS = (
    "V254_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS"
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

V254_ALLOWED_SCOPE = (
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

V255_PROPOSED_SCOPE = (
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

PILOT_LIMIT_BAND = (
    1,
    3,
)

PILOT_DECISION_STAGE_ORDER = (
    "authorization",
    "owner eligibility",
    "environment verification",
    "strict readiness",
    "matching preview",
    "reviewer go decision",
    "guarded production invocation",
    "post-run verification",
)

PILOT_PREVIEW_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

PILOT_PRODUCTION_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--execute-production-send "
    "--confirm-production-delivery "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

PILOT_PREFLIGHT_REASON_ORDER = (
    "invalid_owner_id",
    "invalid_pilot_limit",
    "owner_not_approved",
    "reviewer_not_approved",
    "owner_scope_not_isolated",
    "notification_opt_in_disabled",
    "no_eligible_due_saved_search",
    "recipient_unusable",
    "concurrent_owner_run",
    "unresolved_incident",
    "feature_gate_disabled",
    "email_backend_rejected",
    "default_sender_missing",
    "sender_unverified",
    "provider_credentials_unavailable",
    "provider_quota_insufficient",
    "provider_not_operational",
    "bounce_complaint_owner_missing",
    "execution_window_not_approved",
    "rollback_reviewer_missing",
    "strict_readiness_not_ready",
    "readiness_check_count_mismatch",
    "readiness_json_missing",
    "deployed_help_not_reviewed",
    "rollback_controls_unverified",
    "preview_owner_mismatch",
    "preview_limit_mismatch",
    "preview_candidate_count_invalid",
    "preview_skips_unresolved",
    "preview_unexpected_refusal",
)

PILOT_POST_RUN_REASON_ORDER = (
    "failed_count_nonzero",
    "unexpected_refusal_count_nonzero",
    "delivery_counts_unreconciled",
    "attempted_event_count_mismatch",
    "success_event_count_mismatch",
    "failure_event_count_mismatch",
    "timestamp_event_count_mismatch",
    "sent_timestamp_inconsistent",
    "duplicate_attempt_anomaly",
    "audit_gap_detected",
    "provider_anomaly",
    "incident_open",
)

PILOT_ALLOWED_RECORD_FIELDS = (
    "change_record_id",
    "pilot_owner_id",
    "approved_limit",
    "operator_identity",
    "reviewer_identity",
    "execution_window",
    "started_at_utc",
    "finished_at_utc",
    "feature_gate_verified",
    "backend_policy_verified",
    "sender_verification_status",
    "provider_status",
    "provider_quota_verified",
    "readiness_status",
    "readiness_ready_count",
    "readiness_not_ready_count",
    "readiness_warning_count",
    "preview_candidate_count",
    "preview_skipped_count",
    "production_delivered_count",
    "production_skipped_count",
    "production_refused_count",
    "production_failed_count",
    "audit_verified",
    "sent_timestamp_verified",
    "duplicate_attempt_verified",
    "rollback_readiness_verified",
    "decision",
    "incident_reference",
)

PILOT_SENSITIVE_RECORD_FIELDS = (
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

PILOT_IMPLEMENTATION_GATES = (
    "v253 pilot-readiness contract remains packaged",
    "v254 scope is exactly two implementation files",
    "v255 proposed closeout scope is exactly two files",
    "implementation remains documentation and test only",
    "pilot limit band remains exactly 1 through 3",
    "decision-stage order is deterministic",
    "preflight reason-code order is deterministic",
    "post-run reason-code order is deterministic",
    "positive owner identifier is mandatory",
    "explicit owner approval is mandatory",
    "reviewer approval is mandatory",
    "owner scope isolation is mandatory",
    "notification opt-in is mandatory",
    "at least one eligible due saved search is mandatory",
    "usable recipient state is mandatory",
    "concurrent owner run blocks readiness",
    "open incident blocks readiness",
    "feature gate must be enabled",
    "approved email backend is mandatory",
    "default sender configuration is mandatory",
    "sender verification is mandatory",
    "provider credentials availability is mandatory",
    "provider quota for the approved pilot limit is mandatory",
    "provider operational status is mandatory",
    "bounce and complaint ownership is mandatory",
    "approved execution window is mandatory",
    "rollback reviewer is mandatory",
    "strict readiness must report ready",
    "all nine readiness checks must remain present",
    "sanitized readiness JSON retention is mandatory",
    "deployed command help review is mandatory",
    "rollback controls must be source verified",
    "preview owner must match approved owner",
    "preview limit must match approved limit",
    "preview candidate count must be between 1 and approved limit",
    "preview skip reasons must be understood",
    "preview unexpected refusal count must be zero",
    "preview command contains no production flags",
    "production command contains both confirmation flags",
    "preflight decision result is sanitized",
    "pilot evidence record uses an allowlist",
    "sensitive evidence fields are excluded",
    "post-run failed count must be zero",
    "post-run unexpected refusal count must be zero",
    "delivery counts must reconcile",
    "persistent audit-event counts must reconcile",
    "sent timestamp evidence must reconcile",
    "duplicate-attempt review must be clean",
    "audit gaps block success",
    "provider anomaly blocks success",
    "open incident blocks success",
    "tests execute no production delivery",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v255: saved-search notification production delivery pilot readiness closeout audit"

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
)


@dataclass(frozen=True)
class PilotPreflightEvidence:
    owner_id: int = 101
    approved_limit: int = 3
    owner_approved: bool = True
    reviewer_approved: bool = True
    owner_scope_isolated: bool = True
    notification_opt_in_enabled: bool = True
    eligible_due_count: int = 2
    recipient_usable: bool = True
    concurrent_owner_run: bool = False
    unresolved_incident: bool = False
    feature_gate_enabled: bool = True
    email_backend_allowed: bool = True
    default_sender_configured: bool = True
    sender_verified: bool = True
    provider_credentials_available: bool = True
    provider_quota_available: int = 3
    provider_operational: bool = True
    bounce_complaint_owner_assigned: bool = True
    execution_window_approved: bool = True
    rollback_reviewer_available: bool = True
    strict_readiness_ready: bool = True
    readiness_check_count: int = 9
    readiness_json_retained: bool = True
    deployed_help_reviewed: bool = True
    rollback_controls_verified: bool = True
    preview_owner_id: int = 101
    preview_limit: int = 3
    preview_candidate_count: int = 2
    preview_skips_understood: bool = True
    preview_unexpected_refusal_count: int = 0


@dataclass(frozen=True)
class PilotPostRunEvidence:
    preview_candidate_count: int = 2
    delivered_count: int = 2
    skipped_count: int = 0
    refused_count: int = 0
    failed_count: int = 0
    attempted_event_count: int = 2
    succeeded_event_count: int = 2
    failed_event_count: int = 0
    timestamp_event_count: int = 2
    sent_timestamp_consistent: bool = True
    duplicate_attempt_clean: bool = True
    audit_gap_free: bool = True
    provider_anomaly: bool = False
    incident_open: bool = False


def evaluate_pilot_preflight(
    evidence: PilotPreflightEvidence,
) -> dict[str, Any]:
    reasons: list[str] = []

    if evidence.owner_id <= 0:
        reasons.append(
            "invalid_owner_id"
        )

    if not (
        PILOT_LIMIT_BAND[0]
        <= evidence.approved_limit
        <= PILOT_LIMIT_BAND[1]
    ):
        reasons.append(
            "invalid_pilot_limit"
        )

    if not evidence.owner_approved:
        reasons.append(
            "owner_not_approved"
        )

    if not evidence.reviewer_approved:
        reasons.append(
            "reviewer_not_approved"
        )

    if not evidence.owner_scope_isolated:
        reasons.append(
            "owner_scope_not_isolated"
        )

    if not evidence.notification_opt_in_enabled:
        reasons.append(
            "notification_opt_in_disabled"
        )

    if evidence.eligible_due_count <= 0:
        reasons.append(
            "no_eligible_due_saved_search"
        )

    if not evidence.recipient_usable:
        reasons.append(
            "recipient_unusable"
        )

    if evidence.concurrent_owner_run:
        reasons.append(
            "concurrent_owner_run"
        )

    if evidence.unresolved_incident:
        reasons.append(
            "unresolved_incident"
        )

    if not evidence.feature_gate_enabled:
        reasons.append(
            "feature_gate_disabled"
        )

    if not evidence.email_backend_allowed:
        reasons.append(
            "email_backend_rejected"
        )

    if not evidence.default_sender_configured:
        reasons.append(
            "default_sender_missing"
        )

    if not evidence.sender_verified:
        reasons.append(
            "sender_unverified"
        )

    if not evidence.provider_credentials_available:
        reasons.append(
            "provider_credentials_unavailable"
        )

    if (
        evidence.provider_quota_available
        < evidence.approved_limit
    ):
        reasons.append(
            "provider_quota_insufficient"
        )

    if not evidence.provider_operational:
        reasons.append(
            "provider_not_operational"
        )

    if not evidence.bounce_complaint_owner_assigned:
        reasons.append(
            "bounce_complaint_owner_missing"
        )

    if not evidence.execution_window_approved:
        reasons.append(
            "execution_window_not_approved"
        )

    if not evidence.rollback_reviewer_available:
        reasons.append(
            "rollback_reviewer_missing"
        )

    if not evidence.strict_readiness_ready:
        reasons.append(
            "strict_readiness_not_ready"
        )

    if evidence.readiness_check_count != 9:
        reasons.append(
            "readiness_check_count_mismatch"
        )

    if not evidence.readiness_json_retained:
        reasons.append(
            "readiness_json_missing"
        )

    if not evidence.deployed_help_reviewed:
        reasons.append(
            "deployed_help_not_reviewed"
        )

    if not evidence.rollback_controls_verified:
        reasons.append(
            "rollback_controls_unverified"
        )

    if evidence.preview_owner_id != evidence.owner_id:
        reasons.append(
            "preview_owner_mismatch"
        )

    if evidence.preview_limit != evidence.approved_limit:
        reasons.append(
            "preview_limit_mismatch"
        )

    if not (
        1
        <= evidence.preview_candidate_count
        <= evidence.approved_limit
    ):
        reasons.append(
            "preview_candidate_count_invalid"
        )

    if not evidence.preview_skips_understood:
        reasons.append(
            "preview_skips_unresolved"
        )

    if evidence.preview_unexpected_refusal_count != 0:
        reasons.append(
            "preview_unexpected_refusal"
        )

    reason_codes = tuple(reasons)

    return {
        "ready": not reason_codes,
        "status": (
            "ready"
            if not reason_codes
            else "not_ready"
        ),
        "reason_codes": reason_codes,
        "owner_id": evidence.owner_id,
        "approved_limit": evidence.approved_limit,
        "preview_candidate_count": (
            evidence.preview_candidate_count
        ),
    }


def evaluate_pilot_post_run(
    evidence: PilotPostRunEvidence,
) -> dict[str, Any]:
    reasons: list[str] = []

    if evidence.failed_count != 0:
        reasons.append(
            "failed_count_nonzero"
        )

    if evidence.refused_count != 0:
        reasons.append(
            "unexpected_refusal_count_nonzero"
        )

    classified_count = (
        evidence.delivered_count
        + evidence.skipped_count
        + evidence.refused_count
        + evidence.failed_count
    )

    if classified_count != evidence.preview_candidate_count:
        reasons.append(
            "delivery_counts_unreconciled"
        )

    if (
        evidence.attempted_event_count
        != evidence.delivered_count
        + evidence.failed_count
    ):
        reasons.append(
            "attempted_event_count_mismatch"
        )

    if (
        evidence.succeeded_event_count
        != evidence.delivered_count
    ):
        reasons.append(
            "success_event_count_mismatch"
        )

    if (
        evidence.failed_event_count
        != evidence.failed_count
    ):
        reasons.append(
            "failure_event_count_mismatch"
        )

    if (
        evidence.timestamp_event_count
        != evidence.delivered_count
    ):
        reasons.append(
            "timestamp_event_count_mismatch"
        )

    if not evidence.sent_timestamp_consistent:
        reasons.append(
            "sent_timestamp_inconsistent"
        )

    if not evidence.duplicate_attempt_clean:
        reasons.append(
            "duplicate_attempt_anomaly"
        )

    if not evidence.audit_gap_free:
        reasons.append(
            "audit_gap_detected"
        )

    if evidence.provider_anomaly:
        reasons.append(
            "provider_anomaly"
        )

    if evidence.incident_open:
        reasons.append(
            "incident_open"
        )

    reason_codes = tuple(reasons)

    return {
        "successful": not reason_codes,
        "status": (
            "successful"
            if not reason_codes
            else "failed"
        ),
        "reason_codes": reason_codes,
        "preview_candidate_count": (
            evidence.preview_candidate_count
        ),
        "delivered_count": evidence.delivered_count,
        "skipped_count": evidence.skipped_count,
        "refused_count": evidence.refused_count,
        "failed_count": evidence.failed_count,
    }


def sanitize_pilot_evidence_record(
    raw_record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        key: raw_record[key]
        for key in PILOT_ALLOWED_RECORD_FIELDS
        if key in raw_record
    }


class SavedSearchNotificationProductionDeliveryPilotReadinessV254Tests(
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

    def test_v254_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V254_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS,
            (
                "V254_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_READINESS"
            ),
        )

        self.assertEqual(
            len(V253_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V254_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V255_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v255: saved-search notification production "
                "delivery pilot readiness closeout audit"
            ),
        )

    def test_v254_scope_remains_documentation_and_test_only(self):
        self.assertEqual(
            V254_ALLOWED_SCOPE,
            (
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
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V254_ALLOWED_SCOPE
            )
        )

    def test_v254_pilot_limit_and_decision_stage_order_are_exact(self):
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

    def test_v254_default_preflight_evidence_is_ready(self):
        result = evaluate_pilot_preflight(
            PilotPreflightEvidence()
        )

        self.assertEqual(
            result,
            {
                "ready": True,
                "status": "ready",
                "reason_codes": (),
                "owner_id": 101,
                "approved_limit": 3,
                "preview_candidate_count": 2,
            },
        )

    def test_v254_preflight_reason_order_is_deterministic(self):
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

    def test_v254_each_preflight_failure_has_stable_reason_code(self):
        cases = (
            (
                {
                    "owner_id": 0,
                },
                "invalid_owner_id",
            ),
            (
                {
                    "approved_limit": 4,
                    "preview_limit": 4,
                },
                "invalid_pilot_limit",
            ),
            (
                {
                    "owner_approved": False,
                },
                "owner_not_approved",
            ),
            (
                {
                    "reviewer_approved": False,
                },
                "reviewer_not_approved",
            ),
            (
                {
                    "owner_scope_isolated": False,
                },
                "owner_scope_not_isolated",
            ),
            (
                {
                    "notification_opt_in_enabled": False,
                },
                "notification_opt_in_disabled",
            ),
            (
                {
                    "eligible_due_count": 0,
                },
                "no_eligible_due_saved_search",
            ),
            (
                {
                    "recipient_usable": False,
                },
                "recipient_unusable",
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
                    "bounce_complaint_owner_assigned": False,
                },
                "bounce_complaint_owner_missing",
            ),
            (
                {
                    "execution_window_approved": False,
                },
                "execution_window_not_approved",
            ),
            (
                {
                    "rollback_reviewer_available": False,
                },
                "rollback_reviewer_missing",
            ),
            (
                {
                    "strict_readiness_ready": False,
                },
                "strict_readiness_not_ready",
            ),
            (
                {
                    "readiness_check_count": 8,
                },
                "readiness_check_count_mismatch",
            ),
            (
                {
                    "readiness_json_retained": False,
                },
                "readiness_json_missing",
            ),
            (
                {
                    "deployed_help_reviewed": False,
                },
                "deployed_help_not_reviewed",
            ),
            (
                {
                    "rollback_controls_verified": False,
                },
                "rollback_controls_unverified",
            ),
            (
                {
                    "preview_owner_id": 202,
                },
                "preview_owner_mismatch",
            ),
            (
                {
                    "preview_limit": 2,
                },
                "preview_limit_mismatch",
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
        )

        base = PilotPreflightEvidence()

        for changes, expected_reason in cases:
            with self.subTest(
                expected_reason=expected_reason
            ):
                result = evaluate_pilot_preflight(
                    replace(
                        base,
                        **changes,
                    )
                )

                self.assertFalse(
                    result["ready"]
                )

                self.assertIn(
                    expected_reason,
                    result["reason_codes"],
                )

    def test_v254_preview_candidate_count_cannot_exceed_approved_limit(self):
        result = evaluate_pilot_preflight(
            replace(
                PilotPreflightEvidence(),
                approved_limit=2,
                preview_limit=2,
                preview_candidate_count=3,
            )
        )

        self.assertEqual(
            result["reason_codes"],
            (
                "preview_candidate_count_invalid",
            ),
        )

    def test_v254_preflight_result_is_sanitized(self):
        result = evaluate_pilot_preflight(
            PilotPreflightEvidence()
        )

        self.assertEqual(
            set(result),
            {
                "ready",
                "status",
                "reason_codes",
                "owner_id",
                "approved_limit",
                "preview_candidate_count",
            },
        )

        serialized = repr(result).lower()

        for term in (
            "password",
            "api_key",
            "access_token",
            "recipient_email",
            "rendered_body",
            "provider_response",
        ):
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    serialized,
                )

    def test_v254_evidence_record_uses_strict_allowlist(self):
        raw_record = {
            field: f"value-{index}"
            for index, field in enumerate(
                PILOT_ALLOWED_RECORD_FIELDS,
                start=1,
            )
        }

        raw_record.update(
            {
                field: f"secret-{index}"
                for index, field in enumerate(
                    PILOT_SENSITIVE_RECORD_FIELDS,
                    start=1,
                )
            }
        )

        sanitized = sanitize_pilot_evidence_record(
            raw_record
        )

        self.assertEqual(
            tuple(sanitized),
            PILOT_ALLOWED_RECORD_FIELDS,
        )

        for field in PILOT_SENSITIVE_RECORD_FIELDS:
            with self.subTest(
                field=field
            ):
                self.assertNotIn(
                    field,
                    sanitized,
                )

    def test_v254_preview_command_is_nonproduction_and_owner_scoped(self):
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

    def test_v254_production_command_keeps_double_confirmation(self):
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

    def test_v254_default_post_run_evidence_is_successful(self):
        result = evaluate_pilot_post_run(
            PilotPostRunEvidence()
        )

        self.assertEqual(
            result,
            {
                "successful": True,
                "status": "successful",
                "reason_codes": (),
                "preview_candidate_count": 2,
                "delivered_count": 2,
                "skipped_count": 0,
                "refused_count": 0,
                "failed_count": 0,
            },
        )

    def test_v254_post_run_reason_order_is_deterministic(self):
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

    def test_v254_each_post_run_failure_has_stable_reason_code(self):
        cases = (
            (
                {
                    "preview_candidate_count": 3,
                    "delivered_count": 2,
                    "failed_count": 1,
                    "attempted_event_count": 3,
                    "failed_event_count": 1,
                },
                "failed_count_nonzero",
            ),
            (
                {
                    "preview_candidate_count": 3,
                    "delivered_count": 2,
                    "refused_count": 1,
                },
                "unexpected_refusal_count_nonzero",
            ),
            (
                {
                    "preview_candidate_count": 3,
                },
                "delivery_counts_unreconciled",
            ),
            (
                {
                    "attempted_event_count": 1,
                },
                "attempted_event_count_mismatch",
            ),
            (
                {
                    "succeeded_event_count": 1,
                },
                "success_event_count_mismatch",
            ),
            (
                {
                    "failed_event_count": 1,
                },
                "failure_event_count_mismatch",
            ),
            (
                {
                    "timestamp_event_count": 1,
                },
                "timestamp_event_count_mismatch",
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
                "duplicate_attempt_anomaly",
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
                "provider_anomaly",
            ),
            (
                {
                    "incident_open": True,
                },
                "incident_open",
            ),
        )

        base = PilotPostRunEvidence()

        for changes, expected_reason in cases:
            with self.subTest(
                expected_reason=expected_reason
            ):
                result = evaluate_pilot_post_run(
                    replace(
                        base,
                        **changes,
                    )
                )

                self.assertFalse(
                    result["successful"]
                )

                self.assertIn(
                    expected_reason,
                    result["reason_codes"],
                )

    def test_v254_post_run_allows_understood_skips(self):
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

    def test_v254_default_readiness_remains_not_ready(self):
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
    def test_v254_production_like_readiness_remains_ready(self):
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
    def test_v254_readiness_execution_opens_no_email_connection(self):
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

    def test_v254_command_surfaces_remain_unchanged(self):
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

    def test_v254_production_batch_cap_remains_25(self):
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

    def test_v254_scheduler_remains_nonautomatic(self):
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

    def test_v254_v253_contract_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_readiness_contract_v253.py"
        )

        self.assertIn(
            (
                "V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_READINESS_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v254: saved-search notification production "
                "delivery pilot readiness implementation"
            ),
            source,
        )

    def test_v254_historical_safety_package_is_present(self):
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

    def test_v254_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V254_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS
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

    def test_v254_no_migration_0017_exists(self):
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

    def test_v254_implementation_gate_matrix_is_complete(self):
        required = {
            "v253 pilot-readiness contract remains packaged",
            "v254 scope is exactly two implementation files",
            "v255 proposed closeout scope is exactly two files",
            "implementation remains documentation and test only",
            "pilot limit band remains exactly 1 through 3",
            "decision-stage order is deterministic",
            "preflight reason-code order is deterministic",
            "post-run reason-code order is deterministic",
            "positive owner identifier is mandatory",
            "explicit owner approval is mandatory",
            "reviewer approval is mandatory",
            "strict readiness must report ready",
            "all nine readiness checks must remain present",
            "preview owner must match approved owner",
            "preview limit must match approved limit",
            "preview candidate count must be between 1 and approved limit",
            "preview command contains no production flags",
            "production command contains both confirmation flags",
            "preflight decision result is sanitized",
            "pilot evidence record uses an allowlist",
            "sensitive evidence fields are excluded",
            "post-run failed count must be zero",
            "post-run unexpected refusal count must be zero",
            "delivery counts must reconcile",
            "persistent audit-event counts must reconcile",
            "sent timestamp evidence must reconcile",
            "duplicate-attempt review must be clean",
            "tests execute no production delivery",
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
                set(PILOT_IMPLEMENTATION_GATES)
            )
        )
