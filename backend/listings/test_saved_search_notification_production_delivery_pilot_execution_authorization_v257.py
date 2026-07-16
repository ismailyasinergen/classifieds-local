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
from listings.test_saved_search_notification_production_delivery_pilot_execution_authorization_contract_v256 import (
    AUTHORIZATION_COMMAND_FINGERPRINT_FIELDS,
    AUTHORIZATION_EVIDENCE_FIELDS,
    AUTHORIZATION_IMMUTABLE_BINDINGS,
    AUTHORIZATION_LIFECYCLE_STATES,
    AUTHORIZATION_LIMIT_BAND,
    AUTHORIZATION_PRIVACY_EXCLUSIONS,
    AUTHORIZATION_PROHIBITED_ACTIONS,
    AUTHORIZATION_STAGE_ORDER,
    AUTHORIZATION_STOP_REASONS,
    AUTHORIZATION_TERMINAL_STATES,
    AUTHORIZATION_TIME_WINDOWS_SECONDS,
)


V257_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION = (
    "V257_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION"
)

V256_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_contract_v256.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_execution_authorization_contract_v256.md"
    ),
)

V257_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_v257.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_execution_authorization_v257.md"
    ),
)

V258_PROPOSED_SCOPE = (
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

AUTHORIZATION_RESULT_FIELDS = (
    "authorized",
    "status",
    "reason_codes",
    "authorization_id",
    "pilot_owner_id",
    "approved_limit",
    "preview_candidate_count",
    "command_fingerprint",
    "expires_at_utc",
)

AUTHORIZATION_CONSUMPTION_RESULT_FIELDS = (
    "consumed",
    "status",
    "reason_codes",
    "authorization_id",
    "authorization_state",
    "consumed_at_utc",
)

AUTHORIZATION_EVIDENCE_ALLOWLIST = (
    "authorization_id",
    "change_record_id",
    "pilot_owner_id",
    "approved_limit",
    "preview_candidate_count",
    "readiness_status",
    "readiness_ready_count",
    "readiness_not_ready_count",
    "readiness_warning_count",
    "readiness_checked_at_utc",
    "preview_checked_at_utc",
    "issued_at_utc",
    "expires_at_utc",
    "operator_identity",
    "primary_reviewer_identity",
    "secondary_reviewer_identity",
    "provider_status",
    "sender_verification_status",
    "feature_gate_verified",
    "backend_policy_verified",
    "rollback_reviewer_identity",
    "command_fingerprint",
    "authorization_state",
    "consumed_at_utc",
    "decision",
    "reason_codes",
    "incident_reference",
)

AUTHORIZATION_SENSITIVE_FIELDS = (
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

AUTHORIZATION_STATE_ACTIONS = {
    "submit": {
        "draft": "ready_for_review",
    },
    "authorize": {
        "ready_for_review": "authorized",
    },
    "consume": {
        "authorized": "consumed",
    },
    "expire": {
        "authorized": "expired",
    },
    "revoke": {
        "draft": "revoked",
        "ready_for_review": "revoked",
        "authorized": "revoked",
    },
    "fail_closed": {
        "draft": "failed_closed",
        "ready_for_review": "failed_closed",
        "authorized": "failed_closed",
    },
}

V257_IMPLEMENTATION_GATES = (
    "v256 authorization contract remains packaged",
    "v257 scope is exactly two implementation files",
    "v258 closeout scope is exactly two files",
    "implementation remains documentation and test only",
    "authorization limit remains 1 through 3",
    "readiness maximum age remains 300 seconds",
    "preview maximum age remains 300 seconds",
    "authorization lifetime remains 600 seconds",
    "command fingerprint uses canonical SHA-256",
    "command fingerprint binds both confirmation flags",
    "command fingerprint binds owner identifier",
    "command fingerprint binds approved limit",
    "authorization evaluation is deterministic",
    "authorization stop-reason order is deterministic",
    "owner identifier must be positive",
    "approved limit must remain between 1 and 3",
    "preview owner must match approved owner",
    "preview limit must match approved limit",
    "preview candidate count must be bounded",
    "strict readiness status must be ready",
    "all nine readiness checks remain required",
    "readiness evidence freshness is enforced",
    "preview evidence freshness is enforced",
    "authorization lifetime is enforced",
    "expired authorization is rejected",
    "consumed authorization is rejected",
    "revoked authorization is rejected",
    "failed-closed authorization is rejected",
    "feature gate must remain enabled",
    "approved backend must remain configured",
    "default sender must remain configured",
    "sender identity or domain must remain verified",
    "provider credentials must remain available",
    "provider quota must cover approved limit",
    "provider status must remain operational",
    "concurrent owner run blocks authorization",
    "open incident blocks authorization",
    "rollback reviewer remains mandatory",
    "primary reviewer remains mandatory",
    "secondary reviewer remains mandatory",
    "reviewer identities must remain distinct",
    "operator identity remains mandatory",
    "command fingerprint must match immutable bindings",
    "both production confirmations remain mandatory",
    "lifecycle transitions are deterministic",
    "terminal states cannot reopen",
    "authorization is consumed exactly once",
    "authorization reuse fails closed",
    "immutable binding snapshot is deterministic",
    "evidence sanitizer is allowlist based",
    "sensitive evidence fields are excluded",
    "tests perform no production delivery",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v258: saved-search notification production delivery pilot execution authorization closeout audit"

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
        "pilot_execution_authorization_contract_v256.py"
    ),
)


def build_command_fingerprint(
    *,
    command_name: str,
    execute_production_send: bool,
    confirm_production_delivery: bool,
    owner_id: int,
    limit: int,
) -> str:
    payload = {
        "command_name": command_name,
        "execute_production_send": execute_production_send,
        "confirm_production_delivery": confirm_production_delivery,
        "owner_id": owner_id,
        "limit": limit,
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


@dataclass(frozen=True)
class AuthorizationEvidence:
    authorization_id: str = "authorization-001"
    change_record_id: str = "change-001"
    pilot_readiness_lane_closed: bool = True
    pilot_owner_id: int = 101
    approved_limit: int = 3
    preview_owner_id: int = 101
    preview_limit: int = 3
    preview_candidate_count: int = 2
    readiness_status: str = "ready"
    readiness_check_count: int = 9
    readiness_checked_at_utc: int = 900
    preview_checked_at_utc: int = 900
    issued_at_utc: int = 950
    expires_at_utc: int = 1550
    feature_gate_enabled: bool = True
    email_backend_allowed: bool = True
    default_sender_configured: bool = True
    sender_verified: bool = True
    provider_credentials_available: bool = True
    provider_quota_available: int = 3
    provider_operational: bool = True
    concurrent_owner_run: bool = False
    unresolved_incident: bool = False
    rollback_reviewer_available: bool = True
    operator_identity: str = "operator-a"
    primary_reviewer_identity: str = "reviewer-a"
    secondary_reviewer_identity: str = "reviewer-b"
    command_name: str = "process_saved_search_notifications"
    execute_production_send: bool = True
    confirm_production_delivery: bool = True
    command_owner_id: int = 101
    command_limit: int = 3
    command_fingerprint: str = ""
    authorization_state: str = "authorized"
    consumed_at_utc: int | None = None


def make_authorization_evidence(
    **changes: Any,
) -> AuthorizationEvidence:
    evidence = replace(
        AuthorizationEvidence(),
        **changes,
    )

    if "command_fingerprint" in changes:
        return evidence

    fingerprint = build_command_fingerprint(
        command_name=evidence.command_name,
        execute_production_send=(
            evidence.execute_production_send
        ),
        confirm_production_delivery=(
            evidence.confirm_production_delivery
        ),
        owner_id=evidence.command_owner_id,
        limit=evidence.command_limit,
    )

    return replace(
        evidence,
        command_fingerprint=fingerprint,
    )


def immutable_binding_snapshot(
    evidence: AuthorizationEvidence,
) -> dict[str, Any]:
    source = {
        "authorization_id": evidence.authorization_id,
        "change_record_id": evidence.change_record_id,
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
        "command_fingerprint": evidence.command_fingerprint,
        "issued_at_utc": evidence.issued_at_utc,
        "expires_at_utc": evidence.expires_at_utc,
    }

    return {
        field: source[field]
        for field in AUTHORIZATION_IMMUTABLE_BINDINGS
    }


def evaluate_authorization(
    evidence: AuthorizationEvidence,
    *,
    now_utc: int,
) -> dict[str, Any]:
    reasons: list[str] = []

    def add(reason: str) -> None:
        if reason not in reasons:
            reasons.append(
                reason
            )

    if not evidence.pilot_readiness_lane_closed:
        add(
            "pilot_readiness_lane_not_closed"
        )

    if evidence.pilot_owner_id <= 0:
        add(
            "invalid_owner_id"
        )

    if not (
        AUTHORIZATION_LIMIT_BAND[0]
        <= evidence.approved_limit
        <= AUTHORIZATION_LIMIT_BAND[1]
    ):
        add(
            "invalid_pilot_limit"
        )

    if evidence.preview_owner_id != evidence.pilot_owner_id:
        add(
            "preview_owner_mismatch"
        )

    if evidence.preview_limit != evidence.approved_limit:
        add(
            "preview_limit_mismatch"
        )

    if not (
        1
        <= evidence.preview_candidate_count
        <= evidence.approved_limit
    ):
        add(
            "preview_candidate_count_invalid"
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
        <= AUTHORIZATION_TIME_WINDOWS_SECONDS[
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
        <= AUTHORIZATION_TIME_WINDOWS_SECONDS[
            "preview_max_age"
        ]
    ):
        add(
            "preview_evidence_stale"
        )

    authorization_ttl = (
        evidence.expires_at_utc
        - evidence.issued_at_utc
    )

    if not (
        0
        < authorization_ttl
        <= AUTHORIZATION_TIME_WINDOWS_SECONDS[
            "authorization_ttl"
        ]
    ):
        add(
            "authorization_ttl_invalid"
        )

    if (
        now_utc
        >= evidence.expires_at_utc
        or evidence.authorization_state == "expired"
    ):
        add(
            "authorization_expired"
        )

    if (
        evidence.authorization_state == "consumed"
        or evidence.consumed_at_utc is not None
    ):
        add(
            "authorization_already_consumed"
        )

    if evidence.authorization_state == "revoked":
        add(
            "authorization_revoked"
        )

    if (
        evidence.authorization_state == "failed_closed"
        or evidence.authorization_state
        not in AUTHORIZATION_LIFECYCLE_STATES
        or evidence.authorization_state
        in {
            "draft",
            "ready_for_review",
        }
    ):
        add(
            "authorization_failed_closed"
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

    if evidence.concurrent_owner_run:
        add(
            "concurrent_owner_run"
        )

    if evidence.unresolved_incident:
        add(
            "unresolved_incident"
        )

    if not evidence.rollback_reviewer_available:
        add(
            "rollback_reviewer_missing"
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

    if not evidence.operator_identity.strip():
        add(
            "operator_identity_missing"
        )

    expected_fingerprint = build_command_fingerprint(
        command_name=evidence.command_name,
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
        evidence.command_owner_id
        != evidence.pilot_owner_id
        or evidence.command_limit
        != evidence.approved_limit
        or evidence.command_fingerprint
        != expected_fingerprint
    ):
        add(
            "command_fingerprint_mismatch"
        )

    if not (
        evidence.execute_production_send
        and evidence.confirm_production_delivery
    ):
        add(
            "production_confirmation_missing"
        )

    order = {
        reason: index
        for index, reason in enumerate(
            AUTHORIZATION_STOP_REASONS
        )
    }

    reason_codes = tuple(
        sorted(
            reasons,
            key=order.__getitem__,
        )
    )

    return {
        "authorized": not reason_codes,
        "status": (
            "authorized"
            if not reason_codes
            else "not_authorized"
        ),
        "reason_codes": reason_codes,
        "authorization_id": evidence.authorization_id,
        "pilot_owner_id": evidence.pilot_owner_id,
        "approved_limit": evidence.approved_limit,
        "preview_candidate_count": (
            evidence.preview_candidate_count
        ),
        "command_fingerprint": evidence.command_fingerprint,
        "expires_at_utc": evidence.expires_at_utc,
    }


def transition_authorization_state(
    *,
    current_state: str,
    action: str,
) -> dict[str, Any]:
    if current_state in AUTHORIZATION_TERMINAL_STATES:
        return {
            "applied": False,
            "state": current_state,
            "reason_code": "terminal_state_locked",
        }

    target = (
        AUTHORIZATION_STATE_ACTIONS
        .get(
            action,
            {},
        )
        .get(
            current_state
        )
    )

    if target is None:
        return {
            "applied": False,
            "state": "failed_closed",
            "reason_code": "invalid_state_transition",
        }

    return {
        "applied": True,
        "state": target,
        "reason_code": "applied",
    }


def consume_authorization(
    evidence: AuthorizationEvidence,
    *,
    now_utc: int,
    presented_fingerprint: str,
) -> dict[str, Any]:
    if (
        presented_fingerprint
        != evidence.command_fingerprint
    ):
        return {
            "consumed": False,
            "status": "failed_closed",
            "reason_codes": (
                "command_fingerprint_mismatch",
            ),
            "authorization_id": evidence.authorization_id,
            "authorization_state": "failed_closed",
            "consumed_at_utc": None,
        }

    decision = evaluate_authorization(
        evidence,
        now_utc=now_utc,
    )

    if not decision["authorized"]:
        return {
            "consumed": False,
            "status": "failed_closed",
            "reason_codes": decision["reason_codes"],
            "authorization_id": evidence.authorization_id,
            "authorization_state": "failed_closed",
            "consumed_at_utc": None,
        }

    transition = transition_authorization_state(
        current_state=evidence.authorization_state,
        action="consume",
    )

    if not transition["applied"]:
        return {
            "consumed": False,
            "status": "failed_closed",
            "reason_codes": (
                transition["reason_code"],
            ),
            "authorization_id": evidence.authorization_id,
            "authorization_state": transition["state"],
            "consumed_at_utc": None,
        }

    return {
        "consumed": True,
        "status": "consumed",
        "reason_codes": (),
        "authorization_id": evidence.authorization_id,
        "authorization_state": "consumed",
        "consumed_at_utc": now_utc,
    }


def sanitize_authorization_evidence(
    raw_record: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        field: raw_record[field]
        for field in AUTHORIZATION_EVIDENCE_ALLOWLIST
        if field in raw_record
    }


class SavedSearchNotificationProductionDeliveryPilotExecutionAuthorizationV257Tests(
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

    def test_v257_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V257_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION,
            (
                "V257_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_EXECUTION_AUTHORIZATION"
            ),
        )

        self.assertEqual(
            len(V256_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V257_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V258_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v258: saved-search notification production "
                "delivery pilot execution authorization closeout audit"
            ),
        )

    def test_v257_scope_remains_documentation_and_test_only(self):
        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V257_ALLOWED_SCOPE
            )
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V258_PROPOSED_SCOPE
            )
        )

    def test_v257_contract_constants_remain_exact(self):
        self.assertEqual(
            AUTHORIZATION_LIMIT_BAND,
            (
                1,
                3,
            ),
        )

        self.assertEqual(
            AUTHORIZATION_TIME_WINDOWS_SECONDS,
            {
                "readiness_max_age": 300,
                "preview_max_age": 300,
                "authorization_ttl": 600,
            },
        )

        self.assertEqual(
            len(AUTHORIZATION_STOP_REASONS),
            31,
        )

        self.assertEqual(
            len(AUTHORIZATION_STAGE_ORDER),
            8,
        )

    def test_v257_command_fingerprint_is_deterministic(self):
        first = build_command_fingerprint(
            command_name="process_saved_search_notifications",
            execute_production_send=True,
            confirm_production_delivery=True,
            owner_id=101,
            limit=3,
        )

        second = build_command_fingerprint(
            command_name="process_saved_search_notifications",
            execute_production_send=True,
            confirm_production_delivery=True,
            owner_id=101,
            limit=3,
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            len(first),
            64,
        )

    def test_v257_command_fingerprint_binds_each_field(self):
        base = {
            "command_name": "process_saved_search_notifications",
            "execute_production_send": True,
            "confirm_production_delivery": True,
            "owner_id": 101,
            "limit": 3,
        }

        baseline = build_command_fingerprint(
            **base
        )

        variants = (
            {
                **base,
                "command_name": "other",
            },
            {
                **base,
                "execute_production_send": False,
            },
            {
                **base,
                "confirm_production_delivery": False,
            },
            {
                **base,
                "owner_id": 102,
            },
            {
                **base,
                "limit": 2,
            },
        )

        for variant in variants:
            with self.subTest(
                variant=variant
            ):
                self.assertNotEqual(
                    build_command_fingerprint(
                        **variant
                    ),
                    baseline,
                )

    def test_v257_default_authorization_is_authorized(self):
        evidence = make_authorization_evidence()

        result = evaluate_authorization(
            evidence,
            now_utc=1000,
        )

        self.assertEqual(
            result,
            {
                "authorized": True,
                "status": "authorized",
                "reason_codes": (),
                "authorization_id": "authorization-001",
                "pilot_owner_id": 101,
                "approved_limit": 3,
                "preview_candidate_count": 2,
                "command_fingerprint": (
                    evidence.command_fingerprint
                ),
                "expires_at_utc": 1550,
            },
        )

    def test_v257_authorization_result_schema_is_sanitized(self):
        result = evaluate_authorization(
            make_authorization_evidence(),
            now_utc=1000,
        )

        self.assertEqual(
            tuple(result),
            AUTHORIZATION_RESULT_FIELDS,
        )

        serialized = repr(
            result
        ).lower()

        for term in (
            "password",
            "api_key",
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

    def test_v257_limit_boundaries_are_fail_closed(self):
        for limit, authorized in (
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

                evidence = make_authorization_evidence(
                    approved_limit=limit,
                    preview_limit=limit,
                    preview_candidate_count=candidate_count,
                    provider_quota_available=max(
                        limit,
                        0,
                    ),
                    command_limit=limit,
                )

                result = evaluate_authorization(
                    evidence,
                    now_utc=1000,
                )

                self.assertEqual(
                    result["authorized"],
                    authorized,
                )

    def test_v257_freshness_boundaries_are_inclusive(self):
        evidence = make_authorization_evidence(
            readiness_checked_at_utc=700,
            preview_checked_at_utc=700,
        )

        result = evaluate_authorization(
            evidence,
            now_utc=1000,
        )

        self.assertTrue(
            result["authorized"]
        )

    def test_v257_stale_readiness_and_preview_fail_closed(self):
        evidence = make_authorization_evidence(
            readiness_checked_at_utc=699,
            preview_checked_at_utc=699,
        )

        result = evaluate_authorization(
            evidence,
            now_utc=1000,
        )

        self.assertEqual(
            result["reason_codes"],
            (
                "readiness_evidence_stale",
                "preview_evidence_stale",
            ),
        )

    def test_v257_authorization_ttl_boundary_is_enforced(self):
        valid = evaluate_authorization(
            make_authorization_evidence(
                issued_at_utc=950,
                expires_at_utc=1550,
            ),
            now_utc=1000,
        )

        invalid = evaluate_authorization(
            make_authorization_evidence(
                issued_at_utc=950,
                expires_at_utc=1551,
            ),
            now_utc=1000,
        )

        self.assertTrue(
            valid["authorized"]
        )

        self.assertIn(
            "authorization_ttl_invalid",
            invalid["reason_codes"],
        )

    def test_v257_expired_authorization_fails_closed(self):
        result = evaluate_authorization(
            make_authorization_evidence(
                issued_at_utc=300,
                expires_at_utc=900,
            ),
            now_utc=1000,
        )

        self.assertIn(
            "authorization_expired",
            result["reason_codes"],
        )

    def test_v257_terminal_authorization_states_fail_closed(self):
        cases = (
            (
                "consumed",
                "authorization_already_consumed",
            ),
            (
                "expired",
                "authorization_expired",
            ),
            (
                "revoked",
                "authorization_revoked",
            ),
            (
                "failed_closed",
                "authorization_failed_closed",
            ),
        )

        for state, reason in cases:
            with self.subTest(
                state=state
            ):
                result = evaluate_authorization(
                    make_authorization_evidence(
                        authorization_state=state,
                        consumed_at_utc=(
                            999
                            if state == "consumed"
                            else None
                        ),
                    ),
                    now_utc=1000,
                )

                self.assertFalse(
                    result["authorized"]
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v257_each_stop_reason_is_reachable(self):
        cases = (
            (
                {
                    "pilot_readiness_lane_closed": False,
                },
                "pilot_readiness_lane_not_closed",
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
                    "preview_owner_id": 999,
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
                    "expires_at_utc": 1551,
                },
                "authorization_ttl_invalid",
            ),
            (
                {
                    "issued_at_utc": 300,
                    "expires_at_utc": 900,
                },
                "authorization_expired",
            ),
            (
                {
                    "authorization_state": "consumed",
                    "consumed_at_utc": 999,
                },
                "authorization_already_consumed",
            ),
            (
                {
                    "authorization_state": "revoked",
                },
                "authorization_revoked",
            ),
            (
                {
                    "authorization_state": "failed_closed",
                },
                "authorization_failed_closed",
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
                    "rollback_reviewer_available": False,
                },
                "rollback_reviewer_missing",
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
                    "operator_identity": "",
                },
                "operator_identity_missing",
            ),
            (
                {
                    "command_owner_id": 999,
                },
                "command_fingerprint_mismatch",
            ),
            (
                {
                    "execute_production_send": False,
                },
                "production_confirmation_missing",
            ),
        )

        self.assertEqual(
            len(cases),
            len(AUTHORIZATION_STOP_REASONS),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_authorization(
                    make_authorization_evidence(
                        **changes
                    ),
                    now_utc=1000,
                )

                self.assertFalse(
                    result["authorized"]
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v257_reason_code_order_matches_contract(self):
        result = evaluate_authorization(
            make_authorization_evidence(
                pilot_readiness_lane_closed=False,
                pilot_owner_id=0,
                approved_limit=4,
                preview_owner_id=999,
                preview_limit=2,
                preview_candidate_count=0,
                readiness_status="not_ready",
                readiness_check_count=8,
                readiness_checked_at_utc=699,
                preview_checked_at_utc=699,
                feature_gate_enabled=False,
                email_backend_allowed=False,
                default_sender_configured=False,
                sender_verified=False,
                provider_credentials_available=False,
                provider_quota_available=0,
                provider_operational=False,
                concurrent_owner_run=True,
                unresolved_incident=True,
                rollback_reviewer_available=False,
                primary_reviewer_identity="",
                secondary_reviewer_identity="",
                operator_identity="",
                command_owner_id=999,
                command_limit=2,
                execute_production_send=False,
                confirm_production_delivery=False,
            ),
            now_utc=1000,
        )

        order = {
            reason: index
            for index, reason in enumerate(
                AUTHORIZATION_STOP_REASONS
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

    def test_v257_immutable_binding_snapshot_is_exact(self):
        evidence = make_authorization_evidence()

        snapshot = immutable_binding_snapshot(
            evidence
        )

        self.assertEqual(
            tuple(snapshot),
            AUTHORIZATION_IMMUTABLE_BINDINGS,
        )

        self.assertEqual(
            snapshot["pilot_owner_id"],
            101,
        )

        self.assertEqual(
            snapshot["approved_limit"],
            3,
        )

    def test_v257_valid_lifecycle_sequence_is_deterministic(self):
        state = "draft"

        for action, expected_state in (
            (
                "submit",
                "ready_for_review",
            ),
            (
                "authorize",
                "authorized",
            ),
            (
                "consume",
                "consumed",
            ),
        ):
            transition = transition_authorization_state(
                current_state=state,
                action=action,
            )

            self.assertTrue(
                transition["applied"]
            )

            self.assertEqual(
                transition["state"],
                expected_state,
            )

            state = transition["state"]

    def test_v257_terminal_states_cannot_reopen(self):
        for state in AUTHORIZATION_TERMINAL_STATES:
            with self.subTest(
                state=state
            ):
                transition = transition_authorization_state(
                    current_state=state,
                    action="authorize",
                )

                self.assertFalse(
                    transition["applied"]
                )

                self.assertEqual(
                    transition["state"],
                    state,
                )

                self.assertEqual(
                    transition["reason_code"],
                    "terminal_state_locked",
                )

    def test_v257_invalid_transition_fails_closed(self):
        transition = transition_authorization_state(
            current_state="draft",
            action="consume",
        )

        self.assertEqual(
            transition,
            {
                "applied": False,
                "state": "failed_closed",
                "reason_code": "invalid_state_transition",
            },
        )

    def test_v257_authorization_consumes_exactly_once(self):
        evidence = make_authorization_evidence()

        first = consume_authorization(
            evidence,
            now_utc=1000,
            presented_fingerprint=(
                evidence.command_fingerprint
            ),
        )

        self.assertEqual(
            tuple(first),
            AUTHORIZATION_CONSUMPTION_RESULT_FIELDS,
        )

        self.assertTrue(
            first["consumed"]
        )

        consumed_evidence = replace(
            evidence,
            authorization_state="consumed",
            consumed_at_utc=1000,
        )

        second = consume_authorization(
            consumed_evidence,
            now_utc=1001,
            presented_fingerprint=(
                evidence.command_fingerprint
            ),
        )

        self.assertFalse(
            second["consumed"]
        )

        self.assertIn(
            "authorization_already_consumed",
            second["reason_codes"],
        )

    def test_v257_presented_fingerprint_mismatch_fails_closed(self):
        evidence = make_authorization_evidence()

        result = consume_authorization(
            evidence,
            now_utc=1000,
            presented_fingerprint="wrong",
        )

        self.assertEqual(
            result["reason_codes"],
            (
                "command_fingerprint_mismatch",
            ),
        )

        self.assertEqual(
            result["authorization_state"],
            "failed_closed",
        )

    def test_v257_evidence_sanitizer_uses_strict_allowlist(self):
        raw_record = {
            field: f"allowed-{index}"
            for index, field in enumerate(
                AUTHORIZATION_EVIDENCE_ALLOWLIST,
                start=1,
            )
        }

        raw_record.update(
            {
                field: f"sensitive-{index}"
                for index, field in enumerate(
                    AUTHORIZATION_SENSITIVE_FIELDS,
                    start=1,
                )
            }
        )

        raw_record["unknown_field"] = "discard"

        sanitized = sanitize_authorization_evidence(
            raw_record
        )

        self.assertEqual(
            tuple(sanitized),
            AUTHORIZATION_EVIDENCE_ALLOWLIST,
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        for field in AUTHORIZATION_SENSITIVE_FIELDS:
            with self.subTest(
                field=field
            ):
                self.assertNotIn(
                    field,
                    sanitized,
                )

    def test_v257_contract_evidence_fields_match_allowlist(self):
        self.assertEqual(
            AUTHORIZATION_EVIDENCE_ALLOWLIST,
            AUTHORIZATION_EVIDENCE_FIELDS,
        )

        self.assertTrue(
            set(AUTHORIZATION_EVIDENCE_ALLOWLIST)
            .isdisjoint(
                AUTHORIZATION_SENSITIVE_FIELDS
            )
        )

    def test_v257_contract_privacy_and_prohibitions_remain_packaged(self):
        self.assertIn(
            "SMTP password",
            AUTHORIZATION_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "authorization reuse",
            AUTHORIZATION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "global all-owner execution",
            AUTHORIZATION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "multi-owner command execution",
            AUTHORIZATION_PROHIBITED_ACTIONS,
        )

    def test_v257_default_readiness_remains_not_ready(self):
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
    def test_v257_production_like_readiness_remains_ready(self):
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
    def test_v257_readiness_execution_opens_no_email_connection(self):
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

    def test_v257_command_surfaces_remain_unchanged(self):
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

    def test_v257_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v257_scheduler_remains_nonautomatic(self):
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

    def test_v257_v256_contract_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_execution_authorization_contract_v256.py"
        )

        self.assertIn(
            (
                "V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v257: saved-search notification production "
                "delivery pilot execution authorization implementation"
            ),
            source,
        )

    def test_v257_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V257_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION
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

    def test_v257_no_migration_0017_exists(self):
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

    def test_v257_implementation_gate_matrix_is_complete(self):
        required = {
            "v256 authorization contract remains packaged",
            "v257 scope is exactly two implementation files",
            "v258 closeout scope is exactly two files",
            "implementation remains documentation and test only",
            "authorization limit remains 1 through 3",
            "readiness maximum age remains 300 seconds",
            "preview maximum age remains 300 seconds",
            "authorization lifetime remains 600 seconds",
            "command fingerprint uses canonical SHA-256",
            "authorization evaluation is deterministic",
            "authorization stop-reason order is deterministic",
            "authorization is consumed exactly once",
            "authorization reuse fails closed",
            "terminal states cannot reopen",
            "evidence sanitizer is allowlist based",
            "sensitive evidence fields are excluded",
            "tests perform no production delivery",
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
                set(V257_IMPLEMENTATION_GATES)
            )
        )
