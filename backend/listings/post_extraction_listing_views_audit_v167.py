from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


POST_EXTRACTION_LISTING_VIEWS_AUDIT_MARKER_V167 = "POST_EXTRACTION_LISTING_VIEWS_AUDIT_V167"

EXPECTED_EXTRACTED_MODULES_V167 = {
    "listing_crud_uploads": "listings/listing_crud_uploads_views.py",
    "listing_reports": "listings/listing_reports_views.py",
    "saved_searches": "listings/saved_searches_views.py",
}

EXPECTED_VIEWS_REEXPORT_MODULE_NAMES_V167 = {
    "listing_crud_uploads_views",
    "listing_reports_views",
    "saved_searches_views",
}


@dataclass(frozen=True)
class ExtractedModuleAuditV167:
    lane_name: str
    module_path: str
    exists: bool
    mentioned_in_views: bool


@dataclass(frozen=True)
class PostExtractionListingViewsAuditReportV167:
    marker: str
    views_path: str
    views_total_lines: int
    top_level_function_names: tuple[str, ...]
    top_level_class_names: tuple[str, ...]
    extracted_modules: tuple[ExtractedModuleAuditV167, ...]
    reexport_module_names: tuple[str, ...]
    recommended_next_step: str

    @property
    def total_top_level_definitions(self) -> int:
        return len(self.top_level_function_names) + len(self.top_level_class_names)

    @property
    def has_no_local_runtime_views(self) -> bool:
        return self.total_top_level_definitions == 0

    @property
    def missing_extracted_modules(self) -> tuple[str, ...]:
        return tuple(module.lane_name for module in self.extracted_modules if not module.exists)

    @property
    def missing_reexport_mentions(self) -> tuple[str, ...]:
        return tuple(
            module.lane_name
            for module in self.extracted_modules
            if not module.mentioned_in_views
        )


def _resolve_app_root(repo_root: Path) -> Path:
    repo_root = repo_root.resolve()

    candidates = (
        repo_root / "backend",
        repo_root,
    )

    for candidate in candidates:
        if (candidate / "listings" / "views.py").exists():
            return candidate

    raise FileNotFoundError(
        f"Could not resolve app root containing listings/views.py from {repo_root}"
    )


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


def _reexport_modules_from_views_source(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    modules: set[str] = set()

    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
            modules.add(node.module)

    return tuple(sorted(modules))


def build_report(repo_root: Path | str = Path(".")) -> PostExtractionListingViewsAuditReportV167:
    app_root = _resolve_app_root(Path(repo_root))
    views_path = app_root / "listings" / "views.py"
    views_source = views_path.read_text(encoding="utf-8")

    function_names, class_names = _top_level_definitions(views_source)
    reexport_module_names = _reexport_modules_from_views_source(views_source)

    extracted_modules = []
    for lane_name, module_path in EXPECTED_EXTRACTED_MODULES_V167.items():
        module_relative_to_app_root = module_path.replace("listings/", "", 1)
        module_file = app_root / "listings" / module_relative_to_app_root
        module_name = Path(module_path).stem

        extracted_modules.append(
            ExtractedModuleAuditV167(
                lane_name=lane_name,
                module_path=module_path,
                exists=module_file.exists(),
                mentioned_in_views=module_name in reexport_module_names,
            )
        )

    return PostExtractionListingViewsAuditReportV167(
        marker=POST_EXTRACTION_LISTING_VIEWS_AUDIT_MARKER_V167,
        views_path=views_path.relative_to(app_root).as_posix(),
        views_total_lines=len(views_source.splitlines()),
        top_level_function_names=function_names,
        top_level_class_names=class_names,
        extracted_modules=tuple(extracted_modules),
        reexport_module_names=reexport_module_names,
        recommended_next_step=(
            "No further blind extraction from listings/views.py. "
            "Use a fresh targeted audit or a compatibility/import hygiene contract before changing runtime code."
        ),
    )


def write_markdown_report(path: Path, report: PostExtractionListingViewsAuditReportV167) -> None:
    lines = [
        "# v167 Post-Extraction Listing Views Audit",
        "",
        report.marker,
        "",
        "## Summary",
        "",
        f"- Views path: `{report.views_path}`",
        f"- Views total lines: `{report.views_total_lines}`",
        f"- Top-level functions/classes remaining in `views.py`: `{report.total_top_level_definitions}`",
        f"- Has no local runtime views: `{report.has_no_local_runtime_views}`",
        "",
        "## Extracted modules",
        "",
    ]

    for module in report.extracted_modules:
        lines.append(
            f"- `{module.lane_name}` -> `{module.module_path}` "
            f"(exists: `{module.exists}`, re-export mentioned in views: `{module.mentioned_in_views}`)"
        )

    lines.extend(
        [
            "",
            "## Remaining local definitions",
            "",
        ]
    )

    if report.top_level_function_names:
        lines.append("### Functions")
        lines.extend(f"- `{name}`" for name in report.top_level_function_names)
        lines.append("")
    else:
        lines.append("No top-level functions remain in `listings/views.py`.")
        lines.append("")

    if report.top_level_class_names:
        lines.append("### Classes")
        lines.extend(f"- `{name}`" for name in report.top_level_class_names)
        lines.append("")
    else:
        lines.append("No top-level classes remain in `listings/views.py`.")
        lines.append("")

    lines.extend(
        [
            "## Compatibility re-export modules detected",
            "",
        ]
    )

    for module_name in report.reexport_module_names:
        lines.append(f"- `{module_name}`")

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            report.recommended_next_step,
            "",
            "## Non-goals",
            "",
            "- Do not move runtime code in v167.",
            "- Do not change URLs, templates, permissions, models, migrations, or behavior.",
            "- Do not remove compatibility re-export paths.",
            "- Do not start another extraction without a new contract checkpoint.",
            "",
        ]
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = build_report(Path("."))
    write_markdown_report(
        Path("docs/post_extraction_listing_views_audit_v167.md"),
        report,
    )


if __name__ == "__main__":
    main()
