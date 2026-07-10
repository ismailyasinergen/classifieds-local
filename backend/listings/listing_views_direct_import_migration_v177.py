from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from listings import listing_views_direct_import_migration_audit_v176 as audit_v176
from listings import listing_views_remaining_facade_surface_audit_v175 as surface_v175


LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_MARKER_V177 = "LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_V177"

MIGRATED_SOURCE_MODULE_V177 = 'listing_promotion_views'
MIGRATED_NAMES_V177 = ('listing_feature_priority_update',)
REMOVED_IN_V179_FACADE_REEXPORT_NAMES_V177 = ('listing_feature_priority_update',)
MIGRATED_RELATIVE_PATH_V177 = 'listings/urls.py'
MIGRATED_USAGE_FORM_V177 = 'direct_from_listings_views_import'
def _resolve_app_root_v177(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    for candidate in (repo_root / "backend", repo_root):
        if (candidate / "listings" / "views.py").exists():
            return candidate
    raise FileNotFoundError(f"Could not resolve app root containing listings/views.py from {repo_root}")


def resolve_migrated_file_path(repo_root: Path | str = Path(".")) -> Path:
    app_root = _resolve_app_root_v177(Path(repo_root))
    return app_root / MIGRATED_RELATIVE_PATH_V177


def resolve_views_file_path(repo_root: Path | str = Path(".")) -> Path:
    app_root = _resolve_app_root_v177(Path(repo_root))
    return app_root / "listings" / "views.py"


MIGRATED_IMPORT_V177 = 'from listings.listing_promotion_views import listing_feature_priority_update'


@dataclass(frozen=True)
class ListingViewsDirectImportMigrationReportV177:
    marker: str
    migrated_source_module: str
    migrated_names: tuple[str, ...]
    migrated_relative_path: str
    migrated_usage_form: str
    migrated_import: str
    views_path: str
    views_total_lines: int
    remaining_target_migration_records: int
    names_without_migration_records: tuple[str, ...]
    v175_candidate_names: tuple[str, ...]
    target_removed_from_facade: bool
    v176_safe_to_change_imports: bool

    @property
    def target_group_migrated(self) -> bool:
        missing_or_removed = (
            set(self.migrated_names).issubset(set(self.names_without_migration_records))
            or self.target_removed_from_facade
        )
        candidate_or_removed = (
            set(self.migrated_names).issubset(set(self.v175_candidate_names))
            or self.target_removed_from_facade
        )
        return (
            self.remaining_target_migration_records == 0
            and missing_or_removed
            and candidate_or_removed
        )

    @property
    def safe_to_remove_facade_reexport_in_v177(self) -> bool:
        return False


def build_report(repo_root: Path | str = Path(".")) -> ListingViewsDirectImportMigrationReportV177:
    repo_root = Path(repo_root)
    v176_report = audit_v176.build_report(repo_root)
    v175_report = surface_v175.build_report(repo_root)

    target_records = tuple(
        record
        for record in v176_report.migration_records
        if record.source_module == MIGRATED_SOURCE_MODULE_V177
        and record.name in MIGRATED_NAMES_V177
    )

    return ListingViewsDirectImportMigrationReportV177(
        marker=LISTING_VIEWS_DIRECT_IMPORT_MIGRATION_MARKER_V177,
        migrated_source_module=MIGRATED_SOURCE_MODULE_V177,
        migrated_names=MIGRATED_NAMES_V177,
        migrated_relative_path=MIGRATED_RELATIVE_PATH_V177,
        migrated_usage_form=MIGRATED_USAGE_FORM_V177,
        migrated_import=MIGRATED_IMPORT_V177,
        views_path=v176_report.views_path,
        views_total_lines=v176_report.views_total_lines,
        remaining_target_migration_records=len(target_records),
        names_without_migration_records=v176_report.names_without_migration_records,
        v175_candidate_names=v175_report.candidate_names,
        target_removed_from_facade=set(MIGRATED_NAMES_V177).isdisjoint(set(v176_report.protected_names)),
        v176_safe_to_change_imports=v176_report.safe_to_change_imports_in_v176,
    )


def write_markdown_report(path: Path, report: ListingViewsDirectImportMigrationReportV177) -> None:
    lines = [
        "# v177 Direct Import Migration",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Migrated source module: `{report.migrated_source_module}`",
        f"- Migrated names: `{report.migrated_names}`",
        f"- Migrated file: `{report.migrated_relative_path}`",
        f"- Original usage form: `{report.migrated_usage_form}`",
        f"- Dedicated import: `{report.migrated_import}`",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Remaining target migration records: `{report.remaining_target_migration_records}`",
        f"- Names without migration records after v177: `{report.names_without_migration_records}`",
        f"- v175 candidate names after v177: `{report.v175_candidate_names}`",
        f"- Target removed from facade by v179: `{report.target_removed_from_facade}`",
        f"- Target group migrated: `{report.target_group_migrated}`",
        f"- Safe to remove facade re-export in v177: `{report.safe_to_remove_facade_reexport_in_v177}`",
        "",
        "## Guardrails",
        "",
        "- v177 migrates one small dependency group only.",
        "- v177 does not edit `backend/listings/views.py`.",
        "- v177 does not remove any facade re-export.",
        "- A later checkpoint may contract and remove the migrated facade name only after this migration remains green.",
        "",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(Path("docs/listing_views_direct_import_migration_v177.md"), report)


if __name__ == "__main__":
    main()
