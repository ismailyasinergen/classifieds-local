from __future__ import annotations

from dataclasses import dataclass


V184_CATEGORY_SEED_TAXONOMY_MARKER = "V184_CATEGORY_SEED_TAXONOMY_EXPANDED_PLAN"
V184_MAX_CATEGORY_DEPTH = 3


@dataclass(frozen=True)
class CategorySeedRecordV184:
    name: str
    slug: str
    parent_slug: str | None
    depth: int


EXPANDED_CATEGORY_TREE_V184: tuple[dict[str, object], ...] = (
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
            {
                "name": "Commercial Vehicles",
                "slug": "vehicles-commercial",
                "children": (
                    {"name": "Vans", "slug": "vehicles-commercial-vans"},
                    {"name": "Trucks", "slug": "vehicles-commercial-trucks"},
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
            {
                "name": "Commercial Property",
                "slug": "real-estate-commercial",
                "children": (
                    {"name": "Offices", "slug": "real-estate-commercial-offices"},
                    {"name": "Shops", "slug": "real-estate-commercial-shops"},
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
            {
                "name": "Audio & Video",
                "slug": "electronics-audio-video",
                "children": (
                    {"name": "TVs", "slug": "electronics-tvs"},
                    {"name": "Speakers", "slug": "electronics-speakers"},
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
            {
                "name": "Home Decor",
                "slug": "home-garden-decor",
                "children": (
                    {"name": "Lighting", "slug": "home-garden-lighting"},
                    {"name": "Rugs & Carpets", "slug": "home-garden-rugs-carpets"},
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
            {
                "name": "Trade Jobs",
                "slug": "jobs-trades",
                "children": (
                    {"name": "Construction Jobs", "slug": "jobs-construction"},
                    {"name": "Driving Jobs", "slug": "jobs-driving"},
                ),
            },
        ),
    },
    {
        "name": "Services",
        "slug": "services",
        "children": (
            {
                "name": "Home Services",
                "slug": "services-home",
                "children": (
                    {"name": "Repairs", "slug": "services-home-repairs"},
                    {"name": "Moving Services", "slug": "services-home-moving"},
                ),
            },
            {
                "name": "Lessons & Training",
                "slug": "services-lessons-training",
                "children": (
                    {"name": "Language Lessons", "slug": "services-language-lessons"},
                    {"name": "Music Lessons", "slug": "services-music-lessons"},
                ),
            },
            {
                "name": "Business Services",
                "slug": "services-business",
                "children": (
                    {"name": "Accounting", "slug": "services-accounting"},
                    {"name": "Marketing", "slug": "services-marketing"},
                ),
            },
        ),
    },
    {
        "name": "Fashion",
        "slug": "fashion",
        "children": (
            {
                "name": "Women's Clothing",
                "slug": "fashion-womens-clothing",
                "children": (
                    {"name": "Dresses", "slug": "fashion-womens-dresses"},
                    {"name": "Coats", "slug": "fashion-womens-coats"},
                ),
            },
            {
                "name": "Men's Clothing",
                "slug": "fashion-mens-clothing",
                "children": (
                    {"name": "Shirts", "slug": "fashion-mens-shirts"},
                    {"name": "Suits", "slug": "fashion-mens-suits"},
                ),
            },
            {
                "name": "Shoes & Accessories",
                "slug": "fashion-shoes-accessories",
                "children": (
                    {"name": "Sneakers", "slug": "fashion-sneakers"},
                    {"name": "Bags", "slug": "fashion-bags"},
                ),
            },
        ),
    },
    {
        "name": "Baby & Kids",
        "slug": "baby-kids",
        "children": (
            {
                "name": "Baby Gear",
                "slug": "baby-kids-baby-gear",
                "children": (
                    {"name": "Strollers", "slug": "baby-kids-strollers"},
                    {"name": "Car Seats", "slug": "baby-kids-car-seats"},
                ),
            },
            {
                "name": "Toys",
                "slug": "baby-kids-toys",
                "children": (
                    {"name": "Educational Toys", "slug": "baby-kids-educational-toys"},
                    {"name": "Outdoor Toys", "slug": "baby-kids-outdoor-toys"},
                ),
            },
            {
                "name": "Kids Furniture",
                "slug": "baby-kids-furniture",
                "children": (
                    {"name": "Kids Beds", "slug": "baby-kids-beds"},
                    {"name": "Kids Storage", "slug": "baby-kids-storage"},
                ),
            },
        ),
    },
    {
        "name": "Sports & Hobbies",
        "slug": "sports-hobbies",
        "children": (
            {
                "name": "Sports Equipment",
                "slug": "sports-hobbies-equipment",
                "children": (
                    {"name": "Fitness Equipment", "slug": "sports-hobbies-fitness"},
                    {"name": "Bicycles", "slug": "sports-hobbies-bicycles"},
                ),
            },
            {
                "name": "Musical Instruments",
                "slug": "sports-hobbies-musical-instruments",
                "children": (
                    {"name": "Guitars", "slug": "sports-hobbies-guitars"},
                    {"name": "Keyboards", "slug": "sports-hobbies-keyboards"},
                ),
            },
            {
                "name": "Collectibles",
                "slug": "sports-hobbies-collectibles",
                "children": (
                    {"name": "Coins", "slug": "sports-hobbies-coins"},
                    {"name": "Trading Cards", "slug": "sports-hobbies-trading-cards"},
                ),
            },
        ),
    },
    {
        "name": "Pets",
        "slug": "pets",
        "children": (
            {
                "name": "Pet Supplies",
                "slug": "pets-supplies",
                "children": (
                    {"name": "Pet Beds", "slug": "pets-beds"},
                    {"name": "Pet Carriers", "slug": "pets-carriers"},
                ),
            },
            {
                "name": "Dogs",
                "slug": "pets-dogs",
                "children": (
                    {"name": "Dog Accessories", "slug": "pets-dog-accessories"},
                    {"name": "Dog Training", "slug": "pets-dog-training"},
                ),
            },
            {
                "name": "Cats",
                "slug": "pets-cats",
                "children": (
                    {"name": "Cat Trees", "slug": "pets-cat-trees"},
                    {"name": "Cat Litter Boxes", "slug": "pets-cat-litter-boxes"},
                ),
            },
        ),
    },
)


def flatten_category_tree_v184(
    tree: tuple[dict[str, object], ...] = EXPANDED_CATEGORY_TREE_V184,
    *,
    parent_slug: str | None = None,
    depth: int = 1,
) -> tuple[CategorySeedRecordV184, ...]:
    records: list[CategorySeedRecordV184] = []

    for node in tree:
        name = str(node.get("name", "")).strip()
        slug = str(node.get("slug", "")).strip()

        records.append(
            CategorySeedRecordV184(
                name=name,
                slug=slug,
                parent_slug=parent_slug,
                depth=depth,
            )
        )

        children = node.get("children", ())
        if children:
            records.extend(
                flatten_category_tree_v184(
                    tuple(children),
                    parent_slug=slug,
                    depth=depth + 1,
                )
            )

    return tuple(records)


def validate_category_seed_plan_v184(
    records: tuple[CategorySeedRecordV184, ...],
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

        if record.depth < 1 or record.depth > V184_MAX_CATEGORY_DEPTH:
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


def build_category_seed_plan_v184() -> tuple[CategorySeedRecordV184, ...]:
    records = flatten_category_tree_v184()
    errors = validate_category_seed_plan_v184(records)
    if errors:
        raise ValueError("Invalid v184 category seed plan: " + " | ".join(errors))
    return records


def summarize_category_seed_plan_v184(
    records: tuple[CategorySeedRecordV184, ...],
) -> dict[str, int]:
    return {
        "total": len(records),
        "roots": sum(1 for record in records if record.depth == 1),
        "children": sum(1 for record in records if record.depth == 2),
        "grandchildren": sum(1 for record in records if record.depth == 3),
        "max_depth": max((record.depth for record in records), default=0),
    }
