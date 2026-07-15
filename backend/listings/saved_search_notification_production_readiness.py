from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings


V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS = (
    "V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS"
)

READINESS_STATUS_VALUES = (
    "ready",
    "not_ready",
    "warning",
)

READINESS_CHECK_IDS = (
    "feature_gate_declared",
    "feature_gate_enabled",
    "email_backend_configured",
    "email_backend_allowed",
    "default_sender_configured",
    "double_confirmation_packaged",
    "owner_scope_packaged",
    "explicit_limit_packaged",
    "batch_cap_packaged",
)

READINESS_REASON_CODES = (
    "ready",
    "feature_gate_missing",
    "feature_gate_disabled",
    "email_backend_missing",
    "email_backend_rejected",
    "default_sender_missing",
    "delivery_confirmation_missing",
    "owner_scope_missing",
    "explicit_limit_missing",
    "batch_cap_mismatch",
)

READINESS_RESULT_KEYS = (
    "marker",
    "status",
    "ready",
    "checks",
    "ready_count",
    "not_ready_count",
    "warning_count",
)

READINESS_CHECK_RESULT_KEYS = (
    "check_id",
    "status",
    "passed",
    "reason_code",
)

REJECTED_EMAIL_BACKEND_PREFIXES = (
    "django.core.mail.backends.locmem.",
    "django.core.mail.backends.dummy.",
    "django.core.mail.backends.console.",
    "django.core.mail.backends.filebased.",
)

_LISTINGS_ROOT = Path(__file__).resolve().parent
_SENDER_PATH = (
    _LISTINGS_ROOT
    / "saved_search_notification_email_sender.py"
)
_DELIVERY_COMMAND_PATH = (
    _LISTINGS_ROOT
    / "management"
    / "commands"
    / "process_saved_search_notifications.py"
)


def _read_packaged_source(
    path: Path,
) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except OSError:
        return ""


def _check_result(
    *,
    check_id: str,
    passed: bool,
    failure_reason_code: str,
) -> dict[str, object]:
    if check_id not in READINESS_CHECK_IDS:
        raise ValueError(
            "Unknown readiness check identifier."
        )

    reason_code = (
        "ready"
        if passed
        else failure_reason_code
    )

    if reason_code not in READINESS_REASON_CODES:
        raise ValueError(
            "Unknown readiness reason code."
        )

    return {
        "check_id": check_id,
        "status": (
            "ready"
            if passed
            else "not_ready"
        ),
        "passed": passed,
        "reason_code": reason_code,
    }


def get_saved_search_notification_production_readiness(
) -> dict[str, Any]:
    feature_gate_declared = hasattr(
        settings,
        "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED",
    )

    feature_gate_enabled = (
        feature_gate_declared
        and bool(
            getattr(
                settings,
                "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED",
                False,
            )
        )
    )

    configured_backend = getattr(
        settings,
        "EMAIL_BACKEND",
        "",
    )

    email_backend_configured = (
        isinstance(
            configured_backend,
            str,
        )
        and bool(
            configured_backend.strip()
        )
    )

    normalized_backend = (
        configured_backend.strip()
        if email_backend_configured
        else ""
    )

    email_backend_allowed = (
        email_backend_configured
        and not any(
            normalized_backend.startswith(
                prefix
            )
            for prefix
            in REJECTED_EMAIL_BACKEND_PREFIXES
        )
    )

    configured_sender = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        "",
    )

    default_sender_configured = (
        isinstance(
            configured_sender,
            str,
        )
        and bool(
            configured_sender.strip()
        )
    )

    sender_source = _read_packaged_source(
        _SENDER_PATH
    )

    command_source = _read_packaged_source(
        _DELIVERY_COMMAND_PATH
    )

    double_confirmation_packaged = all(
        term in command_source
        for term in (
            "--execute-production-send",
            "--confirm-production-delivery",
        )
    )

    owner_scope_packaged = (
        "--owner-id"
        in command_source
    )

    explicit_limit_packaged = (
        "--limit"
        in command_source
    )

    batch_cap_packaged = (
        "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25"
        in sender_source
    )

    checks = [
        _check_result(
            check_id="feature_gate_declared",
            passed=feature_gate_declared,
            failure_reason_code="feature_gate_missing",
        ),
        _check_result(
            check_id="feature_gate_enabled",
            passed=feature_gate_enabled,
            failure_reason_code="feature_gate_disabled",
        ),
        _check_result(
            check_id="email_backend_configured",
            passed=email_backend_configured,
            failure_reason_code="email_backend_missing",
        ),
        _check_result(
            check_id="email_backend_allowed",
            passed=email_backend_allowed,
            failure_reason_code=(
                "email_backend_rejected"
                if email_backend_configured
                else "email_backend_missing"
            ),
        ),
        _check_result(
            check_id="default_sender_configured",
            passed=default_sender_configured,
            failure_reason_code="default_sender_missing",
        ),
        _check_result(
            check_id="double_confirmation_packaged",
            passed=double_confirmation_packaged,
            failure_reason_code="delivery_confirmation_missing",
        ),
        _check_result(
            check_id="owner_scope_packaged",
            passed=owner_scope_packaged,
            failure_reason_code="owner_scope_missing",
        ),
        _check_result(
            check_id="explicit_limit_packaged",
            passed=explicit_limit_packaged,
            failure_reason_code="explicit_limit_missing",
        ),
        _check_result(
            check_id="batch_cap_packaged",
            passed=batch_cap_packaged,
            failure_reason_code="batch_cap_mismatch",
        ),
    ]

    ready_count = sum(
        check["status"] == "ready"
        for check in checks
    )

    not_ready_count = sum(
        check["status"] == "not_ready"
        for check in checks
    )

    warning_count = sum(
        check["status"] == "warning"
        for check in checks
    )

    ready = (
        not_ready_count == 0
        and warning_count == 0
    )

    result = {
        "marker": (
            V245_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_OPERATIONAL_READINESS
        ),
        "status": (
            "ready"
            if ready
            else "not_ready"
        ),
        "ready": ready,
        "checks": checks,
        "ready_count": ready_count,
        "not_ready_count": not_ready_count,
        "warning_count": warning_count,
    }

    if tuple(result) != READINESS_RESULT_KEYS:
        raise RuntimeError(
            "Readiness result key contract changed."
        )

    for check in checks:
        if tuple(check) != READINESS_CHECK_RESULT_KEYS:
            raise RuntimeError(
                "Readiness check key contract changed."
            )

    return result
