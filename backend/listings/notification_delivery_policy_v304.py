from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from accounts.models import EmailVerificationState

from listings.models import NotificationDeliveryEvent


V304_NOTIFICATION_DELIVERY_POLICY_BASELINE = (
    "V304_NOTIFICATION_DELIVERY_POLICY_BASELINE"
)

V304_NOTIFICATION_DELIVERY_POLICY_SCHEMA_VERSION = 1

V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT = (
    "redacted_by_default"
)

V304_VERIFIED_RECIPIENT_FIELD_CANDIDATES = frozenset(
    {
        "email_verified",
        "email_verified_at",
        "is_email_verified",
        "verified_email",
        "verified_email_at",
    }
)

V306_VERIFIED_RECIPIENT_STATE_MODEL = (
    "accounts.EmailVerificationState"
)

V306_VERIFIED_RECIPIENT_REQUIRED_FIELDS = frozenset(
    {
        "user",
        "email_snapshot",
        "verified_at",
        "verification_method",
        "token_version",
        "last_requested_at",
    }
)

V304_PROVIDER_MESSAGE_ID_FIELD_CANDIDATES = frozenset(
    {
        "provider_message_id",
        "provider_delivery_id",
    }
)

V304_PROVIDER_OUTCOME_FIELD_CANDIDATES = frozenset(
    {
        "provider_event_id",
        "provider_outcome",
        "provider_status",
        "provider_delivery_status",
        "bounced_at",
        "complained_at",
    }
)

from listings.notification_recipient_output_redaction_v305 import (
    V305_MIGRATED_RECIPIENT_OUTPUT_SURFACES,
)


V304_MIGRATED_RECIPIENT_OUTPUT_SURFACES = (
    V305_MIGRATED_RECIPIENT_OUTPUT_SURFACES
)
V304_LEGACY_RECIPIENT_OUTPUT_SURFACES = ()


@dataclass(frozen=True)
class NotificationDeliveryPolicyCheckV304:
    check_id: str
    category: str
    status: str
    ready: bool
    blocking: bool
    enforcement_enabled: bool
    reason_code: str
    current_contract: str
    required_contract: str
    safe_default: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _model_field_names(model) -> frozenset[str]:
    return frozenset(
        field.name
        for field in model._meta.get_fields()
        if getattr(field, "concrete", False)
    )


def _positive_integer_or_none(value) -> int | None:
    if isinstance(value, bool):
        return None

    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None

    if normalized <= 0:
        return None

    return normalized


def discover_notification_delivery_policy_capabilities_v304(
) -> dict[str, Any]:
    verification_state_fields = _model_field_names(
        EmailVerificationState
    )

    event_fields = _model_field_names(
        NotificationDeliveryEvent
    )

    verified_fields = sorted(
        verification_state_fields
        & V306_VERIFIED_RECIPIENT_REQUIRED_FIELDS
    )

    verified_recipient_state = (
        V306_VERIFIED_RECIPIENT_REQUIRED_FIELDS
        <= verification_state_fields
    )

    provider_message_id_fields = sorted(
        event_fields
        & V304_PROVIDER_MESSAGE_ID_FIELD_CANDIDATES
    )

    provider_outcome_fields = sorted(
        event_fields
        & V304_PROVIDER_OUTCOME_FIELD_CANDIDATES
    )

    retention_days = _positive_integer_or_none(
        getattr(
            settings,
            "NOTIFICATION_DELIVERY_EVENT_RETENTION_DAYS",
            None,
        )
    )

    operator_output_policy = str(
        getattr(
            settings,
            "NOTIFICATION_OPERATOR_RECIPIENT_OUTPUT_POLICY",
            "",
        )
        or ""
    ).strip().casefold()

    return {
        "verified_recipient_state": (
            verified_recipient_state
        ),
        "verified_recipient_model": (
            V306_VERIFIED_RECIPIENT_STATE_MODEL
            if verified_recipient_state
            else ""
        ),
        "verified_recipient_fields": verified_fields,
        "provider_message_id_state": bool(
            provider_message_id_fields
        ),
        "provider_message_id_fields": (
            provider_message_id_fields
        ),
        "provider_outcome_state": bool(
            provider_outcome_fields
        ),
        "provider_outcome_fields": (
            provider_outcome_fields
        ),
        "retention_days": retention_days,
        "operator_recipient_output_policy": (
            operator_output_policy
        ),
        "legacy_recipient_output_surfaces": list(
            V304_LEGACY_RECIPIENT_OUTPUT_SURFACES
        ),
    }


def _policy_check(
    *,
    check_id: str,
    category: str,
    status: str,
    ready: bool,
    blocking: bool,
    enforcement_enabled: bool,
    reason_code: str,
    current_contract: str,
    required_contract: str,
    safe_default: str,
) -> dict[str, Any]:
    return NotificationDeliveryPolicyCheckV304(
        check_id=check_id,
        category=category,
        status=status,
        ready=ready,
        blocking=blocking,
        enforcement_enabled=enforcement_enabled,
        reason_code=reason_code,
        current_contract=current_contract,
        required_contract=required_contract,
        safe_default=safe_default,
    ).as_dict()


def build_notification_delivery_policy_baseline_v304(
    *,
    verified_recipient_state: bool,
    provider_message_id_state: bool,
    provider_outcome_state: bool,
    retention_days=None,
    operator_recipient_output_policy="",
    legacy_recipient_output_surfaces=(
        V304_LEGACY_RECIPIENT_OUTPUT_SURFACES
    ),
) -> dict[str, Any]:
    normalized_retention_days = (
        _positive_integer_or_none(
            retention_days
        )
    )

    normalized_operator_policy = str(
        operator_recipient_output_policy
        or ""
    ).strip().casefold()

    verified_ready = bool(
        verified_recipient_state
    )

    provider_ready = bool(
        provider_message_id_state
        and provider_outcome_state
    )

    retention_ready = (
        normalized_retention_days is not None
    )

    operator_output_ready = (
        normalized_operator_policy
        == V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT
    )

    checks = [
        _policy_check(
            check_id="current_delivery_guardrails",
            category="current_runtime",
            status="ready",
            ready=True,
            blocking=False,
            enforcement_enabled=True,
            reason_code=(
                "current_guardrails_present"
            ),
            current_contract=(
                "Delivery requires a non-empty account email, "
                "explicit notification preferences, logical-event "
                "deduplication and bounded retry handling."
            ),
            required_contract=(
                "Preserve the established v287-v288 delivery "
                "correctness boundary while later policy work "
                "is implemented."
            ),
            safe_default=(
                "Do not weaken the current delivery guardrails."
            ),
        ),
        _policy_check(
            check_id="verified_recipient",
            category="security_privacy",
            status=(
                "ready"
                if verified_ready
                else "blocked"
            ),
            ready=verified_ready,
            blocking=True,
            enforcement_enabled=False,
            reason_code=(
                "verified_recipient_state_available"
                if verified_ready
                else "verified_recipient_state_missing"
            ),
            current_contract=(
                (
                    "A persisted email-specific verification "
                    "lifecycle is bound to the current account "
                    "address, while notification enforcement "
                    "remains disabled."
                )
                if verified_ready
                else (
                    "The repository currently treats a non-empty "
                    "account email as the recipient address."
                )
            ),
            required_contract=(
                "A persisted email-specific verification state "
                "must be bound to the current address and include "
                "verification provenance and timestamp semantics."
            ),
            safe_default=(
                "Do not describe an address as verified and do "
                "not silently enable verification enforcement."
            ),
        ),
        _policy_check(
            check_id="provider_delivery_outcomes",
            category="correctness_operations",
            status=(
                "ready"
                if provider_ready
                else "deferred"
            ),
            ready=provider_ready,
            blocking=True,
            enforcement_enabled=False,
            reason_code=(
                "provider_outcome_contract_available"
                if provider_ready
                else "provider_outcome_contract_missing"
            ),
            current_contract=(
                "Synchronous email-backend exceptions and "
                "zero-delivery returns are recorded locally."
            ),
            required_contract=(
                "Provider message identity plus authenticated, "
                "idempotent bounce and complaint outcome "
                "ingestion must be defined."
            ),
            safe_default=(
                "Do not claim provider delivery from backend "
                "acceptance alone."
            ),
        ),
        _policy_check(
            check_id="delivery_event_retention",
            category="privacy_database",
            status=(
                "ready"
                if retention_ready
                else "deferred"
            ),
            ready=retention_ready,
            blocking=True,
            enforcement_enabled=False,
            reason_code=(
                "retention_duration_configured"
                if retention_ready
                else "retention_policy_missing"
            ),
            current_contract=(
                "Notification delivery events are durable and "
                "no age-based deletion runs automatically."
            ),
            required_contract=(
                "An approved retention duration, legal-hold "
                "behavior, backup handling and deletion evidence "
                "contract must be documented."
            ),
            safe_default=(
                "Do not perform destructive retention cleanup."
            ),
        ),
        _policy_check(
            check_id="operator_recipient_output",
            category="privacy_observability",
            status=(
                "ready"
                if operator_output_ready
                else "migration_required"
            ),
            ready=operator_output_ready,
            blocking=True,
            enforcement_enabled=False,
            reason_code=(
                "operator_output_redacted_by_default"
                if operator_output_ready
                else "operator_output_policy_missing"
            ),
            current_contract=(
                (
                    "Command, preview, observability and rollback "
                    "operator outputs redact configured recipient "
                    "addresses by default."
                )
                if operator_output_ready
                else (
                    "New notification command summaries are "
                    "recipient-sanitized, while identified legacy "
                    "preview, observability and rollback surfaces "
                    "may still expose configured addresses."
                )
            ),
            required_contract=(
                "Operator output must redact recipient addresses "
                "by default across text, JSON, preview, audit and "
                "rollback surfaces."
            ),
            safe_default=(
                "Add no new raw-recipient command output and "
                "migrate legacy contracts together."
            ),
        ),
    ]

    blocking_checks = [
        check
        for check in checks
        if check["blocking"]
    ]

    blocking_not_ready = [
        check
        for check in blocking_checks
        if not check["ready"]
    ]

    runtime_enforcement_ready = not (
        blocking_not_ready
    )

    status = (
        "implementation_ready_enforcement_disabled"
        if runtime_enforcement_ready
        else "policy_defined_runtime_not_ready"
    )

    legacy_surfaces = tuple(
        str(surface)
        for surface in (
            legacy_recipient_output_surfaces
            or ()
        )
    )

    return {
        "marker": (
            V304_NOTIFICATION_DELIVERY_POLICY_BASELINE
        ),
        "schema_version": (
            V304_NOTIFICATION_DELIVERY_POLICY_SCHEMA_VERSION
        ),
        "status": status,
        "policy_defined": True,
        "read_only": True,
        "mutation_allowed": False,
        "delivery_attempted": False,
        "provider_accessed": False,
        "runtime_enforcement_ready": (
            runtime_enforcement_ready
        ),
        "runtime_enforcement_enabled": False,
        "check_count": len(checks),
        "ready_count": sum(
            1
            for check in checks
            if check["ready"]
        ),
        "not_ready_count": sum(
            1
            for check in checks
            if not check["ready"]
        ),
        "blocking_not_ready_count": len(
            blocking_not_ready
        ),
        "retention_days": (
            normalized_retention_days
        ),
        "operator_recipient_output_policy": (
            normalized_operator_policy
        ),
        "legacy_recipient_output_surface_count": (
            len(legacy_surfaces)
        ),
        "legacy_recipient_output_surfaces": list(
            legacy_surfaces
        ),
        "checks": checks,
    }


def get_notification_delivery_policy_baseline_v304(
) -> dict[str, Any]:
    capabilities = (
        discover_notification_delivery_policy_capabilities_v304()
    )

    return build_notification_delivery_policy_baseline_v304(
        verified_recipient_state=(
            capabilities["verified_recipient_state"]
        ),
        provider_message_id_state=(
            capabilities["provider_message_id_state"]
        ),
        provider_outcome_state=(
            capabilities["provider_outcome_state"]
        ),
        retention_days=(
            capabilities["retention_days"]
        ),
        operator_recipient_output_policy=(
            capabilities[
                "operator_recipient_output_policy"
            ]
        ),
        legacy_recipient_output_surfaces=(
            capabilities[
                "legacy_recipient_output_surfaces"
            ]
        ),
    )


__all__ = [
    "V304_LEGACY_RECIPIENT_OUTPUT_SURFACES",
    "V304_MIGRATED_RECIPIENT_OUTPUT_SURFACES",
    "V304_NOTIFICATION_DELIVERY_POLICY_BASELINE",
    "V304_NOTIFICATION_DELIVERY_POLICY_SCHEMA_VERSION",
    "V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT",
    "V306_VERIFIED_RECIPIENT_REQUIRED_FIELDS",
    "V306_VERIFIED_RECIPIENT_STATE_MODEL",
    "build_notification_delivery_policy_baseline_v304",
    "discover_notification_delivery_policy_capabilities_v304",
    "get_notification_delivery_policy_baseline_v304",
]
