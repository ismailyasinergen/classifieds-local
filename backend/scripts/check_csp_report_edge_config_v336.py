"""Validate the V336 Nginx CSP report edge boundary without mutation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


CSP_REPORT_EDGE_ABUSE_CONTROL_BASELINE_V336 = (
    "CSP_REPORT_EDGE_ABUSE_CONTROL_BASELINE_V336"
)
CSP_REPORT_EDGE_CONFIG_MAX_BYTES_V336 = 256 * 1024
CSP_REPORT_EDGE_CHECK_IDS_V336 = (
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
CSP_REPORT_EDGE_REASON_CODES_V336 = (
    "ready",
    "configuration_unreadable",
    "shared_client_zone_missing",
    "exact_report_location_missing",
    "endpoint_body_bound_missing",
    "endpoint_body_timeout_missing",
    "endpoint_rate_limit_missing",
    "rate_limit_status_missing",
    "rate_limit_log_level_missing",
    "endpoint_proxy_target_missing",
    "forwarding_headers_missing",
    "fallback_proxy_missing",
    "rate_limit_dry_run_enabled",
    "csp_enforcement_detected",
)
CSP_REPORT_EDGE_RESULT_KEYS_V336 = (
    "marker",
    "status",
    "ready",
    "read_only",
    "checks",
    "ready_count",
    "not_ready_count",
)
CSP_REPORT_EDGE_CHECK_KEYS_V336 = (
    "check_id",
    "status",
    "passed",
    "reason_code",
)

_EXACT_LOCATION_PATTERN_V336 = re.compile(
    r"\blocation\s*=\s*/__csp_reports__/\s*\{"
)
_ENFORCEMENT_HEADER_PATTERN_V336 = re.compile(
    r"\b(?:add_header|proxy_set_header)\s+"
    r"Content-Security-Policy(?:\s|;)",
    re.IGNORECASE,
)


def _check_v336(
    *,
    check_id: str,
    passed: bool,
    failure_reason: str,
) -> dict[str, object]:
    if check_id not in CSP_REPORT_EDGE_CHECK_IDS_V336:
        raise ValueError("Unknown V336 edge check identifier.")

    reason_code = "ready" if passed else failure_reason

    if reason_code not in CSP_REPORT_EDGE_REASON_CODES_V336:
        raise ValueError("Unknown V336 edge reason code.")

    return {
        "check_id": check_id,
        "status": "ready" if passed else "not_ready",
        "passed": passed,
        "reason_code": reason_code,
    }


def _strip_comments_v336(source: str) -> str:
    return "\n".join(
        line.split("#", 1)[0]
        for line in source.splitlines()
    )


def _exact_location_blocks_v336(source: str) -> tuple[str, ...]:
    blocks = []

    for match in _EXACT_LOCATION_PATTERN_V336.finditer(source):
        opening_brace = source.find("{", match.start())
        depth = 0

        for index in range(opening_brace, len(source)):
            character = source[index]

            if character == "{":
                depth += 1
            elif character == "}":
                depth -= 1

                if depth == 0:
                    blocks.append(source[opening_brace + 1:index])
                    break

    return tuple(blocks)


def audit_csp_report_edge_config_v336(
    source: str | None,
) -> dict[str, Any]:
    """Return deterministic evidence for the exact Nginx report boundary."""

    readable = isinstance(source, str)
    normalized = _strip_comments_v336(source or "")
    location_blocks = _exact_location_blocks_v336(normalized)
    exact_location_unique = len(location_blocks) == 1
    location = location_blocks[0] if exact_location_unique else ""
    forwarding_headers = (
        "proxy_set_header Host $host;",
        "proxy_set_header X-Real-IP $remote_addr;",
        (
            "proxy_set_header X-Forwarded-For "
            "$proxy_add_x_forwarded_for;"
        ),
        "proxy_set_header X-Forwarded-Proto $scheme;",
    )
    checks = [
        _check_v336(
            check_id="configuration_readable",
            passed=readable,
            failure_reason="configuration_unreadable",
        ),
        _check_v336(
            check_id="shared_client_zone_declared",
            passed=(
                "limit_req_zone $binary_remote_addr "
                "zone=csp_reports_v336:10m rate=1r/s;"
                in normalized
            ),
            failure_reason="shared_client_zone_missing",
        ),
        _check_v336(
            check_id="exact_report_location_unique",
            passed=exact_location_unique,
            failure_reason="exact_report_location_missing",
        ),
        _check_v336(
            check_id="endpoint_body_bound",
            passed="client_max_body_size 16k;" in location,
            failure_reason="endpoint_body_bound_missing",
        ),
        _check_v336(
            check_id="endpoint_body_timeout",
            passed="client_body_timeout 10s;" in location,
            failure_reason="endpoint_body_timeout_missing",
        ),
        _check_v336(
            check_id="endpoint_rate_limit_enabled",
            passed=(
                "limit_req zone=csp_reports_v336 burst=10 nodelay;"
                in location
            ),
            failure_reason="endpoint_rate_limit_missing",
        ),
        _check_v336(
            check_id="rate_limit_status_bounded",
            passed="limit_req_status 429;" in location,
            failure_reason="rate_limit_status_missing",
        ),
        _check_v336(
            check_id="rate_limit_observable",
            passed="limit_req_log_level notice;" in location,
            failure_reason="rate_limit_log_level_missing",
        ),
        _check_v336(
            check_id="endpoint_proxy_target_preserved",
            passed=(
                "proxy_pass http://web:8000;" in location
                and "proxy_redirect off;" in location
            ),
            failure_reason="endpoint_proxy_target_missing",
        ),
        _check_v336(
            check_id="forwarding_headers_preserved",
            passed=all(
                header in location
                for header in forwarding_headers
            ),
            failure_reason="forwarding_headers_missing",
        ),
        _check_v336(
            check_id="fallback_proxy_preserved",
            passed=bool(
                re.search(r"\blocation\s+/\s*\{", normalized)
            ),
            failure_reason="fallback_proxy_missing",
        ),
        _check_v336(
            check_id="rate_limit_enforcement_active",
            passed=not bool(
                re.search(
                    r"\blimit_req_dry_run\s+on\s*;",
                    location,
                )
            ),
            failure_reason="rate_limit_dry_run_enabled",
        ),
        _check_v336(
            check_id="csp_enforcement_absent",
            passed=not bool(
                _ENFORCEMENT_HEADER_PATTERN_V336.search(normalized)
            ),
            failure_reason="csp_enforcement_detected",
        ),
    ]
    ready_count = sum(check["passed"] for check in checks)
    not_ready_count = len(checks) - ready_count
    ready = not_ready_count == 0
    result = {
        "marker": CSP_REPORT_EDGE_ABUSE_CONTROL_BASELINE_V336,
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "read_only": True,
        "checks": checks,
        "ready_count": ready_count,
        "not_ready_count": not_ready_count,
    }

    if tuple(result) != CSP_REPORT_EDGE_RESULT_KEYS_V336:
        raise RuntimeError("V336 edge result key contract changed.")

    for check in checks:
        if tuple(check) != CSP_REPORT_EDGE_CHECK_KEYS_V336:
            raise RuntimeError("V336 edge check key contract changed.")

    return result


def _read_config_v336(path: Path) -> str | None:
    try:
        if path.stat().st_size > CSP_REPORT_EDGE_CONFIG_MAX_BYTES_V336:
            return None

        return path.read_text(
            encoding="utf-8",
            errors="strict",
        )
    except (OSError, UnicodeError):
        return None


def _build_parser_v336() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the read-only V336 Nginx CSP report edge boundary."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("nginx/default.conf"),
        help="Nginx configuration path.",
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
    options = _build_parser_v336().parse_args()
    result = audit_csp_report_edge_config_v336(
        _read_config_v336(options.config)
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
