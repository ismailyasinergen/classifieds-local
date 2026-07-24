"""Canonical promotion catalog and pricing rules introduced in V342."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import StrEnum
from typing import Final


DOPING_CATALOG_V342 = True
MONEY_QUANTUM_V342: Final = Decimal("0.01")


class PromotionCodeV342(StrEnum):
    SMALL_PHOTO = "small_photo"
    URGENT = "urgent"
    HOMEPAGE_SHOWCASE = "homepage_showcase"
    CATEGORY_SHOWCASE = "category_showcase"
    TOP_RANKING = "top_ranking"
    DETAILED_SEARCH_SHOWCASE = "detailed_search_showcase"
    COLORFUL_TITLE = "colorful_title"
    REFRESH = "refresh"


class PriceGroupV342(StrEnum):
    REAL_ESTATE = "real_estate"
    VEHICLES = "vehicles"
    VEHICLE_PARTS = "vehicle_parts"
    MARKETPLACE = "marketplace"
    INDUSTRIAL = "industrial"
    LESSONS = "lessons"
    JOBS = "jobs"
    PETS = "pets"
    HELPERS = "helpers"


class DurationModeV342(StrEnum):
    FIXED_WEEKS = "fixed_weeks"
    LISTING_LIFETIME = "listing_lifetime"
    SINGLE_USE = "single_use"


@dataclass(frozen=True)
class PromotionDefinitionV342:
    code: PromotionCodeV342
    label: str
    duration_mode: DurationModeV342
    allowed_weeks: tuple[int, ...]


@dataclass(frozen=True)
class PromotionQuoteV342:
    promotion_code: PromotionCodeV342
    price_group: PriceGroupV342
    duration_mode: DurationModeV342
    requested_weeks: int | None
    unit_price: Decimal
    subtotal: Decimal
    discount_percent: Decimal
    total_price: Decimal
    duration_days: int | None


PRICE_GROUP_LABELS_V342: Final = {
    PriceGroupV342.REAL_ESTATE: "Real Estate",
    PriceGroupV342.VEHICLES: "Vehicles",
    PriceGroupV342.VEHICLE_PARTS: "Vehicle Parts",
    PriceGroupV342.MARKETPLACE: "Marketplace",
    PriceGroupV342.INDUSTRIAL: "Industrial",
    PriceGroupV342.LESSONS: "Lessons & Training",
    PriceGroupV342.JOBS: "Jobs",
    PriceGroupV342.PETS: "Pets",
    PriceGroupV342.HELPERS: "Helpers Wanted",
}


DURATION_MODE_LABELS_V342: Final = {
    DurationModeV342.FIXED_WEEKS: "Fixed Weeks",
    DurationModeV342.LISTING_LIFETIME: "Listing Lifetime",
    DurationModeV342.SINGLE_USE: "Single Use",
}


PROMOTION_DEFINITIONS_V342: Final = {
    PromotionCodeV342.SMALL_PHOTO: PromotionDefinitionV342(
        PromotionCodeV342.SMALL_PHOTO,
        "Small Photo",
        DurationModeV342.LISTING_LIFETIME,
        (),
    ),
    PromotionCodeV342.URGENT: PromotionDefinitionV342(
        PromotionCodeV342.URGENT,
        "Urgent",
        DurationModeV342.FIXED_WEEKS,
        (1, 2, 4),
    ),
    PromotionCodeV342.HOMEPAGE_SHOWCASE: PromotionDefinitionV342(
        PromotionCodeV342.HOMEPAGE_SHOWCASE,
        "Homepage Showcase",
        DurationModeV342.FIXED_WEEKS,
        (1, 2, 4),
    ),
    PromotionCodeV342.CATEGORY_SHOWCASE: PromotionDefinitionV342(
        PromotionCodeV342.CATEGORY_SHOWCASE,
        "Category Showcase",
        DurationModeV342.FIXED_WEEKS,
        (1, 2, 4),
    ),
    PromotionCodeV342.TOP_RANKING: PromotionDefinitionV342(
        PromotionCodeV342.TOP_RANKING,
        "Top Ranking",
        DurationModeV342.FIXED_WEEKS,
        (1, 2, 4),
    ),
    PromotionCodeV342.DETAILED_SEARCH_SHOWCASE: PromotionDefinitionV342(
        PromotionCodeV342.DETAILED_SEARCH_SHOWCASE,
        "Detailed Search Showcase",
        DurationModeV342.FIXED_WEEKS,
        (1, 2, 4),
    ),
    PromotionCodeV342.COLORFUL_TITLE: PromotionDefinitionV342(
        PromotionCodeV342.COLORFUL_TITLE,
        "Bold Title & Colorful Frame",
        DurationModeV342.LISTING_LIFETIME,
        (),
    ),
    PromotionCodeV342.REFRESH: PromotionDefinitionV342(
        PromotionCodeV342.REFRESH,
        "Refresh Listing",
        DurationModeV342.SINGLE_USE,
        (),
    ),
}


PROMOTION_CODE_CHOICES_V342: Final = tuple(
    (
        code.value,
        PROMOTION_DEFINITIONS_V342[code].label,
    )
    for code in PromotionCodeV342
)

PRICE_GROUP_CHOICES_V342: Final = tuple(
    (
        group.value,
        PRICE_GROUP_LABELS_V342[group],
    )
    for group in PriceGroupV342
)

DURATION_MODE_CHOICES_V342: Final = tuple(
    (
        mode.value,
        DURATION_MODE_LABELS_V342[mode],
    )
    for mode in DurationModeV342
)


WEEK_DISCOUNTS_V342: Final = {
    1: Decimal("0.00"),
    2: Decimal("0.05"),
    4: Decimal("0.07"),
}


def _prices(*values: str | None) -> dict[PriceGroupV342, Decimal | None]:
    groups = tuple(PriceGroupV342)
    return {
        group: Decimal(value) if value is not None else None
        for group, value in zip(groups, values, strict=True)
    }


PRICE_MATRIX_V342: Final = {
    PromotionCodeV342.SMALL_PHOTO: _prices(
        "429", "429", "65", "89", "109", "75", "75", "75", "75"
    ),
    PromotionCodeV342.URGENT: _prices(
        "1999", "1999", "89", "89", "409", "99", "99", "99", "99"
    ),
    PromotionCodeV342.HOMEPAGE_SHOWCASE: _prices(
        "8399", "8399", "4699", "8799", "5099", "3199", None, "2859", "1949"
    ),
    PromotionCodeV342.CATEGORY_SHOWCASE: _prices(
        "2549", "2549", "219", "229", "999", None, None, "219", None
    ),
    PromotionCodeV342.TOP_RANKING: _prices(
        "7299", "7299", "649", "1149", "1429", "309", "309", "509", "309"
    ),
    PromotionCodeV342.DETAILED_SEARCH_SHOWCASE: _prices(
        "989", "989", "89", "89", "409", "89", "89", "89", "89"
    ),
    PromotionCodeV342.COLORFUL_TITLE: _prices(
        None, "679", "109", "89", "109", "75", "75", "75", "75"
    ),
    PromotionCodeV342.REFRESH: _prices(
        "979", "979", "120", "99", "109", "89", "79", "79", "79"
    ),
}


ROOT_PRICE_GROUPS_V342: Final = {
    "real-estate": PriceGroupV342.REAL_ESTATE,
    "vehicles": PriceGroupV342.VEHICLES,
    "vehicle-parts": PriceGroupV342.VEHICLE_PARTS,
    "spare-parts": PriceGroupV342.VEHICLE_PARTS,
    "industrial": PriceGroupV342.INDUSTRIAL,
    "jobs": PriceGroupV342.JOBS,
    "pets": PriceGroupV342.PETS,
    "electronics": PriceGroupV342.MARKETPLACE,
    "fashion": PriceGroupV342.MARKETPLACE,
    "home-garden": PriceGroupV342.MARKETPLACE,
    "baby-kids": PriceGroupV342.MARKETPLACE,
    "sports-hobbies": PriceGroupV342.MARKETPLACE,
    "services": PriceGroupV342.MARKETPLACE,
}


EXCLUDED_ROOT_SLUGS_V342: Final = {
    "moderation-scenarios",
    "report-test",
    "scenario-electronics",
    "scenario-fashion",
    "scenario-vehicles",
}


def resolve_price_group_v342(category) -> PriceGroupV342 | None:
    """Resolve a Category-like object without importing Django models."""

    chain = []
    seen = set()
    current = category

    while current is not None:
        identity = getattr(current, "pk", None) or id(current)
        if identity in seen:
            return None

        seen.add(identity)
        chain.append(current)
        current = getattr(current, "parent", None)

    slugs = [str(getattr(item, "slug", "") or "") for item in chain]

    if any(
        slug == "services-lessons-training"
        or slug.startswith("services-lessons-training-")
        for slug in slugs
    ):
        return PriceGroupV342.LESSONS

    if any(
        slug == "jobs-service"
        or slug.startswith("jobs-service-")
        for slug in slugs
    ):
        return PriceGroupV342.HELPERS

    root_slug = slugs[-1] if slugs else ""

    if root_slug in EXCLUDED_ROOT_SLUGS_V342:
        return None

    return ROOT_PRICE_GROUPS_V342.get(root_slug)


def quote_promotion_v342(
    promotion_code: PromotionCodeV342 | str,
    price_group: PriceGroupV342 | str,
    *,
    requested_weeks: int | None = None,
) -> PromotionQuoteV342:
    code = PromotionCodeV342(promotion_code)
    group = PriceGroupV342(price_group)
    definition = PROMOTION_DEFINITIONS_V342[code]
    unit_price = PRICE_MATRIX_V342[code][group]

    if unit_price is None:
        raise ValueError("Promotion is unavailable for this price group.")

    if definition.duration_mode == DurationModeV342.FIXED_WEEKS:
        if requested_weeks not in definition.allowed_weeks:
            raise ValueError("Duration must be 1, 2, or 4 weeks.")

        discount = WEEK_DISCOUNTS_V342[requested_weeks]
        subtotal = unit_price * requested_weeks
        total = subtotal * (Decimal("1.00") - discount)
        duration_days = requested_weeks * 7
    else:
        if requested_weeks is not None:
            raise ValueError("This promotion does not accept a week duration.")

        discount = Decimal("0.00")
        subtotal = unit_price
        total = unit_price
        duration_days = None

    return PromotionQuoteV342(
        promotion_code=code,
        price_group=group,
        duration_mode=definition.duration_mode,
        requested_weeks=requested_weeks,
        unit_price=unit_price.quantize(MONEY_QUANTUM_V342),
        subtotal=subtotal.quantize(MONEY_QUANTUM_V342),
        discount_percent=discount,
        total_price=total.quantize(
            MONEY_QUANTUM_V342,
            rounding=ROUND_HALF_UP,
        ),
        duration_days=duration_days,
    )


def promotion_end_at_v342(
    *,
    starts_at: datetime,
    duration_mode: DurationModeV342 | str,
    requested_weeks: int | None,
    listing_expires_at: datetime | None,
) -> datetime | None:
    mode = DurationModeV342(duration_mode)

    if mode == DurationModeV342.FIXED_WEEKS:
        if requested_weeks not in WEEK_DISCOUNTS_V342:
            raise ValueError("Duration must be 1, 2, or 4 weeks.")
        return starts_at + timedelta(days=requested_weeks * 7)

    if mode == DurationModeV342.LISTING_LIFETIME:
        return listing_expires_at

    if requested_weeks is not None:
        raise ValueError("Single-use promotions do not accept a duration.")

    return starts_at
