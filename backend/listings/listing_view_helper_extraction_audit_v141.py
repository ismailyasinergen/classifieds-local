"""
LISTING_VIEW_HELPER_EXTRACTION_CANDIDATE_LOCK_V141

Static extraction-candidate helper for backend/listings/views.py.

This module does not move runtime code. It identifies low-risk helper and
query-builder candidates so the first real extraction can be done in a later
checkpoint with a small, explicit target list.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


LISTING_VIEW_TARGET = Path("backend/listings/views.py")
REPORT_PATH = Path("docs/listing_view_helper_extraction_candidates_v141.md")

LOW_RISK_MAX_LINES = 120
VIEW_DECORATOR_NAMES = {
    "login_required",
    "staff_member_required",
    "user_passes_test",
    "permission_required",
    "require_GET",
    "require_POST",
    "require_http_methods",
}
HELPER_NAME_TOKENS = (
    "filter",
    "query",
    "paginate",
    "page",
    "sort",
    "order",
    "export",
    "format",
    "build",
    "get_",
    "parse",
    "normalize",
    "serialize",
    "schema",
    "attribute",
    "highlight",
    "category",
)


@dataclass(frozen=True)
class FunctionCandidate:
    name: str
    start_line: int
    end_line: int
    line_count: int
    first_arg: str
    decorators: tuple[str, ...] = ()
    category: str = ""
    risk: str = ""
    extraction_stage: str = ""
    reason: str = ""


@dataclass
class ListingHelperExtractionReport:
    target: Path
    exists: bool
    total_lines: int = 0
    top_level_function_count: int = 0
    view_like_function_count: int = 0
    helper_candidate_count: int = 0
    low_risk_candidate_count: int = 0
    candidates: list[FunctionCandidate] = field(default_factory=list)
    low_risk_candidates: list[FunctionCandidate] = field(default_factory=list)


def configure_unicode_safe_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="backslashreplace")
            except Exception:
                pass


def safe_output_text(value: object, encoding: str | None = None) -> str:
    text = str(value)
    output_encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(output_encoding, errors="backslashreplace").decode(
        output_encoding,
        errors="replace",
    )


def safe_print(value: object = "") -> None:
    print(safe_output_text(value))


def resolve_project_file_path(root: Path, relative_path: Path) -> Path:
    direct = root / relative_path
    if direct.exists():
        return direct

    parts = relative_path.parts
    if parts and parts[0] == "backend":
        without_backend = root / Path(*parts[1:])
        if without_backend.exists():
            return without_backend

    return direct


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def count_lines(text: str) -> int:
    return len(text.splitlines())


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return dotted_name(node.func)
    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)
    return ""


def decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, ...]:
    names: list[str] = []
    for decorator in getattr(node, "decorator_list", []):
        name = dotted_name(decorator)
        if name:
            names.append(name)
    return tuple(names)


def first_arg_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if not node.args.args:
        return ""
    return node.args.args[0].arg


def node_line_count(node: ast.AST) -> int:
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start)
    return max(0, end - start + 1)


def has_view_decorator(decorators: Iterable[str]) -> bool:
    normalized = {item.split(".")[-1] for item in decorators}
    return bool(normalized & VIEW_DECORATOR_NAMES)


def is_view_like_function(node: ast.FunctionDef | ast.AsyncFunctionDef, first_arg: str, decorators: tuple[str, ...]) -> bool:
    return first_arg == "request" or has_view_decorator(decorators)


def has_helper_name(name: str) -> bool:
    return name.startswith("_") or any(token in name for token in HELPER_NAME_TOKENS)


def categorize_function(node: ast.FunctionDef | ast.AsyncFunctionDef, first_arg: str, decorators: tuple[str, ...]) -> str:
    if is_view_like_function(node, first_arg, decorators):
        return "view_like_function"

    if node.name.startswith("_"):
        return "private_helper"

    if has_helper_name(node.name):
        return "query_or_format_helper"

    return "service_candidate"


def candidate_risk(category: str, line_count: int, decorators: tuple[str, ...]) -> str:
    if decorators:
        return "medium"

    if category in {"private_helper", "query_or_format_helper"} and line_count <= LOW_RISK_MAX_LINES:
        return "low"

    if category == "service_candidate" and line_count <= LOW_RISK_MAX_LINES:
        return "medium"

    return "medium"


def extraction_stage(category: str, risk: str) -> str:
    if risk == "low" and category in {"private_helper", "query_or_format_helper"}:
        return "Stage 1: first extraction candidate"

    if category == "service_candidate":
        return "Stage 2: review after Stage 1 helpers are moved"

    return "Stage 3: leave in view module until behavior tests are stronger"


def candidate_reason(category: str, risk: str, line_count: int, decorators: tuple[str, ...]) -> str:
    if decorators:
        return "decorated function; do not move in first extraction"

    if risk == "low":
        return f"non-view helper under {LOW_RISK_MAX_LINES} lines"

    if line_count > LOW_RISK_MAX_LINES:
        return f"large helper over {LOW_RISK_MAX_LINES} lines"

    if category == "service_candidate":
        return "non-view function but name is not clearly query/format/helper oriented"

    return "manual review needed"


def parse_top_level_functions(path: Path) -> list[FunctionCandidate]:
    source = read_text(path)
    tree = ast.parse(source, filename=str(path))
    functions: list[FunctionCandidate] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        decorators = decorator_names(node)
        first_arg = first_arg_name(node)
        lines = node_line_count(node)
        category = categorize_function(node, first_arg, decorators)
        risk = candidate_risk(category, lines, decorators)

        functions.append(
            FunctionCandidate(
                name=node.name,
                start_line=getattr(node, "lineno", 0),
                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                line_count=lines,
                first_arg=first_arg,
                decorators=decorators,
                category=category,
                risk=risk,
                extraction_stage=extraction_stage(category, risk),
                reason=candidate_reason(category, risk, lines, decorators),
            )
        )

    return functions


def build_report(root: Path, target: Path = LISTING_VIEW_TARGET) -> ListingHelperExtractionReport:
    path = resolve_project_file_path(root, target)
    if not path.exists():
        return ListingHelperExtractionReport(target=target, exists=False)

    text = read_text(path)
    functions = parse_top_level_functions(path)
    candidates = [
        item for item in functions if item.category in {"private_helper", "query_or_format_helper", "service_candidate"}
    ]
    low_risk_candidates = [item for item in candidates if item.risk == "low"]

    return ListingHelperExtractionReport(
        target=target,
        exists=True,
        total_lines=count_lines(text),
        top_level_function_count=len(functions),
        view_like_function_count=sum(1 for item in functions if item.category == "view_like_function"),
        helper_candidate_count=len(candidates),
        low_risk_candidate_count=len(low_risk_candidates),
        candidates=candidates,
        low_risk_candidates=low_risk_candidates,
    )


def format_candidate_table(candidates: list[FunctionCandidate], limit: int = 40) -> str:
    if not candidates:
        return "_No candidates found._\n"

    rows = [
        "| Candidate | Lines | Category | Risk | Stage | Reason |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]

    ordered = sorted(candidates, key=lambda item: (item.risk != "low", item.line_count, item.start_line))
    for item in ordered[:limit]:
        rows.append(
            f"| `{item.name}` | {item.line_count} | {item.category} | {item.risk} | {item.extraction_stage} | {item.reason} |"
        )

    if len(candidates) > limit:
        rows.append(f"| … | … | … | … | … | {len(candidates) - limit} more candidates not shown |")

    return "\n".join(rows) + "\n"


def format_markdown_report(report: ListingHelperExtractionReport) -> str:
    lines: list[str] = [
        "# v141 Listing View Helper Extraction Candidates",
        "",
        "This report is generated by `scripts/listing_view_helper_extraction_audit_v141.py`.",
        "",
        "## Purpose",
        "",
        "v141 locks the first candidate list for extracting low-risk helper/query-builder logic from `backend/listings/views.py`.",
        "This checkpoint does not move runtime code.",
        "",
        "## Target",
        "",
        f"- File: `{report.target}`",
        f"- Exists: **{report.exists}**",
        f"- Total lines: **{report.total_lines}**",
        f"- Top-level functions: **{report.top_level_function_count}**",
        f"- View-like functions: **{report.view_like_function_count}**",
        f"- Helper/service candidates: **{report.helper_candidate_count}**",
        f"- Low-risk first-extraction candidates: **{report.low_risk_candidate_count}**",
        "",
        "## Low-risk candidates",
        "",
        format_candidate_table(report.low_risk_candidates),
        "",
        "## All non-view candidates",
        "",
        format_candidate_table(report.candidates),
        "",
        "## Recommended v142 extraction rule",
        "",
        "Move only one low-risk candidate or one small group of tightly related low-risk helpers.",
        "The extraction must keep imports, return values, redirects, messages, pagination, query strings, and template context unchanged.",
        "",
        "## v141 non-goals",
        "",
        "- Do not move code out of `backend/listings/views.py` in this checkpoint.",
        "- Do not change URLs, templates, models, migrations, or user-visible behavior.",
        "- Do not rename active views.",
        "- Do not remove the large view file yet.",
        "",
    ]
    return "\n".join(lines)


def write_markdown_report(root: Path, output_path: Path = REPORT_PATH) -> Path:
    report = build_report(root)
    target = root / output_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_markdown_report(report), encoding="utf-8")
    return target


def print_summary(report: ListingHelperExtractionReport) -> None:
    safe_print("===== LISTING_VIEW_HELPER_EXTRACTION_CANDIDATE_LOCK_V141 SUMMARY =====")
    safe_print(f"Target: {report.target}")
    safe_print(f"Exists: {report.exists}")
    safe_print(f"Total lines: {report.total_lines}")
    safe_print(f"Top-level functions: {report.top_level_function_count}")
    safe_print(f"View-like functions: {report.view_like_function_count}")
    safe_print(f"Helper/service candidates: {report.helper_candidate_count}")
    safe_print(f"Low-risk candidates: {report.low_risk_candidate_count}")
    safe_print()

    if report.low_risk_candidates:
        safe_print("Low-risk first candidates:")
        for item in report.low_risk_candidates[:20]:
            safe_print(f"  - {item.name}: {item.line_count} lines, {item.category}, {item.reason}")
    else:
        safe_print("Low-risk first candidates: none")
    safe_print()


def main() -> int:
    configure_unicode_safe_output()

    parser = argparse.ArgumentParser(description="Listing view helper extraction candidate audit v141.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument(
        "--write-report",
        default=str(REPORT_PATH),
        help="Markdown report path relative to root.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root)
    print_summary(report)
    written = write_markdown_report(root, Path(args.write_report))
    safe_print(f"Wrote report: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
