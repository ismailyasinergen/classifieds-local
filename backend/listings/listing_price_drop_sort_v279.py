"""
RECENT_PRICE_DROP_SORT_V279

Shared public listing ordering with recent price-drop support.
"""

from django.db.models import (
    DateTimeField,
    F,
    OuterRef,
    Subquery,
)

from .listing_price_drop_filter_v278 import (
    PRICE_DROP_PREVIOUS_ANNOTATION_V278,
    PRICE_DROP_TRANSITION_ANNOTATION_V278,
    annotate_current_price_transition_v278,
    apply_price_drop_filter_v278,
)
from .models import ListingPriceHistory


RECENT_PRICE_DROP_SORT_V279 = True
RECENT_PRICE_DROP_SORT_VALUE_V279 = "recent_price_drop"
RECENT_PRICE_DROP_SORT_LABEL_V279 = "Recently reduced"

PRICE_DROP_CHANGED_AT_ANNOTATION_V279 = (
    "price_drop_changed_at_v279"
)


def annotate_current_price_drop_time_v279(queryset):
    queryset = annotate_current_price_transition_v278(
        queryset
    )

    latest_transition = (
        ListingPriceHistory.objects
        .filter(
            listing_id=OuterRef("pk"),
            previous_price__isnull=False,
        )
        .order_by("-changed_at", "-pk")
    )

    return queryset.annotate(
        price_drop_changed_at_v279=Subquery(
            latest_transition.values("changed_at")[:1],
            output_field=DateTimeField(),
        )
    )


def apply_public_listing_sort_v279(
    queryset,
    request,
):
    queryset = apply_price_drop_filter_v278(
        queryset,
        request,
    )

    sort_value = request.GET.get(
        "sort",
        "newest",
    ).strip()

    if sort_value == RECENT_PRICE_DROP_SORT_VALUE_V279:
        queryset = annotate_current_price_drop_time_v279(
            queryset
        )

        return queryset.filter(
            **{
                PRICE_DROP_PREVIOUS_ANNOTATION_V278
                + "__gt": F(
                    PRICE_DROP_TRANSITION_ANNOTATION_V278
                ),
                PRICE_DROP_TRANSITION_ANNOTATION_V278: F(
                    "price"
                ),
            }
        ).order_by(
            "-price_drop_changed_at_v279",
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
