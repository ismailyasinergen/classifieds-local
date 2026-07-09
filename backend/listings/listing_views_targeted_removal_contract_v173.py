from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_TARGETED_REMOVAL_CONTRACT_MARKER_V173 = "LISTING_VIEWS_TARGETED_REMOVAL_CONTRACT_V173"

TARGETED_UNUSED_FACADE_REEXPORT_CANDIDATE_NAMES_V173 = (
    "SidebarCategoriesMixin",
    "_safe_reporter_note",
)

EXPECTED_VIEW_REEXPORT_MODULES_V173 = (
    "listing_browse_detail_views",
    "listing_crud_uploads_views",
    "listing_favorite_views",
    "listing_promotion_views",
    "listing_reports_views",
    "listing_uncategorized_views",
    "saved_searches_views",
)

EXPECTED_HELPER_REEXPORTS_V173 = {
    "listing_filter_helpers": ("apply_listing_filters",),
    "listing_moderation_helpers": ("_create_moderation_notice",),
    "listing_lifecycle_helpers": ("default_listing_expiry",),
    "listing_visibility_helpers": ("active_approved_listings",),
    "listing_image_helpers": ("save_uploaded_listing_images", "validate_uploaded_images"),
}

IGNORED_SCAN_SUFFIXES_V173 = (
    "listing_views_targeted_removal_contract_v173.py",
    "test_listing_views_targeted_removal_contract_v173.py",
)


@dataclass(frozen=True)
class TargetedRemovalUsageRecordV173:
    relative_path: str
    line_number: int
    name: str
    category: str
    evidence: str


@dataclass(frozen=True)
class ListingViewsTargetedRemovalContractReportV173:
    marker: str
    app_root: str
    views_path: str
    views_total_lines: int
    top_level_definition_names: tuple[str, ...]
    view_reexport_modules: tuple[str, ...]
    view_reexport_names: tuple[str, ...]
    helper_reexport_modules: tuple[str, ...]
    helper_reexport_names: tuple[str, ...]
    unexpected_import_modules: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]
    candidate_names: tuple[str, ...]
    candidate_source_modules: tuple[tuple[str, str], ...]
    target_facade_dependency_records: tuple[TargetedRemovalUsageRecordV173, ...]
    target_informational_plain_reference_records: tuple[TargetedRemovalUsageRecordV173, ...]

    @property
    def protected_names(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.view_reexport_names) | set(self.helper_reexport_names)))

    @property
    def protected_non_candidate_names(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.protected_names) - set(self.candidate_names)))

    @property
    def candidate_names_present_in_facade(self) -> tuple[str, ...]:
        protected = set(self.protected_names)
        return tuple(sorted(name for name in self.candidate_names if name in protected))

    @property
    def candidate_names_missing_from_facade(self) -> tuple[str, ...]:
        protected = set(self.protected_names)
        return tuple(sorted(name for name in self.candidate_names if name not in protected))

    @property
    def is_facade_only(self) -> bool:
        return not self.top_level_definition_names

    @property
    def has_only_approved_reexports(self) -> bool:
        return not self.unexpected_import_modules

    @property
    def has_no_wildcard_imports(self) -> bool:
        return not self.wildcard_import_modules

    @property
    def has_no_target_facade_dependencies(self) -> bool:
        return not self.target_facade_dependency_records

    @property
    def eligible_for_future_targeted_removal_checkpoint(self) -> bool:
        return (
            self.is_facade_only
            and self.has_only_approved_reexports
            and self.has_no_wildcard_imports
            and not self.candidate_names_missing_from_facade
            and self.has_no_target_facade_dependencies
        )

    @property
    def safe_to_remove_in_v173(self) -> bool:
        return False

    @property
    def missing_view_reexport_modules(self) -> tuple[str, ...]:
        return tuple(sorted(set(EXPECTED_VIEW_REEXPORT_MODULES_V173) - set(self.view_reexport_modules)))

    @property
    def missing_helper_reexport_names(self) -> tuple[str, ...]:
        expected = {
            name
            for names in EXPECTED_HELPER_REEXPORTS_V173.values()
            for name in names
        }
        return tuple(sorted(expected - set(self.helper_reexport_names)))


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    candidates = (repo_root / "backend", repo_root)

    for candidate in candidates:
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
    return any(path.as_posix().endswith(suffix) for suffix in IGNORED_SCAN_SUFFIXES_V173)


def _extract_facade_inventory(views_path: Path) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[tuple[str, str], ...],
]:
    source = views_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    top_level_definitions: list[str] = []
    view_modules: set[str] = set()
    view_names: list[str] = []
    helper_modules: set[str] = set()
    helper_names: list[str] = []
    unexpected_modules: set[str] = set()
    wildcard_modules: set[str] = set()
    candidate_source_modules: dict[str, str] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top_level_definitions.append(node.name)

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = tuple(alias.asname or alias.name for alias in node.names)
            has_wildcard = any(alias.name == "*" for alias in node.names)

            if node.level == 1 and module.endswith("_views"):
                view_modules.add(module)
                view_names.extend(name for name in names if name != "*")
                for name in names:
                    if name in TARGETED_UNUSED_FACADE_REEXPORT_CANDIDATE_NAMES_V173:
                        candidate_source_modules[name] = module
            elif node.level == 1 and module in EXPECTED_HELPER_REEXPORTS_V173:
                helper_modules.add(module)
                helper_names.extend(name for name in names if name != "*")
            else:
                unexpected_modules.add(module)

            if has_wildcard:
                wildcard_modules.add(module)

        elif isinstance(node, ast.Import):
            unexpected_modules.add(", ".join(alias.name for alias in node.names))

    return (
        tuple(sorted(top_level_definitions)),
        tuple(sorted(view_modules)),
        tuple(sorted(view_names)),
        tuple(sorted(helper_modules)),
        tuple(sorted(helper_names)),
        tuple(sorted(unexpected_modules)),
        tuple(sorted(wildcard_modules)),
        tuple(sorted(candidate_source_modules.items())),
    )


def _is_listings_views_attr(node: ast.AST, aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in aliases

    if isinstance(node, ast.Attribute):
        if node.attr == "views" and isinstance(node.value, ast.Name) and node.value.id == "listings":
            return True
        return _is_listings_views_attr(node.value, aliases)

    return False


def _scan_python_file_for_target_facade_dependencies(
    path: Path,
    relative_path: str,
    target_names: set[str],
) -> tuple[TargetedRemovalUsageRecordV173, ...]:
    source = path.read_text(encoding="utf-8")

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()

    records: list[TargetedRemovalUsageRecordV173] = []
    facade_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if module == "listings.views" or (node.level == 1 and module == "views"):
                for alias in node.names:
                    imported_name = alias.name
                    if imported_name in target_names or imported_name == "*":
                        records.append(
                            TargetedRemovalUsageRecordV173(
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
                    facade_aliases.add(alias.asname or "listings.views")

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in target_names:
            if _is_listings_views_attr(node.value, facade_aliases):
                records.append(
                    TargetedRemovalUsageRecordV173(
                        relative_path=relative_path,
                        line_number=node.lineno,
                        name=node.attr,
                        category="facade_attribute_usage",
                        evidence=_line_evidence(path, node.lineno),
                    )
                )

    return tuple(records)


def _scan_file_for_informational_plain_references(
    path: Path,
    relative_path: str,
    target_names: set[str],
) -> tuple[TargetedRemovalUsageRecordV173, ...]:
    if path.suffix not in {".py", ".html", ".txt"}:
        return ()

    records: list[TargetedRemovalUsageRecordV173] = []

    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        compact = " ".join(line.strip().split())
        if not compact:
            continue

        for name in target_names:
            if name in compact:
                records.append(
                    TargetedRemovalUsageRecordV173(
                        relative_path=relative_path,
                        line_number=line_number,
                        name=name,
                        category="informational_plain_target_reference",
                        evidence=compact[:220],
                    )
                )

    return tuple(records)


def _scan_target_usage(
    app_root: Path,
    target_names: set[str],
) -> tuple[
    tuple[TargetedRemovalUsageRecordV173, ...],
    tuple[TargetedRemovalUsageRecordV173, ...],
]:
    facade_dependency_records: list[TargetedRemovalUsageRecordV173] = []
    informational_plain_reference_records: list[TargetedRemovalUsageRecordV173] = []

    for path in sorted(app_root.rglob("*")):
        if not path.is_file() or _is_ignored_path(path):
            continue

        relative_path = path.relative_to(app_root).as_posix()

        if relative_path == "listings/views.py":
            continue

        if path.suffix == ".py":
            facade_dependency_records.extend(
                _scan_python_file_for_target_facade_dependencies(path, relative_path, target_names)
            )

        informational_plain_reference_records.extend(
            _scan_file_for_informational_plain_references(path, relative_path, target_names)
        )

    return (
        tuple(
            sorted(
                facade_dependency_records,
                key=lambda record: (record.name, record.relative_path, record.line_number, record.category),
            )
        ),
        tuple(
            sorted(
                informational_plain_reference_records,
                key=lambda record: (record.name, record.relative_path, record.line_number, record.category),
            )
        ),
    )


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsTargetedRemovalContractReportV173:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"

    (
        top_level_definition_names,
        view_reexport_modules,
        view_reexport_names,
        helper_reexport_modules,
        helper_reexport_names,
        unexpected_import_modules,
        wildcard_import_modules,
        candidate_source_modules,
    ) = _extract_facade_inventory(views_path)

    target_names = set(TARGETED_UNUSED_FACADE_REEXPORT_CANDIDATE_NAMES_V173)
    target_facade_dependency_records, target_informational_plain_reference_records = _scan_target_usage(
        app_root=app_root,
        target_names=target_names,
    )

    return ListingViewsTargetedRemovalContractReportV173(
        marker=LISTING_VIEWS_TARGETED_REMOVAL_CONTRACT_MARKER_V173,
        app_root=app_root.as_posix(),
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(views_path.read_text(encoding="utf-8").splitlines()),
        top_level_definition_names=top_level_definition_names,
        view_reexport_modules=view_reexport_modules,
        view_reexport_names=view_reexport_names,
        helper_reexport_modules=helper_reexport_modules,
        helper_reexport_names=helper_reexport_names,
        unexpected_import_modules=unexpected_import_modules,
        wildcard_import_modules=wildcard_import_modules,
        candidate_names=TARGETED_UNUSED_FACADE_REEXPORT_CANDIDATE_NAMES_V173,
        candidate_source_modules=candidate_source_modules,
        target_facade_dependency_records=target_facade_dependency_records,
        target_informational_plain_reference_records=target_informational_plain_reference_records,
    )


def write_markdown_report(path: Path, report: ListingViewsTargetedRemovalContractReportV173) -> None:
    lines = [
        "# v173 Listing Views Targeted Removal Contract",
        "",
        report.marker,
        "",
        "## Purpose",
        "",
        "v173 freezes the exact two-name candidate pair discovered by the v172 checkpoint before v173 test/doc references existed.",
        "",
        "v173 does not remove either candidate.",
        "",
        "## Candidate names",
        "",
    ]

    for name in report.candidate_names:
        lines.append(f"- `{name}`")

    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Views path: `{report.views_path}`",
            f"- Views total lines: `{report.views_total_lines}`",
            f"- Facade-only state: `{report.is_facade_only}`",
            f"- Only approved compatibility re-exports remain: `{report.has_only_approved_reexports}`",
            f"- Wildcard imports present: `{not report.has_no_wildcard_imports}`",
            f"- Candidate names present in facade: `{report.candidate_names_present_in_facade}`",
            f"- Candidate names missing from facade: `{report.candidate_names_missing_from_facade}`",
            f"- Target facade dependency records: `{len(report.target_facade_dependency_records)}`",
            f"- Informational plain target reference records: `{len(report.target_informational_plain_reference_records)}`",
            f"- Eligible for future targeted removal checkpoint: `{report.eligible_for_future_targeted_removal_checkpoint}`",
            f"- Safe to remove in v173: `{report.safe_to_remove_in_v173}`",
            "",
            "## Candidate source modules",
            "",
        ]
    )

    for name, module in report.candidate_source_modules:
        lines.append(f"- `{name}` from `{module}`")

    lines.extend(["", "## Target facade dependency records", ""])

    if report.target_facade_dependency_records:
        for record in report.target_facade_dependency_records:
            lines.append(
                f"- `{record.name}` — `{record.category}` — "
                f"`{record.relative_path}:{record.line_number}` — {record.evidence}"
            )
    else:
        lines.append("No target facade dependency records detected.")

    lines.extend(["", "## Informational plain target reference records", ""])

    if report.target_informational_plain_reference_records:
        for record in report.target_informational_plain_reference_records:
            lines.append(
                f"- `{record.name}` — `{record.category}` — "
                f"`{record.relative_path}:{record.line_number}` — {record.evidence}"
            )
    else:
        lines.append("No plain target references detected.")

    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- Do not remove `SidebarCategoriesMixin` or `_safe_reporter_note` in v173.",
            "- Plain references are informational only; facade dependency records are the blocker for removing names from `listings.views`.",
            "- The candidate pair is frozen from the v172 checkpoint result; live v172 scans after adding v173 files are expected to see v173's own references.",
            "- Do not remove helper compatibility re-exports in v173.",
            "- Do not remove route/view compatibility re-export paths in v173.",
            "- Do not change URLs, templates, permissions, models, migrations, or behavior.",
            "- A later checkpoint may remove only these two names from `listings.views` if this contract remains green.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_targeted_removal_contract_v173.md"), report)


if __name__ == "__main__":
    main()
