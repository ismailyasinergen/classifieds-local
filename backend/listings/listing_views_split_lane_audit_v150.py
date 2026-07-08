#!/usr/bin/env python
"""
LISTING_VIEWS_SPLIT_LANE_AUDIT_V150

Granular split-lane audit for backend/listings/views.py.

This audit intentionally does not change product behavior. After v148 exhausted
low-risk helper extraction candidates and v149 identified listings/views.py as
the largest active product-code module, v150 maps the remaining top-level view
definitions into safer future split lanes.

Non-goals:
- Do not move view functions or classes.
- Do not change URL routing.
- Do not change imports.
- Do not change templates, models, migrations, permissions, forms, or behavior.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


LANE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "saved_search",
        (
            "saved_search",
            "savedsearch",
            "notification",
            "alert",
        ),
    ),
    (
        "listing_reports_moderation",
        (
            "report",
            "moderation",
            "suspend",
            "review",
            "trust",
            "safety",
        ),
    ),
    (
        "listing_promotions",
        (
            "promotion",
            "promote",
            "featured",
            "top_listing",
            "priority",
            "payment",
        ),
    ),
    (
        "favorites",
        (
            "favorite",
            "favourite",
            "watch",
        ),
    ),
    (
        "listing_crud_uploads",
        (
            "create",
            "edit",
            "update",
            "delete",
            "renew",
            "expire",
            "image",
            "upload",
            "photo",
            "draft",
        ),
    ),
    (
        "browse_search_detail",
        (
            "browse",
            "category",
            "detail",
            "search",
            "filter",
            "attribute",
            "card",
            "public",
        ),
    ),
    (
        "seller_listing_management",
        (
            "seller",
            "my_listing",
            "dashboard",
            "manage",
            "account",
        ),
    ),
)

LANE_ORDER = (
    "saved_search",
    "favorites",
    "listing_promotions",
    "listing_reports_moderation",
    "listing_crud_uploads",
    "seller_listing_management",
    "browse_search_detail",
    "uncategorized",
)


@dataclass(frozen=True)
class ViewDefinitionReport:
    name: str
    kind: str
    start_line: int
    end_line: int
    line_count: int
    lane: str
    decorators: tuple[str, ...]
    request_first: bool

    @property
    def risk_label(self) -> str:
        if self.line_count >= 120:
            return "high"
        if self.line_count >= 50:
            return "medium"
        return "low"


@dataclass(frozen=True)
class LaneReport:
    name: str
    definitions: tuple[ViewDefinitionReport, ...]

    @property
    def definition_count(self) -> int:
        return len(self.definitions)

    @property
    def total_lines(self) -> int:
        return sum(item.line_count for item in self.definitions)

    @property
    def high_risk_count(self) -> int:
        return sum(1 for item in self.definitions if item.risk_label == "high")

    @property
    def medium_risk_count(self) -> int:
        return sum(1 for item in self.definitions if item.risk_label == "medium")

    @property
    def low_risk_count(self) -> int:
        return sum(1 for item in self.definitions if item.risk_label == "low")

    @property
    def request_first_count(self) -> int:
        return sum(1 for item in self.definitions if item.request_first)

    @property
    def split_readiness(self) -> str:
        if self.definition_count == 0:
            return "empty"
        if self.high_risk_count:
            return "needs_contract_tests_first"
        if self.definition_count <= 8 and self.total_lines <= 350:
            return "candidate_for_first_split"
        if self.definition_count <= 15:
            return "candidate_after_lane_tests"
        return "too_large_split_in_sub_lanes"


@dataclass(frozen=True)
class ListingViewsSplitAuditReport:
    root: Path
    target_path: Path
    exists: bool
    total_lines: int
    top_level_function_count: int
    top_level_class_count: int
    lane_reports: tuple[LaneReport, ...]

    @property
    def total_definition_count(self) -> int:
        return self.top_level_function_count + self.top_level_class_count

    @property
    def recommended_next_lane(self) -> LaneReport | None:
        candidates = [
            lane
            for lane in self.lane_reports
            if lane.definition_count
            and lane.name != "uncategorized"
            and lane.split_readiness in {
                "candidate_for_first_split",
                "candidate_after_lane_tests",
            }
        ]
        if not candidates:
            return None

        def sort_key(lane: LaneReport) -> tuple[int, int, int]:
            readiness_rank = 0 if lane.split_readiness == "candidate_for_first_split" else 1
            return (readiness_rank, lane.high_risk_count, lane.total_lines)

        return sorted(candidates, key=sort_key)[0]


def resolve_views_path(root: Path) -> Path:
    backend_path = root / "backend" / "listings" / "views.py"
    if backend_path.exists():
        return backend_path

    app_path = root / "listings" / "views.py"
    if app_path.exists():
        return app_path

    return backend_path


def decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = decorator_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return decorator_name(node.func)
    return ""


def classify_lane(name: str) -> str:
    lowered = name.lower()
    for lane, hints in LANE_RULES:
        if any(hint in lowered for hint in hints):
            return lane
    return "uncategorized"


def first_argument_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    if not node.args.args:
        return None
    return node.args.args[0].arg


def is_request_first(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return first_argument_name(node) == "request"


def build_definition_report(node: ast.AST) -> ViewDefinitionReport | None:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        start_line = node.lineno
        end_line = node.end_lineno or node.lineno
        return ViewDefinitionReport(
            name=node.name,
            kind="function",
            start_line=start_line,
            end_line=end_line,
            line_count=end_line - start_line + 1,
            lane=classify_lane(node.name),
            decorators=tuple(decorator_name(item) for item in node.decorator_list),
            request_first=is_request_first(node),
        )

    if isinstance(node, ast.ClassDef):
        start_line = node.lineno
        end_line = node.end_lineno or node.lineno
        return ViewDefinitionReport(
            name=node.name,
            kind="class",
            start_line=start_line,
            end_line=end_line,
            line_count=end_line - start_line + 1,
            lane=classify_lane(node.name),
            decorators=tuple(decorator_name(item) for item in node.decorator_list),
            request_first=False,
        )

    return None


def build_report(root: Path) -> ListingViewsSplitAuditReport:
    root = root.resolve()
    target_path = resolve_views_path(root)

    if not target_path.exists():
        return ListingViewsSplitAuditReport(
            root=root,
            target_path=target_path,
            exists=False,
            total_lines=0,
            top_level_function_count=0,
            top_level_class_count=0,
            lane_reports=tuple(LaneReport(name=name, definitions=tuple()) for name in LANE_ORDER),
        )

    text = target_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(target_path))

    definitions = tuple(
        item
        for item in (build_definition_report(node) for node in tree.body)
        if item is not None
    )

    lane_reports = []
    for lane_name in LANE_ORDER:
        lane_definitions = tuple(
            item
            for item in definitions
            if item.lane == lane_name
        )
        lane_reports.append(LaneReport(name=lane_name, definitions=lane_definitions))

    return ListingViewsSplitAuditReport(
        root=root,
        target_path=target_path,
        exists=True,
        total_lines=len(text.splitlines()),
        top_level_function_count=sum(1 for item in definitions if item.kind == "function"),
        top_level_class_count=sum(1 for item in definitions if item.kind == "class"),
        lane_reports=tuple(lane_reports),
    )


def iter_lane_detail_rows(report: ListingViewsSplitAuditReport) -> Iterable[str]:
    for lane in report.lane_reports:
        for item in sorted(lane.definitions, key=lambda definition: definition.start_line):
            yield (
                "| "
                f"{lane.name} | `{item.name}` | {item.kind} | "
                f"{item.start_line}-{item.end_line} | {item.line_count} | "
                f"{item.risk_label} | {item.request_first} |"
            )


def render_markdown(report: ListingViewsSplitAuditReport) -> str:
    recommended = report.recommended_next_lane

    lines = [
        "# v150 Listing Views Split-Lane Audit",
        "",
        "LISTING_VIEWS_SPLIT_LANE_AUDIT_V150",
        "",
        "## Purpose",
        "",
        "After v148, low-risk helper extraction candidates in `backend/listings/views.py` are exhausted.",
        "After v149, the project-wide audit still identifies `backend/listings/views.py` as the largest active product-code refactor target.",
        "v150 maps the remaining top-level definitions into split lanes before any behavior-bearing code is moved.",
        "",
        "## Non-goals",
        "",
        "- Do not move view functions or classes.",
        "- Do not change URL routing.",
        "- Do not change imports.",
        "- Do not change templates, models, migrations, permissions, forms, or behavior.",
        "",
        "## Summary",
        "",
        f"- Root: `{report.root}`",
        f"- Target: `{report.target_path}`",
        f"- Exists: {report.exists}",
        f"- Total lines: {report.total_lines}",
        f"- Top-level functions: {report.top_level_function_count}",
        f"- Top-level classes: {report.top_level_class_count}",
        f"- Total top-level definitions: {report.total_definition_count}",
        "",
        "## Recommended next lane",
        "",
    ]

    if recommended is None:
        lines.append("No split lane is recommended yet. Add more lane-specific tests first.")
    else:
        lines.extend(
            [
                f"- Lane: `{recommended.name}`",
                f"- Definitions: {recommended.definition_count}",
                f"- Total lines: {recommended.total_lines}",
                f"- High-risk definitions: {recommended.high_risk_count}",
                f"- Medium-risk definitions: {recommended.medium_risk_count}",
                f"- Low-risk definitions: {recommended.low_risk_count}",
                f"- Request-first functions: {recommended.request_first_count}",
                f"- Split readiness: `{recommended.split_readiness}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Lane summary",
            "",
            "| Lane | Definitions | Lines | High | Medium | Low | Request-first | Split readiness |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )

    for lane in report.lane_reports:
        lines.append(
            "| "
            f"{lane.name} | {lane.definition_count} | {lane.total_lines} | "
            f"{lane.high_risk_count} | {lane.medium_risk_count} | {lane.low_risk_count} | "
            f"{lane.request_first_count} | {lane.split_readiness} |"
        )

    lines.extend(
        [
            "",
            "## Definition details",
            "",
            "| Lane | Name | Kind | Lines | Line count | Risk | Request first |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )

    detail_rows = list(iter_lane_detail_rows(report))
    lines.extend(detail_rows if detail_rows else ["| none | none | none | none | 0 | none | False |"])

    lines.extend(
        [
            "",
            "## Safe sequencing rule",
            "",
            "Before moving a lane into a new module, create or confirm focused tests for that lane and keep URL names, permission behavior, templates, redirects, querystrings, messages, and pagination unchanged.",
            "",
        ]
    )

    return "\n".join(lines)


def write_markdown_report(report: ListingViewsSplitAuditReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(report), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Listing views split-lane audit v150")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument(
        "--output",
        default="docs/listing_views_split_lane_audit_v150.md",
        help="Markdown output path",
    )
    args = parser.parse_args()

    report = build_report(Path(args.root))
    write_markdown_report(report, Path(args.output))

    print("===== LISTING_VIEWS_SPLIT_LANE_AUDIT_V150 SUMMARY =====")
    print(f"Root: {report.root}")
    print(f"Target: {report.target_path}")
    print(f"Exists: {report.exists}")
    print(f"Total lines: {report.total_lines}")
    print(f"Top-level functions: {report.top_level_function_count}")
    print(f"Top-level classes: {report.top_level_class_count}")
    print(f"Total definitions: {report.total_definition_count}")

    recommended = report.recommended_next_lane
    if recommended is None:
        print("Recommended next lane: none")
    else:
        print(
            "Recommended next lane: "
            f"{recommended.name} "
            f"({recommended.definition_count} definitions, "
            f"{recommended.total_lines} lines, "
            f"{recommended.split_readiness})"
        )

    print()
    print("Lane summary:")
    for lane in report.lane_reports:
        print(
            f"  - {lane.name}: "
            f"{lane.definition_count} definitions, "
            f"{lane.total_lines} lines, "
            f"{lane.split_readiness}"
        )

    print(f"\nMarkdown report written to: {args.output}")
    return 0 if report.exists else 1


if __name__ == "__main__":
    raise SystemExit(main())
