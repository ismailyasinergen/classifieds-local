from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_REMAINING_FACADE_SURFACE_AUDIT_MARKER_V175 = "LISTING_VIEWS_REMAINING_FACADE_SURFACE_AUDIT_V175"

REMOVED_IN_V174_FACADE_REEXPORT_NAMES = (
    "SidebarCategoriesMixin",
    "_safe_reporter_note",
)

MIGRATED_IN_V177_FACADE_DEPENDENCY_NAMES_V175 = ('listing_feature_priority_update',)

EXPECTED_VIEW_REEXPORT_MODULES_V175 = (
    "listing_browse_detail_views",
    "listing_crud_uploads_views",
    "listing_favorite_views",
    "listing_promotion_views",
    "listing_reports_views",
    "listing_uncategorized_views",
    "saved_searches_views",
)

EXPECTED_HELPER_REEXPORT_MODULES_V175 = (
    "listing_filter_helpers",
    "listing_image_helpers",
    "listing_lifecycle_helpers",
    "listing_moderation_helpers",
    "listing_visibility_helpers",
)

IGNORED_SCAN_SUFFIXES_V175 = (
    "listing_views_remaining_facade_surface_audit_v175.py",
    "test_listing_views_remaining_facade_surface_audit_v175.py",
)


@dataclass(frozen=True)
class FacadeDependencyRecordV175:
    relative_path: str
    line_number: int
    name: str
    category: str
    evidence: str


@dataclass(frozen=True)
class RemainingFacadeCandidateV175:
    name: str
    source_module: str
    source_kind: str
    dependency_count: int
    candidate_reason: str


@dataclass(frozen=True)
class ListingViewsRemainingFacadeSurfaceReportV175:
    marker: str
    app_root: str
    views_path: str
    views_total_lines: int
    view_reexport_modules: tuple[str, ...]
    view_reexport_names: tuple[str, ...]
    helper_reexport_modules: tuple[str, ...]
    helper_reexport_names: tuple[str, ...]
    protected_names: tuple[str, ...]
    removed_v174_names_present: tuple[str, ...]
    removed_v174_names_absent: tuple[str, ...]
    top_level_definition_names: tuple[str, ...]
    unexpected_import_modules: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]
    dependency_records: tuple[FacadeDependencyRecordV175, ...]
    candidates_without_facade_dependencies: tuple[RemainingFacadeCandidateV175, ...]

    @property
    def protected_name_count(self) -> int:
        return len(self.protected_names)

    @property
    def dependency_names(self) -> tuple[str, ...]:
        return tuple(sorted({record.name for record in self.dependency_records}))

    @property
    def candidate_names(self) -> tuple[str, ...]:
        return tuple(candidate.name for candidate in self.candidates_without_facade_dependencies)

    @property
    def candidate_count(self) -> int:
        return len(self.candidates_without_facade_dependencies)

    @property
    def next_removal_candidate_available(self) -> bool:
        return bool(self.candidates_without_facade_dependencies)

    @property
    def all_remaining_names_have_facade_dependencies(self) -> bool:
        return set(self.dependency_names) == set(self.protected_names)

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
            and self.removed_v174_names_absent == REMOVED_IN_V174_FACADE_REEXPORT_NAMES
        )

    @property
    def post_v177_migration_candidate_names(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                set(self.candidate_names)
                & set(MIGRATED_IN_V177_FACADE_DEPENDENCY_NAMES_V175)
            )
        )

    @property
    def only_v177_migrated_names_are_candidates(self) -> bool:
        return set(self.candidate_names) == set(MIGRATED_IN_V177_FACADE_DEPENDENCY_NAMES_V175)

    @property
    def safe_to_remove_anything_in_v175(self) -> bool:
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
    return " ".join(line.strip().split())[:220]


def _is_ignored_path(path: Path) -> bool:
    parts = set(path.parts)
    if ".git" in parts or "__pycache__" in parts:
        return True
    return any(path.as_posix().endswith(suffix) for suffix in IGNORED_SCAN_SUFFIXES_V175)


def _format_alias(alias: ast.alias) -> str:
    if alias.asname:
        return f"{alias.name} as {alias.asname}"
    return alias.name


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

    helper_module_set = set(EXPECTED_HELPER_REEXPORT_MODULES_V175)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            local_defs.append(node.name)

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = tuple(alias.asname or alias.name for alias in node.names)

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


def _scan_python_file_for_facade_dependencies(
    path: Path,
    relative_path: str,
    protected_names: set[str],
) -> tuple[FacadeDependencyRecordV175, ...]:
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()

    records: list[FacadeDependencyRecordV175] = []
    facade_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if module == "listings.views" or (node.level == 1 and module == "views"):
                for alias in node.names:
                    imported_name = alias.name
                    if imported_name == "*":
                        records.append(
                            FacadeDependencyRecordV175(
                                relative_path=relative_path,
                                line_number=node.lineno,
                                name="*",
                                category="wildcard_from_listings_views_import",
                                evidence=_line_evidence(path, node.lineno),
                            )
                        )
                    elif imported_name in protected_names:
                        records.append(
                            FacadeDependencyRecordV175(
                                relative_path=relative_path,
                                line_number=node.lineno,
                                name=imported_name,
                                category="direct_from_listings_views_import",
                                evidence=_line_evidence(path, node.lineno),
                            )
                        )

            if module == "listings" or (node.level == 1 and module == ""):
                for alias in node.names:
                    if alias.name == "views":
                        facade_aliases.add(alias.asname or alias.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "listings.views":
                    if alias.asname:
                        facade_aliases.add(alias.asname)

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in protected_names:
            if _is_listings_views_attr(node.value, facade_aliases):
                records.append(
                    FacadeDependencyRecordV175(
                        relative_path=relative_path,
                        line_number=node.lineno,
                        name=node.attr,
                        category="facade_attribute_usage",
                        evidence=_line_evidence(path, node.lineno),
                    )
                )

    return tuple(records)


def _scan_facade_dependencies(app_root: Path, protected_names: set[str]) -> tuple[FacadeDependencyRecordV175, ...]:
    records: list[FacadeDependencyRecordV175] = []

    for path in sorted(app_root.rglob("*.py")):
        if not path.is_file() or _is_ignored_path(path):
            continue

        relative_path = path.relative_to(app_root).as_posix()

        if relative_path == "listings/views.py":
            continue

        records.extend(
            _scan_python_file_for_facade_dependencies(
                path=path,
                relative_path=relative_path,
                protected_names=protected_names,
            )
        )

    return tuple(
        sorted(
            records,
            key=lambda record: (
                record.name,
                record.relative_path,
                record.line_number,
                record.category,
                record.evidence,
            ),
        )
    )


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsRemainingFacadeSurfaceReportV175:
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
    dependency_records = _scan_facade_dependencies(app_root, protected_set)

    dependency_counts: dict[str, int] = {name: 0 for name in protected_names}
    for record in dependency_records:
        if record.name in dependency_counts:
            dependency_counts[record.name] += 1

    candidates: list[RemainingFacadeCandidateV175] = []
    for name in protected_names:
        dependency_count = dependency_counts[name]
        if dependency_count != 0:
            continue

        source_module, source_kind = source_by_name.get(name, ("", "unknown"))
        candidates.append(
            RemainingFacadeCandidateV175(
                name=name,
                source_module=source_module,
                source_kind=source_kind,
                dependency_count=dependency_count,
                candidate_reason="No direct `listings.views` import or `views.<name>` facade attribute usage detected.",
            )
        )

    removed_set = set(REMOVED_IN_V174_FACADE_REEXPORT_NAMES)

    return ListingViewsRemainingFacadeSurfaceReportV175(
        marker=LISTING_VIEWS_REMAINING_FACADE_SURFACE_AUDIT_MARKER_V175,
        app_root=app_root.as_posix(),
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(source.splitlines()),
        view_reexport_modules=view_modules,
        view_reexport_names=view_names,
        helper_reexport_modules=helper_modules,
        helper_reexport_names=helper_names,
        protected_names=protected_names,
        removed_v174_names_present=tuple(sorted(removed_set & protected_set)),
        removed_v174_names_absent=tuple(sorted(removed_set - protected_set)),
        top_level_definition_names=local_defs,
        unexpected_import_modules=unexpected_imports,
        wildcard_import_modules=wildcard_modules,
        dependency_records=dependency_records,
        candidates_without_facade_dependencies=tuple(candidates),
    )


def write_markdown_report(path: Path, report: ListingViewsRemainingFacadeSurfaceReportV175) -> None:
    lines = [
        "# v175 Remaining Listing Views Facade Surface Audit",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Protected remaining facade names: `{report.protected_name_count}`",
        f"- Facade dependency records: `{len(report.dependency_records)}`",
        f"- Names with detected facade dependencies: `{report.dependency_names}`",
        f"- Candidate names without detected facade dependencies: `{report.candidate_names}`",
        f"- Candidate count: `{report.candidate_count}`",
        f"- Next removal candidate available: `{report.next_removal_candidate_available}`",
        f"- All remaining names have facade dependencies: `{report.all_remaining_names_have_facade_dependencies}`",
        f"- v177 migrated candidate names: `{report.post_v177_migration_candidate_names}`",
        f"- Only v177 migrated names are candidates: `{report.only_v177_migrated_names_are_candidates}`",
        f"- v174 targeted removal preserved: `{report.v174_targeted_removal_is_preserved}`",
        f"- Removed-v174 names still present: `{report.removed_v174_names_present}`",
        f"- Removed-v174 names absent: `{report.removed_v174_names_absent}`",
        f"- Facade-only state: `{report.is_facade_only}`",
        f"- Import hygiene: `{report.has_import_hygiene}`",
        f"- Safe to remove anything in v175: `{report.safe_to_remove_anything_in_v175}`",
        "",
        "## Candidate names without detected facade dependencies",
        "",
    ]

    if report.candidates_without_facade_dependencies:
        for candidate in report.candidates_without_facade_dependencies:
            lines.append(
                f"- `{candidate.name}` — `{candidate.source_kind}` from `{candidate.source_module}` — "
                f"{candidate.candidate_reason}"
            )
    else:
        lines.append("No next removal candidates were detected.")

    lines.extend(["", "## Facade dependency records", ""])

    if report.dependency_records:
        for record in report.dependency_records:
            lines.append(
                f"- `{record.name}` — `{record.category}` — "
                f"`{record.relative_path}:{record.line_number}` — {record.evidence}"
            )
    else:
        lines.append("No facade dependency records detected.")

    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- v175 is audit-only.",
            "- Do not remove any remaining facade re-export in v175.",
            "- Do not remove helper compatibility re-exports in v175.",
            "- Do not remove route/view compatibility paths in v175.",
            "- If candidate count is zero, do not attempt another facade-removal checkpoint yet.",
            "- After v177, the only candidate should be the intentionally migrated import group.",
            "- A later checkpoint may target a candidate only after a dedicated contract freezes it first.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_remaining_facade_surface_audit_v175.md"), report)


if __name__ == "__main__":
    main()
