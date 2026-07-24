"""Bounded privacy-safe CSP observation-window analysis for v340."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import BinaryIO, Iterable

from config.csp_report_logging_v337 import (
    CSP_REPORT_EVIDENCE_KEYS_V337,
    CSP_REPORT_LOG_EVENT_V337,
    CSP_REPORT_LOG_SCHEMA_VERSION_V337,
    _valid_evidence_v337,
)


CSP_OBSERVATION_WINDOW_ANALYSIS_V340 = (
    "CSP_OBSERVATION_WINDOW_ANALYSIS_V340"
)

CSP_WINDOW_INPUT_MAX_BYTES_V340 = 1024 * 1024
CSP_WINDOW_CLOSEOUT_MAX_BYTES_V340 = 128 * 1024
CSP_WINDOW_MAX_RECORDS_V340 = 10_000
CSP_WINDOW_MIN_SECONDS_V340 = 60
CSP_WINDOW_MAX_SECONDS_V340 = 7 * 24 * 60 * 60
CSP_WINDOW_MAX_BUCKETS_V340 = 8
CSP_WINDOW_OTHER_BUCKET_V340 = "__other__"

CSP_WINDOW_RECORD_KEYS_V340 = (
    "observed_at",
    "event",
    "schema_version",
    "evidence",
)

CSP_WINDOW_SUMMARY_KEYS_V340 = (
    "value",
    "count",
)

CSP_WINDOW_RESULT_KEYS_V340 = (
    "marker",
    "status",
    "ready",
    "read_only",
    "network_activity",
    "persistence",
    "enforcement",
    "window_start",
    "window_end",
    "window_seconds",
    "input_record_count",
    "included_record_count",
    "excluded_record_count",
    "synthetic_record_count",
    "organic_record_count",
    "directive_summary",
    "blocked_resource_summary",
    "disposition_summary",
    "media_type_summary",
    "status_code_summary",
    "reason_codes",
)

CSP_WINDOW_REASON_CODES_V340 = frozenset(
    {
        "analysis_ready",
        "no_records_in_window",
        "synthetic_only_window",
        "closeout_not_approved",
        "window_invalid",
        "window_too_short",
        "window_too_long",
        "input_unreadable",
        "input_too_large",
        "record_limit_exceeded",
        "record_invalid",
    }
)

_CLOSEOUT_MARKER_V340 = (
    "CSP_OBSERVATION_EVIDENCE_CLOSEOUT_AUDIT_V339"
)

_CLOSEOUT_RESULT_KEYS_V340 = (
    "marker",
    "status",
    "ready",
    "read_only",
    "checks",
    "ready_count",
    "not_ready_count",
)

_CLOSEOUT_CHECK_KEYS_V340 = (
    "check_id",
    "status",
    "passed",
    "reason_code",
)

_CLOSEOUT_CHECK_IDS_V340 = (
    "expected_origin_valid",
    "readiness_evidence_valid",
    "edge_evidence_valid",
    "retention_evidence_valid",
    "delivery_evidence_valid",
    "log_evidence_valid",
    "smoke_evidence_linked",
    "enforcement_absent",
)

_SYNTHETIC_ORIGIN_PATTERN_V340 = re.compile(
    r"^https://v338-[a-f0-9]{16}\.invalid$"
)


def _canonical_timestamp_v340(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc)

    if normalized.microsecond:
        rendered = normalized.isoformat(
            timespec="microseconds"
        )
    else:
        rendered = normalized.isoformat(
            timespec="seconds"
        )

    return rendered.replace("+00:00", "Z")


def _parse_timestamp_v340(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None

    if any(
        character.isspace()
        for character in value
    ):
        return None

    candidate = (
        value[:-1] + "+00:00"
        if value.endswith("Z")
        else value
    )

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return None

    return parsed.astimezone(timezone.utc)


def _valid_closeout_v340(value: object) -> bool:
    if type(value) is not dict:
        return False

    if (
        len(value) != len(_CLOSEOUT_RESULT_KEYS_V340)
        or set(value) != set(_CLOSEOUT_RESULT_KEYS_V340)
    ):
        return False

    checks = value.get("checks")

    if (
        value["marker"] != _CLOSEOUT_MARKER_V340
        or value["status"] != "ready"
        or value["ready"] is not True
        or value["read_only"] is not True
        or value["ready_count"] != len(_CLOSEOUT_CHECK_IDS_V340)
        or value["not_ready_count"] != 0
        or type(checks) is not list
        or len(checks) != len(_CLOSEOUT_CHECK_IDS_V340)
    ):
        return False

    observed_ids = []

    for check in checks:
        if (
            type(check) is not dict
            or len(check) != len(_CLOSEOUT_CHECK_KEYS_V340)
            or set(check) != set(_CLOSEOUT_CHECK_KEYS_V340)
            or check["status"] != "ready"
            or check["passed"] is not True
            or check["reason_code"] != "ready"
            or check["check_id"] not in _CLOSEOUT_CHECK_IDS_V340
        ):
            return False

        observed_ids.append(check["check_id"])

    return tuple(observed_ids) == _CLOSEOUT_CHECK_IDS_V340


def _ordered_evidence_v340(
    value: object,
) -> dict[str, object] | None:
    if (
        type(value) is not dict
        or len(value) != len(CSP_REPORT_EVIDENCE_KEYS_V337)
        or set(value) != set(CSP_REPORT_EVIDENCE_KEYS_V337)
    ):
        return None

    ordered = {
        key: value[key]
        for key in CSP_REPORT_EVIDENCE_KEYS_V337
    }

    if not _valid_evidence_v337(ordered):
        return None

    return ordered


def _validated_record_v340(
    value: object,
) -> tuple[datetime, dict[str, object]] | None:
    if (
        type(value) is not dict
        or len(value) != len(CSP_WINDOW_RECORD_KEYS_V340)
        or set(value) != set(CSP_WINDOW_RECORD_KEYS_V340)
        or value.get("event") != CSP_REPORT_LOG_EVENT_V337
        or value.get("schema_version")
        != CSP_REPORT_LOG_SCHEMA_VERSION_V337
    ):
        return None

    observed_at = _parse_timestamp_v340(
        value.get("observed_at")
    )

    evidence = _ordered_evidence_v340(
        value.get("evidence")
    )

    if observed_at is None or evidence is None:
        return None

    return observed_at, evidence


def _blocked_resource_class_v340(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return "origin"

    if value.endswith("-scheme"):
        return "scheme"

    return value


def _status_code_class_v340(value: int | None) -> str:
    if value is None:
        return "none"

    if value == 0:
        return "zero"

    return f"{value // 100}xx"


def _is_synthetic_v340(
    evidence: dict[str, object],
) -> bool:
    document_origin = evidence["document_origin"]
    source_origin = evidence["source_origin"]

    return (
        isinstance(document_origin, str)
        and isinstance(source_origin, str)
        and document_origin == source_origin
        and bool(
            _SYNTHETIC_ORIGIN_PATTERN_V340.fullmatch(
                document_origin
            )
        )
    )


def _bounded_summary_v340(
    values: Iterable[str],
) -> list[dict[str, object]]:
    counter = Counter(values)

    ordered = sorted(
        counter.items(),
        key=lambda item: (
            -item[1],
            item[0],
        ),
    )

    if len(ordered) > CSP_WINDOW_MAX_BUCKETS_V340:
        retained = ordered[
            : CSP_WINDOW_MAX_BUCKETS_V340 - 1
        ]
        overflow_count = sum(
            count
            for _, count in ordered[
                CSP_WINDOW_MAX_BUCKETS_V340 - 1 :
            ]
        )
        ordered = [
            *retained,
            (
                CSP_WINDOW_OTHER_BUCKET_V340,
                overflow_count,
            ),
        ]

    result = [
        {
            "value": value,
            "count": count,
        }
        for value, count in ordered
    ]

    for item in result:
        if tuple(item) != CSP_WINDOW_SUMMARY_KEYS_V340:
            raise RuntimeError(
                "V340 summary item key contract changed."
            )

    return result


def _result_v340(
    *,
    status: str,
    ready: bool,
    reason_codes: tuple[str, ...],
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    window_seconds: int | None = None,
    input_record_count: int = 0,
    included_record_count: int = 0,
    excluded_record_count: int = 0,
    synthetic_record_count: int = 0,
    organic_record_count: int = 0,
    directive_summary: list[dict[str, object]] | None = None,
    blocked_resource_summary: list[dict[str, object]] | None = None,
    disposition_summary: list[dict[str, object]] | None = None,
    media_type_summary: list[dict[str, object]] | None = None,
    status_code_summary: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if not set(reason_codes).issubset(
        CSP_WINDOW_REASON_CODES_V340
    ):
        raise RuntimeError(
            "V340 reason-code contract changed."
        )

    result = {
        "marker": CSP_OBSERVATION_WINDOW_ANALYSIS_V340,
        "status": status,
        "ready": ready,
        "read_only": True,
        "network_activity": False,
        "persistence": False,
        "enforcement": False,
        "window_start": (
            _canonical_timestamp_v340(window_start)
            if window_start is not None
            else None
        ),
        "window_end": (
            _canonical_timestamp_v340(window_end)
            if window_end is not None
            else None
        ),
        "window_seconds": window_seconds,
        "input_record_count": input_record_count,
        "included_record_count": included_record_count,
        "excluded_record_count": excluded_record_count,
        "synthetic_record_count": synthetic_record_count,
        "organic_record_count": organic_record_count,
        "directive_summary": directive_summary or [],
        "blocked_resource_summary": blocked_resource_summary or [],
        "disposition_summary": disposition_summary or [],
        "media_type_summary": media_type_summary or [],
        "status_code_summary": status_code_summary or [],
        "reason_codes": list(reason_codes),
    }

    if tuple(result) != CSP_WINDOW_RESULT_KEYS_V340:
        raise RuntimeError(
            "V340 result key contract changed."
        )

    return result


def analyze_csp_observation_window_v340(
    *,
    closeout_evidence: object,
    records: object,
    window_start: object,
    window_end: object,
) -> dict[str, object]:
    if not _valid_closeout_v340(closeout_evidence):
        return _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=("closeout_not_approved",),
        )

    parsed_start = _parse_timestamp_v340(window_start)
    parsed_end = _parse_timestamp_v340(window_end)

    if parsed_start is None or parsed_end is None:
        return _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=("window_invalid",),
        )

    duration_total_seconds = (
        parsed_end - parsed_start
    ).total_seconds()

    duration_seconds = int(
        duration_total_seconds
    )

    if duration_total_seconds <= 0:
        return _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=("window_invalid",),
            window_start=parsed_start,
            window_end=parsed_end,
            window_seconds=duration_seconds,
        )

    if duration_total_seconds < CSP_WINDOW_MIN_SECONDS_V340:
        return _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=("window_too_short",),
            window_start=parsed_start,
            window_end=parsed_end,
            window_seconds=duration_seconds,
        )

    if duration_total_seconds > CSP_WINDOW_MAX_SECONDS_V340:
        return _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=("window_too_long",),
            window_start=parsed_start,
            window_end=parsed_end,
            window_seconds=duration_seconds,
        )

    if type(records) is not list:
        return _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=("input_unreadable",),
            window_start=parsed_start,
            window_end=parsed_end,
            window_seconds=duration_seconds,
        )

    if len(records) > CSP_WINDOW_MAX_RECORDS_V340:
        return _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=("record_limit_exceeded",),
            window_start=parsed_start,
            window_end=parsed_end,
            window_seconds=duration_seconds,
            input_record_count=len(records),
        )

    validated = []

    for record in records:
        parsed = _validated_record_v340(record)

        if parsed is None:
            return _result_v340(
                status="not_ready",
                ready=False,
                reason_codes=("record_invalid",),
                window_start=parsed_start,
                window_end=parsed_end,
                window_seconds=duration_seconds,
                input_record_count=len(records),
            )

        validated.append(parsed)

    included = [
        evidence
        for observed_at, evidence in validated
        if parsed_start <= observed_at < parsed_end
    ]

    included_count = len(included)
    synthetic_count = sum(
        1
        for evidence in included
        if _is_synthetic_v340(evidence)
    )
    organic_count = included_count - synthetic_count

    reason_codes = ["analysis_ready"]

    if included_count == 0:
        reason_codes.append(
            "no_records_in_window"
        )
    elif synthetic_count == included_count:
        reason_codes.append(
            "synthetic_only_window"
        )

    return _result_v340(
        status="ready",
        ready=True,
        reason_codes=tuple(reason_codes),
        window_start=parsed_start,
        window_end=parsed_end,
        window_seconds=duration_seconds,
        input_record_count=len(validated),
        included_record_count=included_count,
        excluded_record_count=(
            len(validated) - included_count
        ),
        synthetic_record_count=synthetic_count,
        organic_record_count=organic_count,
        directive_summary=_bounded_summary_v340(
            str(evidence["effective_directive"])
            for evidence in included
        ),
        blocked_resource_summary=_bounded_summary_v340(
            _blocked_resource_class_v340(
                str(evidence["blocked_resource"])
            )
            for evidence in included
        ),
        disposition_summary=_bounded_summary_v340(
            str(evidence["disposition"])
            for evidence in included
        ),
        media_type_summary=_bounded_summary_v340(
            str(evidence["media_type"])
            for evidence in included
        ),
        status_code_summary=_bounded_summary_v340(
            _status_code_class_v340(
                evidence["status_code"]
                if isinstance(
                    evidence["status_code"],
                    int,
                )
                else None
            )
            for evidence in included
        ),
    )


def _read_bounded_json_v340(
    path: Path,
) -> dict[str, object] | None:
    try:
        with path.open("rb") as input_file:
            raw = input_file.read(
                CSP_WINDOW_CLOSEOUT_MAX_BYTES_V340 + 1
            )
    except OSError:
        return None

    if len(raw) > CSP_WINDOW_CLOSEOUT_MAX_BYTES_V340:
        return None

    try:
        value = json.loads(raw.decode("utf-8"))
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        RecursionError,
    ):
        return None

    return value if type(value) is dict else None


def _read_jsonl_stream_v340(
    stream: BinaryIO,
) -> tuple[list[object] | None, str | None]:
    try:
        raw = stream.read(
            CSP_WINDOW_INPUT_MAX_BYTES_V340 + 1
        )
    except (
        OSError,
        ValueError,
    ):
        return None, "input_unreadable"

    if not isinstance(raw, bytes):
        return None, "input_unreadable"

    if len(raw) > CSP_WINDOW_INPUT_MAX_BYTES_V340:
        return None, "input_too_large"

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, "input_unreadable"

    lines = [
        line
        for line in text.splitlines()
        if line.strip()
    ]

    if len(lines) > CSP_WINDOW_MAX_RECORDS_V340:
        return None, "record_limit_exceeded"

    values = []

    for line in lines:
        try:
            values.append(json.loads(line))
        except (
            json.JSONDecodeError,
            RecursionError,
        ):
            return None, "input_unreadable"

    return values, None


def _build_parser_v340() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analyze one bounded window of approved sanitized "
            "V337 CSP evidence from JSONL stdin."
        )
    )
    parser.add_argument(
        "--closeout-json",
        type=Path,
        required=True,
        help="Approved bounded V339 closeout JSON file.",
    )
    parser.add_argument(
        "--window-start",
        required=True,
        help="Inclusive timezone-aware observation-window start.",
    )
    parser.add_argument(
        "--window-end",
        required=True,
        help="Exclusive timezone-aware observation-window end.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Emit compact deterministic JSON.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero unless the analysis is ready.",
    )
    return parser


def main(
    argv: list[str] | None = None,
    *,
    stdin: BinaryIO | None = None,
) -> int:
    options = _build_parser_v340().parse_args(argv)

    closeout = _read_bounded_json_v340(
        options.closeout_json
    )

    records, input_error = _read_jsonl_stream_v340(
        stdin if stdin is not None else sys.stdin.buffer
    )

    if input_error is not None:
        result = _result_v340(
            status="not_ready",
            ready=False,
            reason_codes=(input_error,),
        )
    else:
        result = analyze_csp_observation_window_v340(
            closeout_evidence=closeout,
            records=records,
            window_start=options.window_start,
            window_end=options.window_end,
        )

    if options.json_output:
        print(
            json.dumps(
                result,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    else:
        print(result["marker"])
        print(
            f"status={result['status']} "
            f"ready={str(result['ready']).lower()} "
            f"read_only=true "
            f"window_start={result['window_start']} "
            f"window_end={result['window_end']} "
            f"window_seconds={result['window_seconds']}"
        )
        print(
            f"input_records={result['input_record_count']} "
            f"included={result['included_record_count']} "
            f"excluded={result['excluded_record_count']} "
            f"synthetic={result['synthetic_record_count']} "
            f"organic={result['organic_record_count']}"
        )
        print(
            "reason_codes="
            + ",".join(result["reason_codes"])
        )

    if options.strict and not result["ready"]:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
