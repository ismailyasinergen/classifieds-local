from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_FACADE_CONSOLIDATION_AUDIT_MARKER_V171 = "LISTING_VIEWS_FACADE_CONSOLIDATION_AUDIT_V171"

EXPECTED_VIEW_REEXPORT_MODULES_V171 = (
    "listing_browse_detail_views",
    "listing_crud_uploads_views",
    "listing_favorite_views",
    "listing_reports_views",
    "listing_uncategorized_views",
    "saved_searches_views",
)

EXPECTED_HELPER_REEXPORTS_V171 = {
    "listing_filter_helpers": ("apply_listing_filters",),
    "listing_moderation_helpers": ("_create_moderation_notice",),
    "listing_lifecycle_helpers": ("default_listing_expiry",),
    "listing_visibility_helpers": ("active_approved_listings",),
    "listing_image_helpers": ("save_uploaded_listing_images", "validate_uploaded_images"),
}


@dataclass(frozen=True)
class ListingViewsFacadeConsolidationReportV171:
    marker: str
    views_path: str
    views_total_lines: int
    top_level_definition_names: tuple[str, ...]
    view_reexport_modules: tuple[str, ...]
    view_reexport_names: tuple[str, ...]
    helper_reexport_modules: tuple[str, ...]
    helper_reexport_names: tuple[str, ...]
    unexpected_import_modules: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]

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
        return tuple(sorted(set(EXPECTED_VIEW_REEXPORT_MODULES_V171) - set(self.view_reexport_modules)))

    @property
    def missing_helper_reexport_names(self) -> tuple[str, ...]:
        expected = {
            name
            for names in EXPECTED_HELPER_REEXPORTS_V171.values()
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


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsFacadeConsolidationReportV171:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"
    source = views_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    top_level_definition_names: list[str] = []
    view_modules: set[str] = set()
    view_names: list[str] = []
    helper_modules: set[str] = set()
    helper_names: list[str] = []
    unexpected_modules: set[str] = set()
    wildcard_modules: set[str] = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top_level_definition_names.append(node.name)

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = tuple(alias.asname or alias.name for alias in node.names)
            has_wildcard = any(alias.name == "*" for alias in node.names)

            if node.level == 1 and module.endswith("_views"):
                view_modules.add(module)
                view_names.extend(name for name in names if name != "*")
            elif node.level == 1 and module in EXPECTED_HELPER_REEXPORTS_V171:
                helper_modules.add(module)
                helper_names.extend(name for name in names if name != "*")
            else:
                unexpected_modules.add(module)

            if has_wildcard:
                wildcard_modules.add(module)

        elif isinstance(node, ast.Import):
            unexpected_modules.add(", ".join(alias.name for alias in node.names))

    return ListingViewsFacadeConsolidationReportV171(
        marker=LISTING_VIEWS_FACADE_CONSOLIDATION_AUDIT_MARKER_V171,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(source.splitlines()),
        top_level_definition_names=tuple(sorted(top_level_definition_names)),
        view_reexport_modules=tuple(sorted(view_modules)),
        view_reexport_names=tuple(sorted(view_names)),
        helper_reexport_modules=tuple(sorted(helper_modules)),
        helper_reexport_names=tuple(sorted(helper_names)),
        unexpected_import_modules=tuple(sorted(unexpected_modules)),
        wildcard_import_modules=tuple(sorted(wildcard_modules)),
    )


def write_markdown_report(path: Path, report: ListingViewsFacadeConsolidationReportV171) -> None:
    lines = [
        "# v171 Listing Views Facade Consolidation Audit",
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
        f"- Missing `*_views` re-export modules: `{report.missing_view_reexport_modules}`",
        f"- Missing helper re-export names: `{report.missing_helper_reexport_names}`",
        "",
        "## Protected `*_views` compatibility modules",
        "",
    ]

    for module in report.view_reexport_modules:
        lines.append(f"- `{module}`")

    lines.extend(["", "## Protected helper compatibility re-export names", ""])

    for name in report.helper_reexport_names:
        lines.append(f"- `{name}`")

    lines.extend(
        [
            "",
            "## Consolidation recommendation",
            "",
            "Do not remove helper compatibility re-exports or `*_views` re-export paths yet.",
            "",
            "A future checkpoint must first prove that no tests, URL configuration, templates, or external compatibility paths still import these names from `listings.views`.",
            "",
            "## Non-goals",
            "",
            "- Do not move runtime code in v171.",
            "- Do not remove helper compatibility re-exports in v171.",
            "- Do not remove `*_views` compatibility re-export paths in v171.",
            "- Do not change URLs, templates, permissions, models, migrations, or behavior.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_facade_consolidation_audit_v171.md"), report)


if __name__ == "__main__":
    main()
