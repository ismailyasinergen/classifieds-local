"""
PRICE_DROP_PUBLIC_BROWSE_FILTER_V278

QuerySet-level filtering for listings whose latest real price transition is a
current reduction.
"""

from __future__ import annotations

from django.db.models import (
    CharField,
    DecimalField,
    F,
    OuterRef,
    QuerySet,
    Subquery,
)

from .models import ListingPriceHistory


PRICE_DROP_PUBLIC_BROWSE_FILTER_V278 = True

PRICE_DROP_FILTER_PARAM_V278 = "price_drops"
PRICE_DROP_FILTER_ENABLED_VALUE_V278 = "1"

PRICE_DROP_PREVIOUS_ANNOTATION_V278 = (
    "price_drop_previous_price_v278"
)

PRICE_DROP_TRANSITION_ANNOTATION_V278 = (
    "price_drop_transition_price_v278"
)
PRICE_DROP_GUARDRAIL_ANNOTATION_V293 = (
    "price_drop_guardrail_status_v293"
)


def price_drop_filter_is_enabled_v278(
    request,
) -> bool:
    value = (
        request.GET
        .get(
            PRICE_DROP_FILTER_PARAM_V278,
            "",
        )
        .strip()
    )

    return (
        value
        == PRICE_DROP_FILTER_ENABLED_VALUE_V278
    )


def annotate_current_price_transition_v278(
    queryset: QuerySet,
) -> QuerySet:
    """
    Annotate the newest non-baseline transition for each listing.

    Ordering by changed_at and then primary key matches the v275/v276
    price-history contract when multiple events share a timestamp.
    """

    latest_transition = (
        ListingPriceHistory.objects
        .filter(
            listing_id=OuterRef("pk"),
            previous_price__isnull=False,
        )
        .order_by(
            "-changed_at",
            "-pk",
        )
    )

    decimal_output = DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    return queryset.annotate(
        price_drop_previous_price_v278=Subquery(
            latest_transition.values(
                "previous_price"
            )[:1],
            output_field=decimal_output,
        ),
        price_drop_transition_price_v278=Subquery(
            latest_transition.values(
                "new_price"
            )[:1],
            output_field=decimal_output,
        ),
        price_drop_guardrail_status_v293=Subquery(
            latest_transition.values(
                "discount_guardrail_status"
            )[:1],
            output_field=CharField(max_length=32),
        ),
    )


def apply_price_drop_filter_v278(
    queryset: QuerySet,
    request,
) -> QuerySet:
    """
    Apply the optional public-browse price-drop filter.

    A listing qualifies only when:

    1. the filter value is exactly ``price_drops=1``;
    2. a non-baseline price transition exists;
    3. the latest transition reduced the price;
    4. that transition's new price still equals the listing's current price;
    5. v293 has not restricted the transition after a raise-then-drop sequence.

    The final requirement prevents an old or stale reduction from appearing as
    a current price drop.
    """

    if not price_drop_filter_is_enabled_v278(
        request
    ):
        return queryset

    queryset = (
        annotate_current_price_transition_v278(
            queryset
        )
    )

    return queryset.filter(
        price_drop_previous_price_v278__gt=F(
            PRICE_DROP_TRANSITION_ANNOTATION_V278
        ),
        price_drop_transition_price_v278=F(
            "price"
        ),
        price_drop_guardrail_status_v293="",
    )
