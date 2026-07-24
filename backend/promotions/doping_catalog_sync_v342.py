"""Idempotent database synchronization for the V342 doping catalog."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from django.db import transaction

from .doping_catalog_v342 import (
    PRICE_GROUP_LABELS_V342,
    PRICE_MATRIX_V342,
    PROMOTION_DEFINITIONS_V342,
    DurationModeV342,
    PriceGroupV342,
    PromotionCodeV342,
)
from .models import PromotionPackage


DOPING_CATALOG_SYNC_V342 = True


@dataclass(frozen=True)
class CatalogPackageSpecV342:
    catalog_code: PromotionCodeV342
    price_group: PriceGroupV342
    name: str
    package_type: str
    duration_mode: DurationModeV342
    duration_days: int
    price: Decimal
    priority: int


PRIORITY_BY_CODE_V342: Final = {
    PromotionCodeV342.SMALL_PHOTO: 0,
    PromotionCodeV342.URGENT: 0,
    PromotionCodeV342.HOMEPAGE_SHOWCASE: 0,
    PromotionCodeV342.CATEGORY_SHOWCASE: 0,
    PromotionCodeV342.TOP_RANKING: 200,
    PromotionCodeV342.DETAILED_SEARCH_SHOWCASE: 0,
    PromotionCodeV342.COLORFUL_TITLE: 0,
    PromotionCodeV342.REFRESH: 0,
}


def _legacy_package_type_v342(code: PromotionCodeV342) -> str:
    """
    Preserve the historical two-value package_type field.

    New behavior is selected by catalog_code, not by this compatibility value.
    """
    if code == PromotionCodeV342.TOP_RANKING:
        return PromotionPackage.PackageType.TOP

    return PromotionPackage.PackageType.FEATURED


def _base_duration_days_v342(mode: DurationModeV342) -> int:
    if mode == DurationModeV342.FIXED_WEEKS:
        return 7

    return 0


def build_catalog_package_specs_v342() -> tuple[CatalogPackageSpecV342, ...]:
    specs = []

    for code in PromotionCodeV342:
        definition = PROMOTION_DEFINITIONS_V342[code]

        for group in PriceGroupV342:
            price = PRICE_MATRIX_V342[code][group]

            if price is None:
                continue

            specs.append(
                CatalogPackageSpecV342(
                    catalog_code=code,
                    price_group=group,
                    name=(
                        f"{definition.label} — "
                        f"{PRICE_GROUP_LABELS_V342[group]}"
                    ),
                    package_type=_legacy_package_type_v342(code),
                    duration_mode=definition.duration_mode,
                    duration_days=_base_duration_days_v342(
                        definition.duration_mode
                    ),
                    price=price,
                    priority=PRIORITY_BY_CODE_V342[code],
                )
            )

    return tuple(specs)


def _package_defaults_v342(
    spec: CatalogPackageSpecV342,
) -> dict[str, object]:
    return {
        "name": spec.name,
        "package_type": spec.package_type,
        "duration_days": spec.duration_days,
        "price": spec.price,
        "priority": spec.priority,
        "duration_mode": spec.duration_mode,
        "is_active": True,
    }


@transaction.atomic
def sync_doping_catalog_v342() -> dict[str, int]:
    specs = build_catalog_package_specs_v342()
    desired_keys = {
        (
            spec.catalog_code.value,
            spec.price_group.value,
        )
        for spec in specs
    }

    created_count = 0
    updated_count = 0
    unchanged_count = 0

    for spec in specs:
        package = (
            PromotionPackage.objects
            .filter(
                catalog_code=spec.catalog_code,
                price_group=spec.price_group,
            )
            .first()
        )
        defaults = _package_defaults_v342(spec)

        if package is None:
            PromotionPackage.objects.create(
                catalog_code=spec.catalog_code,
                price_group=spec.price_group,
                **defaults,
            )
            created_count += 1
            continue

        changed_fields = []

        for field_name, expected_value in defaults.items():
            if getattr(package, field_name) != expected_value:
                setattr(package, field_name, expected_value)
                changed_fields.append(field_name)

        if changed_fields:
            package.save(update_fields=changed_fields)
            updated_count += 1
        else:
            unchanged_count += 1

    deactivated_count = 0

    for package in PromotionPackage.objects.exclude(catalog_code=""):
        key = (
            package.catalog_code,
            package.price_group,
        )

        if key in desired_keys or not package.is_active:
            continue

        package.is_active = False
        package.save(update_fields=["is_active"])
        deactivated_count += 1

    return {
        "created": created_count,
        "updated": updated_count,
        "unchanged": unchanged_count,
        "deactivated": deactivated_count,
        "total": len(specs),
    }
