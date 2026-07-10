from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_COMPATIBILITY_USAGE_AUDIT_MARKER_V172 = "LISTING_VIEWS_COMPATIBILITY_USAGE_AUDIT_V172"

EXPECTED_VIEW_REEXPORT_MODULES_V172 = (
    "listing_browse_detail_views",
    "listing_crud_uploads_views",
    "listing_favorite_views",
    "listing_reports_views",
    "listing_uncategorized_views",
    "saved_searches_views",
)

EXPECTED_HELPER_REEXPORTS_V172 = {
    "listing_filter_helpers": ("apply_listing_filters",),
    "listing_moderation_helpers": ("_create_moderation_notice",),
    "listing_lifecycle_helpers": ("default_listing_expiry",),
    "listing_visibility_helpers": ("active_approved_listings",),
    "listing_image_helpers": ("save_uploaded_listing_images", "validate_uploaded_images"),
}

IGNORED_SCAN_SUFFIXES_V172 = (
    "listing_views_compatibility_usage_audit_v172.py",
    "test_listing_views_compatibility_usage_audit_v172.py",
)


@dataclass(frozen=True)
class CompatibilityUsageRecordV172:
    relative_path: str
    line_number: int
    name: str
    category: str
    evidence: str


@dataclass(frozen=True)
class ListingViewsCompatibilityUsageReportV172:
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
    usage_records: tuple[CompatibilityUsageRecordV172, ...]

    @property
    def protected_names(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.view_reexport_names) | set(self.helper_reexport_names)))

    @property
    def usage_dependency_names(self) -> tuple[str, ...]:
        protected = set(self.protected_names)
        return tuple(sorted({record.name for record in self.usage_records if record.name in protected}))

    @property
    def helper_names_with_usage(self) -> tuple[str, ...]:
        helpers = set(self.helper_reexport_names)
        return tuple(sorted(name for name in self.usage_dependency_names if name in helpers))

    @property
    def view_names_with_usage(self) -> tuple[str, ...]:
        view_names = set(self.view_reexport_names)
        return tuple(sorted(name for name in self.usage_dependency_names if name in view_names))

    @property
    def names_without_detected_usage(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.protected_names) - set(self.usage_dependency_names)))

    @property
    def has_usage_dependencies(self) -> bool:
        return bool(self.usage_dependency_names)

    @property
    def safe_to_remove_any_reexports_now(self) -> bool:
        return not self.has_usage_dependencies

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
    def missing_view_reexport_modules(self) -> tuple[str, ...]:
        return tuple(sorted(set(EXPECTED_VIEW_REEXPORT_MODULES_V172) - set(self.view_reexport_modules)))

    @property
    def missing_helper_reexport_names(self) -> tuple[str, ...]:
        expected = {
            name
            for names in EXPECTED_HELPER_REEXPORTS_V172.values()
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
    return any(path.as_posix().endswith(suffix) for suffix in IGNORED_SCAN_SUFFIXES_V172)


def _extract_facade_inventory(views_path: Path) -> tuple[
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
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
            elif node.level == 1 and module in EXPECTED_HELPER_REEXPORTS_V172:
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
    )


def _is_listings_views_attr(node: ast.AST, aliases: set[str]) -> bool:
    if isinstance(node, ast.Name):
        return node.id in aliases

    if isinstance(node, ast.Attribute):
        if node.attr == "views" and isinstance(node.value, ast.Name) and node.value.id == "listings":
            return True
        return _is_listings_views_attr(node.value, aliases)

    return False


def _scan_python_file(path: Path, relative_path: str, protected_names: set[str]) -> tuple[CompatibilityUsageRecordV172, ...]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()

    records: list[CompatibilityUsageRecordV172] = []
    facade_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""

            if module == "listings.views" or (node.level == 1 and module == "views"):
                for alias in node.names:
                    imported_name = alias.name
                    if imported_name in protected_names or imported_name == "*":
                        records.append(
                            CompatibilityUsageRecordV172(
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
                        records.append(
                            CompatibilityUsageRecordV172(
                                relative_path=relative_path,
                                line_number=node.lineno,
                                name="__facade_module__",
                                category="facade_module_import",
                                evidence=_line_evidence(path, node.lineno),
                            )
                        )

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "listings.views":
                    facade_aliases.add(alias.asname or "listings.views")
                    records.append(
                        CompatibilityUsageRecordV172(
                            relative_path=relative_path,
                            line_number=node.lineno,
                            name="__facade_module__",
                            category="facade_module_import",
                            evidence=_line_evidence(path, node.lineno),
                        )
                    )

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in protected_names:
            if _is_listings_views_attr(node.value, facade_aliases):
                records.append(
                    CompatibilityUsageRecordV172(
                        relative_path=relative_path,
                        line_number=node.lineno,
                        name=node.attr,
                        category="facade_attribute_usage",
                        evidence=_line_evidence(path, node.lineno),
                    )
                )

    return tuple(records)


def _scan_text_file(path: Path, relative_path: str, protected_names: set[str]) -> tuple[CompatibilityUsageRecordV172, ...]:
    records: list[CompatibilityUsageRecordV172] = []
    text = path.read_text(encoding="utf-8", errors="ignore")

    for index, line in enumerate(text.splitlines(), start=1):
        compact = " ".join(line.strip().split())
        if not compact:
            continue

        if "listings.views" not in compact and "views." not in compact:
            continue

        for name in sorted(protected_names):
            if name in compact:
                records.append(
                    CompatibilityUsageRecordV172(
                        relative_path=relative_path,
                        line_number=index,
                        name=name,
                        category="textual_facade_reference",
                        evidence=compact[:220],
                    )
                )

    return tuple(records)


def _scan_usage(app_root: Path, protected_names: set[str]) -> tuple[CompatibilityUsageRecordV172, ...]:
    records: list[CompatibilityUsageRecordV172] = []

    for path in sorted(app_root.rglob("*")):
        if not path.is_file() or _is_ignored_path(path):
            continue

        relative_path = path.relative_to(app_root).as_posix()

        if path.suffix == ".py":
            records.extend(_scan_python_file(path, relative_path, protected_names))
        elif path.suffix in {".html", ".txt"}:
            records.extend(_scan_text_file(path, relative_path, protected_names))

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


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsCompatibilityUsageReportV172:
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
    ) = _extract_facade_inventory(views_path)

    protected_names = set(view_reexport_names) | set(helper_reexport_names)
    usage_records = _scan_usage(app_root, protected_names)

    return ListingViewsCompatibilityUsageReportV172(
        marker=LISTING_VIEWS_COMPATIBILITY_USAGE_AUDIT_MARKER_V172,
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
        usage_records=usage_records,
    )


def write_markdown_report(path: Path, report: ListingViewsCompatibilityUsageReportV172) -> None:
    lines = [
        "# v172 Listing Views Compatibility Usage / Dependency Audit",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Facade-only state: `{report.is_facade_only}`",
        f"- Only approved compatibility re-exports remain: `{report.has_only_approved_reexports}`",
        f"- Wildcard imports present: `{not report.has_no_wildcard_imports}`",
        f"- Protected facade names: `{len(report.protected_names)}`",
        f"- Usage/dependency records found: `{len(report.usage_records)}`",
        f"- Names with detected compatibility usage: `{report.usage_dependency_names}`",
        f"- Names without detected usage: `{report.names_without_detected_usage}`",
        f"- Safe to remove any re-exports now: `{report.safe_to_remove_any_reexports_now}`",
        "",
        "## Helper compatibility names with detected usage",
        "",
    ]

    if report.helper_names_with_usage:
        for name in report.helper_names_with_usage:
            lines.append(f"- `{name}`")
    else:
        lines.append("No helper compatibility usage detected.")

    lines.extend(["", "## `*_views` compatibility names with detected usage", ""])

    if report.view_names_with_usage:
        for name in report.view_names_with_usage:
            lines.append(f"- `{name}`")
    else:
        lines.append("No `*_views` compatibility usage detected.")

    lines.extend(["", "## Usage records", ""])

    if report.usage_records:
        for record in report.usage_records:
            lines.append(
                f"- `{record.name}` — `{record.category}` — "
                f"`{record.relative_path}:{record.line_number}` — {record.evidence}"
            )
    else:
        lines.append("No compatibility usage records detected.")

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            "Do not remove helper compatibility re-exports or `*_views` re-export paths in v172.",
            "",
            "A later implementation checkpoint may remove a compatibility name only after this audit reports no source, test, template, URL configuration, or route dependency for that name.",
            "",
            "## Non-goals",
            "",
            "- Do not move runtime code in v172.",
            "- Do not remove helper compatibility re-exports in v172.",
            "- Do not remove `*_views` compatibility re-export paths in v172.",
            "- Do not change URLs, templates, permissions, models, migrations, or behavior.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_compatibility_usage_audit_v172.md"), report)


if __name__ == "__main__":
    main()
