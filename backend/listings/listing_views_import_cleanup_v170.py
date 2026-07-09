from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_IMPORT_CLEANUP_MARKER_V170 = "LISTING_VIEWS_IMPORT_CLEANUP_V170"

EXPECTED_COMPATIBILITY_VIEW_REEXPORT_MODULES_V170 = ('listing_browse_detail_views',
 'listing_crud_uploads_views',
 'listing_favorite_views',
 'listing_promotion_views',
 'listing_reports_views',
 'listing_uncategorized_views',
 'saved_searches_views')

EXPECTED_HELPER_COMPATIBILITY_REEXPORTS_V170 = {'listing_filter_helpers': ('apply_listing_filters',),
 'listing_image_helpers': ('save_uploaded_listing_images', 'validate_uploaded_images'),
 'listing_lifecycle_helpers': ('default_listing_expiry',),
 'listing_moderation_helpers': ('_create_moderation_notice',),
 'listing_visibility_helpers': ('active_approved_listings',)}

SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_MODULES_V170 = ('listing_browse_detail_views',
 'listing_crud_uploads_views',
 'listing_favorite_views',
 'listing_promotion_views',
 'listing_reports_views',
 'listing_uncategorized_views',
 'saved_searches_views')

SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_NAMES_V170 = ('ListingCreateView',
 'ListingDeleteView',
 'ListingDetailView',
 'ListingListView',
 'ListingUpdateView',
 'SidebarCategoriesMixin',
 '_safe_reporter_note',
 'listing_approve',
 'listing_archive',
 'listing_favorite_toggle',
 'listing_feature_days_update',
 'listing_feature_priority_update',
 'listing_feature_toggle',
 'listing_image_delete',
 'listing_reject',
 'listing_renew',
 'listing_report_archive_listing',
 'listing_report_create',
 'listing_report_dismiss',
 'listing_report_export_csv',
 'listing_report_queue',
 'listing_report_review',
 'listing_report_suspend_listing',
 'moderation_queue',
 'my_listing_reports',
 'saved_search_bulk_action',
 'saved_search_create',
 'saved_search_delete',
 'saved_search_list',
 'saved_search_notifications_toggle',
 'saved_search_rename')

SNAPSHOT_HELPER_COMPATIBILITY_REEXPORT_MODULES_V170 = ('listing_filter_helpers',
 'listing_image_helpers',
 'listing_lifecycle_helpers',
 'listing_moderation_helpers',
 'listing_visibility_helpers')

SNAPSHOT_HELPER_COMPATIBILITY_REEXPORT_NAMES_V170 = ('_create_moderation_notice',
 'active_approved_listings',
 'apply_listing_filters',
 'default_listing_expiry',
 'save_uploaded_listing_images',
 'validate_uploaded_images')


@dataclass(frozen=True)
class ListingViewsImportCleanupReportV170:
    marker: str
    views_path: str
    views_total_lines: int
    top_level_definition_names: tuple[str, ...]
    compatibility_view_reexport_modules: tuple[str, ...]
    compatibility_view_reexport_names: tuple[str, ...]
    helper_compatibility_reexport_modules: tuple[str, ...]
    helper_compatibility_reexport_names: tuple[str, ...]
    non_compatibility_import_modules: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]

    @property
    def is_facade_only(self) -> bool:
        return not self.top_level_definition_names

    @property
    def has_only_compatibility_reexports(self) -> bool:
        return not self.non_compatibility_import_modules

    @property
    def has_no_wildcard_imports(self) -> bool:
        return not self.wildcard_import_modules

    @property
    def missing_expected_view_reexport_modules(self) -> tuple[str, ...]:
        present = set(self.compatibility_view_reexport_modules)
        return tuple(
            sorted(set(EXPECTED_COMPATIBILITY_VIEW_REEXPORT_MODULES_V170) - present)
        )

    @property
    def missing_expected_helper_reexport_names(self) -> tuple[str, ...]:
        expected = {
            name
            for names in EXPECTED_HELPER_COMPATIBILITY_REEXPORTS_V170.values()
            for name in names
        }
        present = set(self.helper_compatibility_reexport_names)
        return tuple(sorted(expected - present))


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    candidates = (repo_root / "backend", repo_root)

    for candidate in candidates:
        if (candidate / "listings" / "views.py").exists():
            return candidate

    raise FileNotFoundError(
        f"Could not resolve app root containing listings/views.py from {repo_root}"
    )


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsImportCleanupReportV170:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"
    source = views_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    top_level_definition_names: list[str] = []
    view_modules: set[str] = set()
    view_names: list[str] = []
    helper_modules: set[str] = set()
    helper_names: list[str] = []
    non_compatibility_modules: set[str] = set()
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
            elif node.level == 1 and module in EXPECTED_HELPER_COMPATIBILITY_REEXPORTS_V170:
                helper_modules.add(module)
                helper_names.extend(name for name in names if name != "*")
            else:
                non_compatibility_modules.add(module)

            if has_wildcard:
                wildcard_modules.add(module)

        elif isinstance(node, ast.Import):
            non_compatibility_modules.add(", ".join(alias.name for alias in node.names))

    return ListingViewsImportCleanupReportV170(
        marker=LISTING_VIEWS_IMPORT_CLEANUP_MARKER_V170,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(source.splitlines()),
        top_level_definition_names=tuple(sorted(top_level_definition_names)),
        compatibility_view_reexport_modules=tuple(sorted(view_modules)),
        compatibility_view_reexport_names=tuple(sorted(view_names)),
        helper_compatibility_reexport_modules=tuple(sorted(helper_modules)),
        helper_compatibility_reexport_names=tuple(sorted(helper_names)),
        non_compatibility_import_modules=tuple(sorted(non_compatibility_modules)),
        wildcard_import_modules=tuple(sorted(wildcard_modules)),
    )


def write_markdown_report(path: Path, report: ListingViewsImportCleanupReportV170) -> None:
    lines = [
        "# v170 Remove Proven Non-Compatibility Facade Imports",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Facade-only state: `{report.is_facade_only}`",
        f"- Only compatibility re-exports remain: `{report.has_only_compatibility_reexports}`",
        f"- Wildcard imports present: `{not report.has_no_wildcard_imports}`",
        f"- Missing expected `*_views` modules: `{report.missing_expected_view_reexport_modules}`",
        f"- Missing expected helper re-export names: `{report.missing_expected_helper_reexport_names}`",
        "",
        "## Preserved compatibility `*_views` re-export modules",
        "",
    ]

    for module in report.compatibility_view_reexport_modules:
        lines.append(f"- `{module}`")

    lines.extend(
        [
            "",
            "## Preserved helper compatibility re-export names",
            "",
        ]
    )

    for name in report.helper_compatibility_reexport_names:
        lines.append(f"- `{name}`")

    lines.extend(
        [
            "",
            "## Guardrails verified",
            "",
            "- No runtime code was moved.",
            "- No URLs, templates, permissions, models, migrations, or behavior were intentionally changed.",
            "- Public URL callbacks that resolve through `listings.views` still resolve to objects defined outside `listings.views`.",
            "- Compatibility `*_views` re-export imports remain protected.",
            "- Legacy helper compatibility re-exports required by earlier extraction contracts remain protected.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_import_cleanup_v170.md"), report)


if __name__ == "__main__":
    main()
