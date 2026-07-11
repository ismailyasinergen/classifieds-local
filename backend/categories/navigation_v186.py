from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from django.http import QueryDict

from categories.models import Category


V186_CATEGORY_NAVIGATION_FILTER_MARKER = "V186_CATEGORY_NAVIGATION_LISTING_FILTER_INTEGRATION"


@dataclass(frozen=True)
class CategoryNavigationNodeV186:
    name: str
    slug: str
    depth: int
    url: str
    is_selected: bool
    is_active_branch: bool
    children: tuple["CategoryNavigationNodeV186", ...]


def normalize_category_slug_v186(slug: str | None) -> str:
    return (slug or "").strip()


def get_category_by_slug_v186(slug: str | None) -> Category | None:
    normalized_slug = normalize_category_slug_v186(slug)
    if not normalized_slug:
        return None

    return Category.objects.filter(slug=normalized_slug).select_related("parent").first()


def get_category_descendant_ids_v186(category: Category) -> tuple[int, ...]:
    ids: list[int] = [category.pk]
    queue: list[Category] = [category]
    seen: set[int] = {category.pk}

    while queue:
        current = queue.pop(0)
        children = Category.objects.filter(parent=current).order_by("name", "id")
        for child in children:
            if child.pk in seen:
                continue
            seen.add(child.pk)
            ids.append(child.pk)
            queue.append(child)

    return tuple(ids)


def get_category_descendant_slugs_v186(category: Category) -> tuple[str, ...]:
    ids = get_category_descendant_ids_v186(category)
    return tuple(
        Category.objects.filter(pk__in=ids)
        .order_by("name", "id")
        .values_list("slug", flat=True)
    )


def filter_queryset_by_category_slug_v186(
    queryset,
    category_slug: str | None,
    *,
    category_field: str = "category",
):
    selected_category = get_category_by_slug_v186(category_slug)
    if selected_category is None:
        return queryset, None, tuple()

    category_ids = get_category_descendant_ids_v186(selected_category)
    filtered_queryset = queryset.filter(**{f"{category_field}_id__in": category_ids})

    return filtered_queryset, selected_category, category_ids


def _copy_query_params_v186(query_params: QueryDict | dict[str, Any] | None) -> dict[str, list[str]]:
    copied: dict[str, list[str]] = {}

    if not query_params:
        return copied

    if hasattr(query_params, "lists"):
        iterator = query_params.lists()
    else:
        iterator = query_params.items()

    for key, value in iterator:
        if isinstance(value, (list, tuple)):
            copied[str(key)] = [str(item) for item in value]
        else:
            copied[str(key)] = [str(value)]

    return copied


def build_category_filter_url_v186(
    path: str,
    query_params: QueryDict | dict[str, Any] | None,
    category_slug: str | None,
) -> str:
    params = _copy_query_params_v186(query_params)
    params.pop("page", None)

    normalized_slug = normalize_category_slug_v186(category_slug)
    if normalized_slug:
        params["category"] = [normalized_slug]
    else:
        params.pop("category", None)

    querystring = urlencode(params, doseq=True)
    clean_path = path or ""

    return f"{clean_path}?{querystring}" if querystring else clean_path


def _active_slug_chain_v186(selected_category: Category | None) -> tuple[str, ...]:
    if selected_category is None:
        return tuple()

    slugs: list[str] = []
    current: Category | None = selected_category

    while current is not None:
        slugs.append(current.slug)
        current = current.parent

    return tuple(slugs)


def _build_navigation_node_v186(
    category: Category,
    *,
    selected_slug: str,
    active_slugs: tuple[str, ...],
    query_params: QueryDict | dict[str, Any] | None,
    path: str,
    depth: int,
) -> CategoryNavigationNodeV186:
    children = tuple(
        _build_navigation_node_v186(
            child,
            selected_slug=selected_slug,
            active_slugs=active_slugs,
            query_params=query_params,
            path=path,
            depth=depth + 1,
        )
        for child in Category.objects.filter(parent=category).order_by("name", "id")
    )

    return CategoryNavigationNodeV186(
        name=category.name,
        slug=category.slug,
        depth=depth,
        url=build_category_filter_url_v186(path, query_params, category.slug),
        is_selected=category.slug == selected_slug,
        is_active_branch=category.slug in active_slugs,
        children=children,
    )


def build_category_navigation_context_v186(
    selected_slug: str | None = None,
    *,
    query_params: QueryDict | dict[str, Any] | None = None,
    path: str = "",
) -> dict[str, object]:
    normalized_selected_slug = normalize_category_slug_v186(selected_slug)
    selected_category = get_category_by_slug_v186(normalized_selected_slug)
    active_slugs = _active_slug_chain_v186(selected_category)

    roots = tuple(
        _build_navigation_node_v186(
            category,
            selected_slug=normalized_selected_slug,
            active_slugs=active_slugs,
            query_params=query_params,
            path=path,
            depth=1,
        )
        for category in Category.objects.filter(parent__isnull=True).order_by("name", "id")
    )

    return {
        "marker": V186_CATEGORY_NAVIGATION_FILTER_MARKER,
        "roots": roots,
        "selected_category": selected_category,
        "selected_slug": normalized_selected_slug,
        "active_slugs": active_slugs,
        "clear_url": build_category_filter_url_v186(path, query_params, None),
        "root_count": len(roots),
    }
