from __future__ import annotations

from dataclasses import dataclass


V183_CATEGORY_SEED_TAXONOMY_MARKER = "V183_CATEGORY_SEED_TAXONOMY_PLAN"
V183_MAX_CATEGORY_DEPTH = 3


@dataclass(frozen=True)
class CategorySeedRecordV183:
    name: str
    slug: str
    parent_slug: str | None
    depth: int


PILOT_CATEGORY_TREE_V183: tuple[dict[str, object], ...] = (
    {
        "name": "Vehicles",
        "slug": "vehicles",
        "children": (
            {
                "name": "Cars",
                "slug": "vehicles-cars",
                "children": (
                    {"name": "Sedans", "slug": "vehicles-cars-sedans"},
                    {"name": "SUVs", "slug": "vehicles-cars-suvs"},
                ),
            },
            {
                "name": "Motorcycles",
                "slug": "vehicles-motorcycles",
                "children": (
                    {"name": "Street Motorcycles", "slug": "vehicles-motorcycles-street"},
                    {"name": "Scooters", "slug": "vehicles-motorcycles-scooters"},
                ),
            },
        ),
    },
    {
        "name": "Real Estate",
        "slug": "real-estate",
        "children": (
            {
                "name": "Homes for Sale",
                "slug": "real-estate-homes-for-sale",
                "children": (
                    {"name": "Apartments for Sale", "slug": "real-estate-apartments-sale"},
                    {"name": "Houses for Sale", "slug": "real-estate-houses-sale"},
                ),
            },
            {
                "name": "Rentals",
                "slug": "real-estate-rentals",
                "children": (
                    {"name": "Apartments for Rent", "slug": "real-estate-apartments-rent"},
                    {"name": "Rooms for Rent", "slug": "real-estate-rooms-rent"},
                ),
            },
        ),
    },
    {
        "name": "Electronics",
        "slug": "electronics",
        "children": (
            {
                "name": "Phones",
                "slug": "electronics-phones",
                "children": (
                    {"name": "Smartphones", "slug": "electronics-smartphones"},
                    {"name": "Phone Accessories", "slug": "electronics-phone-accessories"},
                ),
            },
            {
                "name": "Computers",
                "slug": "electronics-computers",
                "children": (
                    {"name": "Laptops", "slug": "electronics-laptops"},
                    {"name": "Desktop Computers", "slug": "electronics-desktops"},
                ),
            },
        ),
    },
    {
        "name": "Home & Garden",
        "slug": "home-garden",
        "children": (
            {
                "name": "Furniture",
                "slug": "home-garden-furniture",
                "children": (
                    {"name": "Living Room Furniture", "slug": "home-garden-living-room"},
                    {"name": "Bedroom Furniture", "slug": "home-garden-bedroom"},
                ),
            },
            {
                "name": "Garden",
                "slug": "home-garden-garden",
                "children": (
                    {"name": "Garden Tools", "slug": "home-garden-garden-tools"},
                    {"name": "Outdoor Furniture", "slug": "home-garden-outdoor-furniture"},
                ),
            },
        ),
    },
    {
        "name": "Jobs",
        "slug": "jobs",
        "children": (
            {
                "name": "Technology Jobs",
                "slug": "jobs-technology",
                "children": (
                    {"name": "Software Development Jobs", "slug": "jobs-software-development"},
                    {"name": "IT Support Jobs", "slug": "jobs-it-support"},
                ),
            },
            {
                "name": "Service Jobs",
                "slug": "jobs-service",
                "children": (
                    {"name": "Restaurant Jobs", "slug": "jobs-restaurant"},
                    {"name": "Cleaning Jobs", "slug": "jobs-cleaning"},
                ),
            },
        ),
    },
)


def flatten_category_tree_v183(
    tree: tuple[dict[str, object], ...] = PILOT_CATEGORY_TREE_V183,
    *,
    parent_slug: str | None = None,
    depth: int = 1,
) -> tuple[CategorySeedRecordV183, ...]:
    records: list[CategorySeedRecordV183] = []

    for node in tree:
        name = str(node.get("name", "")).strip()
        slug = str(node.get("slug", "")).strip()

        records.append(
            CategorySeedRecordV183(
                name=name,
                slug=slug,
                parent_slug=parent_slug,
                depth=depth,
            )
        )

        children = node.get("children", ())
        if children:
            records.extend(
                flatten_category_tree_v183(
                    tuple(children),  # type: ignore[arg-type]
                    parent_slug=slug,
                    depth=depth + 1,
                )
            )

    return tuple(records)


def validate_category_seed_plan_v183(
    records: tuple[CategorySeedRecordV183, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    seen_slugs: set[str] = set()

    for record in records:
        if not record.name:
            errors.append(f"Missing category name for slug `{record.slug}`.")

        if not record.slug:
            errors.append(f"Missing category slug for name `{record.name}`.")

        if record.slug in seen_slugs:
            errors.append(f"Duplicate category slug `{record.slug}`.")
        seen_slugs.add(record.slug)

        if record.depth < 1 or record.depth > V183_MAX_CATEGORY_DEPTH:
            errors.append(
                f"Category `{record.slug}` depth `{record.depth}` exceeds allowed depth."
            )

        if record.depth == 1 and record.parent_slug is not None:
            errors.append(f"Root category `{record.slug}` should not have a parent.")

        if record.depth > 1 and not record.parent_slug:
            errors.append(f"Child category `{record.slug}` is missing parent slug.")

    known_slugs = {record.slug for record in records}
    for record in records:
        if record.parent_slug and record.parent_slug not in known_slugs:
            errors.append(
                f"Category `{record.slug}` references missing parent `{record.parent_slug}`."
            )

    return tuple(errors)


def build_category_seed_plan_v183() -> tuple[CategorySeedRecordV183, ...]:
    records = flatten_category_tree_v183()
    errors = validate_category_seed_plan_v183(records)
    if errors:
        raise ValueError("Invalid v183 category seed plan: " + " | ".join(errors))
    return records


def summarize_category_seed_plan_v183(
    records: tuple[CategorySeedRecordV183, ...],
) -> dict[str, int]:
    return {
        "total": len(records),
        "roots": sum(1 for record in records if record.depth == 1),
        "children": sum(1 for record in records if record.depth == 2),
        "grandchildren": sum(1 for record in records if record.depth == 3),
        "max_depth": max((record.depth for record in records), default=0),
    }
