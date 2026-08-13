
import ast
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path



LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_MARKER_V179 = (
    "LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_V179"
)

REMOVED_FACADE_REEXPORT_NAME_V179 = "listing_feature_priority_update"
SOURCE_MODULE_V179 = "listing_promotion_views"
DEDICATED_IMPORT_V179 = (
    "from listings.listing_promotion_views import listing_feature_priority_update"
)


@dataclass(frozen=True)
class ListingFeaturePriorityReexportRemovalReportV179:
    marker: str
    removed_name: str
    source_module: str
    dedicated_import: str
    views_path: str
    views_total_lines: int
    removed_from_facade_source: bool
    absent_from_runtime_facade: bool
    source_module_still_defines_name: bool
    urls_use_dedicated_import: bool
    urls_avoid_facade_import_for_target: bool
    v175_candidate_names: tuple[str, ...]
    v176_names_without_migration_records: tuple[str, ...]
    v177_target_group_migrated: bool
    v178_contract_satisfied_by_v179: bool

    @property
    def removal_complete(self) -> bool:
        return (
            self.removed_from_facade_source
            and self.absent_from_runtime_facade
            and self.source_module_still_defines_name
            and self.urls_use_dedicated_import
            and self.urls_avoid_facade_import_for_target
            and self.v175_candidate_names == ()
            and self.v176_names_without_migration_records == ()
            and self.v177_target_group_migrated
            and self.v178_contract_satisfied_by_v179
        )


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    for candidate in (repo_root / "backend", repo_root):
        if (candidate / "listings" / "views.py").exists():
            return candidate
    raise FileNotFoundError(f"Could not resolve app root containing listings/views.py from {repo_root}")


def _module_imports_name_from_relative_module(path: Path, module_name: str, name: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))

    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level == 1 and node.module == module_name:
            for alias in node.names:
                if (alias.asname or alias.name) == name:
                    return True

    return False


def build_report(repo_root: Path | str = Path(".")) -> ListingFeaturePriorityReexportRemovalReportV179:
    repo_root = Path(repo_root)
    app_root = _resolve_app_root(repo_root)

    views_path = app_root / "listings" / "views.py"
    urls_path = app_root / "listings" / "urls.py"

    views_text = views_path.read_text(encoding="utf-8")
    urls_text = urls_path.read_text(encoding="utf-8")

    runtime_facade = import_module("listings.views")
    listing_promotion_views = import_module("listings.listing_promotion_views")
    surface_v175 = import_module("listings.listing_views_remaining_facade_surface_audit_v175")
    audit_v176 = import_module("listings.listing_views_direct_import_migration_audit_v176")
    migration_v177 = import_module("listings.listing_views_direct_import_migration_v177")
    contract_v178 = import_module("listings.listing_feature_priority_reexport_removal_contract_v178")

    v175_report = surface_v175.build_report(repo_root)
    v176_report = audit_v176.build_report(repo_root)
    v177_report = migration_v177.build_report(repo_root)
    v178_report = contract_v178.build_report(repo_root)

    return ListingFeaturePriorityReexportRemovalReportV179(
        marker=LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_MARKER_V179,
        removed_name=REMOVED_FACADE_REEXPORT_NAME_V179,
        source_module=SOURCE_MODULE_V179,
        dedicated_import=DEDICATED_IMPORT_V179,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(views_text.splitlines()),
        removed_from_facade_source=not _module_imports_name_from_relative_module(
            views_path,
            SOURCE_MODULE_V179,
            REMOVED_FACADE_REEXPORT_NAME_V179,
        ),
        absent_from_runtime_facade=not hasattr(runtime_facade, REMOVED_FACADE_REEXPORT_NAME_V179),
        source_module_still_defines_name=hasattr(
            listing_promotion_views,
            REMOVED_FACADE_REEXPORT_NAME_V179,
        ),
        urls_use_dedicated_import=DEDICATED_IMPORT_V179 in urls_text,
        urls_avoid_facade_import_for_target=(
            f"from .views import {REMOVED_FACADE_REEXPORT_NAME_V179}" not in urls_text
            and f"from listings.views import {REMOVED_FACADE_REEXPORT_NAME_V179}" not in urls_text
        ),
        v175_candidate_names=v175_report.candidate_names,
        v176_names_without_migration_records=v176_report.names_without_migration_records,
        v177_target_group_migrated=v177_report.target_group_migrated,
        v178_contract_satisfied_by_v179=v178_report.contract_satisfied_by_v179,
    )


def write_markdown_report(path: Path, report: ListingFeaturePriorityReexportRemovalReportV179) -> None:
    lines = [
        "# v179 Listing Feature Priority Facade Re-export Removal",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Removed facade re-export: `{report.removed_name}`",
        f"- Source module kept: `{report.source_module}`",
        f"- Dedicated import retained: `{report.dedicated_import}`",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Removed from facade source: `{report.removed_from_facade_source}`",
        f"- Absent from runtime facade: `{report.absent_from_runtime_facade}`",
        f"- Source module still defines name: `{report.source_module_still_defines_name}`",
        f"- URLs use dedicated import: `{report.urls_use_dedicated_import}`",
        f"- URLs avoid facade import for target: `{report.urls_avoid_facade_import_for_target}`",
        f"- v175 candidate names after v179: `{report.v175_candidate_names}`",
        f"- v176 names without migration records after v179: `{report.v176_names_without_migration_records}`",
        f"- v177 target group migrated: `{report.v177_target_group_migrated}`",
        f"- v178 contract satisfied by v179: `{report.v178_contract_satisfied_by_v179}`",
        f"- Removal complete: `{report.removal_complete}`",
        "",
        "## Guardrails",
        "",
        "- v179 removes only `listing_feature_priority_update` from `backend/listings/views.py`.",
        "- v179 keeps `backend/listings/listing_promotion_views.py` intact.",
        "- v179 keeps `backend/listings/urls.py` intact.",
        "- v179 does not remove any other facade re-export.",
        "",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(
        Path("docs/listing_feature_priority_reexport_removal_v179.md"),
        report,
    )


if __name__ == "__main__":
    main()
