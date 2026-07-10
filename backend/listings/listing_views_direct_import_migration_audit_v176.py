from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_AUDIT_MARKER_V176 = "LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_AUDIT_V176"

REMOVED_IN_V174_FACADE_REEXPORT_NAMES_V176 = (
    "SidebarCategoriesMixin",
    "_safe_reporter_note",
)

MIGRATED_IN_V177_FACADE_DEPENDENCY_NAMES_V176 = ('listing_feature_priority_update',)

REMOVED_IN_V179_FACADE_REEXPORT_NAMES_V176 = ('listing_feature_priority_update',)

EXPECTED_VIEW_REEXPORT_MODULES_V176 = (
    "listing_browse_detail_views",
    "listing_crud_uploads_views",
    "listing_favorite_views",
    "listing_promotion_views",
    "listing_reports_views",
    "listing_uncategorized_views",
    "saved_searches_views",
)

EXPECTED_HELPER_REEXPORT_MODULES_V176 = (
    "listing_filter_helpers",
    "listing_image_helpers",
    "listing_lifecycle_helpers",
    "listing_moderation_helpers",
    "listing_visibility_helpers",
)

IGNORED_SCAN_SUFFIXES_V176 = (
    "listing_views_direct_import_migration_audit_v176.py",
    "test_listing_views_direct_import_migration_audit_v176.py",
)


@dataclass(frozen=True)
class FacadeImportMigrationRecordV176:
    relative_path: str
    line_number: int
    name: str
    source_module: str
    source_kind: str
    facade_usage_form: str
    migration_import: str
    suggested_action: str
    evidence: str


@dataclass(frozen=True)
class ManualReviewImportRecordV176:
    relative_path: str
    line_number: int
    facade_usage_form: str
    reason: str
    evidence: str


@dataclass(frozen=True)
class ListingViewsDirectImportMigrationAuditReportV176:
    marker: str
    app_root: str
    views_path: str
    views_total_lines: int
    protected_names: tuple[str, ...]
    view_reexport_modules: tuple[str, ...]
    view_reexport_names: tuple[str, ...]
    helper_reexport_modules: tuple[str, ...]
    helper_reexport_names: tuple[str, ...]
    removed_v174_names_present: tuple[str, ...]
    removed_v174_names_absent: tuple[str, ...]
    top_level_definition_names: tuple[str, ...]
    unexpected_import_modules: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]
    migration_records: tuple[FacadeImportMigrationRecordV176, ...]
    manual_review_records: tuple[ManualReviewImportRecordV176, ...]

    @property
    def protected_name_count(self) -> int:
        return len(self.protected_names)

    @property
    def migration_record_count(self) -> int:
        return len(self.migration_records)

    @property
    def migration_names(self) -> tuple[str, ...]:
        return tuple(sorted({record.name for record in self.migration_records}))

    @property
    def source_modules_with_migrations(self) -> tuple[str, ...]:
        return tuple(sorted({record.source_module for record in self.migration_records}))

    @property
    def migration_count_by_source_module(self) -> tuple[tuple[str, int], ...]:
        counter = Counter(record.source_module for record in self.migration_records)
        return tuple(sorted(counter.items()))

    @property
    def migration_count_by_usage_form(self) -> tuple[tuple[str, int], ...]:
        counter = Counter(record.facade_usage_form for record in self.migration_records)
        return tuple(sorted(counter.items()))

    @property
    def names_without_migration_records(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.protected_names) - set(self.migration_names)))

    @property
    def all_remaining_names_have_migration_paths(self) -> bool:
        return not self.names_without_migration_records

    @property
    def names_migrated_after_v176(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                set(self.names_without_migration_records)
                & set(MIGRATED_IN_V177_FACADE_DEPENDENCY_NAMES_V176)
            )
        )

    @property
    def all_unmigrated_names_still_have_migration_paths(self) -> bool:
        allowed_missing = (
            set(MIGRATED_IN_V177_FACADE_DEPENDENCY_NAMES_V176)
            - set(REMOVED_IN_V179_FACADE_REEXPORT_NAMES_V176)
        )
        return set(self.names_without_migration_records) == allowed_missing

    @property
    def names_removed_after_v177_migration(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                set(REMOVED_IN_V179_FACADE_REEXPORT_NAMES_V176)
                - set(self.protected_names)
            )
        )

    @property
    def v179_removed_names_are_absent_from_migration_records(self) -> bool:
        removed = set(REMOVED_IN_V179_FACADE_REEXPORT_NAMES_V176)
        return removed.isdisjoint(set(self.migration_names))

    @property
    def is_facade_only(self) -> bool:
        return not self.top_level_definition_names

    @property
    def has_import_hygiene(self) -> bool:
        return not self.unexpected_import_modules and not self.wildcard_import_modules

    @property
    def v174_targeted_removal_is_preserved(self) -> bool:
        return (
            self.removed_v174_names_present == ()
            and self.removed_v174_names_absent == REMOVED_IN_V174_FACADE_REEXPORT_NAMES_V176
        )

    @property
    def safe_to_change_imports_in_v176(self) -> bool:
        return False


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    for candidate in (repo_root / "backend", repo_root):
        if (candidate / "listings" / "views.py").exists():
            return candidate
    raise FileNotFoundError(f"Could not resolve app root containing listings/views.py from {repo_root}")


def _line_evidence(path: Path, line_number: int) -> str:
    try:
        line = path.read_text(encoding="utf-8").splitlines()[line_number - 1]
    except Exception:
        return ""
    return " ".join(line.strip().split())[:240]


def _is_ignored_path(path: Path) -> bool:
    parts = set(path.parts)
    if ".git" in parts or "__pycache__" in parts:
        return True
    return any(path.as_posix().endswith(suffix) for suffix in IGNORED_SCAN_SUFFIXES_V176)


def _extract_facade_inventory(views_path: Path):
    source = views_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    view_modules: set[str] = set()
    view_names: list[str] = []
    helper_modules: set[str] = set()
    helper_names: list[str] = []
    source_by_name: dict[str, tuple[str, str]] = {}
    unexpected_imports: set[str] = set()
    wildcard_modules: set[str] = set()
    local_defs: list[str] = []

    helper_module_set = set(EXPECTED_HELPER_REEXPORT_MODULES_V176)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            local_defs.append(node.name)

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if node.level == 1 and module.endswith("_views"):
                view_modules.add(module)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    public_name = alias.asname or alias.name
                    view_names.append(public_name)
                    source_by_name[public_name] = (module, "view_reexport")
            elif node.level == 1 and module in helper_module_set:
                helper_modules.add(module)
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    public_name = alias.asname or alias.name
                    helper_names.append(public_name)
                    source_by_name[public_name] = (module, "helper_reexport")
            else:
                unexpected_imports.add(module)

            if any(alias.name == "*" for alias in node.names):
                wildcard_modules.add(module)

        elif isinstance(node, ast.Import):
            unexpected_imports.add(", ".join(alias.name for alias in node.names))

    return (
        source,
        tuple(sorted(view_modules)),
        tuple(sorted(view_names)),
        tuple(sorted(helper_modules)),
        tuple(sorted(helper_names)),
        source_by_name,
        tuple(sorted(unexpected_imports)),
        tuple(sorted(wildcard_modules)),
        tuple(sorted(local_defs)),
    )


def _is_listings_views_attr(node: ast.AST, aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in aliases

    if isinstance(node, ast.Attribute):
        if node.attr == "views" and isinstance(node.value, ast.Name) and node.value.id == "listings":
            return True
        return _is_listings_views_attr(node.value, aliases)

    return False


def _migration_import(name: str, source_module: str) -> str:
    return f"from listings.{source_module} import {name}"


def _scan_python_file_for_migration_records(
    path: Path,
    relative_path: str,
    protected_names: set[str],
    source_by_name: dict[str, tuple[str, str]],
) -> tuple[tuple[FacadeImportMigrationRecordV176, ...], tuple[ManualReviewImportRecordV176, ...]]:
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return (), ()

    migration_records: list[FacadeImportMigrationRecordV176] = []
    manual_review_records: list[ManualReviewImportRecordV176] = []
    facade_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if module == "listings.views" or (node.level == 1 and module == "views"):
                for alias in node.names:
                    imported_name = alias.name

                    if imported_name == "*":
                        manual_review_records.append(
                            ManualReviewImportRecordV176(
                                relative_path=relative_path,
                                line_number=node.lineno,
                                facade_usage_form="wildcard_from_listings_views_import",
                                reason="Wildcard facade imports require manual expansion before a dedicated-module import can be recommended.",
                                evidence=_line_evidence(path, node.lineno),
                            )
                        )
                        continue

                    if imported_name not in protected_names:
                        continue

                    source_module, source_kind = source_by_name[imported_name]
                    migration_records.append(
                        FacadeImportMigrationRecordV176(
                            relative_path=relative_path,
                            line_number=node.lineno,
                            name=imported_name,
                            source_module=source_module,
                            source_kind=source_kind,
                            facade_usage_form="direct_from_listings_views_import",
                            migration_import=_migration_import(imported_name, source_module),
                            suggested_action="Replace the facade import with the dedicated-module import.",
                            evidence=_line_evidence(path, node.lineno),
                        )
                    )

            if module == "listings" or (node.level == 1 and module == ""):
                for alias in node.names:
                    if alias.name == "views":
                        facade_aliases.add(alias.asname or alias.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "listings.views" and alias.asname:
                    facade_aliases.add(alias.asname)

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in protected_names:
            if _is_listings_views_attr(node.value, facade_aliases):
                source_module, source_kind = source_by_name[node.attr]
                migration_records.append(
                    FacadeImportMigrationRecordV176(
                        relative_path=relative_path,
                        line_number=node.lineno,
                        name=node.attr,
                        source_module=source_module,
                        source_kind=source_kind,
                        facade_usage_form="facade_attribute_usage",
                        migration_import=_migration_import(node.attr, source_module),
                        suggested_action="Import the name from its dedicated module and replace the facade attribute reference.",
                        evidence=_line_evidence(path, node.lineno),
                    )
                )

    return tuple(migration_records), tuple(manual_review_records)


def _scan_migration_paths(
    app_root: Path,
    protected_names: set[str],
    source_by_name: dict[str, tuple[str, str]],
):
    migration_records: list[FacadeImportMigrationRecordV176] = []
    manual_review_records: list[ManualReviewImportRecordV176] = []

    for path in sorted(app_root.rglob("*.py")):
        if not path.is_file() or _is_ignored_path(path):
            continue

        relative_path = path.relative_to(app_root).as_posix()

        if relative_path == "listings/views.py":
            continue

        file_records, file_manual_records = _scan_python_file_for_migration_records(
            path=path,
            relative_path=relative_path,
            protected_names=protected_names,
            source_by_name=source_by_name,
        )
        migration_records.extend(file_records)
        manual_review_records.extend(file_manual_records)

    return (
        tuple(
            sorted(
                migration_records,
                key=lambda record: (
                    record.relative_path,
                    record.line_number,
                    record.name,
                    record.facade_usage_form,
                ),
            )
        ),
        tuple(
            sorted(
                manual_review_records,
                key=lambda record: (
                    record.relative_path,
                    record.line_number,
                    record.facade_usage_form,
                ),
            )
        ),
    )


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsDirectImportMigrationAuditReportV176:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"

    (
        source,
        view_modules,
        view_names,
        helper_modules,
        helper_names,
        source_by_name,
        unexpected_imports,
        wildcard_modules,
        local_defs,
    ) = _extract_facade_inventory(views_path)

    protected_names = tuple(sorted(set(view_names) | set(helper_names)))
    protected_set = set(protected_names)
    migration_records, manual_review_records = _scan_migration_paths(
        app_root=app_root,
        protected_names=protected_set,
        source_by_name=source_by_name,
    )

    removed_set = set(REMOVED_IN_V174_FACADE_REEXPORT_NAMES_V176)

    return ListingViewsDirectImportMigrationAuditReportV176(
        marker=LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_AUDIT_MARKER_V176,
        app_root=app_root.as_posix(),
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(source.splitlines()),
        protected_names=protected_names,
        view_reexport_modules=view_modules,
        view_reexport_names=view_names,
        helper_reexport_modules=helper_modules,
        helper_reexport_names=helper_names,
        removed_v174_names_present=tuple(sorted(removed_set & protected_set)),
        removed_v174_names_absent=tuple(sorted(removed_set - protected_set)),
        top_level_definition_names=local_defs,
        unexpected_import_modules=unexpected_imports,
        wildcard_import_modules=wildcard_modules,
        migration_records=migration_records,
        manual_review_records=manual_review_records,
    )


def write_markdown_report(path: Path, report: ListingViewsDirectImportMigrationAuditReportV176) -> None:
    lines = [
        "# v176 Listing Views Direct Import Migration Audit",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Protected remaining facade names: `{report.protected_name_count}`",
        f"- Migration records: `{report.migration_record_count}`",
        f"- Migration names: `{report.migration_names}`",
        f"- Names without migration records: `{report.names_without_migration_records}`",
        f"- All remaining names have migration paths: `{report.all_remaining_names_have_migration_paths}`",
        f"- Names migrated after v176: `{report.names_migrated_after_v176}`",
        f"- All unmigrated names still have migration paths: `{report.all_unmigrated_names_still_have_migration_paths}`",
        f"- Names removed after v177 migration: `{report.names_removed_after_v177_migration}`",
        f"- v179 removed names absent from migration records: `{report.v179_removed_names_are_absent_from_migration_records}`",
        f"- Source modules with migrations: `{report.source_modules_with_migrations}`",
        f"- Migration count by source module: `{report.migration_count_by_source_module}`",
        f"- Migration count by usage form: `{report.migration_count_by_usage_form}`",
        f"- Manual review records: `{len(report.manual_review_records)}`",
        f"- v174 targeted removal preserved: `{report.v174_targeted_removal_is_preserved}`",
        f"- Removed-v174 names still present: `{report.removed_v174_names_present}`",
        f"- Removed-v174 names absent: `{report.removed_v174_names_absent}`",
        f"- Facade-only state: `{report.is_facade_only}`",
        f"- Import hygiene: `{report.has_import_hygiene}`",
        f"- Safe to change imports in v176: `{report.safe_to_change_imports_in_v176}`",
        "",
        "## Migration records",
        "",
    ]

    if report.migration_records:
        for record in report.migration_records:
            lines.append(
                f"- `{record.relative_path}:{record.line_number}` — `{record.name}` — "
                f"`{record.facade_usage_form}` → `{record.migration_import}` — {record.evidence}"
            )
    else:
        lines.append("No migration records detected.")

    lines.extend(["", "## Manual review records", ""])

    if report.manual_review_records:
        for record in report.manual_review_records:
            lines.append(
                f"- `{record.relative_path}:{record.line_number}` — `{record.facade_usage_form}` — "
                f"{record.reason} — {record.evidence}"
            )
    else:
        lines.append("No manual review records detected.")

    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- v176 is audit-only.",
            "- Do not change imports in v176.",
            "- Do not edit `backend/listings/views.py` in v176.",
            "- Do not remove any remaining facade re-export in v176.",
            "- After v177, one small import group has been intentionally migrated.",
            "- After v179, that migrated group has been removed from the facade.",
            "- A later checkpoint may migrate one small import group after this audit is reviewed.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_direct_import_migration_audit_v176.md"), report)


if __name__ == "__main__":
    main()
