from __future__ import annotations

import ast
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_IMPORT_CLEANUP_CONTRACT_MARKER_V169 = "LISTING_VIEWS_IMPORT_CLEANUP_CONTRACT_V169"

EXPECTED_COMPATIBILITY_VIEW_REEXPORT_MODULES_V169 = ('listing_crud_uploads_views', 'listing_reports_views', 'saved_searches_views')

SNAPSHOT_IMPORT_RECORDS_V169 = ({'bound_names': ('timedelta',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 1,
  'module': 'datetime',
  'original_names': ('timedelta',)},
 {'bound_names': ('Decimal', 'InvalidOperation'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 2,
  'module': 'decimal',
  'original_names': ('Decimal', 'InvalidOperation')},
 {'bound_names': ('Path',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 3,
  'module': 'pathlib',
  'original_names': ('Path',)},
 {'bound_names': ('messages',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 5,
  'module': 'django.contrib',
  'original_names': ('messages',)},
 {'bound_names': ('staff_member_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 6,
  'module': 'django.contrib.admin.views.decorators',
  'original_names': ('staff_member_required',)},
 {'bound_names': ('login_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 7,
  'module': 'django.contrib.auth.decorators',
  'original_names': ('login_required',)},
 {'bound_names': ('LoginRequiredMixin', 'UserPassesTestMixin'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 8,
  'module': 'django.contrib.auth.mixins',
  'original_names': ('LoginRequiredMixin', 'UserPassesTestMixin')},
 {'bound_names': ('Q',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 9,
  'module': 'django.db.models',
  'original_names': ('Q',)},
 {'bound_names': ('get_object_or_404', 'redirect', 'render'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 10,
  'module': 'django.shortcuts',
  'original_names': ('get_object_or_404', 'redirect', 'render')},
 {'bound_names': ('reverse_lazy',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 11,
  'module': 'django.urls',
  'original_names': ('reverse_lazy',)},
 {'bound_names': ('timezone',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 12,
  'module': 'django.utils',
  'original_names': ('timezone',)},
 {'bound_names': ('require_POST',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 13,
  'module': 'django.views.decorators.http',
  'original_names': ('require_POST',)},
 {'bound_names': ('CreateView', 'DeleteView', 'DetailView', 'ListView', 'UpdateView'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 14,
  'module': 'django.views.generic',
  'original_names': ('CreateView', 'DeleteView', 'DetailView', 'ListView', 'UpdateView')},
 {'bound_names': ('SellerStore',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 16,
  'module': 'accounts.models',
  'original_names': ('SellerStore',)},
 {'bound_names': ('Category',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 17,
  'module': 'categories.models',
  'original_names': ('Category',)},
 {'bound_names': ('ListingForm',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 19,
  'module': 'forms',
  'original_names': ('ListingForm',)},
 {'bound_names': ('Listing', 'ListingFavorite', 'ListingImage'),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 20,
  'module': 'models',
  'original_names': ('Listing', 'ListingFavorite', 'ListingImage')},
 {'bound_names': ('SidebarCategoriesMixin',
                  'ListingListView',
                  'listing_approve',
                  'listing_reject',
                  'listing_archive',
                  'listing_renew',
                  'listing_feature_toggle'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 22,
  'module': 'listing_uncategorized_views',
  'original_names': ('SidebarCategoriesMixin',
                     'ListingListView',
                     'listing_approve',
                     'listing_reject',
                     'listing_archive',
                     'listing_renew',
                     'listing_feature_toggle')},
 {'bound_names': ('ListingCreateView',
                  'ListingUpdateView',
                  'ListingDeleteView',
                  'listing_image_delete',
                  'listing_feature_days_update'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 32,
  'module': 'listing_crud_uploads_views',
  'original_names': ('ListingCreateView',
                     'ListingUpdateView',
                     'ListingDeleteView',
                     'listing_image_delete',
                     'listing_feature_days_update')},
 {'bound_names': ('moderation_queue',
                  'listing_report_create',
                  'listing_report_queue',
                  'listing_report_export_csv',
                  'my_listing_reports',
                  '_safe_reporter_note',
                  'listing_report_review',
                  'listing_report_dismiss',
                  'listing_report_suspend_listing',
                  'listing_report_archive_listing'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 61,
  'module': 'listing_reports_views',
  'original_names': ('moderation_queue',
                     'listing_report_create',
                     'listing_report_queue',
                     'listing_report_export_csv',
                     'my_listing_reports',
                     '_safe_reporter_note',
                     'listing_report_review',
                     'listing_report_dismiss',
                     'listing_report_suspend_listing',
                     'listing_report_archive_listing')},
 {'bound_names': ('listing_feature_priority_update',),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 77,
  'module': 'listing_promotion_views',
  'original_names': ('listing_feature_priority_update',)},
 {'bound_names': ('messages',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 105,
  'module': 'django.contrib',
  'original_names': ('messages',)},
 {'bound_names': ('staff_member_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 106,
  'module': 'django.contrib.admin.views.decorators',
  'original_names': ('staff_member_required',)},
 {'bound_names': ('login_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 107,
  'module': 'django.contrib.auth.decorators',
  'original_names': ('login_required',)},
 {'bound_names': ('Q',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 108,
  'module': 'django.db.models',
  'original_names': ('Q',)},
 {'bound_names': ('HttpResponse',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 109,
  'module': 'django.http',
  'original_names': ('HttpResponse',)},
 {'bound_names': ('get_object_or_404', 'redirect', 'render'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 110,
  'module': 'django.shortcuts',
  'original_names': ('get_object_or_404', 'redirect', 'render')},
 {'bound_names': ('require_POST',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 111,
  'module': 'django.views.decorators.http',
  'original_names': ('require_POST',)},
 {'bound_names': ('staff_member_required',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 150,
  'module': 'django.contrib.admin.views.decorators',
  'original_names': ('staff_member_required',)},
 {'bound_names': ('messages',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 151,
  'module': 'django.contrib',
  'original_names': ('messages',)},
 {'bound_names': ('get_object_or_404', 'redirect'),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 152,
  'module': 'django.shortcuts',
  'original_names': ('get_object_or_404', 'redirect')},
 {'bound_names': ('require_POST',),
  'category': 'absolute_import',
  'has_wildcard': False,
  'level': 0,
  'line': 153,
  'module': 'django.views.decorators.http',
  'original_names': ('require_POST',)},
 {'bound_names': ('apply_listing_filters',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 154,
  'module': 'listing_filter_helpers',
  'original_names': ('apply_listing_filters',)},
 {'bound_names': ('_create_moderation_notice',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 155,
  'module': 'listing_moderation_helpers',
  'original_names': ('_create_moderation_notice',)},
 {'bound_names': ('default_listing_expiry',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 156,
  'module': 'listing_lifecycle_helpers',
  'original_names': ('default_listing_expiry',)},
 {'bound_names': ('active_approved_listings',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 157,
  'module': 'listing_visibility_helpers',
  'original_names': ('active_approved_listings',)},
 {'bound_names': ('save_uploaded_listing_images',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 158,
  'module': 'listing_image_helpers',
  'original_names': ('save_uploaded_listing_images',)},
 {'bound_names': ('validate_uploaded_images',),
  'category': 'relative_non_view_import',
  'has_wildcard': False,
  'level': 1,
  'line': 159,
  'module': 'listing_image_helpers',
  'original_names': ('validate_uploaded_images',)},
 {'bound_names': ('listing_favorite_toggle',),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 160,
  'module': 'listing_favorite_views',
  'original_names': ('listing_favorite_toggle',)},
 {'bound_names': ('ListingDetailView',),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 161,
  'module': 'listing_browse_detail_views',
  'original_names': ('ListingDetailView',)},
 {'bound_names': ('saved_search_create',
                  'saved_search_list',
                  'saved_search_notifications_toggle',
                  'saved_search_delete',
                  'saved_search_bulk_action',
                  'saved_search_rename'),
  'category': 'compatibility_view_reexport',
  'has_wildcard': False,
  'level': 1,
  'line': 180,
  'module': 'saved_searches_views',
  'original_names': ('saved_search_create',
                     'saved_search_list',
                     'saved_search_notifications_toggle',
                     'saved_search_delete',
                     'saved_search_bulk_action',
                     'saved_search_rename')})

SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_MODULES_V169 = ('listing_browse_detail_views',
 'listing_crud_uploads_views',
 'listing_favorite_views',
 'listing_promotion_views',
 'listing_reports_views',
 'listing_uncategorized_views',
 'saved_searches_views')

SNAPSHOT_COMPATIBILITY_VIEW_REEXPORT_NAMES_V169 = ('ListingCreateView',
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

SNAPSHOT_NON_VIEW_IMPORT_MODULES_V169 = ('accounts.models',
 'categories.models',
 'datetime',
 'decimal',
 'django.contrib',
 'django.contrib.admin.views.decorators',
 'django.contrib.auth.decorators',
 'django.contrib.auth.mixins',
 'django.db.models',
 'django.http',
 'django.shortcuts',
 'django.urls',
 'django.utils',
 'django.views.decorators.http',
 'django.views.generic',
 'forms',
 'listing_filter_helpers',
 'listing_image_helpers',
 'listing_lifecycle_helpers',
 'listing_moderation_helpers',
 'listing_visibility_helpers',
 'models',
 'pathlib')

SNAPSHOT_NON_VIEW_IMPORT_BOUND_NAMES_V169 = ('Category',
 'CreateView',
 'Decimal',
 'DeleteView',
 'DetailView',
 'HttpResponse',
 'InvalidOperation',
 'ListView',
 'Listing',
 'ListingFavorite',
 'ListingForm',
 'ListingImage',
 'LoginRequiredMixin',
 'Path',
 'Q',
 'Q',
 'SellerStore',
 'UpdateView',
 'UserPassesTestMixin',
 '_create_moderation_notice',
 'active_approved_listings',
 'apply_listing_filters',
 'default_listing_expiry',
 'get_object_or_404',
 'get_object_or_404',
 'get_object_or_404',
 'login_required',
 'login_required',
 'messages',
 'messages',
 'messages',
 'redirect',
 'redirect',
 'redirect',
 'render',
 'render',
 'require_POST',
 'require_POST',
 'require_POST',
 'reverse_lazy',
 'save_uploaded_listing_images',
 'staff_member_required',
 'staff_member_required',
 'staff_member_required',
 'timedelta',
 'timezone',
 'validate_uploaded_images')

SNAPSHOT_DUPLICATE_BOUND_NAMES_V169 = ('Q', 'get_object_or_404', 'login_required', 'messages', 'redirect', 'render', 'require_POST', 'staff_member_required')

SNAPSHOT_WILDCARD_IMPORT_MODULES_V169 = ()


@dataclass(frozen=True)
class ListingViewsImportCleanupContractReportV169:
    marker: str
    views_path: str
    views_total_lines: int
    top_level_function_names: tuple[str, ...]
    top_level_class_names: tuple[str, ...]
    import_records: tuple[dict, ...]
    compatibility_view_reexport_modules: tuple[str, ...]
    compatibility_view_reexport_names: tuple[str, ...]
    non_view_import_modules: tuple[str, ...]
    non_view_import_bound_names: tuple[str, ...]
    duplicate_bound_names: tuple[str, ...]
    wildcard_import_modules: tuple[str, ...]

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
        present = set(self.compatibility_view_reexport_modules)
        return tuple(
            sorted(set(EXPECTED_COMPATIBILITY_VIEW_REEXPORT_MODULES_V169) - present)
        )


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    candidates = (repo_root / "backend", repo_root)

    for candidate in candidates:
        if (candidate / "listings" / "views.py").exists():
            return candidate

    raise FileNotFoundError(
        f"Could not resolve app root containing listings/views.py from {repo_root}"
    )


def _classify_import(module: str, level: int) -> str:
    if level == 1 and module.endswith("_views"):
        return "compatibility_view_reexport"
    if level > 0:
        return "relative_non_view_import"
    return "absolute_import"


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


def _import_records(source: str) -> tuple[dict, ...]:
    tree = ast.parse(source)
    records: list[dict] = []

    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            original_names = tuple(alias.name for alias in node.names)
            bound_names = tuple(alias.asname or alias.name for alias in node.names)

            records.append(
                {
                    "line": node.lineno,
                    "module": module,
                    "level": node.level,
                    "original_names": original_names,
                    "bound_names": bound_names,
                    "category": _classify_import(module, node.level),
                    "has_wildcard": any(name == "*" for name in original_names),
                }
            )

        elif isinstance(node, ast.Import):
            original_names = tuple(alias.name for alias in node.names)
            bound_names = tuple(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)

            records.append(
                {
                    "line": node.lineno,
                    "module": ", ".join(original_names),
                    "level": 0,
                    "original_names": original_names,
                    "bound_names": bound_names,
                    "category": "absolute_import",
                    "has_wildcard": False,
                }
            )

    return tuple(records)


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsImportCleanupContractReportV169:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"
    source = views_path.read_text(encoding="utf-8")

    function_names, class_names = _top_level_definitions(source)
    records = _import_records(source)

    compatibility_records = tuple(
        record for record in records if record["category"] == "compatibility_view_reexport"
    )
    non_view_records = tuple(
        record for record in records if record["category"] != "compatibility_view_reexport"
    )

    compatibility_modules = tuple(
        sorted({record["module"] for record in compatibility_records})
    )
    compatibility_names = tuple(
        sorted(
            name
            for record in compatibility_records
            for name in record["bound_names"]
            if name != "*"
        )
    )
    non_view_modules = tuple(
        sorted({record["module"] for record in non_view_records})
    )
    non_view_names = tuple(
        sorted(
            name
            for record in non_view_records
            for name in record["bound_names"]
            if name != "*"
        )
    )
    wildcard_modules = tuple(
        sorted({record["module"] for record in records if record["has_wildcard"]})
    )

    bound_name_counts = Counter(
        name
        for record in records
        for name in record["bound_names"]
        if name != "*"
    )
    duplicate_names = tuple(
        sorted(name for name, count in bound_name_counts.items() if count > 1)
    )

    return ListingViewsImportCleanupContractReportV169(
        marker=LISTING_VIEWS_IMPORT_CLEANUP_CONTRACT_MARKER_V169,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(source.splitlines()),
        top_level_function_names=function_names,
        top_level_class_names=class_names,
        import_records=records,
        compatibility_view_reexport_modules=compatibility_modules,
        compatibility_view_reexport_names=compatibility_names,
        non_view_import_modules=non_view_modules,
        non_view_import_bound_names=non_view_names,
        duplicate_bound_names=duplicate_names,
        wildcard_import_modules=wildcard_modules,
    )


def write_markdown_report(path: Path, report: ListingViewsImportCleanupContractReportV169) -> None:
    lines = [
        "# v169 Listing Views Import Cleanup Contract",
        "",
        report.marker,
        "",
        "## Purpose",
        "",
        "This is a contract checkpoint before any imports are removed from `listings/views.py`.",
        "",
        "v169 does not move runtime code and does not remove imports.",
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
        "## Compatibility view re-export modules protected",
        "",
    ]

    for module in report.compatibility_view_reexport_modules:
        lines.append(f"- `{module}`")

    lines.extend(
        [
            "",
            "## Compatibility view re-export names protected",
            "",
        ]
    )

    for name in report.compatibility_view_reexport_names:
        lines.append(f"- `{name}`")

    lines.extend(
        [
            "",
            "## Non-view import modules captured as cleanup candidates",
            "",
        ]
    )

    if report.non_view_import_modules:
        for module in report.non_view_import_modules:
            lines.append(f"- `{module}`")
    else:
        lines.append("No non-view import modules detected.")

    lines.extend(
        [
            "",
            "## Non-view bound names captured as cleanup candidates",
            "",
        ]
    )

    if report.non_view_import_bound_names:
        for name in report.non_view_import_bound_names:
            lines.append(f"- `{name}`")
    else:
        lines.append("No non-view bound names detected.")

    lines.extend(
        [
            "",
            "## Cleanup guardrails",
            "",
            "- Do not remove imports in v169.",
            "- Do not move runtime code in v169.",
            "- Do not change URLs, templates, permissions, models, migrations, or behavior.",
            "- Before removing non-view imports, create a cleanup implementation checkpoint that preserves all public URL callback identities.",
            "- Keep `listings.views` compatibility re-exports unless a later contract explicitly proves they are safe to remove.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(
        Path("docs/listing_views_import_cleanup_contract_v169.md"),
        report,
    )


if __name__ == "__main__":
    main()
