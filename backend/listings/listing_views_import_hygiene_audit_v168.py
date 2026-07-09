from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_IMPORT_HYGIENE_AUDIT_MARKER_V168 = "LISTING_VIEWS_IMPORT_HYGIENE_AUDIT_V168"

EXPECTED_COMPATIBILITY_REEXPORT_MODULES_V168 = {
    "listing_crud_uploads_views",
    "listing_reports_views",
    "saved_searches_views",
}


@dataclass(frozen=True)
class ImportStatementAuditV168:
    line_number: int
    module: str
    imported_names: tuple[str, ...]
    level: int
    category: str
    has_wildcard: bool


@dataclass(frozen=True)
class ListingViewsImportHygieneReportV168:
    marker: str
    views_path: str
    views_total_lines: int
    top_level_function_names: tuple[str, ...]
    top_level_class_names: tuple[str, ...]
    import_statements: tuple[ImportStatementAuditV168, ...]
    compatibility_reexport_modules: tuple[str, ...]
    compatibility_reexport_names: tuple[str, ...]
    relative_non_view_import_modules: tuple[str, ...]
    absolute_import_modules: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]
    duplicate_imported_names: tuple[str, ...]
    recommendation: str

    @property
    def total_top_level_definitions(self) -> int:
        return len(self.top_level_function_names) + len(self.top_level_class_names)

    @property
    def is_facade_only(self) -> bool:
        return self.total_top_level_definitions == 0

    @property
    def has_no_wildcard_imports(self) -> bool:
        return not self.wildcard_import_modules

    @property
    def missing_expected_reexport_modules(self) -> tuple[str, ...]:
        present = set(self.compatibility_reexport_modules)
        return tuple(sorted(EXPECTED_COMPATIBILITY_REEXPORT_MODULES_V168 - present))


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    candidates = (repo_root / "backend", repo_root)

    for candidate in candidates:
        if (candidate / "listings" / "views.py").exists():
            return candidate

    raise FileNotFoundError(
        f"Could not resolve app root containing listings/views.py from {repo_root}"
    )


def _top_level_definitions(source: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    tree = ast.parse(source)

    function_names = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    class_names = tuple(
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    )

    return function_names, class_names


def _classify_import(module: str, level: int) -> str:
    if level == 1 and module.endswith("_views"):
        return "compatibility_view_reexport"
    if level > 0:
        return "relative_non_view_import"
    return "absolute_import"


def _import_statements(source: str) -> tuple[ImportStatementAuditV168, ...]:
    tree = ast.parse(source)
    statements: list[ImportStatementAuditV168] = []

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_names = tuple(alias.asname or alias.name for alias in node.names)
            has_wildcard = any(alias.name == "*" for alias in node.names)

            statements.append(
                ImportStatementAuditV168(
                    line_number=node.lineno,
                    module=module,
                    imported_names=imported_names,
                    level=node.level,
                    category=_classify_import(module, node.level),
                    has_wildcard=has_wildcard,
                )
            )

        elif isinstance(node, ast.Import):
            imported_names = tuple(alias.asname or alias.name for alias in node.names)
            module = ", ".join(alias.name for alias in node.names)

            statements.append(
                ImportStatementAuditV168(
                    line_number=node.lineno,
                    module=module,
                    imported_names=imported_names,
                    level=0,
                    category="absolute_import",
                    has_wildcard=False,
                )
            )

    return tuple(statements)


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsImportHygieneReportV168:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"
    source = views_path.read_text(encoding="utf-8")

    function_names, class_names = _top_level_definitions(source)
    imports = _import_statements(source)

    compatibility_imports = [
        statement
        for statement in imports
        if statement.category == "compatibility_view_reexport"
    ]

    compatibility_reexport_modules = tuple(
        sorted({statement.module for statement in compatibility_imports})
    )

    compatibility_reexport_names = tuple(
        sorted(
            name
            for statement in compatibility_imports
            for name in statement.imported_names
            if name != "*"
        )
    )

    relative_non_view_import_modules = tuple(
        sorted(
            {
                statement.module
                for statement in imports
                if statement.category == "relative_non_view_import"
            }
        )
    )

    absolute_import_modules = tuple(
        sorted(
            {
                statement.module
                for statement in imports
                if statement.category == "absolute_import"
            }
        )
    )

    wildcard_import_modules = tuple(
        sorted(
            {
                statement.module
                for statement in imports
                if statement.has_wildcard
            }
        )
    )

    imported_name_counts = Counter(
        name
        for statement in imports
        for name in statement.imported_names
        if name != "*"
    )

    duplicate_imported_names = tuple(
        sorted(name for name, count in imported_name_counts.items() if count > 1)
    )

    return ListingViewsImportHygieneReportV168(
        marker=LISTING_VIEWS_IMPORT_HYGIENE_AUDIT_MARKER_V168,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(source.splitlines()),
        top_level_function_names=function_names,
        top_level_class_names=class_names,
        import_statements=imports,
        compatibility_reexport_modules=compatibility_reexport_modules,
        compatibility_reexport_names=compatibility_reexport_names,
        relative_non_view_import_modules=relative_non_view_import_modules,
        absolute_import_modules=absolute_import_modules,
        wildcard_import_modules=wildcard_import_modules,
        duplicate_imported_names=duplicate_imported_names,
        recommendation=(
            "Keep listings/views.py as a compatibility facade. "
            "Before removing any imports, add a dedicated compatibility/import cleanup contract "
            "and verify every public URL callback still resolves through listings.views."
        ),
    )


def write_markdown_report(path: Path, report: ListingViewsImportHygieneReportV168) -> None:
    lines = [
        "# v168 Listing Views Compatibility / Import Hygiene Audit",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Top-level functions/classes remaining: `{report.total_top_level_definitions}`",
        f"- Facade-only state: `{report.is_facade_only}`",
        f"- Wildcard imports present: `{not report.has_no_wildcard_imports}`",
        f"- Missing expected compatibility re-export modules: `{report.missing_expected_reexport_modules}`",
        "",
        "## Compatibility view re-export modules",
        "",
    ]

    for module in report.compatibility_reexport_modules:
        lines.append(f"- `{module}`")

    lines.extend(
        [
            "",
            "## Compatibility re-exported names",
            "",
        ]
    )

    for name in report.compatibility_reexport_names:
        lines.append(f"- `{name}`")

    lines.extend(
        [
            "",
            "## Relative non-view import modules still present in facade",
            "",
        ]
    )

    if report.relative_non_view_import_modules:
        for module in report.relative_non_view_import_modules:
            lines.append(f"- `{module}`")
    else:
        lines.append("No relative non-view imports detected.")

    lines.extend(
        [
            "",
            "## Absolute import modules still present in facade",
            "",
        ]
    )

    if report.absolute_import_modules:
        for module in report.absolute_import_modules:
            lines.append(f"- `{module}`")
    else:
        lines.append("No absolute imports detected.")

    lines.extend(
        [
            "",
            "## Duplicate imported names",
            "",
        ]
    )

    if report.duplicate_imported_names:
        for name in report.duplicate_imported_names:
            lines.append(f"- `{name}`")
    else:
        lines.append("No duplicate imported names detected.")

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            report.recommendation,
            "",
            "## Non-goals",
            "",
            "- Do not move runtime code in v168.",
            "- Do not remove compatibility re-export paths in v168.",
            "- Do not change URLs, templates, permissions, models, migrations, or behavior.",
            "- Do not delete imports without a separate cleanup contract and route-resolution guard.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(
        Path("docs/listing_views_import_hygiene_audit_v168.md"),
        report,
    )


if __name__ == "__main__":
    main()
