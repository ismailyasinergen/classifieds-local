from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from listings import listing_views_targeted_removal_contract_v173 as contract_v173


LISTING_VIEWS_TARGETED_REEXPORT_REMOVAL_MARKER_V174 = "LISTING_VIEWS_TARGETED_REEXPORT_REMOVAL_V174"

V179_ALLOWED_LATER_FACADE_REMOVAL_NAMES_V174 = ("listing_feature_priority_update",)

TARGETED_REMOVED_FACADE_REEXPORT_NAMES_V174 = ('SidebarCategoriesMixin', '_safe_reporter_note')

TARGETED_REMOVED_FACADE_REEXPORT_SOURCE_MODULES_V174 = (('SidebarCategoriesMixin', 'listing_uncategorized_views'), ('_safe_reporter_note', 'listing_reports_views'))

BASELINE_PROTECTED_FACADE_NAMES_V173 = ('ListingCreateView',
 'ListingDeleteView',
 'ListingDetailView',
 'ListingListView',
 'ListingUpdateView',
 'SidebarCategoriesMixin',
 '_create_moderation_notice',
 '_safe_reporter_note',
 'active_approved_listings',
 'apply_listing_filters',
 'default_listing_expiry',
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
 'save_uploaded_listing_images',
 'saved_search_bulk_action',
 'saved_search_create',
 'saved_search_delete',
 'saved_search_list',
 'saved_search_notifications_toggle',
 'saved_search_rename',
 'validate_uploaded_images')

EXPECTED_REMAINING_PROTECTED_FACADE_NAMES_V174 = ('ListingCreateView',
 'ListingDeleteView',
 'ListingDetailView',
 'ListingListView',
 'ListingUpdateView',
 '_create_moderation_notice',
 'active_approved_listings',
 'apply_listing_filters',
 'default_listing_expiry',
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
 'save_uploaded_listing_images',
 'saved_search_bulk_action',
 'saved_search_create',
 'saved_search_delete',
 'saved_search_list',
 'saved_search_notifications_toggle',
 'saved_search_rename',
 'validate_uploaded_images')

EXPECTED_VIEW_REEXPORT_MODULES_V174 = ('listing_browse_detail_views',
 'listing_crud_uploads_views',
 'listing_favorite_views',
 'listing_promotion_views',
 'listing_reports_views',
 'listing_uncategorized_views',
 'saved_searches_views')

EXPECTED_HELPER_REEXPORT_NAMES_V174 = ('_create_moderation_notice',
 'active_approved_listings',
 'apply_listing_filters',
 'default_listing_expiry',
 'save_uploaded_listing_images',
 'validate_uploaded_images')


@dataclass(frozen=True)
class ListingViewsTargetedReexportRemovalReportV174:
    marker: str
    views_path: str
    views_total_lines: int
    view_reexport_modules: tuple[str, ...]
    view_reexport_names: tuple[str, ...]
    helper_reexport_names: tuple[str, ...]
    current_protected_names: tuple[str, ...]
    target_names_present_in_facade: tuple[str, ...]
    target_names_absent_from_facade: tuple[str, ...]
    missing_expected_remaining_names: tuple[str, ...]
    unexpected_remaining_names: tuple[str, ...]
    unexpected_import_modules: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]
    top_level_definition_names: tuple[str, ...]
    target_facade_dependency_count: int

    @property
    def removed_exactly_target_pair(self) -> bool:
        allowed_later_missing = set(V179_ALLOWED_LATER_FACADE_REMOVAL_NAMES_V174)
        return (
            not self.target_names_present_in_facade
            and set(self.missing_expected_remaining_names).issubset(allowed_later_missing)
            and not self.unexpected_remaining_names
        )
    @property
    def preserved_facade_only_state(self) -> bool:
        return not self.top_level_definition_names

    @property
    def preserved_import_hygiene(self) -> bool:
        return not self.unexpected_import_modules and not self.wildcard_import_modules

    @property
    def preserved_helper_reexports(self) -> bool:
        return self.helper_reexport_names == EXPECTED_HELPER_REEXPORT_NAMES_V174

    @property
    def has_no_target_facade_dependencies(self) -> bool:
        return self.target_facade_dependency_count == 0


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    for candidate in (repo_root / "backend", repo_root):
        if (candidate / "listings" / "views.py").exists():
            return candidate
    raise FileNotFoundError(f"Could not resolve app root containing listings/views.py from {repo_root}")


def _extract_inventory(views_path: Path):
    source = views_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    view_modules: set[str] = set()
    view_names: list[str] = []
    helper_names: list[str] = []
    unexpected_imports: set[str] = set()
    wildcard_modules: set[str] = set()
    local_defs: list[str] = []

    helper_modules = {
        "listing_filter_helpers",
        "listing_moderation_helpers",
        "listing_lifecycle_helpers",
        "listing_visibility_helpers",
        "listing_image_helpers",
    }

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            local_defs.append(node.name)

        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = tuple(alias.asname or alias.name for alias in node.names)

            if node.level == 1 and module.endswith("_views"):
                view_modules.add(module)
                view_names.extend(name for name in names if name != "*")
            elif node.level == 1 and module in helper_modules:
                helper_names.extend(name for name in names if name != "*")
            else:
                unexpected_imports.add(module)

            if any(alias.name == "*" for alias in node.names):
                wildcard_modules.add(module)

        elif isinstance(node, ast.Import):
            unexpected_imports.add(", ".join(alias.name for alias in node.names))

    return source, tuple(sorted(view_modules)), tuple(sorted(view_names)), tuple(sorted(helper_names)), tuple(sorted(unexpected_imports)), tuple(sorted(wildcard_modules)), tuple(sorted(local_defs))


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsTargetedReexportRemovalReportV174:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"

    (
        source,
        view_modules,
        view_names,
        helper_names,
        unexpected_imports,
        wildcard_modules,
        local_defs,
    ) = _extract_inventory(views_path)

    current_protected = tuple(sorted(set(view_names) | set(helper_names)))
    targets = set(TARGETED_REMOVED_FACADE_REEXPORT_NAMES_V174)
    expected_remaining = set(EXPECTED_REMAINING_PROTECTED_FACADE_NAMES_V174)

    contract_report = contract_v173.build_report(repo_root)

    return ListingViewsTargetedReexportRemovalReportV174(
        marker=LISTING_VIEWS_TARGETED_REEXPORT_REMOVAL_MARKER_V174,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(source.splitlines()),
        view_reexport_modules=view_modules,
        view_reexport_names=view_names,
        helper_reexport_names=helper_names,
        current_protected_names=current_protected,
        target_names_present_in_facade=tuple(sorted(targets & set(current_protected))),
        target_names_absent_from_facade=tuple(sorted(targets - set(current_protected))),
        missing_expected_remaining_names=tuple(sorted(expected_remaining - set(current_protected))),
        unexpected_remaining_names=tuple(sorted(set(current_protected) - expected_remaining)),
        unexpected_import_modules=unexpected_imports,
        wildcard_import_modules=wildcard_modules,
        top_level_definition_names=local_defs,
        target_facade_dependency_count=len(contract_report.target_facade_dependency_records),
    )


def write_markdown_report(path: Path, report: ListingViewsTargetedReexportRemovalReportV174) -> None:
    lines = [
        "# v174 Remove Two Unused Listing Views Facade Re-exports",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Removed exactly target pair: `{report.removed_exactly_target_pair}`",
        f"- Target names present in facade: `{report.target_names_present_in_facade}`",
        f"- Target names absent from facade: `{report.target_names_absent_from_facade}`",
        f"- Missing expected remaining names: `{tuple(name for name in report.missing_expected_remaining_names if name not in V179_ALLOWED_LATER_FACADE_REMOVAL_NAMES_V174)}`",
        f"- Unexpected remaining names: `{report.unexpected_remaining_names}`",
        f"- Facade-only state preserved: `{report.preserved_facade_only_state}`",
        f"- Import hygiene preserved: `{report.preserved_import_hygiene}`",
        f"- Helper compatibility re-exports preserved: `{report.preserved_helper_reexports}`",
        f"- Target facade dependency count: `{report.target_facade_dependency_count}`",
        "",
        "## Removed from `listings.views` only",
        "",
    ]

    for name in TARGETED_REMOVED_FACADE_REEXPORT_NAMES_V174:
        lines.append(f"- `{name}`")

    lines.extend(
        [
            "",
            "## Preserved source modules",
            "",
        ]
    )

    for name, module in TARGETED_REMOVED_FACADE_REEXPORT_SOURCE_MODULES_V174:
        lines.append(f"- `{name}` remains defined/exported by `{module}`")

    lines.extend(
        [
            "",
            "## Guardrails",
            "",
            "- No runtime implementation code was moved.",
            "- No URLs, templates, permissions, models, migrations, or behavior were intentionally changed.",
            "- Every non-target compatibility re-export remains protected except the later v179 targeted removal.",
            "- Route callback identity through the remaining facade exports remains protected.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_targeted_reexport_removal_v174.md"), report)


if __name__ == "__main__":
    main()
