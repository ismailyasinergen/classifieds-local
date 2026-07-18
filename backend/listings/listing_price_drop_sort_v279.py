"""
RECENT_PRICE_DROP_SORT_V279

Shared public listing ordering with recent price-drop support.
"""

from .listing_biggest_price_drop_sort_v281 import (
    BIGGEST_PRICE_DROP_SORT_VALUE_V281,
    order_biggest_price_drop_v281,
)
from .listing_price_drop_period_filter_v280 import (
    PRICE_DROP_CHANGED_AT_ANNOTATION_V280,
    annotate_current_price_drop_time_v280,
)
from .listing_price_drop_threshold_filter_v282 import (
    apply_minimum_price_drop_filters_v282,
)


RECENT_PRICE_DROP_SORT_V279 = True
RECENT_PRICE_DROP_SORT_VALUE_V279 = "recent_price_drop"
RECENT_PRICE_DROP_SORT_LABEL_V279 = "Recently reduced"

PRICE_DROP_CHANGED_AT_ANNOTATION_V279 = (
    "price_drop_changed_at_v279"
)


def annotate_current_price_drop_time_v279(queryset):
    return annotate_current_price_drop_time_v280(
        queryset,
        changed_at_annotation=(
            PRICE_DROP_CHANGED_AT_ANNOTATION_V279
        ),
    )


def apply_public_listing_sort_v279(
    queryset,
    request,
):
    sort_value = request.GET.get(
        "sort",
        "newest",
    ).strip()

    biggest_drop_sort = (
        sort_value == BIGGEST_PRICE_DROP_SORT_VALUE_V281
    )
    queryset = apply_minimum_price_drop_filters_v282(
        queryset,
        request,
        require_current_reduction=(
            sort_value
            == RECENT_PRICE_DROP_SORT_VALUE_V279
        ),
        require_metrics=biggest_drop_sort,
    )

    if biggest_drop_sort:
        return order_biggest_price_drop_v281(queryset)

    if sort_value == RECENT_PRICE_DROP_SORT_VALUE_V279:
        return queryset.order_by(
            f"-{PRICE_DROP_CHANGED_AT_ANNOTATION_V280}",
            "-pk",
        )

    if sort_value == "price_low":
        return queryset.order_by("price", "pk")

    if sort_value == "price_high":
        return queryset.order_by("-price", "-pk")

    return queryset.order_by(
        "-top_listing_priority",
        "-created_at",
        "-pk",
    )
