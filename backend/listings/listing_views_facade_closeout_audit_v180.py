from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


LISTING_VIEWS_FACADE_CLOSEOUT_AUDIT_MARKER_V180 = (
    "LISTING_VIEWS_FACADE_CLOSEOUT_AUDIT_V180"
)

REMOVED_FACADE_REEXPORT_NAME_V180 = "listing_feature_priority_update"
SOURCE_MODULE_BASENAME_V180 = "listing_promotion_views"

FACADE_REEXPORT_IMPORT_LINES_V180 = (
    "from .listing_promotion_views import listing_feature_priority_update",
    "from listings.listing_promotion_views import listing_feature_priority_update",
)

URLS_DEDICATED_IMPORT_LINE_V180 = (
    "from listings.listing_promotion_views import listing_feature_priority_update"
)

URLS_FACADE_IMPORT_LINES_V180 = (
    "from .views import listing_feature_priority_update",
    "from listings.views import listing_feature_priority_update",
)

VIEWS_PATH_CANDIDATES_V180 = (
    "listings/views.py",
    "backend/listings/views.py",
)

URLS_PATH_CANDIDATES_V180 = (
    "listings/urls.py",
    "backend/listings/urls.py",
)

SOURCE_PATH_CANDIDATES_V180 = (
    "listings/listing_promotion_views.py",
    "backend/listings/listing_promotion_views.py",
)


@dataclass(frozen=True)
class ListingViewsFacadeCloseoutReportV180:
    marker: str
    views_path: str
    urls_path: str
    source_path: str
    views_line_count: int
    removed_target_name: str
    target_absent_from_views_source: bool
    facade_reexport_import_absent: bool
    source_module_still_defines_target: bool
    urls_use_dedicated_import: bool
    urls_avoid_facade_import_for_target: bool
    views_line_count_within_closeout_limit: bool
    remaining_known_candidate_names: tuple[str, ...]
    closeout_complete: bool


def _first_existing_path(project_root: Path, candidates: tuple[str, ...]) -> Path:
    for candidate in candidates:
        path = project_root / candidate
        if path.exists():
            return path
    raise FileNotFoundError(
        f"None of the expected paths exists under {project_root}: {candidates}"
    )


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def build_report(project_root: Path) -> ListingViewsFacadeCloseoutReportV180:
    views_path = _first_existing_path(project_root, VIEWS_PATH_CANDIDATES_V180)
    urls_path = _first_existing_path(project_root, URLS_PATH_CANDIDATES_V180)
    source_path = _first_existing_path(project_root, SOURCE_PATH_CANDIDATES_V180)

    views_text = views_path.read_text(encoding="utf-8")
    urls_text = urls_path.read_text(encoding="utf-8")
    source_text = source_path.read_text(encoding="utf-8")

    target_absent_from_views_source = REMOVED_FACADE_REEXPORT_NAME_V180 not in views_text
    facade_reexport_import_absent = not _contains_any(
        views_text,
        FACADE_REEXPORT_IMPORT_LINES_V180,
    )
    source_module_still_defines_target = (
        f"def {REMOVED_FACADE_REEXPORT_NAME_V180}" in source_text
    )
    urls_use_dedicated_import = URLS_DEDICATED_IMPORT_LINE_V180 in urls_text
    urls_avoid_facade_import_for_target = not _contains_any(
        urls_text,
        URLS_FACADE_IMPORT_LINES_V180,
    )

    views_line_count = len(views_text.splitlines())
    views_line_count_within_closeout_limit = views_line_count <= 180

    closeout_complete = all(
        (
            target_absent_from_views_source,
            facade_reexport_import_absent,
            source_module_still_defines_target,
            urls_use_dedicated_import,
            urls_avoid_facade_import_for_target,
            views_line_count_within_closeout_limit,
        )
    )

    remaining_known_candidate_names = (
        ()
        if closeout_complete
        else (REMOVED_FACADE_REEXPORT_NAME_V180,)
    )

    return ListingViewsFacadeCloseoutReportV180(
        marker=LISTING_VIEWS_FACADE_CLOSEOUT_AUDIT_MARKER_V180,
        views_path=views_path.as_posix(),
        urls_path=urls_path.as_posix(),
        source_path=source_path.as_posix(),
        views_line_count=views_line_count,
        removed_target_name=REMOVED_FACADE_REEXPORT_NAME_V180,
        target_absent_from_views_source=target_absent_from_views_source,
        facade_reexport_import_absent=facade_reexport_import_absent,
        source_module_still_defines_target=source_module_still_defines_target,
        urls_use_dedicated_import=urls_use_dedicated_import,
        urls_avoid_facade_import_for_target=urls_avoid_facade_import_for_target,
        views_line_count_within_closeout_limit=views_line_count_within_closeout_limit,
        remaining_known_candidate_names=remaining_known_candidate_names,
        closeout_complete=closeout_complete,
    )


def write_markdown_report(
    output_path: Path,
    report: ListingViewsFacadeCloseoutReportV180,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            [
                "# v180 Listing Views Facade Closeout Audit",
                "",
                report.marker,
                "",
                "## Summary",
                "",
                f"- Views path: `{report.views_path}`",
                f"- URLs path: `{report.urls_path}`",
                f"- Source path: `{report.source_path}`",
                f"- Views total lines: `{report.views_line_count}`",
                f"- Removed target name: `{report.removed_target_name}`",
                f"- Target absent from views source: `{report.target_absent_from_views_source}`",
                f"- Facade re-export import absent: `{report.facade_reexport_import_absent}`",
                f"- Source module still defines target: `{report.source_module_still_defines_target}`",
                f"- URLs use dedicated import: `{report.urls_use_dedicated_import}`",
                f"- URLs avoid facade import for target: `{report.urls_avoid_facade_import_for_target}`",
                f"- Views line count within closeout limit: `{report.views_line_count_within_closeout_limit}`",
                f"- Remaining known candidate names: `{report.remaining_known_candidate_names}`",
                f"- Closeout complete: `{report.closeout_complete}`",
                "",
                "## Guardrails",
                "",
                "- v180 is an audit-only checkpoint.",
                "- v180 does not change production view, URL, model, template, or migration behavior.",
                "- v180 confirms the v179 facade re-export removal remains stable.",
                "- v180 keeps `backend/docs/` out of the repository.",
                "",
            ]
        ),
        encoding="utf-8",
    )
