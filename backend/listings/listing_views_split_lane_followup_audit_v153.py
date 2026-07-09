"""
V153 split-lane follow-up audit after listing promotion view extraction.

This module is intentionally read-only. It records extracted lanes and selects
the next safest split lane from the remaining active lanes.

Updated in v155 to record the favorites lane as extracted after
listing_favorite_toggle moved into listing_favorite_views.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from listings import listing_views_split_lane_audit_v150 as split_audit


LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153 = True
EXTRACTED_LANES_V153 = {
    "listing_promotions": {
        "view": "listing_feature_priority_update",
        "module": "backend/listings/listing_promotion_views.py",
        "checkpoint": "v152",
        "tag": "project-checkpoint-v152-listing-promotion-view-extraction",
    },
    "favorites": {
        "view": "listing_favorite_toggle",
        "module": "backend/listings/listing_favorite_views.py",
        "checkpoint": "v155",
        "tag": "project-checkpoint-v155-favorite-view-extraction",
    },
}


@dataclass(frozen=True)
class ExtractedLaneStatusV153:
    name: str
    extracted: bool
    definition_count: int
    total_lines: int
    view: str
    module: str
    checkpoint: str


@dataclass(frozen=True)
class NextSplitLaneCandidateV153:
    name: str
    definition_count: int
    total_lines: int
    readiness: str
    reason: str


@dataclass(frozen=True)
class SplitLaneFollowupReportV153:
    extracted_lanes: tuple[ExtractedLaneStatusV153, ...]
    remaining_candidates: tuple[NextSplitLaneCandidateV153, ...]
    recommended_next_lane: NextSplitLaneCandidateV153


def _lane_value(lane, name, default=None):
    return getattr(lane, name, default)


def _candidate_reason(lane) -> str:
    name = _lane_value(lane, "name")
    definition_count = _lane_value(lane, "definition_count", 0)
    total_lines = _lane_value(lane, "total_lines", 0)

    if definition_count == 1:
        return (
            f"{name} has one remaining definition and {total_lines} lines, "
            "making it a low-risk next split candidate after extracted lanes."
        )

    return (
        f"{name} remains candidate-sized but has {definition_count} definitions "
        f"across {total_lines} lines, so it should follow smaller single-definition lanes."
    )


def build_followup_report(root: Path | str = ".") -> SplitLaneFollowupReportV153:
    root = Path(root)
    base_report = split_audit.build_report(root)

    extracted_statuses: list[ExtractedLaneStatusV153] = []
    remaining_candidates: list[NextSplitLaneCandidateV153] = []

    extracted_lane_names = set(EXTRACTED_LANES_V153)

    for lane in base_report.lane_reports:
        lane_name = _lane_value(lane, "name")
        definition_count = _lane_value(lane, "definition_count", 0)
        total_lines = _lane_value(lane, "total_lines", 0)
        readiness = _lane_value(lane, "split_readiness", "")

        if lane_name in extracted_lane_names:
            metadata = EXTRACTED_LANES_V153[lane_name]
            extracted_statuses.append(
                ExtractedLaneStatusV153(
                    name=lane_name,
                    extracted=definition_count == 0 and total_lines == 0,
                    definition_count=definition_count,
                    total_lines=total_lines,
                    view=metadata["view"],
                    module=metadata["module"],
                    checkpoint=metadata["checkpoint"],
                )
            )
            continue

        if readiness == "candidate_for_first_split" and definition_count > 0:
            remaining_candidates.append(
                NextSplitLaneCandidateV153(
                    name=lane_name,
                    definition_count=definition_count,
                    total_lines=total_lines,
                    readiness=readiness,
                    reason=_candidate_reason(lane),
                )
            )

    remaining_candidates.sort(
        key=lambda candidate: (
            candidate.definition_count,
            candidate.total_lines,
            candidate.name,
        )
    )

    if not extracted_statuses:
        raise ValueError("No extracted lane status was recorded for v153.")

    if not all(status.extracted for status in extracted_statuses):
        not_extracted = [
            f"{status.name} definitions={status.definition_count} lines={status.total_lines}"
            for status in extracted_statuses
            if not status.extracted
        ]
        raise ValueError(
            "Expected extracted lanes to have zero remaining definitions: "
            + ", ".join(not_extracted)
        )

    if not remaining_candidates:
        raise ValueError("No remaining candidate_for_first_split lanes found.")

    return SplitLaneFollowupReportV153(
        extracted_lanes=tuple(extracted_statuses),
        remaining_candidates=tuple(remaining_candidates),
        recommended_next_lane=remaining_candidates[0],
    )


def write_markdown_report(path: Path | str, report: SplitLaneFollowupReportV153) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# v153 Split-Lane Follow-Up Audit",
        "",
        "LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153",
        "",
        "## Purpose",
        "",
        "Record the current split-lane state: extracted lanes are excluded, and the next safest split lane is selected from the remaining active lanes.",
        "",
        "## Extracted lanes",
        "",
    ]

    for status in report.extracted_lanes:
        lines.extend(
            [
                f"- Lane: `{status.name}`",
                f"  - Extracted: `{status.extracted}`",
                f"  - Remaining definitions in `views.py`: `{status.definition_count}`",
                f"  - Remaining lines in `views.py`: `{status.total_lines}`",
                f"  - Extracted view: `{status.view}`",
                f"  - Extracted module: `{status.module}`",
                f"  - Checkpoint: `{status.checkpoint}`",
                "",
            ]
        )

    lines.extend(
        [
            "## Recommended next split lane",
            "",
            f"- Lane: `{report.recommended_next_lane.name}`",
            f"- Definitions: `{report.recommended_next_lane.definition_count}`",
            f"- Lines: `{report.recommended_next_lane.total_lines}`",
            f"- Readiness: `{report.recommended_next_lane.readiness}`",
            f"- Reason: {report.recommended_next_lane.reason}",
            "",
            "## Remaining candidate order",
            "",
        ]
    )

    for candidate in report.remaining_candidates:
        lines.append(
            f"- `{candidate.name}` — definitions `{candidate.definition_count}`, lines `{candidate.total_lines}`, readiness `{candidate.readiness}`"
        )

    lines.extend(
        [
            "",
            "## Non-goals",
            "",
            "- Do not move another view in this audit module.",
            "- Do not change URLs, permissions, templates, models, migrations, or runtime behavior.",
            "- Do not remove compatibility re-export paths.",
            "",
            "## Next safe step",
            "",
            f"The next extraction checkpoint should protect and move the `{report.recommended_next_lane.name}` lane.",
        ]
    )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    report = build_followup_report(Path("."))
    print("LISTING_VIEWS_SPLIT_LANE_FOLLOWUP_AUDIT_V153")
    print("Extracted lanes:", [status.name for status in report.extracted_lanes])
    print("Recommended next lane:", report.recommended_next_lane.name)
    print("Remaining candidates:", [candidate.name for candidate in report.remaining_candidates])
