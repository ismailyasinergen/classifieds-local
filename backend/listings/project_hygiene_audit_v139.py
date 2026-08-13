"""
PROJECT_HYGIENE_AUDIT_CLEANUP_V139

A lightweight project hygiene audit that separates active app code from:
- reference snapshots, especially backend/reference_html downloaded/minified assets
- development backup files
- generated cache files
- binary/static assets

The goal is to keep project audits useful without treating copied reference HTML,
minified JavaScript, or old backups as active application-code blockers.
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


ACTIVE_TEXT_SUFFIXES = {
    ".py",
    ".html",
    ".css",
    ".js",
    ".json",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".md",
    ".txt",
    ".env",
    ".example",
}

ASSET_OR_BINARY_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".sqlite3",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".mp4",
    ".mov",
    ".avi",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
}

REFERENCE_PATH_PARTS = {"reference_html"}
DEV_BACKUP_PATH_PARTS = {"_dev_backups"}

GENERATED_OR_CACHE_PATH_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "staticfiles",
    "media",
}

VENDOR_OR_DEPENDENCY_PATH_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
}

MERGE_START_MARKER = "<<<<<<< "
MERGE_END_MARKER = ">>>>>>> "
MERGE_SEPARATOR_MARKER = "======="


@dataclass
class HygieneAuditReport:
    active_source_files: list[Path] = field(default_factory=list)
    reference_snapshot_files: list[Path] = field(default_factory=list)
    dev_backup_files: list[Path] = field(default_factory=list)
    generated_or_cache_files: list[Path] = field(default_factory=list)
    vendor_or_dependency_files: list[Path] = field(default_factory=list)
    asset_or_binary_files: list[Path] = field(default_factory=list)
    ignored_other_files: list[Path] = field(default_factory=list)
    active_conflict_marker_hits: list[tuple[Path, int, str]] = field(default_factory=list)
    large_active_python_files: list[tuple[Path, int]] = field(default_factory=list)
    large_dev_backup_python_files: list[tuple[Path, int]] = field(default_factory=list)


def configure_unicode_safe_output() -> None:
    """Avoid Windows cp1252 crashes when paths contain Turkish or other Unicode chars."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(errors="backslashreplace")
            except Exception:
                pass


def safe_output_text(value: object, encoding: str | None = None) -> str:
    text = str(value)
    output_encoding = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(output_encoding, errors="backslashreplace").decode(
        output_encoding,
        errors="replace",
    )


def safe_print(value: object = "") -> None:
    print(safe_output_text(value))


def lower_parts(path: Path) -> set[str]:
    return {part.lower() for part in path.parts}


def has_any_path_part(path: Path, parts: set[str]) -> bool:
    normalized = lower_parts(path)
    return any(part.lower() in normalized for part in parts)


def is_downloaded_reference_asset(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".download") or name in {"js", "gtm.js.download", "otbannersdk.js.download"}


def classify_path(path: Path) -> str:
    """
    Return one of:
    - active_source
    - reference_snapshot
    - dev_backup
    - generated_or_cache
    - vendor_or_dependency
    - asset_or_binary
    - ignored_other
    """
    if has_any_path_part(path, VENDOR_OR_DEPENDENCY_PATH_PARTS):
        return "vendor_or_dependency"

    if has_any_path_part(path, GENERATED_OR_CACHE_PATH_PARTS):
        return "generated_or_cache"

    if has_any_path_part(path, REFERENCE_PATH_PARTS) or is_downloaded_reference_asset(path):
        return "reference_snapshot"

    if has_any_path_part(path, DEV_BACKUP_PATH_PARTS):
        return "dev_backup"

    if path.suffix.lower() in ASSET_OR_BINARY_SUFFIXES:
        return "asset_or_binary"

    if path.suffix.lower() in ACTIVE_TEXT_SUFFIXES or path.name in {
        "Dockerfile",
        "docker-compose.yml",
        "requirements.txt",
        ".env.example",
    }:
        return "active_source"

    return "ignored_other"


def iter_project_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def read_text_safely(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def line_count(path: Path) -> int:
    return len(read_text_safely(path).splitlines())


def is_real_merge_conflict_marker(stripped_line: str) -> bool:
    return (
        stripped_line.startswith(MERGE_START_MARKER)
        or stripped_line == MERGE_SEPARATOR_MARKER
        or stripped_line.startswith(MERGE_END_MARKER)
    )


def scan_active_conflict_markers(path: Path) -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    text = read_text_safely(path)
    for index, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if is_real_merge_conflict_marker(stripped):
            hits.append((path, index, stripped[:160]))
    return hits


def build_report(root: Path, large_python_threshold: int = 1200) -> HygieneAuditReport:
    report = HygieneAuditReport()

    for path in iter_project_files(root):
        classification = classify_path(path)

        if classification == "active_source":
            report.active_source_files.append(path)
            if path.suffix == ".py":
                count = line_count(path)
                if count > large_python_threshold:
                    report.large_active_python_files.append((path, count))
            report.active_conflict_marker_hits.extend(scan_active_conflict_markers(path))

        elif classification == "reference_snapshot":
            report.reference_snapshot_files.append(path)

        elif classification == "dev_backup":
            report.dev_backup_files.append(path)
            if path.suffix == ".py":
                count = line_count(path)
                if count > large_python_threshold:
                    report.large_dev_backup_python_files.append((path, count))

        elif classification == "generated_or_cache":
            report.generated_or_cache_files.append(path)

        elif classification == "vendor_or_dependency":
            report.vendor_or_dependency_files.append(path)

        elif classification == "asset_or_binary":
            report.asset_or_binary_files.append(path)

        else:
            report.ignored_other_files.append(path)

    return report


def print_path_count(title: str, paths: list[Path], limit: int = 20) -> None:
    safe_print(title)
    safe_print(f"  count: {len(paths)}")
    for path in paths[:limit]:
        safe_print(f"  - {path}")
    if len(paths) > limit:
        safe_print(f"  ... {len(paths) - limit} more")
    safe_print()


def print_report(report: HygieneAuditReport) -> None:
    safe_print("===== PROJECT_HYGIENE_AUDIT_CLEANUP_V139 REPORT =====")
    safe_print()

    print_path_count("Active source files scanned", report.active_source_files)
    print_path_count("Reference snapshot files skipped from blocker scans", report.reference_snapshot_files)
    print_path_count("Development backup files reported separately", report.dev_backup_files)
    print_path_count("Generated/cache files ignored", report.generated_or_cache_files, limit=10)
    print_path_count("Vendor/dependency files ignored", report.vendor_or_dependency_files, limit=10)
    print_path_count("Asset/binary files ignored", report.asset_or_binary_files, limit=10)

    safe_print("Large active Python files over threshold")
    if report.large_active_python_files:
        for path, count in report.large_active_python_files:
            safe_print(f"  - {path}: {count} lines")
    else:
        safe_print("  none")
    safe_print()

    safe_print("Large development backup Python files over threshold")
    if report.large_dev_backup_python_files:
        for path, count in report.large_dev_backup_python_files:
            safe_print(f"  - {path}: {count} lines")
    else:
        safe_print("  none")
    safe_print()

    safe_print("Active-source merge conflict marker hits")
    if report.active_conflict_marker_hits:
        for path, line_no, line in report.active_conflict_marker_hits:
            safe_print(f"  - {path}:{line_no}: {line}")
    else:
        safe_print("  none")
    safe_print()

    safe_print("V139 hygiene guidance")
    safe_print("  - reference_html and downloaded/minified JS are treated as reference snapshots.")
    safe_print("  - _dev_backups files are reported separately and do not block active-source audits.")
    safe_print("  - generated/cache files are ignored.")
    safe_print("  - active-source merge conflict markers remain blockers.")
    safe_print()


def main() -> int:
    configure_unicode_safe_output()

    parser = argparse.ArgumentParser(description="Project hygiene audit cleanup v139.")
    parser.add_argument("--root", default=".", help="Project root to scan.")
    parser.add_argument(
        "--fail-on-conflicts",
        action="store_true",
        help="Exit non-zero when active-source merge conflict markers are found.",
    )
    parser.add_argument(
        "--large-python-threshold",
        type=int,
        default=1200,
        help="Line threshold for large Python file reporting.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report = build_report(root=root, large_python_threshold=args.large_python_threshold)
    print_report(report)

    if args.fail_on_conflicts and report.active_conflict_marker_hits:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
