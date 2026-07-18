"""
BIGGEST_PRICE_DROP_SORT_V281

Database-side discount annotations and deterministic public browse ordering.
"""

from __future__ import annotations

from decimal import Decimal

from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    QuerySet,
    Value,
)

from .listing_price_drop_filter_v278 import (
    PRICE_DROP_PREVIOUS_ANNOTATION_V278,
)
from .listing_price_drop_period_filter_v280 import (
    PRICE_DROP_CHANGED_AT_ANNOTATION_V280,
    apply_price_drop_period_filter_v280,
)


BIGGEST_PRICE_DROP_SORT_V281 = True
BIGGEST_PRICE_DROP_SORT_VALUE_V281 = "biggest_price_drop"
BIGGEST_PRICE_DROP_SORT_LABEL_V281 = "Biggest discount"

PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281 = (
    "price_drop_discount_amount_v281"
)
PRICE_DROP_DISCOUNT_PERCENTAGE_ANNOTATION_V281 = (
    "price_drop_discount_percentage_v281"
)


def annotate_biggest_price_drop_values_v281(
    queryset: QuerySet,
) -> QuerySet:
    """Annotate current discount amount and percentage for ordering."""

    amount_output = DecimalField(
        max_digits=13,
        decimal_places=2,
    )
    percentage_output = DecimalField(
        max_digits=24,
        decimal_places=10,
    )

    queryset = queryset.filter(
        **{
            PRICE_DROP_PREVIOUS_ANNOTATION_V278
            + "__gt": Decimal("0.00"),
        }
    ).annotate(
        **{
            PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281: (
                ExpressionWrapper(
                    F(PRICE_DROP_PREVIOUS_ANNOTATION_V278)
                    - F("price"),
                    output_field=amount_output,
                )
            ),
        }
    )

    return queryset.annotate(
        **{
            PRICE_DROP_DISCOUNT_PERCENTAGE_ANNOTATION_V281: (
                ExpressionWrapper(
                    F(PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281)
                    * Value(Decimal("100.0000000000"))
                    / F(PRICE_DROP_PREVIOUS_ANNOTATION_V278),
                    output_field=percentage_output,
                )
            ),
        }
    )


def apply_biggest_price_drop_sort_v281(
    queryset: QuerySet,
    request,
) -> QuerySet:
    """Restrict to valid current reductions and apply the v281 ordering."""

    queryset = apply_price_drop_period_filter_v280(
        queryset,
        request,
        require_current_reduction=True,
    )
    queryset = annotate_biggest_price_drop_values_v281(queryset)

    return order_biggest_price_drop_v281(queryset)


def order_biggest_price_drop_v281(
    queryset: QuerySet,
) -> QuerySet:
    """Apply the exact v281 deterministic metric ordering."""

    return queryset.order_by(
        f"-{PRICE_DROP_DISCOUNT_PERCENTAGE_ANNOTATION_V281}",
        f"-{PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281}",
        f"-{PRICE_DROP_CHANGED_AT_ANNOTATION_V280}",
        "-pk",
    )
