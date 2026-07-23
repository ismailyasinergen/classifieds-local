"""Safely plan, execute, and verify a synthetic CSP observation smoke."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import secrets
import socket
import sys
from contextlib import closing
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    Request,
    build_opener,
)


CSP_OBSERVATION_SYNTHETIC_DELIVERY_SMOKE_V338 = (
    "CSP_OBSERVATION_SYNTHETIC_DELIVERY_SMOKE_V338"
)
CSP_SMOKE_PATH_V338 = "/__csp_reports__/"
CSP_SMOKE_MEDIA_TYPE_V338 = "application/csp-report"
CSP_SMOKE_TIMEOUT_MIN_SECONDS_V338 = 1.0
CSP_SMOKE_TIMEOUT_MAX_SECONDS_V338 = 10.0
CSP_SMOKE_RESPONSE_MAX_BYTES_V338 = 1024
CSP_SMOKE_LOG_INPUT_MAX_BYTES_V338 = 512 * 1024
CSP_SMOKE_ID_PATTERN_V338 = re.compile(r"^[a-f0-9]{16}$")
CSP_SMOKE_RESULT_KEYS_V338 = (
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
)
CSP_SMOKE_REASON_CODES_V338 = frozenset(
    {
        "plan_ready",
        "delivery_not_run",
        "delivery_passed",
        "network_error",
        "unexpected_status",
        "enforcement_detected",
        "cache_control_missing",
        "unexpected_response_body",
        "log_not_checked",
        "log_verified",
        "log_evidence_missing",
        "log_input_unreadable",
    }
)


class InvalidCspSmokeTargetV338(ValueError):
    """Raised when an explicit smoke target is not safely approved."""


@dataclass(frozen=True)
class CspSmokePlanV338:
    smoke_id: str
    target_url: str
    target_origin: str
    target_path: str
    timeout_seconds: float
    payload: bytes
    expected_log: str
    expected_log_sha256: str


class _NoRedirectHandlerV338(HTTPRedirectHandler):
    def redirect_request(
        self,
        request,
        file_pointer,
        code,
        message,
        headers,
        new_url,
    ):
        return None


def _normalized_hostname_v338(hostname: str) -> str:
    try:
        return hostname.encode("idna").decode("ascii").casefold()
    except UnicodeError as exc:
        raise InvalidCspSmokeTargetV338(
            "Target hostname is invalid."
        ) from exc


def _is_loopback_v338(hostname: str) -> bool:
    if hostname == "localhost":
        return True

    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _validated_target_v338(
    target_url: str,
    *,
    confirmed_remote_host: str,
) -> tuple[str, str, str]:
    if (
        not isinstance(target_url, str)
        or not target_url
        or any(
            character.isspace()
            or ord(character) < 0x21
            or ord(character) > 0x7E
            for character in target_url
        )
    ):
        raise InvalidCspSmokeTargetV338(
            "Target URL must be printable ASCII without whitespace."
        )

    try:
        parsed = urlsplit(target_url)
        port = parsed.port
    except ValueError as exc:
        raise InvalidCspSmokeTargetV338(
            "Target URL is invalid."
        ) from exc

    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != CSP_SMOKE_PATH_V338
        or parsed.query
        or parsed.fragment
    ):
        raise InvalidCspSmokeTargetV338(
            "Target must use the exact CSP smoke path without credentials."
        )

    hostname = _normalized_hostname_v338(parsed.hostname)
    loopback = _is_loopback_v338(hostname)

    if not loopback:
        if parsed.scheme != "https":
            raise InvalidCspSmokeTargetV338(
                "Remote CSP smoke targets require HTTPS."
            )

        confirmed = _normalized_hostname_v338(
            confirmed_remote_host.strip()
        ) if confirmed_remote_host.strip() else ""

        if confirmed != hostname:
            raise InvalidCspSmokeTargetV338(
                "Remote hostname confirmation does not match."
            )

    rendered_host = (
        f"[{hostname}]"
        if ":" in hostname
        else hostname
    )
    authority = rendered_host

    if port is not None:
        authority += f":{port}"

    origin = f"{parsed.scheme}://{authority}"
    normalized_url = origin + CSP_SMOKE_PATH_V338

    return normalized_url, origin, CSP_SMOKE_PATH_V338


def _expected_evidence_v338(smoke_id: str) -> dict[str, object]:
    synthetic_origin = f"https://v338-{smoke_id}.invalid"

    return {
        "media_type": CSP_SMOKE_MEDIA_TYPE_V338,
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
    }


def _payload_v338(smoke_id: str) -> bytes:
    synthetic_origin = f"https://v338-{smoke_id}.invalid"
    payload = {
        "csp-report": {
            "document-uri": (
                f"{synthetic_origin}/private/page"
                "?token=v338-document-secret"
            ),
            "blocked-uri": "inline",
            "effective-directive": "script-src-attr",
            "violated-directive": "script-src-attr 'none'",
            "source-file": (
                f"{synthetic_origin}/private/source.js"
                "?token=v338-source-secret"
            ),
            "script-sample": "v338-script-sample-secret",
            "line-number": 17,
            "column-number": 4,
            "status-code": 200,
            "disposition": "report",
        }
    }

    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _expected_log_v338(smoke_id: str) -> str:
    return json.dumps(
        {
            "event": "csp_violation_v334",
            "evidence": _expected_evidence_v338(smoke_id),
            "schema_version": 1,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_csp_smoke_plan_v338(
    *,
    target_url: str,
    smoke_id: str,
    timeout_seconds: float,
    confirmed_remote_host: str = "",
) -> CspSmokePlanV338:
    """Build a bounded invented smoke plan without network access."""

    if (
        not isinstance(smoke_id, str)
        or not CSP_SMOKE_ID_PATTERN_V338.fullmatch(smoke_id)
    ):
        raise ValueError("Smoke identifier must be 16 lowercase hex digits.")

    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not (
            CSP_SMOKE_TIMEOUT_MIN_SECONDS_V338
            <= timeout_seconds
            <= CSP_SMOKE_TIMEOUT_MAX_SECONDS_V338
        )
    ):
        raise ValueError("Smoke timeout is outside the approved range.")

    normalized_url, origin, path = _validated_target_v338(
        target_url,
        confirmed_remote_host=confirmed_remote_host,
    )
    expected_log = _expected_log_v338(smoke_id)

    return CspSmokePlanV338(
        smoke_id=smoke_id,
        target_url=normalized_url,
        target_origin=origin,
        target_path=path,
        timeout_seconds=float(timeout_seconds),
        payload=_payload_v338(smoke_id),
        expected_log=expected_log,
        expected_log_sha256=hashlib.sha256(
            expected_log.encode("utf-8")
        ).hexdigest(),
    )


def execute_csp_smoke_v338(
    plan: CspSmokePlanV338,
    *,
    opener=None,
) -> dict[str, object]:
    """POST the invented report once without redirects, cookies, or proxies."""

    request = Request(
        plan.target_url,
        data=plan.payload,
        headers={
            "Accept": "application/json",
            "Content-Type": CSP_SMOKE_MEDIA_TYPE_V338,
            "User-Agent": "classifieds-local-csp-smoke-v338/1",
        },
        method="POST",
    )
    active_opener = opener or build_opener(
        ProxyHandler({}),
        _NoRedirectHandlerV338(),
    )

    try:
        response = active_opener.open(
            request,
            timeout=plan.timeout_seconds,
        )
    except HTTPError as exc:
        response = exc
    except (
        URLError,
        TimeoutError,
        OSError,
        socket.timeout,
    ):
        return {
            "status": "failed",
            "response_status": None,
            "enforcement_absent": None,
            "cache_control_no_store": None,
            "passed": False,
            "reason_code": "network_error",
        }

    with closing(response):
        body = response.read(CSP_SMOKE_RESPONSE_MAX_BYTES_V338 + 1)
        status = int(
            getattr(
                response,
                "status",
                response.getcode(),
            )
        )
        headers = response.headers

    enforcement_absent = (
        headers.get("Content-Security-Policy") is None
    )
    cache_control = headers.get("Cache-Control", "")
    cache_control_no_store = "no-store" in {
        token.strip().casefold()
        for token in cache_control.split(",")
    }

    if status != 204:
        reason_code = "unexpected_status"
    elif not enforcement_absent:
        reason_code = "enforcement_detected"
    elif not cache_control_no_store:
        reason_code = "cache_control_missing"
    elif body:
        reason_code = "unexpected_response_body"
    else:
        reason_code = "delivery_passed"

    passed = reason_code == "delivery_passed"

    return {
        "status": "passed" if passed else "failed",
        "response_status": status,
        "enforcement_absent": enforcement_absent,
        "cache_control_no_store": cache_control_no_store,
        "passed": passed,
        "reason_code": reason_code,
    }


def verify_csp_smoke_log_v338(
    plan: CspSmokePlanV338,
    observed_log: str | None,
) -> dict[str, object]:
    """Require exactly one standalone expected sanitized JSON log line."""

    if observed_log is None:
        return {
            "status": "failed",
            "passed": False,
            "reason_code": "log_input_unreadable",
        }

    if (
        len(observed_log.encode("utf-8"))
        > CSP_SMOKE_LOG_INPUT_MAX_BYTES_V338
    ):
        return {
            "status": "failed",
            "passed": False,
            "reason_code": "log_input_unreadable",
        }

    matches = sum(
        line.strip() == plan.expected_log
        for line in observed_log.splitlines()
    )
    passed = matches == 1

    return {
        "status": "verified" if passed else "failed",
        "passed": passed,
        "reason_code": (
            "log_verified"
            if passed
            else "log_evidence_missing"
        ),
    }


def _read_log_stdin_v338() -> str | None:
    try:
        raw = sys.stdin.buffer.read(
            CSP_SMOKE_LOG_INPUT_MAX_BYTES_V338 + 1
        )
    except OSError:
        return None

    if len(raw) > CSP_SMOKE_LOG_INPUT_MAX_BYTES_V338:
        return None

    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def build_csp_smoke_result_v338(
    *,
    plan: CspSmokePlanV338,
    execute: bool,
    verify_log: bool,
    opener=None,
    observed_log: str | None = None,
) -> dict[str, Any]:
    delivery = (
        execute_csp_smoke_v338(plan, opener=opener)
        if execute
        else {
            "status": "not_run",
            "response_status": None,
            "enforcement_absent": None,
            "cache_control_no_store": None,
            "passed": True,
            "reason_code": "delivery_not_run",
        }
    )
    log_result = (
        verify_csp_smoke_log_v338(plan, observed_log)
        if verify_log
        else {
            "status": "not_checked",
            "passed": True,
            "reason_code": "log_not_checked",
        }
    )
    reason_codes = (
        (
            "plan_ready",
            delivery["reason_code"],
            log_result["reason_code"],
        )
        if not execute and not verify_log
        else (
            delivery["reason_code"],
            log_result["reason_code"],
        )
    )
    passed = bool(delivery["passed"] and log_result["passed"])
    mode = (
        "execute_and_verify"
        if execute and verify_log
        else "execute"
        if execute
        else "verify"
        if verify_log
        else "plan"
    )
    result = {
        "marker": CSP_OBSERVATION_SYNTHETIC_DELIVERY_SMOKE_V338,
        "mode": mode,
        "smoke_id": plan.smoke_id,
        "target_origin": plan.target_origin,
        "target_path": plan.target_path,
        "timeout_seconds": plan.timeout_seconds,
        "expected_log_sha256": plan.expected_log_sha256,
        "delivery_status": delivery["status"],
        "response_status": delivery["response_status"],
        "enforcement_absent": delivery["enforcement_absent"],
        "cache_control_no_store": delivery[
            "cache_control_no_store"
        ],
        "log_status": log_result["status"],
        "passed": passed,
        "reason_codes": reason_codes,
    }

    if tuple(result) != CSP_SMOKE_RESULT_KEYS_V338:
        raise RuntimeError("V338 smoke result key contract changed.")

    if not set(reason_codes).issubset(CSP_SMOKE_REASON_CODES_V338):
        raise RuntimeError("V338 smoke reason contract changed.")

    return result


def _build_parser_v338() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan, execute, or verify a privacy-safe CSP observation smoke."
        )
    )
    parser.add_argument(
        "--target-url",
        required=True,
        help="Exact CSP ingestion URL.",
    )
    parser.add_argument(
        "--smoke-id",
        default="",
        help="Optional reusable 16-character lowercase hex identifier.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=5.0,
        help="Network timeout from 1 through 10 seconds.",
    )
    parser.add_argument(
        "--confirm-remote-host",
        default="",
        help="Repeat a non-loopback HTTPS hostname to approve it.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Send exactly one invented report; otherwise only plan.",
    )
    parser.add_argument(
        "--verify-log-stdin",
        action="store_true",
        help="Verify one exact expected JSON line from bounded stdin.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Emit deterministic JSON.",
    )
    return parser


def main() -> int:
    options = _build_parser_v338().parse_args()
    smoke_id = options.smoke_id or secrets.token_hex(8)

    try:
        plan = build_csp_smoke_plan_v338(
            target_url=options.target_url,
            smoke_id=smoke_id,
            timeout_seconds=options.timeout_seconds,
            confirmed_remote_host=options.confirm_remote_host,
        )
    except (InvalidCspSmokeTargetV338, ValueError):
        print("CSP smoke configuration rejected.", file=sys.stderr)
        return 2

    observed_log = (
        _read_log_stdin_v338()
        if options.verify_log_stdin
        else None
    )
    result = build_csp_smoke_result_v338(
        plan=plan,
        execute=options.execute,
        verify_log=options.verify_log_stdin,
        observed_log=observed_log,
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
            f"mode={result['mode']} "
            f"passed={str(result['passed']).lower()} "
            f"smoke_id={result['smoke_id']} "
            f"target_origin={result['target_origin']} "
            f"target_path={result['target_path']} "
            f"delivery_status={result['delivery_status']} "
            f"response_status={result['response_status']} "
            f"enforcement_absent={result['enforcement_absent']} "
            f"cache_control_no_store="
            f"{result['cache_control_no_store']} "
            f"log_status={result['log_status']} "
            f"expected_log_sha256={result['expected_log_sha256']}"
        )
        print(
            "reason_codes="
            + ",".join(result["reason_codes"])
        )

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
