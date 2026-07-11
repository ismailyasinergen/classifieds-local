from __future__ import annotations

from dataclasses import dataclass

from django.contrib import admin

import categories.admin as category_admin  # noqa: F401 - ensures admin registration is loaded
from categories.admin import CategoryAdmin
from categories.models import Category
from categories.seed_taxonomy_v184 import build_category_seed_plan_v184


V185_CATEGORY_SEED_VERIFICATION_MARKER = "V185_CATEGORY_SEED_APPLY_ADMIN_VERIFICATION"
V185_EXPECTED_TOTAL_CATEGORIES = 100
V185_EXPECTED_MAX_DEPTH = 3


@dataclass(frozen=True)
class CategorySeedVerificationReportV185:
    marker: str
    planned_count: int
    existing_planned_count: int
    missing_count: int
    mismatched_count: int
    extra_count: int
    max_depth: int
    admin_registered: bool
    admin_fields_ok: bool
    verified: bool
    missing_slugs: tuple[str, ...]
    mismatched_slugs: tuple[str, ...]
    extra_slugs: tuple[str, ...]


def _category_depth(category: Category) -> int:
    depth = 1
    seen: set[int] = set()
    parent = category.parent

    while parent is not None:
        if parent.pk in seen:
            return V185_EXPECTED_MAX_DEPTH + 1
        seen.add(parent.pk)
        depth += 1
        parent = parent.parent

    return depth


def _admin_fields_are_safe() -> bool:
    registered_admin = admin.site._registry.get(Category)
    if not isinstance(registered_admin, CategoryAdmin):
        return False

    return all(
        (
            registered_admin.list_display == ("name", "slug", "parent"),
            registered_admin.list_filter == ("parent",),
            registered_admin.search_fields == ("name", "slug"),
            registered_admin.prepopulated_fields == {"slug": ("name",)},
        )
    )


def build_category_seed_verification_report_v185() -> CategorySeedVerificationReportV185:
    records = build_category_seed_plan_v184()
    planned_by_slug = {record.slug: record for record in records}
    planned_slugs = set(planned_by_slug)

    existing_categories = {
        category.slug: category
        for category in Category.objects.select_related("parent").filter(slug__in=planned_slugs)
    }

    missing_slugs: list[str] = []
    mismatched_slugs: list[str] = []
    depths: list[int] = []

    for slug, record in planned_by_slug.items():
        category = existing_categories.get(slug)
        if category is None:
            missing_slugs.append(slug)
            continue

        parent_slug = category.parent.slug if category.parent_id else None
        if category.name != record.name or parent_slug != record.parent_slug:
            mismatched_slugs.append(slug)

        depths.append(_category_depth(category))

    extra_slugs = tuple(
        Category.objects.exclude(slug__in=planned_slugs)
        .order_by("slug")
        .values_list("slug", flat=True)
    )

    max_depth = max(depths, default=0)
    admin_registered = Category in admin.site._registry
    admin_fields_ok = _admin_fields_are_safe()

    verified = all(
        (
            len(records) == V185_EXPECTED_TOTAL_CATEGORIES,
            len(existing_categories) == V185_EXPECTED_TOTAL_CATEGORIES,
            not missing_slugs,
            not mismatched_slugs,
            max_depth <= V185_EXPECTED_MAX_DEPTH,
            admin_registered,
            admin_fields_ok,
        )
    )

    return CategorySeedVerificationReportV185(
        marker=V185_CATEGORY_SEED_VERIFICATION_MARKER,
        planned_count=len(records),
        existing_planned_count=len(existing_categories),
        missing_count=len(missing_slugs),
        mismatched_count=len(mismatched_slugs),
        extra_count=len(extra_slugs),
        max_depth=max_depth,
        admin_registered=admin_registered,
        admin_fields_ok=admin_fields_ok,
        verified=verified,
        missing_slugs=tuple(missing_slugs),
        mismatched_slugs=tuple(mismatched_slugs),
        extra_slugs=extra_slugs,
    )
