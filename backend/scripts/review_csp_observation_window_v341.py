from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from scripts.analyze_csp_observation_window_v340 import (
    CSP_OBSERVATION_WINDOW_ANALYSIS_V340,
    CSP_WINDOW_MAX_BUCKETS_V340,
    CSP_WINDOW_MAX_SECONDS_V340,
    CSP_WINDOW_MIN_SECONDS_V340,
    CSP_WINDOW_OTHER_BUCKET_V340,
    CSP_WINDOW_REASON_CODES_V340,
    CSP_WINDOW_RESULT_KEYS_V340,
    CSP_WINDOW_SUMMARY_KEYS_V340,
)

CSP_OBSERVATION_WINDOW_REVIEW_V341 = (
    "CSP_OBSERVATION_WINDOW_REVIEW_V341"
)

CSP_REVIEW_INPUT_MAX_BYTES_V341 = 128 * 1024
CSP_REVIEW_MIN_WINDOW_SECONDS_V341 = 24 * 60 * 60
CSP_REVIEW_MIN_ORGANIC_RECORDS_V341 = 25
CSP_REVIEW_MAX_SYNTHETIC_RECORDS_V341 = 0

CSP_REVIEW_RESULT_KEYS_V341 = (
    "marker",
    "source_marker",
    "status",
    "ready",
    "recommendation",
    "automatic_action",
    "read_only",
    "network_activity",
    "persistence",
    "enforcement",
    "gate_change",
    "configuration_mutation",
    "window_start",
    "window_end",
    "window_seconds",
    "input_record_count",
    "included_record_count",
    "excluded_record_count",
    "synthetic_record_count",
    "organic_record_count",
    "thresholds",
    "reason_codes",
)

CSP_REVIEW_THRESHOLD_KEYS_V341 = (
    "minimum_window_seconds",
    "minimum_organic_records",
    "maximum_synthetic_records",
)

CSP_REVIEW_REASON_CODES_V341 = frozenset(
    {
        "review_ready",
        "summary_invalid",
        "summary_input_unreadable",
        "summary_input_too_large",
        "window_too_short_for_review",
        "no_records_in_window",
        "synthetic_only_window",
        "synthetic_records_present",
        "organic_record_count_below_threshold",
    }
)

CSP_REVIEW_RECOMMENDATIONS_V341 = frozenset(
    {
        "reject_summary",
        "continue_observation",
        "review_clean_organic_findings",
    }
)

CSP_REVIEW_STATUSES_V341 = frozenset(
    {
        "not_ready",
        "insufficient_evidence",
        "ready",
    }
)


_SOURCE_SUMMARY_FIELDS_V341 = (
    "directive_summary",
    "blocked_resource_summary",
    "disposition_summary",
    "media_type_summary",
    "status_code_summary",
)


def _canonical_timestamp_v341(
    value: object,
) -> datetime | None:
    if type(value) is not str:
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

    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat().replace("+00:00", "Z")

    if value != canonical:
        return None

    return parsed


def _valid_count_v341(value: object) -> bool:
    return type(value) is int and value >= 0


def _valid_summary_v341(
    value: object,
    *,
    included_record_count: int,
) -> bool:
    if (
        type(value) is not list
        or len(value) > CSP_WINDOW_MAX_BUCKETS_V340
    ):
        return False

    observed = []

    for item in value:
        if (
            type(item) is not dict
            or len(item) != len(CSP_WINDOW_SUMMARY_KEYS_V340)
            or set(item) != set(CSP_WINDOW_SUMMARY_KEYS_V340)
            or type(item["value"]) is not str
            or not item["value"]
            or type(item["count"]) is not int
            or item["count"] <= 0
        ):
            return False

        observed.append(
            (item["value"], item["count"])
        )

    if len({name for name, _ in observed}) != len(observed):
        return False

    other_positions = [
        index
        for index, (name, _) in enumerate(observed)
        if name == CSP_WINDOW_OTHER_BUCKET_V340
    ]

    if other_positions:
        if (
            other_positions != [len(observed) - 1]
            or len(observed) != CSP_WINDOW_MAX_BUCKETS_V340
        ):
            return False

        ordered_items = observed[:-1]
    else:
        ordered_items = observed

    if ordered_items != sorted(
        ordered_items,
        key=lambda item: (-item[1], item[0]),
    ):
        return False

    return (
        sum(count for _, count in observed)
        == included_record_count
    )


def _valid_v340_summary_v341(value: object) -> bool:
    if (
        type(value) is not dict
        or len(value) != len(CSP_WINDOW_RESULT_KEYS_V340)
        or set(value) != set(CSP_WINDOW_RESULT_KEYS_V340)
        or value["marker"]
        != CSP_OBSERVATION_WINDOW_ANALYSIS_V340
        or value["status"] != "ready"
        or value["ready"] is not True
        or value["read_only"] is not True
        or value["network_activity"] is not False
        or value["persistence"] is not False
        or value["enforcement"] is not False
    ):
        return False

    start = _canonical_timestamp_v341(
        value["window_start"]
    )
    end = _canonical_timestamp_v341(
        value["window_end"]
    )

    if start is None or end is None or end <= start:
        return False

    exact_seconds = (end - start).total_seconds()
    window_seconds = value["window_seconds"]

    if (
        type(window_seconds) is not int
        or window_seconds != int(exact_seconds)
        or exact_seconds < CSP_WINDOW_MIN_SECONDS_V340
        or exact_seconds > CSP_WINDOW_MAX_SECONDS_V340
    ):
        return False

    count_keys = (
        "input_record_count",
        "included_record_count",
        "excluded_record_count",
        "synthetic_record_count",
        "organic_record_count",
    )

    if not all(
        _valid_count_v341(value[key])
        for key in count_keys
    ):
        return False

    input_count = value["input_record_count"]
    included = value["included_record_count"]
    excluded = value["excluded_record_count"]
    synthetic = value["synthetic_record_count"]
    organic = value["organic_record_count"]

    if (
        included + excluded != input_count
        or synthetic + organic != included
    ):
        return False

    expected_reasons = ["analysis_ready"]
    if included == 0:
        expected_reasons.append("no_records_in_window")
    elif synthetic == included:
        expected_reasons.append("synthetic_only_window")

    reasons = value["reason_codes"]
    if (
        type(reasons) is not list
        or reasons != expected_reasons
        or not set(reasons).issubset(
            CSP_WINDOW_REASON_CODES_V340
        )
    ):
        return False

    return all(
        _valid_summary_v341(
            value[field],
            included_record_count=included,
        )
        for field in _SOURCE_SUMMARY_FIELDS_V341
    )




def _read_bounded_json_v341(
    path: Path,
) -> tuple[object | None, str | None]:
    try:
        with path.open("rb") as handle:
            payload = handle.read(
                CSP_REVIEW_INPUT_MAX_BYTES_V341 + 1
            )
    except OSError:
        return None, "summary_input_unreadable"

    if len(payload) > CSP_REVIEW_INPUT_MAX_BYTES_V341:
        return None, "summary_input_too_large"

    try:
        decoded = payload.decode("utf-8")
        return json.loads(decoded), None
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "summary_input_unreadable"


def _result_v341(
    *,
    source: dict[str, object] | None,
    status: str,
    ready: bool,
    recommendation: str,
    reason_codes: tuple[str, ...],
) -> dict[str, object]:
    if status not in CSP_REVIEW_STATUSES_V341:
        raise RuntimeError("V341 status contract changed.")

    if recommendation not in CSP_REVIEW_RECOMMENDATIONS_V341:
        raise RuntimeError(
            "V341 recommendation contract changed."
        )

    if not set(reason_codes).issubset(
        CSP_REVIEW_REASON_CODES_V341
    ):
        raise RuntimeError(
            "V341 reason-code contract changed."
        )

    thresholds = {
        "minimum_window_seconds":
            CSP_REVIEW_MIN_WINDOW_SECONDS_V341,
        "minimum_organic_records":
            CSP_REVIEW_MIN_ORGANIC_RECORDS_V341,
        "maximum_synthetic_records":
            CSP_REVIEW_MAX_SYNTHETIC_RECORDS_V341,
    }

    if tuple(thresholds) != CSP_REVIEW_THRESHOLD_KEYS_V341:
        raise RuntimeError(
            "V341 threshold key contract changed."
        )

    result = {
        "marker": CSP_OBSERVATION_WINDOW_REVIEW_V341,
        "source_marker": (
            source["marker"] if source is not None else None
        ),
        "status": status,
        "ready": ready,
        "recommendation": recommendation,
        "automatic_action": False,
        "read_only": True,
        "network_activity": False,
        "persistence": False,
        "enforcement": False,
        "gate_change": False,
        "configuration_mutation": False,
        "window_start": (
            source["window_start"]
            if source is not None
            else None
        ),
        "window_end": (
            source["window_end"]
            if source is not None
            else None
        ),
        "window_seconds": (
            source["window_seconds"]
            if source is not None
            else None
        ),
        "input_record_count": (
            source["input_record_count"]
            if source is not None
            else 0
        ),
        "included_record_count": (
            source["included_record_count"]
            if source is not None
            else 0
        ),
        "excluded_record_count": (
            source["excluded_record_count"]
            if source is not None
            else 0
        ),
        "synthetic_record_count": (
            source["synthetic_record_count"]
            if source is not None
            else 0
        ),
        "organic_record_count": (
            source["organic_record_count"]
            if source is not None
            else 0
        ),
        "thresholds": thresholds,
        "reason_codes": list(reason_codes),
    }

    if tuple(result) != CSP_REVIEW_RESULT_KEYS_V341:
        raise RuntimeError(
            "V341 result key contract changed."
        )

    return result


def review_csp_observation_window_v341(
    summary: object,
) -> dict[str, object]:
    if not _valid_v340_summary_v341(summary):
        return _result_v341(
            source=None,
            status="not_ready",
            ready=False,
            recommendation="reject_summary",
            reason_codes=("summary_invalid",),
        )

    source = summary

    if (
        source["window_seconds"]
        < CSP_REVIEW_MIN_WINDOW_SECONDS_V341
    ):
        return _result_v341(
            source=source,
            status="insufficient_evidence",
            ready=False,
            recommendation="continue_observation",
            reason_codes=(
                "window_too_short_for_review",
            ),
        )

    if source["included_record_count"] == 0:
        return _result_v341(
            source=source,
            status="insufficient_evidence",
            ready=False,
            recommendation="continue_observation",
            reason_codes=("no_records_in_window",),
        )

    if (
        source["synthetic_record_count"]
        == source["included_record_count"]
    ):
        return _result_v341(
            source=source,
            status="insufficient_evidence",
            ready=False,
            recommendation="continue_observation",
            reason_codes=("synthetic_only_window",),
        )

    if (
        source["synthetic_record_count"]
        > CSP_REVIEW_MAX_SYNTHETIC_RECORDS_V341
    ):
        return _result_v341(
            source=source,
            status="insufficient_evidence",
            ready=False,
            recommendation="continue_observation",
            reason_codes=("synthetic_records_present",),
        )

    if (
        source["organic_record_count"]
        < CSP_REVIEW_MIN_ORGANIC_RECORDS_V341
    ):
        return _result_v341(
            source=source,
            status="insufficient_evidence",
            ready=False,
            recommendation="continue_observation",
            reason_codes=(
                "organic_record_count_below_threshold",
            ),
        )

    return _result_v341(
        source=source,
        status="ready",
        ready=True,
        recommendation="review_clean_organic_findings",
        reason_codes=("review_ready",),
    )



def _build_parser_v341() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Review one approved bounded V340 CSP "
            "observation-window summary."
        )
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        required=True,
        help="Bounded V340 observation-window summary JSON.",
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
        help="Exit non-zero unless review is ready.",
    )
    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    options = _build_parser_v341().parse_args(argv)

    summary, input_error = _read_bounded_json_v341(
        options.summary_json
    )

    if input_error is not None:
        result = _result_v341(
            source=None,
            status="not_ready",
            ready=False,
            recommendation="reject_summary",
            reason_codes=(input_error,),
        )
    else:
        result = review_csp_observation_window_v341(
            summary
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
            f"recommendation={result['recommendation']} "
            f"automatic_action=false"
        )
        print(
            f"window_start={result['window_start']} "
            f"window_end={result['window_end']} "
            f"window_seconds={result['window_seconds']}"
        )
        print(
            f"included={result['included_record_count']} "
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
