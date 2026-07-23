"""Bounded, sanitized, non-persistent CSP report ingestion for v334."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from urllib.parse import urlsplit

from django.core.cache import cache
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseNotAllowed,
    JsonResponse,
)
from django.views.decorators.csrf import csrf_exempt

from config.csp_report_logging_v337 import (
    CSP_REPORT_EVIDENCE_EXTRA_V337,
)


CSP_REPORT_INGESTION_FOUNDATION_V334 = True
CSP_REPORT_PATH_V334 = "__csp_reports__/"
CSP_REPORT_MEDIA_TYPES_V334 = frozenset(
    {
        "application/csp-report",
        "application/reports+json",
    }
)
CSP_REPORT_MAX_BODY_BYTES_V334 = 16 * 1024
CSP_REPORT_MAX_BATCH_ITEMS_V334 = 10
CSP_REPORT_RATE_LIMIT_V334 = 60
CSP_REPORT_RATE_WINDOW_SECONDS_V334 = 60
CSP_REPORT_LOGGER_NAME_V334 = "security.csp_report_v334"

_DIRECTIVE_PATTERN_V334 = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_SCHEME_PATTERN_V334 = re.compile(r"^[a-z][a-z0-9+.-]{0,31}$")
_RESOURCE_TOKENS_V334 = frozenset(
    {
        "blob",
        "data",
        "empty",
        "eval",
        "inline",
        "self",
        "wasm-eval",
    }
)

logger = logging.getLogger(CSP_REPORT_LOGGER_NAME_V334)


class InvalidCspReportV334(ValueError):
    """Raised when a CSP report payload does not match an accepted shape."""


def _response_v334(
    *,
    status: int,
    error: str | None = None,
    retry_after: int | None = None,
) -> HttpResponse:
    if error is None:
        response = HttpResponse(status=status)
    else:
        response = JsonResponse(
            {"error": error},
            status=status,
        )

    response["Cache-Control"] = "no-store"

    if retry_after is not None:
        response["Retry-After"] = str(retry_after)

    return response


def _rate_limit_key_v334(request: HttpRequest) -> str:
    remote_address = str(
        request.META.get("REMOTE_ADDR") or "unknown"
    )
    digest = hashlib.sha256(
        remote_address.encode("utf-8", errors="replace")
    ).hexdigest()[:24]

    return f"csp-report-v334:{digest}"


def csp_report_rate_limited_v334(request: HttpRequest) -> bool:
    """Apply a fixed-window, hashed-client cache limit before body parsing."""

    key = _rate_limit_key_v334(request)

    if cache.add(
        key,
        1,
        timeout=CSP_REPORT_RATE_WINDOW_SECONDS_V334,
    ):
        return False

    try:
        request_count = cache.incr(key)
    except ValueError:
        if cache.add(
            key,
            1,
            timeout=CSP_REPORT_RATE_WINDOW_SECONDS_V334,
        ):
            return False
        request_count = cache.incr(key)

    return request_count > CSP_REPORT_RATE_LIMIT_V334


def parse_csp_report_payload_v334(
    *,
    body: bytes,
    media_type: str,
) -> tuple[dict[str, object], ...]:
    """Parse one legacy report or a bounded Reporting API batch."""

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise InvalidCspReportV334("Malformed CSP report JSON.") from exc

    if media_type == "application/csp-report":
        if (
            not isinstance(payload, dict)
            or not isinstance(payload.get("csp-report"), dict)
        ):
            raise InvalidCspReportV334(
                "Legacy CSP report must contain a csp-report object."
            )

        return (payload["csp-report"],)

    if media_type == "application/reports+json":
        if (
            not isinstance(payload, list)
            or not payload
            or len(payload) > CSP_REPORT_MAX_BATCH_ITEMS_V334
        ):
            raise InvalidCspReportV334(
                "Reporting API payload must be a bounded non-empty array."
            )

        reports = []

        for entry in payload:
            if (
                not isinstance(entry, dict)
                or entry.get("type") != "csp-violation"
                or not isinstance(entry.get("body"), dict)
            ):
                raise InvalidCspReportV334(
                    "Reporting API entry must be a csp-violation object."
                )
            reports.append(entry["body"])

        return tuple(reports)

    raise InvalidCspReportV334("Unsupported CSP report media type.")


def _first_value_v334(
    report: dict[str, object],
    *keys: str,
) -> object:
    for key in keys:
        if key in report:
            return report[key]

    return None


def _sanitize_directive_v334(value: object) -> str:
    if not isinstance(value, str):
        return "unknown"

    token = value.strip().casefold().split(" ", 1)[0]

    if _DIRECTIVE_PATTERN_V334.fullmatch(token):
        return token

    return "unknown"


def _sanitize_disposition_v334(value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip().casefold()

        if normalized in {"enforce", "report"}:
            return normalized

    return "unknown"


def _sanitize_bounded_int_v334(
    value: object,
    *,
    maximum: int,
) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        normalized = value
    elif isinstance(value, str) and value.isdecimal():
        normalized = int(value)
    else:
        return None

    if 0 <= normalized <= maximum:
        return normalized

    return None


def _sanitize_resource_v334(value: object) -> str:
    """
    Retain only a CSP keyword, URL origin, relative marker, or scheme class.

    Paths, queries, fragments, credentials, and samples are never returned.
    """

    if not isinstance(value, str):
        return "unknown"

    normalized = value.strip()

    if not normalized:
        return "empty"

    if len(normalized) > 2048:
        return "unknown"

    keyword = normalized.casefold().removesuffix(":")

    if keyword in _RESOURCE_TOKENS_V334:
        return keyword

    if normalized.startswith("/") and not normalized.startswith("//"):
        return "same-origin-relative"

    try:
        parsed = urlsplit(normalized)
        scheme = parsed.scheme.casefold()
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return "unknown"

    if scheme in {"http", "https"} and hostname:
        try:
            ascii_hostname = hostname.encode("idna").decode("ascii")
        except UnicodeError:
            return "unknown"

        origin = f"{scheme}://{ascii_hostname.casefold()}"

        if port is not None:
            origin += f":{port}"

        return origin

    if _SCHEME_PATTERN_V334.fullmatch(scheme):
        return f"{scheme}-scheme"

    return "unknown"


def sanitize_csp_report_v334(
    report: dict[str, object],
) -> dict[str, object]:
    """Return the fixed, privacy-bounded operator evidence schema."""

    return {
        "blocked_resource": _sanitize_resource_v334(
            _first_value_v334(
                report,
                "blocked-uri",
                "blockedURL",
            )
        ),
        "column_number": _sanitize_bounded_int_v334(
            _first_value_v334(
                report,
                "column-number",
                "columnNumber",
            ),
            maximum=10_000_000,
        ),
        "disposition": _sanitize_disposition_v334(
            _first_value_v334(report, "disposition")
        ),
        "document_origin": _sanitize_resource_v334(
            _first_value_v334(
                report,
                "document-uri",
                "documentURL",
            )
        ),
        "effective_directive": _sanitize_directive_v334(
            _first_value_v334(
                report,
                "effective-directive",
                "effectiveDirective",
            )
        ),
        "line_number": _sanitize_bounded_int_v334(
            _first_value_v334(
                report,
                "line-number",
                "lineNumber",
            ),
            maximum=10_000_000,
        ),
        "source_origin": _sanitize_resource_v334(
            _first_value_v334(
                report,
                "source-file",
                "sourceFile",
            )
        ),
        "status_code": _sanitize_bounded_int_v334(
            _first_value_v334(
                report,
                "status-code",
                "statusCode",
            ),
            maximum=599,
        ),
        "violated_directive": _sanitize_directive_v334(
            _first_value_v334(
                report,
                "violated-directive",
                "violatedDirective",
                "effectiveDirective",
            )
        ),
    }


def _read_bounded_body_v334(
    request: HttpRequest,
) -> tuple[bytes | None, str | None]:
    raw_content_length = request.META.get("CONTENT_LENGTH")

    if raw_content_length not in (None, ""):
        try:
            content_length = int(raw_content_length)
        except (TypeError, ValueError):
            return None, "invalid-content-length"

        if content_length < 0:
            return None, "invalid-content-length"

        if content_length > CSP_REPORT_MAX_BODY_BYTES_V334:
            return None, "payload-too-large"

    try:
        body = request.read(CSP_REPORT_MAX_BODY_BYTES_V334 + 1)
    except OSError:
        return None, "unreadable-report"

    if len(body) > CSP_REPORT_MAX_BODY_BYTES_V334:
        return None, "payload-too-large"

    if not body:
        return None, "empty-report"

    return body, None


@csrf_exempt
def csp_report_ingestion_v334(request: HttpRequest) -> HttpResponse:
    """Accept sanitized CSP observations without application persistence."""

    from django.conf import settings

    if not getattr(settings, "CSP_REPORT_INGESTION_ENABLED", False):
        return _response_v334(
            status=404,
            error="not-found",
        )

    if request.method != "POST":
        response = HttpResponseNotAllowed(["POST"])
        response["Cache-Control"] = "no-store"
        return response

    media_type = request.content_type

    if media_type not in CSP_REPORT_MEDIA_TYPES_V334:
        return _response_v334(
            status=415,
            error="unsupported-media-type",
        )

    if csp_report_rate_limited_v334(request):
        return _response_v334(
            status=429,
            error="rate-limit-exceeded",
            retry_after=CSP_REPORT_RATE_WINDOW_SECONDS_V334,
        )

    body, body_error = _read_bounded_body_v334(request)

    if body_error == "payload-too-large":
        return _response_v334(
            status=413,
            error=body_error,
        )

    if body_error is not None or body is None:
        return _response_v334(
            status=400,
            error=body_error or "invalid-report",
        )

    try:
        reports = parse_csp_report_payload_v334(
            body=body,
            media_type=media_type,
        )
    except InvalidCspReportV334:
        return _response_v334(
            status=400,
            error="invalid-report",
        )

    for report_index, report in enumerate(reports, start=1):
        evidence = {
            "media_type": media_type,
            "report_index": report_index,
            **sanitize_csp_report_v334(report),
        }
        logger.info(
            "csp_violation_v334 %s",
            json.dumps(
                evidence,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ),
            extra={
                CSP_REPORT_EVIDENCE_EXTRA_V337: evidence,
            },
        )

    return _response_v334(status=204)
