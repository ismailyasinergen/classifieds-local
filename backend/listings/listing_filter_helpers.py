"""
LISTING_FILTER_HELPER_EXTRACTION_V142

Extracted listing filter helper functions.

This module is intentionally small at v142. It starts by housing
apply_listing_filters, which was previously defined in backend/listings/views.py.

Import hygiene note:
Only imports required by apply_listing_filters should live here. View-only
classes, mixins, decorators, forms, and template helpers belong in views.py.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from django.db.models import Q
from categories.models import Category

from .listing_price_drop_filter_v278 import (
    apply_price_drop_filter_v278,
)


def apply_listing_filters(queryset, request):
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    category_slug = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(location__icontains=q)
            | Q(category__name__icontains=q)
        )

    if location:
        queryset = queryset.filter(location__icontains=location)

    if category_slug:
        category = Category.objects.filter(slug=category_slug).first()
        if category:
            queryset = queryset.filter(category_id__in=category.get_descendant_ids())

    try:
        if min_price:
            queryset = queryset.filter(price__gte=Decimal(min_price))
    except InvalidOperation:
        pass

    try:
        if max_price:
            queryset = queryset.filter(price__lte=Decimal(max_price))
    except InvalidOperation:
        pass

    # PRICE_DROP_PUBLIC_BROWSE_FILTER_V278
    queryset = apply_price_drop_filter_v278(
        queryset,
        request,
    )

    if sort == "price_low":
        queryset = queryset.order_by("price")
    elif sort == "price_high":
        queryset = queryset.order_by("-price")
    else:
        queryset = queryset.order_by("-top_listing_priority", "-created_at")

    return queryset
