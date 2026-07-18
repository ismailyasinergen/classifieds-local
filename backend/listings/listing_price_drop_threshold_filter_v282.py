"""
MINIMUM_PRICE_DROP_FILTERS_V282

Strict public threshold validation and shared database-side filtering.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from django.db.models import QuerySet

from .listing_biggest_price_drop_sort_v281 import (
    PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281,
    PRICE_DROP_DISCOUNT_PERCENTAGE_ANNOTATION_V281,
    annotate_biggest_price_drop_values_v281,
)
from .listing_price_drop_period_filter_v280 import (
    apply_price_drop_period_filter_v280,
)


MINIMUM_PRICE_DROP_FILTERS_V282 = True

MIN_PRICE_DROP_AMOUNT_PARAM_V282 = "min_price_drop_amount"
MIN_PRICE_DROP_PERCENT_PARAM_V282 = "min_price_drop_percent"
MIN_PRICE_DROP_AMOUNT_LABEL_V282 = "Minimum drop amount"
MIN_PRICE_DROP_PERCENT_LABEL_V282 = "Minimum discount"

PRICE_DROP_AMOUNT_MAX_DIGITS_V282 = 13
PRICE_DROP_AMOUNT_DECIMAL_PLACES_V282 = 2
PRICE_DROP_PERCENT_MAX_DIGITS_V282 = 24
PRICE_DROP_PERCENT_DECIMAL_PLACES_V282 = 10

PLAIN_DECIMAL_PATTERN_V282 = re.compile(r"^\d+(?:\.\d+)?$")


def _normalize_positive_decimal_v282(
    value,
    *,
    max_digits: int,
    decimal_places: int,
) -> str:
    text = str(value or "").strip()
    if not text or not PLAIN_DECIMAL_PATTERN_V282.fullmatch(text):
        return ""

    integer_part, separator, fractional_part = text.partition(".")
    if len(integer_part) > max_digits - decimal_places:
        return ""
    if separator and len(fractional_part) > decimal_places:
        return ""
    if len(integer_part) + len(fractional_part) > max_digits:
        return ""

    try:
        decimal_value = Decimal(text)
    except (InvalidOperation, ValueError, TypeError):
        return ""

    if not decimal_value.is_finite() or decimal_value <= 0:
        return ""

    return text


def normalize_min_price_drop_amount_v282(value) -> str:
    return _normalize_positive_decimal_v282(
        value,
        max_digits=PRICE_DROP_AMOUNT_MAX_DIGITS_V282,
        decimal_places=PRICE_DROP_AMOUNT_DECIMAL_PLACES_V282,
    )


def normalize_min_price_drop_percent_v282(value) -> str:
    return _normalize_positive_decimal_v282(
        value,
        max_digits=PRICE_DROP_PERCENT_MAX_DIGITS_V282,
        decimal_places=PRICE_DROP_PERCENT_DECIMAL_PLACES_V282,
    )


def get_min_price_drop_amount_value_v282(request) -> str:
    return normalize_min_price_drop_amount_v282(
        request.GET.get(MIN_PRICE_DROP_AMOUNT_PARAM_V282, "")
    )


def get_min_price_drop_percent_value_v282(request) -> str:
    return normalize_min_price_drop_percent_v282(
        request.GET.get(MIN_PRICE_DROP_PERCENT_PARAM_V282, "")
    )


def format_price_drop_threshold_v282(value) -> str:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return ""

    if not decimal_value.is_finite():
        return ""

    formatted = format(decimal_value, "f")
    if "." in formatted:
        formatted = formatted.rstrip("0").rstrip(".")
    return formatted


def apply_minimum_price_drop_filters_v282(
    queryset: QuerySet,
    request,
    *,
    require_current_reduction: bool = False,
    require_metrics: bool = False,
) -> QuerySet:
    """Apply v282 thresholds while sharing v280 qualification and v281 metrics."""

    amount_value = get_min_price_drop_amount_value_v282(request)
    percent_value = get_min_price_drop_percent_value_v282(request)
    thresholds_active = bool(amount_value or percent_value)
    metrics_required = require_metrics or thresholds_active

    queryset = apply_price_drop_period_filter_v280(
        queryset,
        request,
        require_current_reduction=(
            require_current_reduction or metrics_required
        ),
    )

    if not metrics_required:
        return queryset

    queryset = annotate_biggest_price_drop_values_v281(queryset)

    threshold_filters = {}
    if amount_value:
        threshold_filters[
            PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281 + "__gte"
        ] = Decimal(amount_value)
    if percent_value:
        threshold_filters[
            PRICE_DROP_DISCOUNT_PERCENTAGE_ANNOTATION_V281 + "__gte"
        ] = Decimal(percent_value)

    if not threshold_filters:
        return queryset

    return queryset.filter(**threshold_filters)
