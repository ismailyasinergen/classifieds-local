#!/usr/bin/env python
"""
PROJECT_REFACTOR_CANDIDATE_AUDIT_V149

Project-wide refactor candidate audit.

This audit intentionally does not modify application behavior. It scans active
Python source files and highlights likely next refactor lanes by size and
structure.

Non-goals:
- Do not move code.
- Do not rename modules.
- Do not change imports.
- Do not change URLs, templates, models, migrations, or behavior.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXCLUDED_DIR_PARTS = {
    ".git",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "htmlcov",
    "media",
    "staticfiles",
    "venv",
    ".venv",
    "_dev_backups",
    "migrations",
}

EXCLUDED_FILE_PREFIXES = (
    "test_",
)

EXCLUDED_FILE_SUFFIXES = (
    "_test.py",
)

VIEW_LIKE_NAME_HINTS = (
    "view",
    "list",
    "detail",
    "create",
    "update",
    "delete",
    "dashboard",
    "admin",
    "seller",
    "buyer",
    "login",
    "logout",
    "signup",
    "report",
    "appeal",
    "moderation",
)


@dataclass(frozen=True)
class PythonFileReport:
    path: Path
    total_lines: int
    code_lines: int
    top_level_function_count: int
    top_level_class_count: int
    method_count: int
    import_count: int
    view_like_function_count: int
    syntax_error: str | None = None

    @property
    def score(self) -> int:
        return (
            self.total_lines
            + self.top_level_function_count * 20
            + self.top_level_class_count * 30
            + self.method_count * 5
            + self.import_count * 2
        )

    @property
    def risk_label(self) -> str:
        if self.syntax_error:
            return "needs_parse_review"
        if self.total_lines >= 1200 or self.top_level_function_count >= 35:
            return "high_complexity"
        if self.total_lines >= 600 or self.top_level_function_count >= 18:
            return "medium_complexity"
        return "low_complexity"

    @property
    def likely_lane(self) -> str:
        name = self.path.name
        if name == "views.py":
            return "view_module_split_or_helper_extraction"
        if name == "models.py":
            return "model_manager_or_domain_service_audit"
        if name == "admin.py":
            return "admin_config_split"
        if name == "forms.py":
            return "form_helper_or_fieldset_split"
        if "utils" in name or "helpers" in name:
            return "helper_module_hygiene"
        return "general_module_review"


@dataclass(frozen=True)
class ProjectRefactorAuditReport:
    root: Path
    scanned_file_count: int
    parse_error_count: int
    large_file_count: int
    high_complexity_count: int
    medium_complexity_count: int
    reports: tuple[PythonFileReport, ...]

    @property
    def top_candidates(self) -> tuple[PythonFileReport, ...]:
        return tuple(sorted(self.reports, key=lambda item: item.score, reverse=True)[:15])

    @property
    def recommended_next_candidate(self) -> PythonFileReport | None:
        candidates = [item for item in self.top_candidates if not item.syntax_error]
        return candidates[0] if candidates else None


def should_skip_path(path: Path) -> bool:
    parts = set(path.parts)

    if parts & EXCLUDED_DIR_PARTS:
        return True

    if path.name.startswith(EXCLUDED_FILE_PREFIXES):
        return True

    if path.name.endswith(EXCLUDED_FILE_SUFFIXES):
        return True

    # V149_ACTIVE_CODE_ONLY_AUDIT:
    # Audit/checkpoint tooling documents prior work, but it should not become
    # the recommended next product-code refactor lane.
    if "_audit_v" in path.name or path.name.startswith("remaining_"):
        return True

    return False


def iter_python_files(root: Path) -> Iterable[Path]:
    backend_root = root / "backend"
    search_root = backend_root if backend_root.exists() else root

    for path in sorted(search_root.rglob("*.py")):
        relative_path = path.relative_to(root)
        if should_skip_path(relative_path):
            continue
        yield path


def count_code_lines(text: str) -> int:
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        count += 1
    return count


def is_view_like_function(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in VIEW_LIKE_NAME_HINTS)


def build_file_report(root: Path, path: Path) -> PythonFileReport:
    text = path.read_text(encoding="utf-8")
    total_lines = len(text.splitlines())
    code_lines = count_code_lines(text)

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return PythonFileReport(
            path=path.relative_to(root),
            total_lines=total_lines,
            code_lines=code_lines,
            top_level_function_count=0,
            top_level_class_count=0,
            method_count=0,
            import_count=0,
            view_like_function_count=0,
            syntax_error=str(exc),
        )

    top_level_functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    top_level_classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    ]
    methods = [
        node
        for class_node in top_level_classes
        for node in class_node.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    imports = [
        node
        for node in tree.body
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    view_like_functions = [
        node
        for node in top_level_functions
        if is_view_like_function(node.name)
    ]

    return PythonFileReport(
        path=path.relative_to(root),
        total_lines=total_lines,
        code_lines=code_lines,
        top_level_function_count=len(top_level_functions),
        top_level_class_count=len(top_level_classes),
        method_count=len(methods),
        import_count=len(imports),
        view_like_function_count=len(view_like_functions),
        syntax_error=None,
    )


def build_project_report(root: Path) -> ProjectRefactorAuditReport:
    root = root.resolve()
    reports = tuple(build_file_report(root, path) for path in iter_python_files(root))

    return ProjectRefactorAuditReport(
        root=root,
        scanned_file_count=len(reports),
        parse_error_count=sum(1 for report in reports if report.syntax_error),
        large_file_count=sum(1 for report in reports if report.total_lines >= 600),
        high_complexity_count=sum(1 for report in reports if report.risk_label == "high_complexity"),
        medium_complexity_count=sum(1 for report in reports if report.risk_label == "medium_complexity"),
        reports=reports,
    )


def render_markdown(report: ProjectRefactorAuditReport) -> str:
    recommended = report.recommended_next_candidate

    lines = [
        "# v149 Project-wide Refactor Candidate Audit",
        "",
        "PROJECT_REFACTOR_CANDIDATE_AUDIT_V149",
        "",
        "## Purpose",
        "",
        "After v148, `backend/listings/views.py` has no remaining low-risk helper extraction candidates.",
        "This audit creates a project-wide map of the next safest refactor lanes without changing application behavior.",
        "",
        "## Non-goals",
        "",
        "- Do not move code.",
        "- Do not rename modules.",
        "- Do not change imports.",
        "- Do not change URLs, templates, models, migrations, or behavior.",
        "",
        "## Summary",
        "",
        f"- Root: `{report.root}`",
        f"- Scanned Python files: {report.scanned_file_count}",
        f"- Parse errors: {report.parse_error_count}",
        f"- Large files, 600+ lines: {report.large_file_count}",
        f"- High-complexity files: {report.high_complexity_count}",
        f"- Medium-complexity files: {report.medium_complexity_count}",
        "",
        "## Recommended next candidate",
        "",
    ]

    if recommended is None:
        lines.append("No parseable candidate was found.")
    else:
        lines.extend(
            [
                f"- Path: `{recommended.path}`",
                f"- Lines: {recommended.total_lines}",
                f"- Top-level functions: {recommended.top_level_function_count}",
                f"- Top-level classes: {recommended.top_level_class_count}",
                f"- Methods: {recommended.method_count}",
                f"- Imports: {recommended.import_count}",
                f"- View-like functions: {recommended.view_like_function_count}",
                f"- Risk label: {recommended.risk_label}",
                f"- Likely lane: {recommended.likely_lane}",
            ]
        )

    lines.extend(
        [
            "",
            "## Top candidates",
            "",
            "| Rank | Path | Lines | Functions | Classes | Methods | Imports | View-like funcs | Risk | Likely lane |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
        ]
    )

    for index, item in enumerate(report.top_candidates, start=1):
        lines.append(
            "| "
            f"{index} | `{item.path}` | {item.total_lines} | "
            f"{item.top_level_function_count} | {item.top_level_class_count} | "
            f"{item.method_count} | {item.import_count} | {item.view_like_function_count} | "
            f"{item.risk_label} | {item.likely_lane} |"
        )

    lines.extend(
        [
            "",
            "## Safe sequencing rule",
            "",
            "Choose only one lane for the next checkpoint. Prefer audit-only or test-only checkpoints before moving behavior-bearing code.",
            "",
        ]
    )

    return "\n".join(lines)


def write_markdown_report(report: ProjectRefactorAuditReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(report), encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Project-wide refactor candidate audit v149")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument(
        "--output",
        default="docs/project_refactor_candidate_audit_v149.md",
        help="Markdown output path",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output_path = Path(args.output)

    report = build_project_report(root)
    write_markdown_report(report, output_path)

    print("===== PROJECT_REFACTOR_CANDIDATE_AUDIT_V149 SUMMARY =====")
    print(f"Root: {report.root}")
    print(f"Scanned Python files: {report.scanned_file_count}")
    print(f"Parse errors: {report.parse_error_count}")
    print(f"Large files: {report.large_file_count}")
    print(f"High-complexity files: {report.high_complexity_count}")
    print(f"Medium-complexity files: {report.medium_complexity_count}")

    recommended = report.recommended_next_candidate
    if recommended is None:
        print("Recommended next candidate: none")
    else:
        print(
            "Recommended next candidate: "
            f"{recommended.path} "
            f"({recommended.total_lines} lines, {recommended.risk_label}, {recommended.likely_lane})"
        )

    print()
    print("Top candidates:")
    for item in report.top_candidates[:10]:
        print(
            f"  - {item.path}: "
            f"{item.total_lines} lines, "
            f"{item.top_level_function_count} functions, "
            f"{item.top_level_class_count} classes, "
            f"{item.method_count} methods, "
            f"{item.risk_label}, "
            f"{item.likely_lane}"
        )

    print(f"\nMarkdown report written to: {output_path}")
    return 0 if report.parse_error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
