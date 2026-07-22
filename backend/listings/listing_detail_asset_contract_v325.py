"""Asset-aware listing-detail source contract for tests and audits."""

from __future__ import annotations

from pathlib import Path

from listings.listing_detail_asset_boundary_v324 import (
    PLANNED_CSS_ASSET_V324,
    PLANNED_JS_ASSET_V324,
)


V325_MARKER = "LISTING_DETAIL_EXTRACTION_BLOCKER_REMOVAL_V325"
LISTING_DETAIL_TEMPLATE_PATH_V325 = (
    "listings/templates/listings/listing_detail.html"
)
LISTING_DETAIL_STATIC_ASSET_PATHS_V325 = (
    f"listings/static/{PLANNED_CSS_ASSET_V324}",
    f"listings/static/{PLANNED_JS_ASSET_V324}",
)


def listing_detail_contract_paths_v325(
    backend_dir: Path,
) -> tuple[Path, ...]:
    """Return the template and each currently present planned static asset."""

    backend_dir = Path(backend_dir)
    template_path = backend_dir / LISTING_DETAIL_TEMPLATE_PATH_V325
    asset_paths = tuple(
        backend_dir / relative_path
        for relative_path in LISTING_DETAIL_STATIC_ASSET_PATHS_V325
        if (backend_dir / relative_path).is_file()
    )
    return (template_path,) + asset_paths


def read_listing_detail_contract_source_v325(
    backend_dir: Path,
) -> str:
    """Read the template-plus-assets source in stable contract order."""

    sections = []
    backend_dir = Path(backend_dir)

    for path in listing_detail_contract_paths_v325(backend_dir):
        relative_path = path.relative_to(backend_dir).as_posix()
        sections.append(
            f"/* LISTING_DETAIL_CONTRACT_SOURCE: {relative_path} */\n"
            + path.read_text(encoding="utf-8")
        )

    return "\n".join(sections)
