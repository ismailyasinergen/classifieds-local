from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


MARKER = "REMAINING_LISTING_VIEWS_POST_V161_AUDIT"


@dataclass(frozen=True)
class RemainingViewDefinitionV162:
    name: str
    kind: str
    start_line: int
    end_line: int
    line_count: int


@dataclass(frozen=True)
class RemainingViewLaneV162:
    name: str
    definition_count: int
    total_lines: int
    duplicate_names: tuple[str, ...]
    definition_names: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class RemainingViewsAuditReportV162:
    views_path: str
    total_lines: int
    total_top_level_definitions: int
    lanes: tuple[RemainingViewLaneV162, ...]
    recommended_next_lane: RemainingViewLaneV162


def _repo_root_from(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        if (candidate / "backend" / "listings" / "views.py").exists():
            return candidate
        if (candidate / "listings" / "views.py").exists():
            return candidate

    raise FileNotFoundError("Could not resolve repository root containing listings/views.py")


def _views_path(repo_root: Path) -> Path:
    backend_path = repo_root / "backend" / "listings" / "views.py"
    if backend_path.exists():
        return backend_path

    app_path = repo_root / "listings" / "views.py"
    if app_path.exists():
        return app_path

    raise FileNotFoundError("Could not find listings/views.py")


def _top_level_definitions(source: str) -> list[RemainingViewDefinitionV162]:
    tree = ast.parse(source)
    definitions: list[RemainingViewDefinitionV162] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            kind = "class"
        elif isinstance(node, ast.AsyncFunctionDef):
            kind = "async_function"
        elif isinstance(node, ast.FunctionDef):
            kind = "function"
        else:
            continue

        end_line = getattr(node, "end_lineno", node.lineno)
        definitions.append(
            RemainingViewDefinitionV162(
                name=node.name,
                kind=kind,
                start_line=node.lineno,
                end_line=end_line,
                line_count=end_line - node.lineno + 1,
            )
        )

    return definitions


def _lane_for(definitions: list[RemainingViewDefinitionV162], name: str) -> RemainingViewLaneV162:
    if name == "listing_reports":
        selected = [
            item
            for item in definitions
            if item.name == "moderation_queue"
            or item.name == "my_listing_reports"
            or item.name == "_safe_reporter_note"
            or item.name.startswith("listing_report_")
        ]
        reason = (
            "Largest duplicated/shadowed remaining lane; contains listing report create, queue, review, "
            "dismiss, suspend, archive, CSV export, and reporter helper definitions."
        )
    elif name == "saved_searches":
        selected = [item for item in definitions if item.name.startswith("saved_search_")]
        reason = "Large remaining saved-search management lane, including saved_search_list and owner-scoped actions."
    else:
        selected = []
        reason = "Unknown lane."

    counts: dict[str, int] = {}
    for item in selected:
        counts[item.name] = counts.get(item.name, 0) + 1

    duplicate_names = tuple(sorted(name for name, count in counts.items() if count > 1))
    definition_names = tuple(item.name for item in selected)

    return RemainingViewLaneV162(
        name=name,
        definition_count=len(selected),
        total_lines=sum(item.line_count for item in selected),
        duplicate_names=duplicate_names,
        definition_names=definition_names,
        reason=reason,
    )


def build_report(start: Path | str) -> RemainingViewsAuditReportV162:
    repo_root = _repo_root_from(Path(start))
    views_path = _views_path(repo_root)
    source = views_path.read_text(encoding="utf-8")
    definitions = _top_level_definitions(source)

    lanes = (
        _lane_for(definitions, "listing_reports"),
        _lane_for(definitions, "saved_searches"),
    )

    non_empty_lanes = tuple(lane for lane in lanes if lane.definition_count)
    if not non_empty_lanes:
        raise ValueError("No remaining listing view lanes found.")

    recommended_next_lane = sorted(
        non_empty_lanes,
        key=lambda lane: (
            lane.total_lines,
            len(lane.duplicate_names),
            lane.definition_count,
        ),
        reverse=True,
    )[0]

    return RemainingViewsAuditReportV162(
        views_path=views_path.relative_to(repo_root).as_posix(),
        total_lines=len(source.splitlines()),
        total_top_level_definitions=len(definitions),
        lanes=non_empty_lanes,
        recommended_next_lane=recommended_next_lane,
    )


def write_markdown_report(path: Path | str, report: RemainingViewsAuditReportV162) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# v162 Remaining Listing Views Post-v161 Audit",
        "",
        MARKER,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Total lines: `{report.total_lines}`",
        f"- Total top-level definitions/classes: `{report.total_top_level_definitions}`",
        f"- Recommended next lane: `{report.recommended_next_lane.name}`",
        "",
        "## Remaining lanes",
        "",
    ]

    for lane in report.lanes:
        lines.extend(
            [
                f"### `{lane.name}`",
                "",
                f"- Definitions: `{lane.definition_count}`",
                f"- Total lines: `{lane.total_lines}`",
                f"- Duplicate/shadowed names: `{', '.join(lane.duplicate_names) if lane.duplicate_names else 'none'}`",
                f"- Reason: {lane.reason}",
                "",
                "Definition names:",
                "",
            ]
        )
        for name in lane.definition_names:
            lines.append(f"- `{name}`")
        lines.append("")

    lines.extend(
        [
            "## Recommendation",
            "",
            f"Prepare a contract checkpoint for `{report.recommended_next_lane.name}` before moving runtime code.",
            "",
            "## Non-goals",
            "",
            "- Do not move runtime code in this audit checkpoint.",
            "- Do not change URLs, templates, permissions, models, migrations, or behavior.",
            "- Do not remove compatibility re-export paths.",
        ]
    )

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    report = build_report(Path("."))
    print("Views path:", report.views_path)
    print("Total lines:", report.total_lines)
    print("Total top-level definitions/classes:", report.total_top_level_definitions)
    print("Recommended next lane:", report.recommended_next_lane.name)
