from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from listings import listing_views_direct_import_migration_audit_v176 as audit_v176
from listings import listing_views_direct_import_migration_v177 as migration_v177
from listings import listing_views_remaining_facade_surface_audit_v175 as surface_v175


LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_CONTRACT_MARKER_V178 = (
    "LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_CONTRACT_V178"
)

TARGET_FACADE_REEXPORT_NAME_V178 = "listing_feature_priority_update"
TARGET_SOURCE_MODULE_V178 = "listing_promotion_views"
TARGET_MIGRATED_RELATIVE_PATH_V178 = "listings/urls.py"
TARGET_DEDICATED_IMPORT_V178 = (
    "from listings.listing_promotion_views import listing_feature_priority_update"
)


@dataclass(frozen=True)
class ListingFeaturePriorityReexportRemovalContractReportV178:
    marker: str
    target_name: str
    target_source_module: str
    target_migrated_relative_path: str
    target_dedicated_import: str
    views_path: str
    views_total_lines: int
    target_still_reexported_by_facade: bool
    target_source_module_defines_name: bool
    target_dependency_cleared_by_v177: bool
    target_is_only_v175_candidate: bool
    target_is_only_v176_missing_migration_name: bool
    v177_target_group_migrated: bool
    v177_safe_to_remove_facade_reexport: bool
    target_migration_record_count_after_v177: int

    @property
    def contract_ready_for_later_removal(self) -> bool:
        return (
            self.target_still_reexported_by_facade
            and self.target_source_module_defines_name
            and self.target_dependency_cleared_by_v177
            and self.target_is_only_v175_candidate
            and self.target_is_only_v176_missing_migration_name
            and self.v177_target_group_migrated
            and self.target_migration_record_count_after_v177 == 0
        )

    @property
    def safe_to_remove_in_v178(self) -> bool:
        return False

    @property
    def recommended_next_checkpoint(self) -> str:
        return (
            "v179 may remove only listing_feature_priority_update from the listings.views "
            "facade re-export after this contract remains green."
        )


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()
    for candidate in (repo_root / "backend", repo_root):
        if (candidate / "listings" / "views.py").exists():
            return candidate
    raise FileNotFoundError(f"Could not resolve app root containing listings/views.py from {repo_root}")


def _imported_names_from_module(path: Path, module_name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []

    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level == 1 and node.module == module_name:
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.append(alias.asname or alias.name)

    return tuple(sorted(names))


def _module_defines_name(path: Path, name: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return True

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return True

        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return True

    return False


def build_report(repo_root: Path | str = Path(".")) -> ListingFeaturePriorityReexportRemovalContractReportV178:
    repo_root = Path(repo_root)
    app_root = _resolve_app_root(repo_root)

    views_path = app_root / "listings" / "views.py"
    source_module_path = app_root / "listings" / f"{TARGET_SOURCE_MODULE_V178}.py"

    views_text = views_path.read_text(encoding="utf-8")
    facade_imported_names = _imported_names_from_module(views_path, TARGET_SOURCE_MODULE_V178)

    v175_report = surface_v175.build_report(repo_root)
    v176_report = audit_v176.build_report(repo_root)
    v177_report = migration_v177.build_report(repo_root)

    target_migration_records = tuple(
        record
        for record in v176_report.migration_records
        if record.name == TARGET_FACADE_REEXPORT_NAME_V178
        and record.source_module == TARGET_SOURCE_MODULE_V178
    )

    return ListingFeaturePriorityReexportRemovalContractReportV178(
        marker=LISTING_FEATURE_PRIORITY_REEXPORT_REMOVAL_CONTRACT_MARKER_V178,
        target_name=TARGET_FACADE_REEXPORT_NAME_V178,
        target_source_module=TARGET_SOURCE_MODULE_V178,
        target_migrated_relative_path=TARGET_MIGRATED_RELATIVE_PATH_V178,
        target_dedicated_import=TARGET_DEDICATED_IMPORT_V178,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(views_text.splitlines()),
        target_still_reexported_by_facade=TARGET_FACADE_REEXPORT_NAME_V178 in facade_imported_names,
        target_source_module_defines_name=_module_defines_name(
            source_module_path,
            TARGET_FACADE_REEXPORT_NAME_V178,
        ),
        target_dependency_cleared_by_v177=TARGET_FACADE_REEXPORT_NAME_V178
        in v176_report.names_without_migration_records,
        target_is_only_v175_candidate=set(v175_report.candidate_names)
        == {TARGET_FACADE_REEXPORT_NAME_V178},
        target_is_only_v176_missing_migration_name=set(v176_report.names_without_migration_records)
        == {TARGET_FACADE_REEXPORT_NAME_V178},
        v177_target_group_migrated=v177_report.target_group_migrated,
        v177_safe_to_remove_facade_reexport=v177_report.safe_to_remove_facade_reexport_in_v177,
        target_migration_record_count_after_v177=len(target_migration_records),
    )


def write_markdown_report(
    path: Path,
    report: ListingFeaturePriorityReexportRemovalContractReportV178,
) -> None:
    lines = [
        "# v178 Listing Feature Priority Facade Re-export Removal Contract",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Target facade re-export: `{report.target_name}`",
        f"- Target source module: `{report.target_source_module}`",
        f"- Migrated dependency file: `{report.target_migrated_relative_path}`",
        f"- Dedicated import now used by migrated dependency: `{report.target_dedicated_import}`",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Target still re-exported by facade: `{report.target_still_reexported_by_facade}`",
        f"- Target source module defines name: `{report.target_source_module_defines_name}`",
        f"- Target dependency cleared by v177: `{report.target_dependency_cleared_by_v177}`",
        f"- Target is only v175 candidate: `{report.target_is_only_v175_candidate}`",
        f"- Target is only v176 missing migration name: `{report.target_is_only_v176_missing_migration_name}`",
        f"- v177 target group migrated: `{report.v177_target_group_migrated}`",
        f"- v177 safe to remove facade re-export: `{report.v177_safe_to_remove_facade_reexport}`",
        f"- Target migration record count after v177: `{report.target_migration_record_count_after_v177}`",
        f"- Contract ready for later removal: `{report.contract_ready_for_later_removal}`",
        f"- Safe to remove in v178: `{report.safe_to_remove_in_v178}`",
        f"- Recommended next checkpoint: `{report.recommended_next_checkpoint}`",
        "",
        "## Guardrails",
        "",
        "- v178 is a contract-only checkpoint.",
        "- Do not edit `backend/listings/views.py` in v178.",
        "- Do not remove `listing_feature_priority_update` from the facade in v178.",
        "- Do not change `backend/listings/urls.py` in v178.",
        "- A later checkpoint may remove only the contracted facade re-export if all guards stay green.",
        "",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(
        Path("docs/listing_feature_priority_reexport_removal_contract_v178.md"),
        report,
    )


if __name__ == "__main__":
    main()
