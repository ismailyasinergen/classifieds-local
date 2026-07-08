"""
LARGE_ACTIVE_VIEW_REFACTOR_PLANNING_V140

Static planning helper for large active Django view files.

This module does not change runtime behavior. It maps large active view files,
summarizes top-level definitions, and produces a conservative extraction plan
so future checkpoints can refactor in small, testable steps.
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


TARGET_ACTIVE_VIEW_FILES = (
    Path("backend/accounts/appeal_views.py"),
    Path("backend/listings/views.py"),
)

REFERENCE_ONLY_FILES = (
    Path("backend/_dev_backups/appeal_views_before_override_cleanup.py"),
)

LARGE_FILE_LINE_THRESHOLD = 1200
LARGE_DEFINITION_LINE_THRESHOLD = 120
VIEW_DECORATOR_NAMES = {
    "login_required",
    "staff_member_required",
    "user_passes_test",
    "permission_required",
    "require_GET",
    "require_POST",
    "require_http_methods",
}


@dataclass(frozen=True)
class DefinitionInfo:
    name: str
    kind: str
    start_line: int
    end_line: int
    line_count: int
    decorators: tuple[str, ...] = ()
    first_arg: str = ""
    category: str = ""
    suggested_stage: str = ""
    risk: str = ""


@dataclass
class ViewFileReport:
    path: Path
    exists: bool
    total_lines: int = 0
    definitions: list[DefinitionInfo] = field(default_factory=list)
    large_definitions: list[DefinitionInfo] = field(default_factory=list)
    function_view_count: int = 0
    class_based_view_count: int = 0
    helper_count: int = 0


@dataclass
class LargeViewAuditReport:
    active_files: list[ViewFileReport] = field(default_factory=list)
    reference_files: list[ViewFileReport] = field(default_factory=list)


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


def decorator_names(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> tuple[str, ...]:
    names: list[str] = []
    for decorator in getattr(node, "decorator_list", []):
        name = dotted_name(decorator)
        if name:
            names.append(name)
    return tuple(names)


def node_line_count(node: ast.AST) -> int:
    start = getattr(node, "lineno", 0)
    end = getattr(node, "end_lineno", start)
    return max(0, end - start + 1)


def first_arg_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    if not node.args.args:
        return ""
    return node.args.args[0].arg


def has_view_decorator(decorators: Iterable[str]) -> bool:
    normalized = {item.split(".")[-1] for item in decorators}
    return bool(normalized & VIEW_DECORATOR_NAMES)


def classify_definition(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    decorators: tuple[str, ...],
    first_arg: str,
) -> str:
    if isinstance(node, ast.ClassDef):
        return "class_based_view_or_mixin"

    if first_arg == "request":
        return "function_view"

    if has_view_decorator(decorators):
        return "function_view"

    if node.name.startswith("_"):
        return "private_helper"

    if any(token in node.name for token in ("filter", "query", "paginate", "export", "format", "build", "get_")):
        return "helper_or_query_builder"

    return "helper_or_service_candidate"


def suggested_stage(category: str, line_count: int) -> str:
    if category in {"private_helper", "helper_or_query_builder", "helper_or_service_candidate"}:
        return "Stage 1: extract low-risk helpers/query builders with identical tests"

    if category == "function_view" and line_count <= LARGE_DEFINITION_LINE_THRESHOLD:
        return "Stage 2: group small function views by feature module after helper extraction"

    if category == "function_view":
        return "Stage 3: split larger function views only after request/response tests are locked"

    if category == "class_based_view_or_mixin":
        return "Stage 4: move class-based views/mixins after URL/template contracts are covered"

    return "Stage 5: manual review"


def risk_level(category: str, line_count: int, decorators: tuple[str, ...]) -> str:
    if category in {"private_helper", "helper_or_query_builder", "helper_or_service_candidate"} and line_count <= LARGE_DEFINITION_LINE_THRESHOLD:
        return "low"

    if category == "function_view" and decorators:
        return "medium"

    if line_count > LARGE_DEFINITION_LINE_THRESHOLD:
        return "medium"

    if category == "class_based_view_or_mixin":
        return "medium"

    return "low"


def parse_definitions(path: Path) -> list[DefinitionInfo]:
    source = read_text(path)
    tree = ast.parse(source, filename=str(path))
    definitions: list[DefinitionInfo] = []

    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        decorators = decorator_names(node)
        first_arg = first_arg_name(node) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else ""
        lines = node_line_count(node)
        category = classify_definition(node, decorators, first_arg)

        definitions.append(
            DefinitionInfo(
                name=node.name,
                kind=type(node).__name__,
                start_line=getattr(node, "lineno", 0),
                end_line=getattr(node, "end_lineno", getattr(node, "lineno", 0)),
                line_count=lines,
                decorators=decorators,
                first_arg=first_arg,
                category=category,
                suggested_stage=suggested_stage(category, lines),
                risk=risk_level(category, lines, decorators),
            )
        )

    return definitions


def resolve_project_file_path(root: Path, relative_path: Path) -> Path:
    """
    Resolve a repo-root style path in both host and Docker layouts.

    Host layout keeps Django code under:
      backend/accounts/...
      backend/listings/...

    Docker layout mounts the backend directory as /app, so the same files live under:
      accounts/...
      listings/...

    The report keeps the canonical repo-root path, but file reads use this resolver.
    """
    direct = root / relative_path
    if direct.exists():
        return direct

    parts = relative_path.parts
    if parts and parts[0] == "backend":
        without_backend = root / Path(*parts[1:])
        if without_backend.exists():
            return without_backend

    return direct


def build_file_report(root: Path, relative_path: Path) -> ViewFileReport:
    path = resolve_project_file_path(root, relative_path)
    if not path.exists():
        return ViewFileReport(path=relative_path, exists=False)

    text = read_text(path)
    definitions = parse_definitions(path)
    large_definitions = [
        definition for definition in definitions if definition.line_count > LARGE_DEFINITION_LINE_THRESHOLD
    ]

    return ViewFileReport(
        path=relative_path,
        exists=True,
        total_lines=count_lines(text),
        definitions=definitions,
        large_definitions=large_definitions,
        function_view_count=sum(1 for item in definitions if item.category == "function_view"),
        class_based_view_count=sum(1 for item in definitions if item.category == "class_based_view_or_mixin"),
        helper_count=sum(1 for item in definitions if item.category in {"private_helper", "helper_or_query_builder", "helper_or_service_candidate"}),
    )


def build_audit(root: Path) -> LargeViewAuditReport:
    return LargeViewAuditReport(
        active_files=[build_file_report(root, path) for path in TARGET_ACTIVE_VIEW_FILES],
        reference_files=[build_file_report(root, path) for path in REFERENCE_ONLY_FILES],
    )


def format_definition_table(definitions: list[DefinitionInfo], limit: int = 30) -> str:
    if not definitions:
        return "_No top-level definitions found._\n"

    rows = [
        "| Name | Lines | Category | Risk | Suggested stage |",
        "| --- | ---: | --- | --- | --- |",
    ]

    for item in sorted(definitions, key=lambda value: (-value.line_count, value.start_line))[:limit]:
        rows.append(
            f"| `{item.name}` | {item.line_count} | {item.category} | {item.risk} | {item.suggested_stage} |"
        )

    if len(definitions) > limit:
        rows.append(f"| … | … | … | … | {len(definitions) - limit} more definitions not shown |")

    return "\n".join(rows) + "\n"


def format_markdown_report(report: LargeViewAuditReport) -> str:
    lines: list[str] = [
        "# v140 Large Active View File Refactor Planning",
        "",
        "This report is generated by `scripts/large_view_refactor_audit_v140.py`.",
        "",
        "## Purpose",
        "",
        "v140 is a planning checkpoint only. It does not move runtime code.",
        "It maps the large active Django view files so future checkpoints can refactor them safely.",
        "",
        "## Active large files",
        "",
    ]

    for file_report in report.active_files:
        lines.append(f"### `{file_report.path}`")
        lines.append("")
        if not file_report.exists:
            lines.append("File missing.")
            lines.append("")
            continue

        lines.append(f"- Total lines: **{file_report.total_lines}**")
        lines.append(f"- Top-level definitions: **{len(file_report.definitions)}**")
        lines.append(f"- Function views detected: **{file_report.function_view_count}**")
        lines.append(f"- Class-based views/mixins detected: **{file_report.class_based_view_count}**")
        lines.append(f"- Helper/service candidates detected: **{file_report.helper_count}**")
        lines.append(f"- Large definitions over {LARGE_DEFINITION_LINE_THRESHOLD} lines: **{len(file_report.large_definitions)}**")
        lines.append("")
        lines.append("Largest definitions:")
        lines.append("")
        lines.append(format_definition_table(file_report.definitions))
        lines.append("")

    lines.extend(
        [
            "## Reference-only files",
            "",
            "These are not active app-code refactor targets. They should stay separated from blocker scans.",
            "",
        ]
    )

    for file_report in report.reference_files:
        status = "exists" if file_report.exists else "missing"
        lines.append(f"- `{file_report.path}` — {status}, {file_report.total_lines} lines")
    lines.append("")

    lines.extend(
        [
            "## Recommended safe refactor order",
            "",
            "1. Add or confirm focused tests around the target feature before moving code.",
            "2. Extract low-risk private helpers and query-builder helpers first.",
            "3. Move small function views into feature modules only after helpers are stable.",
            "4. Split large request/response views last, one feature at a time.",
            "5. Keep URLs, template names, redirects, permissions, messages, and pagination behavior unchanged.",
            "",
            "## v140 non-goals",
            "",
            "- Do not change views, URLs, templates, models, migrations, or user behavior.",
            "- Do not remove `_dev_backups` yet.",
            "- Do not refactor `appeal_views.py` or `listings/views.py` in this checkpoint.",
            "",
        ]
    )

    return "\n".join(lines)


def write_markdown_report(root: Path, output_path: Path) -> Path:
    report = build_audit(root)
    target = root / output_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(format_markdown_report(report), encoding="utf-8")
    return target


def print_summary(report: LargeViewAuditReport) -> None:
    safe_print("===== LARGE_ACTIVE_VIEW_REFACTOR_PLANNING_V140 SUMMARY =====")
    safe_print()

    for file_report in report.active_files:
        safe_print(f"Active target: {file_report.path}")
        safe_print(f"  exists: {file_report.exists}")
        safe_print(f"  total lines: {file_report.total_lines}")
        safe_print(f"  definitions: {len(file_report.definitions)}")
        safe_print(f"  function views: {file_report.function_view_count}")
        safe_print(f"  class-based/mixins: {file_report.class_based_view_count}")
        safe_print(f"  helpers/service candidates: {file_report.helper_count}")
        safe_print(f"  large definitions: {len(file_report.large_definitions)}")
        safe_print()

    safe_print("Reference-only files:")
    for file_report in report.reference_files:
        safe_print(f"  - {file_report.path}: {'exists' if file_report.exists else 'missing'}")
    safe_print()


def main() -> int:
    configure_unicode_safe_output()

    parser = argparse.ArgumentParser(description="Large active view refactor planning v140.")
    parser.add_argument("--root", default=".", help="Project root.")
    parser.add_argument(
        "--write-report",
        default="docs/large_active_view_refactor_plan_v140.md",
        help="Markdown report path relative to root.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_audit(root)
    print_summary(report)
    written = write_markdown_report(root, Path(args.write_report))
    safe_print(f"Wrote report: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
