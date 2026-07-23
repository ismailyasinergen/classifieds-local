"""Close out sanitized V333-V338 CSP observation evidence without mutation."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339 = (
    "CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339"
)
CSP_CLOSEOUT_EVIDENCE_MAX_BYTES_V339 = 128 * 1024
CSP_CLOSEOUT_PATH_V339 = "/__csp_reports__/"
CSP_CLOSEOUT_CHECK_IDS_V339 = (
    "expected_origin_valid",
    "readiness_evidence_valid",
    "edge_evidence_valid",
    "retention_evidence_valid",
    "delivery_evidence_valid",
    "log_evidence_valid",
    "smoke_evidence_linked",
    "enforcement_absent",
)
CSP_CLOSEOUT_REASON_CODES_V339 = (
    "ready",
    "expected_origin_invalid",
    "readiness_evidence_invalid",
    "edge_evidence_invalid",
    "retention_evidence_invalid",
    "delivery_evidence_invalid",
    "log_evidence_invalid",
    "smoke_evidence_mismatch",
    "enforcement_evidence_invalid",
    "enforcement_detected",
)
CSP_CLOSEOUT_RESULT_KEYS_V339 = (
    "marker",
    "status",
    "ready",
    "read_only",
    "checks",
    "ready_count",
    "not_ready_count",
)
CSP_CLOSEOUT_CHECK_KEYS_V339 = (
    "check_id",
    "status",
    "passed",
    "reason_code",
)

_READY_RESULT_KEYS_V339 = frozenset(
    {
        "marker",
        "status",
        "ready",
        "read_only",
        "checks",
        "ready_count",
        "not_ready_count",
    }
)
_READY_CHECK_KEYS_V339 = frozenset(
    {
        "check_id",
        "status",
        "passed",
        "reason_code",
    }
)
_SMOKE_RESULT_KEYS_V339 = frozenset(
    {
        "marker",
        "mode",
        "smoke_id",
        "target_origin",
        "target_path",
        "timeout_seconds",
        "expected_log_sha256",
        "delivery_status",
        "response_status",
        "enforcement_absent",
        "cache_control_no_store",
        "log_status",
        "passed",
        "reason_codes",
    }
)
_SMOKE_ID_PATTERN_V339 = re.compile(r"^[a-f0-9]{16}$")
_SHA256_PATTERN_V339 = re.compile(r"^[a-f0-9]{64}$")
_REASON_PATTERN_V339 = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

_READINESS_MARKER_V339 = (
    "CSP_OBSERVATION_OPERATIONAL_READINESS_AUDIT_V335"
)
_READINESS_CHECK_IDS_V339 = (
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
_EDGE_MARKER_V339 = "CSP_REPORT_EDGE_ABUSE_CONTROL_BASELINE_V336"
_EDGE_CHECK_IDS_V339 = (
    "configuration_readable",
    "shared_client_zone_declared",
    "exact_report_location_unique",
    "endpoint_body_bound",
    "endpoint_body_timeout",
    "endpoint_rate_limit_enabled",
    "rate_limit_status_bounded",
    "rate_limit_observable",
    "endpoint_proxy_target_preserved",
    "forwarding_headers_preserved",
    "fallback_proxy_preserved",
    "rate_limit_enforcement_active",
    "csp_enforcement_absent",
)
_RETENTION_MARKER_V339 = "CSP_REPORT_LOG_RETENTION_VALIDATOR_V337"
_RETENTION_CHECK_IDS_V339 = (
    "compose_json_readable",
    "compose_json_valid",
    "web_service_present",
    "local_driver_selected",
    "rotation_size_bounded",
    "rotation_file_count_bounded",
    "rotation_compression_enabled",
)
_SMOKE_MARKER_V339 = (
    "CSP_OBSERVATION_SYNTHETIC_DELIVERY_SMOKE_V338"
)


def _check_v339(
    *,
    check_id: str,
    passed: bool,
    failure_reason: str,
) -> dict[str, object]:
    if check_id not in CSP_CLOSEOUT_CHECK_IDS_V339:
        raise ValueError("Unknown V339 closeout check identifier.")

    reason_code = "ready" if passed else failure_reason

    if reason_code not in CSP_CLOSEOUT_REASON_CODES_V339:
        raise ValueError("Unknown V339 closeout reason code.")

    return {
        "check_id": check_id,
        "status": "ready" if passed else "not_ready",
        "passed": passed,
        "reason_code": reason_code,
    }


def _normalized_origin_v339(value: object) -> str | None:
    if (
        not isinstance(value, str)
        or not value
        or any(
            character.isspace()
            or ord(character) < 0x21
            or ord(character) > 0x7E
            for character in value
        )
    ):
        return None

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        return None

    try:
        hostname = (
            parsed.hostname.encode("idna")
            .decode("ascii")
            .casefold()
        )
    except UnicodeError:
        return None

    loopback = hostname == "localhost"

    if not loopback:
        try:
            loopback = ipaddress.ip_address(hostname).is_loopback
        except ValueError:
            pass

    if parsed.scheme == "http" and not loopback:
        return None

    rendered_host = f"[{hostname}]" if ":" in hostname else hostname
    authority = rendered_host

    if port is not None:
        authority += f":{port}"

    return f"{parsed.scheme}://{authority}"


def _valid_component_shape_v339(
    evidence: object,
    *,
    marker: str,
    check_ids: tuple[str, ...],
) -> bool:
    if (
        not isinstance(evidence, dict)
        or set(evidence) != _READY_RESULT_KEYS_V339
        or evidence.get("marker") != marker
        or evidence.get("status") not in {"ready", "not_ready"}
        or not isinstance(evidence.get("ready"), bool)
        or evidence.get("read_only") is not True
        or type(evidence.get("ready_count")) is not int
        or type(evidence.get("not_ready_count")) is not int
    ):
        return False

    checks = evidence.get("checks")

    if not isinstance(checks, list) or len(checks) != len(check_ids):
        return False

    passed_count = 0

    for expected_id, check in zip(check_ids, checks, strict=True):
        if (
            not isinstance(check, dict)
            or set(check) != _READY_CHECK_KEYS_V339
            or check.get("check_id") != expected_id
            or not isinstance(check.get("passed"), bool)
        ):
            return False

        passed = check["passed"]
        reason_code = check.get("reason_code")

        if (
            not isinstance(reason_code, str)
            or _REASON_PATTERN_V339.fullmatch(reason_code) is None
            or (
                passed
                and (
                    check.get("status") != "ready"
                    or reason_code != "ready"
                )
            )
            or (
                not passed
                and (
                    check.get("status") != "not_ready"
                    or reason_code == "ready"
                )
            )
        ):
            return False

        passed_count += int(passed)

    not_ready_count = len(check_ids) - passed_count
    ready = not_ready_count == 0

    return (
        evidence.get("ready_count") == passed_count
        and evidence.get("not_ready_count") == not_ready_count
        and evidence.get("ready") is ready
        and evidence.get("status")
        == ("ready" if ready else "not_ready")
    )


def _valid_ready_evidence_v339(
    evidence: object,
    *,
    marker: str,
    check_ids: tuple[str, ...],
) -> bool:
    return (
        _valid_component_shape_v339(
            evidence,
            marker=marker,
            check_ids=check_ids,
        )
        and isinstance(evidence, dict)
        and evidence.get("ready") is True
    )


def _valid_smoke_common_v339(
    evidence: object,
    *,
    expected_origin: str | None,
) -> bool:
    if (
        expected_origin is None
        or not isinstance(evidence, dict)
        or set(evidence) != _SMOKE_RESULT_KEYS_V339
        or evidence.get("marker") != _SMOKE_MARKER_V339
        or evidence.get("target_origin") != expected_origin
        or evidence.get("target_path") != CSP_CLOSEOUT_PATH_V339
        or evidence.get("passed") is not True
    ):
        return False

    smoke_id = evidence.get("smoke_id")
    digest = evidence.get("expected_log_sha256")
    timeout = evidence.get("timeout_seconds")

    return (
        isinstance(smoke_id, str)
        and _SMOKE_ID_PATTERN_V339.fullmatch(smoke_id) is not None
        and isinstance(digest, str)
        and _SHA256_PATTERN_V339.fullmatch(digest) is not None
        and digest == _expected_log_sha256_v339(smoke_id)
        and not isinstance(timeout, bool)
        and isinstance(timeout, (int, float))
        and 1.0 <= timeout <= 10.0
    )


def _expected_log_sha256_v339(smoke_id: str) -> str:
    synthetic_origin = f"https://v338-{smoke_id}.invalid"
    expected_log = json.dumps(
        {
            "event": "csp_violation_v334",
            "evidence": {
                "media_type": "application/csp-report",
                "report_index": 1,
                "blocked_resource": "inline",
                "column_number": 4,
                "disposition": "report",
                "document_origin": synthetic_origin,
                "effective_directive": "script-src-attr",
                "line_number": 17,
                "source_origin": synthetic_origin,
                "status_code": 200,
                "violated_directive": "script-src-attr",
            },
            "schema_version": 1,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )

    return hashlib.sha256(expected_log.encode("utf-8")).hexdigest()


def _valid_delivery_evidence_v339(
    evidence: object,
    *,
    expected_origin: str | None,
) -> bool:
    return (
        _valid_smoke_common_v339(
            evidence,
            expected_origin=expected_origin,
        )
        and isinstance(evidence, dict)
        and evidence.get("mode") == "execute"
        and evidence.get("delivery_status") == "passed"
        and evidence.get("response_status") == 204
        and evidence.get("enforcement_absent") is True
        and evidence.get("cache_control_no_store") is True
        and evidence.get("log_status") == "not_checked"
        and evidence.get("reason_codes")
        == ["delivery_passed", "log_not_checked"]
    )


def _valid_log_evidence_v339(
    evidence: object,
    *,
    expected_origin: str | None,
) -> bool:
    return (
        _valid_smoke_common_v339(
            evidence,
            expected_origin=expected_origin,
        )
        and isinstance(evidence, dict)
        and evidence.get("mode") == "verify"
        and evidence.get("delivery_status") == "not_run"
        and evidence.get("response_status") is None
        and evidence.get("enforcement_absent") is None
        and evidence.get("cache_control_no_store") is None
        and evidence.get("log_status") == "verified"
        and evidence.get("reason_codes")
        == ["delivery_not_run", "log_verified"]
    )


def _smoke_evidence_linked_v339(
    delivery_evidence: object,
    log_evidence: object,
) -> bool:
    if not all(
        isinstance(evidence, dict)
        for evidence in (delivery_evidence, log_evidence)
    ):
        return False

    linkage_keys = (
        "smoke_id",
        "target_origin",
        "target_path",
        "timeout_seconds",
        "expected_log_sha256",
    )

    return all(
        delivery_evidence.get(key) == log_evidence.get(key)
        for key in linkage_keys
    )


def _passed_component_check_v339(
    evidence: object,
    check_id: str,
) -> bool:
    if not isinstance(evidence, dict):
        return False

    checks = evidence.get("checks")

    if not isinstance(checks, list):
        return False

    matches = [
        check
        for check in checks
        if (
            isinstance(check, dict)
            and check.get("check_id") == check_id
        )
    ]

    return (
        len(matches) == 1
        and matches[0].get("passed") is True
        and matches[0].get("reason_code") == "ready"
    )


def audit_csp_observation_evidence_closeout_v339(
    *,
    readiness_evidence: object,
    edge_evidence: object,
    retention_evidence: object,
    delivery_evidence: object,
    log_evidence: object,
    expected_origin: object,
) -> dict[str, Any]:
    """Validate linked, sanitized evidence without echoing its contents."""

    normalized_origin = _normalized_origin_v339(expected_origin)
    readiness_valid = _valid_ready_evidence_v339(
        readiness_evidence,
        marker=_READINESS_MARKER_V339,
        check_ids=_READINESS_CHECK_IDS_V339,
    )
    edge_valid = _valid_ready_evidence_v339(
        edge_evidence,
        marker=_EDGE_MARKER_V339,
        check_ids=_EDGE_CHECK_IDS_V339,
    )
    retention_valid = _valid_ready_evidence_v339(
        retention_evidence,
        marker=_RETENTION_MARKER_V339,
        check_ids=_RETENTION_CHECK_IDS_V339,
    )
    delivery_valid = _valid_delivery_evidence_v339(
        delivery_evidence,
        expected_origin=normalized_origin,
    )
    log_valid = _valid_log_evidence_v339(
        log_evidence,
        expected_origin=normalized_origin,
    )
    smoke_linked = (
        delivery_valid
        and log_valid
        and _smoke_evidence_linked_v339(
            delivery_evidence,
            log_evidence,
        )
    )
    readiness_shape_valid = _valid_component_shape_v339(
        readiness_evidence,
        marker=_READINESS_MARKER_V339,
        check_ids=_READINESS_CHECK_IDS_V339,
    )
    edge_shape_valid = _valid_component_shape_v339(
        edge_evidence,
        marker=_EDGE_MARKER_V339,
        check_ids=_EDGE_CHECK_IDS_V339,
    )
    enforcement_evidence_valid = (
        readiness_shape_valid
        and edge_shape_valid
        and delivery_valid
    )
    enforcement_absent = (
        enforcement_evidence_valid
        and _passed_component_check_v339(
            readiness_evidence,
            "enforcement_absent",
        )
        and _passed_component_check_v339(
            edge_evidence,
            "csp_enforcement_absent",
        )
        and isinstance(delivery_evidence, dict)
        and delivery_evidence.get("enforcement_absent") is True
    )
    checks = [
        _check_v339(
            check_id="expected_origin_valid",
            passed=normalized_origin is not None,
            failure_reason="expected_origin_invalid",
        ),
        _check_v339(
            check_id="readiness_evidence_valid",
            passed=readiness_valid,
            failure_reason="readiness_evidence_invalid",
        ),
        _check_v339(
            check_id="edge_evidence_valid",
            passed=edge_valid,
            failure_reason="edge_evidence_invalid",
        ),
        _check_v339(
            check_id="retention_evidence_valid",
            passed=retention_valid,
            failure_reason="retention_evidence_invalid",
        ),
        _check_v339(
            check_id="delivery_evidence_valid",
            passed=delivery_valid,
            failure_reason="delivery_evidence_invalid",
        ),
        _check_v339(
            check_id="log_evidence_valid",
            passed=log_valid,
            failure_reason="log_evidence_invalid",
        ),
        _check_v339(
            check_id="smoke_evidence_linked",
            passed=smoke_linked,
            failure_reason="smoke_evidence_mismatch",
        ),
        _check_v339(
            check_id="enforcement_absent",
            passed=enforcement_absent,
            failure_reason=(
                "enforcement_detected"
                if enforcement_evidence_valid
                else "enforcement_evidence_invalid"
            ),
        ),
    ]
    ready_count = sum(check["passed"] for check in checks)
    not_ready_count = len(checks) - ready_count
    ready = not_ready_count == 0
    result = {
        "marker": CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339,
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "read_only": True,
        "checks": checks,
        "ready_count": ready_count,
        "not_ready_count": not_ready_count,
    }

    if tuple(result) != CSP_CLOSEOUT_RESULT_KEYS_V339:
        raise RuntimeError("V339 closeout result key contract changed.")

    for check in checks:
        if tuple(check) != CSP_CLOSEOUT_CHECK_KEYS_V339:
            raise RuntimeError("V339 closeout check key contract changed.")

    return result


def _read_evidence_v339(path: Path) -> dict[str, object] | None:
    try:
        with path.open("rb") as evidence_file:
            raw = evidence_file.read(
                CSP_CLOSEOUT_EVIDENCE_MAX_BYTES_V339 + 1
            )
    except OSError:
        return None

    if len(raw) > CSP_CLOSEOUT_EVIDENCE_MAX_BYTES_V339:
        return None

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ):
        return None

    return payload if isinstance(payload, dict) else None


def _build_parser_v339() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Close out linked, sanitized V333-V338 CSP observation "
            "evidence without network access or mutation."
        )
    )
    parser.add_argument(
        "--readiness-json",
        type=Path,
        required=True,
        help="Sanitized V335 readiness JSON.",
    )
    parser.add_argument(
        "--edge-json",
        type=Path,
        required=True,
        help="Sanitized V336 edge-validator JSON.",
    )
    parser.add_argument(
        "--retention-json",
        type=Path,
        required=True,
        help="Sanitized V337 retention-validator JSON.",
    )
    parser.add_argument(
        "--delivery-json",
        type=Path,
        required=True,
        help="Sanitized V338 execute-mode JSON.",
    )
    parser.add_argument(
        "--log-json",
        type=Path,
        required=True,
        help="Sanitized V338 verify-mode JSON.",
    )
    parser.add_argument(
        "--expected-origin",
        required=True,
        help="Exact reviewed HTTPS origin, or loopback HTTP origin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit deterministic sanitized JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless every closeout check passes.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    options = _build_parser_v339().parse_args(argv)
    result = audit_csp_observation_evidence_closeout_v339(
        readiness_evidence=_read_evidence_v339(
            options.readiness_json
        ),
        edge_evidence=_read_evidence_v339(options.edge_json),
        retention_evidence=_read_evidence_v339(
            options.retention_json
        ),
        delivery_evidence=_read_evidence_v339(
            options.delivery_json
        ),
        log_evidence=_read_evidence_v339(options.log_json),
        expected_origin=options.expected_origin,
    )

    if options.json_output:
        print(
            json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    else:
        print(result["marker"])
        print(
            f"status={result['status']} "
            f"ready={str(result['ready']).lower()} "
            f"ready_count={result['ready_count']} "
            f"not_ready_count={result['not_ready_count']} "
            "read_only=true"
        )

        for check in result["checks"]:
            print(
                f"check={check['check_id']} "
                f"status={check['status']} "
                f"passed={str(check['passed']).lower()} "
                f"reason={check['reason_code']}"
            )

    if options.strict and not result["ready"]:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
