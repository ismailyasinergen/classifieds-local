"""Validate bounded V337 web-container log retention from Compose JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CSP_REPORT_LOG_RETENTION_VALIDATOR_V337 = (
    "CSP_REPORT_LOG_RETENTION_VALIDATOR_V337"
)
CSP_REPORT_COMPOSE_JSON_MAX_BYTES_V337 = 1024 * 1024
CSP_REPORT_LOG_RETENTION_CHECK_IDS_V337 = (
    "compose_json_readable",
    "compose_json_valid",
    "web_service_present",
    "local_driver_selected",
    "rotation_size_bounded",
    "rotation_file_count_bounded",
    "rotation_compression_enabled",
)
CSP_REPORT_LOG_RETENTION_REASON_CODES_V337 = (
    "ready",
    "compose_json_unreadable",
    "compose_json_invalid",
    "web_service_missing",
    "local_driver_missing",
    "rotation_size_missing",
    "rotation_file_count_missing",
    "rotation_compression_missing",
)
CSP_REPORT_LOG_RETENTION_RESULT_KEYS_V337 = (
    "marker",
    "status",
    "ready",
    "read_only",
    "checks",
    "ready_count",
    "not_ready_count",
)
CSP_REPORT_LOG_RETENTION_CHECK_KEYS_V337 = (
    "check_id",
    "status",
    "passed",
    "reason_code",
)


def _check_v337(
    *,
    check_id: str,
    passed: bool,
    failure_reason: str,
) -> dict[str, object]:
    if check_id not in CSP_REPORT_LOG_RETENTION_CHECK_IDS_V337:
        raise ValueError("Unknown V337 retention check identifier.")

    reason_code = "ready" if passed else failure_reason

    if reason_code not in CSP_REPORT_LOG_RETENTION_REASON_CODES_V337:
        raise ValueError("Unknown V337 retention reason code.")

    return {
        "check_id": check_id,
        "status": "ready" if passed else "not_ready",
        "passed": passed,
        "reason_code": reason_code,
    }


def audit_csp_report_log_retention_v337(
    source: str | None,
) -> dict[str, Any]:
    """Return sanitized retention evidence without changing Docker state."""

    readable = isinstance(source, str)
    valid_json = False
    payload: object = None

    if readable:
        try:
            payload = json.loads(source)
            valid_json = isinstance(payload, dict)
        except (json.JSONDecodeError, RecursionError):
            pass

    services = (
        payload.get("services", {})
        if valid_json and isinstance(payload, dict)
        else {}
    )
    web_service = (
        services.get("web")
        if isinstance(services, dict)
        else None
    )
    web_present = isinstance(web_service, dict)
    logging_config = (
        web_service.get("logging", {})
        if web_present
        else {}
    )

    if not isinstance(logging_config, dict):
        logging_config = {}

    options = logging_config.get("options", {})

    if not isinstance(options, dict):
        options = {}

    checks = [
        _check_v337(
            check_id="compose_json_readable",
            passed=readable,
            failure_reason="compose_json_unreadable",
        ),
        _check_v337(
            check_id="compose_json_valid",
            passed=valid_json,
            failure_reason="compose_json_invalid",
        ),
        _check_v337(
            check_id="web_service_present",
            passed=web_present,
            failure_reason="web_service_missing",
        ),
        _check_v337(
            check_id="local_driver_selected",
            passed=logging_config.get("driver") == "local",
            failure_reason="local_driver_missing",
        ),
        _check_v337(
            check_id="rotation_size_bounded",
            passed=options.get("max-size") == "10m",
            failure_reason="rotation_size_missing",
        ),
        _check_v337(
            check_id="rotation_file_count_bounded",
            passed=options.get("max-file") == "5",
            failure_reason="rotation_file_count_missing",
        ),
        _check_v337(
            check_id="rotation_compression_enabled",
            passed=options.get("compress") == "true",
            failure_reason="rotation_compression_missing",
        ),
    ]
    ready_count = sum(check["passed"] for check in checks)
    not_ready_count = len(checks) - ready_count
    ready = not_ready_count == 0
    result = {
        "marker": CSP_REPORT_LOG_RETENTION_VALIDATOR_V337,
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "read_only": True,
        "checks": checks,
        "ready_count": ready_count,
        "not_ready_count": not_ready_count,
    }

    if tuple(result) != CSP_REPORT_LOG_RETENTION_RESULT_KEYS_V337:
        raise RuntimeError("V337 retention result key contract changed.")

    for check in checks:
        if tuple(check) != CSP_REPORT_LOG_RETENTION_CHECK_KEYS_V337:
            raise RuntimeError("V337 retention check key contract changed.")

    return result


def _read_bounded_v337(path: Path | None) -> str | None:
    try:
        if path is None:
            raw = sys.stdin.buffer.read(
                CSP_REPORT_COMPOSE_JSON_MAX_BYTES_V337 + 1
            )
        else:
            if path.stat().st_size > CSP_REPORT_COMPOSE_JSON_MAX_BYTES_V337:
                return None
            raw = path.read_bytes()
    except OSError:
        return None

    if len(raw) > CSP_REPORT_COMPOSE_JSON_MAX_BYTES_V337:
        return None

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _build_parser_v337() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate bounded V337 web log retention from resolved "
            "Docker Compose JSON."
        )
    )
    parser.add_argument(
        "--config-json",
        type=Path,
        help="Resolved Compose JSON path; stdin is used when omitted.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit deterministic JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless all checks pass.",
    )
    return parser


def main() -> int:
    options = _build_parser_v337().parse_args()
    result = audit_csp_report_log_retention_v337(
        _read_bounded_v337(options.config_json)
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
