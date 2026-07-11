from __future__ import annotations

from pathlib import Path

from django.conf import settings


V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT_MARKER = "V187_CATEGORY_NAVIGATION_PUBLIC_BROWSE_MOUNT"
V187_MOUNTED_TEMPLATE_NAMES = ('listings/listing_list.html',)
V187_MOUNTED_TEMPLATE_PROJECT_PATHS = ('listings/templates/listings/listing_list.html',)


def get_v187_template_root() -> Path:
    return Path(settings.BASE_DIR)


def get_v187_mounted_template_paths() -> tuple[Path, ...]:
    root = get_v187_template_root()
    return tuple(root / project_path for project_path in V187_MOUNTED_TEMPLATE_PROJECT_PATHS)
