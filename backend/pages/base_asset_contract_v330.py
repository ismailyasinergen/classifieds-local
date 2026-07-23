"""Shared base-template static asset contract for v330."""

from pathlib import Path


BASE_TEMPLATE_PATH_V330 = "templates/base.html"
BASE_CSS_ASSET_V330 = "pages/base-v330.css"
BASE_CSS_REPOSITORY_PATH_V330 = "pages/static/pages/base-v330.css"


def base_contract_paths_v330(backend_dir: Path) -> tuple[Path, Path]:
    backend_dir = Path(backend_dir)

    return (
        backend_dir / BASE_TEMPLATE_PATH_V330,
        backend_dir / BASE_CSS_REPOSITORY_PATH_V330,
    )


def read_base_contract_source_v330(backend_dir: Path) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in base_contract_paths_v330(backend_dir)
    )
