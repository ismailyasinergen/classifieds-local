"""Conditional seller-restriction static asset contract for v331."""

from pathlib import Path


SELLER_RESTRICTION_CSS_ASSET_V331 = (
    "accounts/seller-restriction-v331.css"
)
SELLER_RESTRICTION_JS_ASSET_V331 = (
    "accounts/seller-restriction-v331.js"
)
SELLER_RESTRICTION_CSS_REPOSITORY_PATH_V331 = (
    "accounts/static/accounts/seller-restriction-v331.css"
)
SELLER_RESTRICTION_JS_REPOSITORY_PATH_V331 = (
    "accounts/static/accounts/seller-restriction-v331.js"
)


def seller_restriction_asset_paths_v331(
    backend_dir: Path,
) -> tuple[Path, Path]:
    backend_dir = Path(backend_dir)

    return (
        backend_dir / SELLER_RESTRICTION_CSS_REPOSITORY_PATH_V331,
        backend_dir / SELLER_RESTRICTION_JS_REPOSITORY_PATH_V331,
    )


def read_seller_restriction_asset_source_v331(
    backend_dir: Path,
) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in seller_restriction_asset_paths_v331(backend_dir)
    )
