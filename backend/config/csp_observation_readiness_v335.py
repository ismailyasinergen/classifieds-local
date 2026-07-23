"""Read-only CSP observation operational-readiness audit for v335."""

from __future__ import annotations

import json
from typing import Any

from django.conf import settings
from django.urls import Resolver404, resolve

from config.csp_report_ingestion_v334 import (
    CSP_REPORT_LOGGER_NAME_V334,
    CSP_REPORT_PATH_V334,
    csp_report_ingestion_v334,
    parse_csp_report_payload_v334,
    sanitize_csp_report_v334,
)
from config.csp_report_only_v333 import (
    CSP_ENFORCEMENT_HEADER_V333,
    CSP_REPORT_ONLY_HEADER_V333,
    CspReportOnlyMiddlewareV333,
)


CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335 = (
    "CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335"
)
CSP_OBSERVATION_BUILT_IN_REPORT_URI_V335 = (
    f"/{CSP_REPORT_PATH_V334}"
)
CSP_OBSERVATION_MIDDLEWARE_V335 = (
    "config.csp_report_only_v333.CspReportOnlyMiddlewareV333"
)
CSP_NONCE_MIDDLEWARE_V335 = (
    "config.csp_nonce_v332.CspNonceMiddlewareV332"
)

CSP_OBSERVATION_READINESS_CHECK_IDS_V335 = (
    "report_only_gate_declared",
    "ingestion_gate_declared",
    "report_only_enabled",
    "ingestion_enabled",
    "built_in_report_uri_selected",
    "middleware_order_packaged",
    "endpoint_route_packaged",
    "info_log_delivery_configured",
    "synthetic_contract_packaged",
    "edge_rate_limit_approved",
    "log_governance_approved",
    "synthetic_delivery_verified",
    "enforcement_absent",
)
CSP_OBSERVATION_READINESS_REASON_CODES_V335 = (
    "ready",
    "report_only_gate_missing",
    "ingestion_gate_missing",
    "report_only_disabled",
    "ingestion_disabled",
    "built_in_report_uri_not_selected",
    "middleware_order_missing",
    "endpoint_route_missing",
    "info_log_delivery_missing",
    "synthetic_contract_mismatch",
    "edge_rate_limit_not_approved",
    "log_governance_not_approved",
    "synthetic_delivery_not_verified",
    "enforcement_detected",
)
CSP_OBSERVATION_READINESS_RESULT_KEYS_V335 = (
    "marker",
    "status",
    "ready",
    "read_only",
    "checks",
    "ready_count",
    "not_ready_count",
)
CSP_OBSERVATION_READINESS_CHECK_KEYS_V335 = (
    "check_id",
    "status",
    "passed",
    "reason_code",
)


def _check_v335(
    *,
    check_id: str,
    passed: bool,
    failure_reason: str,
) -> dict[str, object]:
    if check_id not in CSP_OBSERVATION_READINESS_CHECK_IDS_V335:
        raise ValueError("Unknown CSP readiness check identifier.")

    reason_code = "ready" if passed else failure_reason

    if reason_code not in CSP_OBSERVATION_READINESS_REASON_CODES_V335:
        raise ValueError("Unknown CSP readiness reason code.")

    return {
        "check_id": check_id,
        "status": "ready" if passed else "not_ready",
        "passed": passed,
        "reason_code": reason_code,
    }


def _middleware_order_packaged_v335() -> bool:
    middleware = tuple(getattr(settings, "MIDDLEWARE", ()))

    try:
        observation_index = middleware.index(
            CSP_OBSERVATION_MIDDLEWARE_V335
        )
        nonce_index = middleware.index(CSP_NONCE_MIDDLEWARE_V335)
    except ValueError:
        return False

    return observation_index < nonce_index


def _endpoint_route_packaged_v335() -> bool:
    try:
        match = resolve(CSP_OBSERVATION_BUILT_IN_REPORT_URI_V335)
    except Resolver404:
        return False

    return (
        match.func is csp_report_ingestion_v334
        and match.url_name == "csp_report_ingestion_v334"
    )


def _level_allows_info_v335(value: object) -> bool:
    if isinstance(value, bool):
        return False

    if isinstance(value, int):
        return value <= 20

    if not isinstance(value, str):
        return False

    return value.strip().upper() in {
        "NOTSET",
        "DEBUG",
        "INFO",
    }


def _info_log_delivery_configured_v335() -> bool:
    logging_config = getattr(settings, "LOGGING", {})

    if not isinstance(logging_config, dict):
        return False

    root_config = logging_config.get("root", {})
    logger_configs = logging_config.get("loggers", {})
    handler_configs = logging_config.get("handlers", {})

    if not all(
        isinstance(item, dict)
        for item in (
            root_config,
            logger_configs,
            handler_configs,
        )
    ):
        return False

    logger_config = logger_configs.get(
        CSP_REPORT_LOGGER_NAME_V334
    )

    if logger_config is not None and not isinstance(
        logger_config,
        dict,
    ):
        return False

    if logger_config is None:
        level = root_config.get("level", "NOTSET")
        handler_names = root_config.get("handlers", ())
    else:
        level = logger_config.get(
            "level",
            root_config.get("level", "NOTSET"),
        )
        handler_names = logger_config.get("handlers", ())

        if (
            not handler_names
            and logger_config.get("propagate", True)
        ):
            handler_names = root_config.get("handlers", ())

    if (
        not _level_allows_info_v335(level)
        or not isinstance(handler_names, (list, tuple))
        or not handler_names
    ):
        return False

    for handler_name in handler_names:
        handler_config = handler_configs.get(handler_name)

        if (
            isinstance(handler_config, dict)
            and _level_allows_info_v335(
                handler_config.get("level", "NOTSET")
            )
        ):
            return True

    return False


def _synthetic_contract_packaged_v335() -> bool:
    payload = {
        "csp-report": {
            "document-uri": (
                "https://audit.invalid/private/page"
                "?token=document-secret"
            ),
            "blocked-uri": "inline",
            "effective-directive": "script-src-attr",
            "violated-directive": "script-src-attr 'none'",
            "source-file": (
                "https://audit.invalid/private/source.js"
                "?token=source-secret"
            ),
            "script-sample": "synthetic-secret-sample",
            "line-number": 17,
            "column-number": 4,
            "status-code": 200,
            "disposition": "report",
        }
    }
    reports = parse_csp_report_payload_v334(
        body=json.dumps(payload).encode("utf-8"),
        media_type="application/csp-report",
    )

    if len(reports) != 1:
        return False

    evidence = sanitize_csp_report_v334(reports[0])
    expected = {
        "blocked_resource": "inline",
        "column_number": 4,
        "disposition": "report",
        "document_origin": "https://audit.invalid",
        "effective_directive": "script-src-attr",
        "line_number": 17,
        "source_origin": "https://audit.invalid",
        "status_code": 200,
        "violated_directive": "script-src-attr",
    }
    serialized = json.dumps(
        evidence,
        sort_keys=True,
        separators=(",", ":"),
    )

    return evidence == expected and all(
        secret not in serialized
        for secret in (
            "private",
            "document-secret",
            "source-secret",
            "synthetic-secret-sample",
        )
    )


def _enforcement_absent_v335() -> bool:
    middleware_names = (
        CspReportOnlyMiddlewareV333.__call__.__code__.co_names
    )

    return (
        CSP_REPORT_ONLY_HEADER_V333
        == "Content-Security-Policy-Report-Only"
        and CSP_ENFORCEMENT_HEADER_V333
        == "Content-Security-Policy"
        and "CSP_REPORT_ONLY_HEADER_V333" in middleware_names
        and "CSP_ENFORCEMENT_HEADER_V333" not in middleware_names
        and not hasattr(settings, "CSP_ENFORCEMENT_ENABLED")
    )


def get_csp_observation_readiness_v335() -> dict[str, Any]:
    """Return sanitized readiness evidence without I/O or mutation."""

    report_only_declared = hasattr(
        settings,
        "CSP_REPORT_ONLY_ENABLED",
    )
    ingestion_declared = hasattr(
        settings,
        "CSP_REPORT_INGESTION_ENABLED",
    )
    checks = [
        _check_v335(
            check_id="report_only_gate_declared",
            passed=report_only_declared,
            failure_reason="report_only_gate_missing",
        ),
        _check_v335(
            check_id="ingestion_gate_declared",
            passed=ingestion_declared,
            failure_reason="ingestion_gate_missing",
        ),
        _check_v335(
            check_id="report_only_enabled",
            passed=report_only_declared
            and bool(settings.CSP_REPORT_ONLY_ENABLED),
            failure_reason="report_only_disabled",
        ),
        _check_v335(
            check_id="ingestion_enabled",
            passed=ingestion_declared
            and bool(settings.CSP_REPORT_INGESTION_ENABLED),
            failure_reason="ingestion_disabled",
        ),
        _check_v335(
            check_id="built_in_report_uri_selected",
            passed=(
                getattr(
                    settings,
                    "CSP_REPORT_ONLY_REPORT_URI",
                    "",
                )
                == CSP_OBSERVATION_BUILT_IN_REPORT_URI_V335
            ),
            failure_reason="built_in_report_uri_not_selected",
        ),
        _check_v335(
            check_id="middleware_order_packaged",
            passed=_middleware_order_packaged_v335(),
            failure_reason="middleware_order_missing",
        ),
        _check_v335(
            check_id="endpoint_route_packaged",
            passed=_endpoint_route_packaged_v335(),
            failure_reason="endpoint_route_missing",
        ),
        _check_v335(
            check_id="info_log_delivery_configured",
            passed=_info_log_delivery_configured_v335(),
            failure_reason="info_log_delivery_missing",
        ),
        _check_v335(
            check_id="synthetic_contract_packaged",
            passed=_synthetic_contract_packaged_v335(),
            failure_reason="synthetic_contract_mismatch",
        ),
        _check_v335(
            check_id="edge_rate_limit_approved",
            passed=bool(
                getattr(
                    settings,
                    "CSP_OBSERVATION_EDGE_RATE_LIMIT_APPROVED",
                    False,
                )
            ),
            failure_reason="edge_rate_limit_not_approved",
        ),
        _check_v335(
            check_id="log_governance_approved",
            passed=bool(
                getattr(
                    settings,
                    "CSP_OBSERVATION_LOG_GOVERNANCE_APPROVED",
                    False,
                )
            ),
            failure_reason="log_governance_not_approved",
        ),
        _check_v335(
            check_id="synthetic_delivery_verified",
            passed=bool(
                getattr(
                    settings,
                    "CSP_OBSERVATION_SYNTHETIC_REPORT_VERIFIED",
                    False,
                )
            ),
            failure_reason="synthetic_delivery_not_verified",
        ),
        _check_v335(
            check_id="enforcement_absent",
            passed=_enforcement_absent_v335(),
            failure_reason="enforcement_detected",
        ),
    ]
    ready_count = sum(check["passed"] for check in checks)
    not_ready_count = len(checks) - ready_count
    ready = not_ready_count == 0
    result = {
        "marker": CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335,
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "read_only": True,
        "checks": checks,
        "ready_count": ready_count,
        "not_ready_count": not_ready_count,
    }

    if tuple(result) != CSP_OBSERVATION_READINESS_RESULT_KEYS_V335:
        raise RuntimeError("CSP readiness result key contract changed.")

    for check in checks:
        if tuple(check) != CSP_OBSERVATION_READINESS_CHECK_KEYS_V335:
            raise RuntimeError("CSP readiness check key contract changed.")

    return result
