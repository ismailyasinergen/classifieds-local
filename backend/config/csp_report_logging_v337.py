"""Fail-closed structured logging for sanitized CSP evidence in v337."""

from __future__ import annotations

import json
import logging
import re


CSP_REPORT_LOG_OPERATIONS_BASELINE_V337 = True
CSP_REPORT_EVIDENCE_EXTRA_V337 = "csp_report_evidence_v337"
CSP_REPORT_LOG_EVENT_V337 = "csp_violation_v334"
CSP_REPORT_LOG_REJECTED_EVENT_V337 = (
    "csp_report_log_rejected_v337"
)
CSP_REPORT_LOG_SCHEMA_VERSION_V337 = 1
CSP_REPORT_EVIDENCE_KEYS_V337 = (
    "media_type",
    "report_index",
    "blocked_resource",
    "column_number",
    "disposition",
    "document_origin",
    "effective_directive",
    "line_number",
    "source_origin",
    "status_code",
    "violated_directive",
)
CSP_REPORT_ALLOWED_MEDIA_TYPES_V337 = frozenset(
    {
        "application/csp-report",
        "application/reports+json",
    }
)

_DIRECTIVE_PATTERN_V337 = re.compile(
    r"^[a-z][a-z0-9-]{0,63}$"
)
_SCHEME_CLASS_PATTERN_V337 = re.compile(
    r"^[a-z][a-z0-9+.-]{0,31}-scheme$"
)
_RESOURCE_CLASSES_V337 = frozenset(
    {
        "blob",
        "data",
        "empty",
        "eval",
        "inline",
        "same-origin-relative",
        "self",
        "unknown",
        "wasm-eval",
    }
)


def _bounded_int_v337(
    value: object,
    *,
    minimum: int,
    maximum: int,
    allow_none: bool = True,
) -> bool:
    if value is None:
        return allow_none

    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and minimum <= value <= maximum
    )


def _safe_resource_v337(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 255:
        return False

    if value in _RESOURCE_CLASSES_V337:
        return True

    if _SCHEME_CLASS_PATTERN_V337.fullmatch(value):
        return True

    for prefix in ("http://", "https://"):
        if value.startswith(prefix):
            authority = value.removeprefix(prefix)

            return (
                bool(authority)
                and all(0x21 <= ord(char) <= 0x7E for char in authority)
                and not any(
                    delimiter in authority
                    for delimiter in ("/", "?", "#", "@", "\\")
                )
            )

    return False


def _valid_evidence_v337(evidence: object) -> bool:
    if type(evidence) is not dict:
        return False

    if tuple(evidence) != CSP_REPORT_EVIDENCE_KEYS_V337:
        return False

    return all(
        (
            evidence["media_type"]
            in CSP_REPORT_ALLOWED_MEDIA_TYPES_V337,
            _bounded_int_v337(
                evidence["report_index"],
                minimum=1,
                maximum=10,
                allow_none=False,
            ),
            _safe_resource_v337(evidence["blocked_resource"]),
            _bounded_int_v337(
                evidence["column_number"],
                minimum=0,
                maximum=10_000_000,
            ),
            evidence["disposition"]
            in {"enforce", "report", "unknown"},
            _safe_resource_v337(evidence["document_origin"]),
            isinstance(evidence["effective_directive"], str)
            and bool(
                _DIRECTIVE_PATTERN_V337.fullmatch(
                    evidence["effective_directive"]
                )
            ),
            _bounded_int_v337(
                evidence["line_number"],
                minimum=0,
                maximum=10_000_000,
            ),
            _safe_resource_v337(evidence["source_origin"]),
            _bounded_int_v337(
                evidence["status_code"],
                minimum=0,
                maximum=599,
            ),
            isinstance(evidence["violated_directive"], str)
            and bool(
                _DIRECTIVE_PATTERN_V337.fullmatch(
                    evidence["violated_directive"]
                )
            ),
        )
    )


class SanitizedCspReportFormatterV337(logging.Formatter):
    """Render only validated evidence and ignore the original log message."""

    def format(self, record: logging.LogRecord) -> str:
        evidence = getattr(
            record,
            CSP_REPORT_EVIDENCE_EXTRA_V337,
            None,
        )

        if _valid_evidence_v337(evidence):
            payload = {
                "event": CSP_REPORT_LOG_EVENT_V337,
                "evidence": evidence,
                "schema_version": CSP_REPORT_LOG_SCHEMA_VERSION_V337,
            }
        else:
            payload = {
                "event": CSP_REPORT_LOG_REJECTED_EVENT_V337,
                "schema_version": CSP_REPORT_LOG_SCHEMA_VERSION_V337,
            }

        return json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
