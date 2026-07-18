"""
PRICE_DROP_PERIOD_FILTER_V280

Shared public-browse filtering for current price reductions within a supported
time period.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import DateTimeField, F, OuterRef, QuerySet, Subquery
from django.utils import timezone

from .listing_price_drop_filter_v278 import (
    PRICE_DROP_PREVIOUS_ANNOTATION_V278,
    PRICE_DROP_TRANSITION_ANNOTATION_V278,
    annotate_current_price_transition_v278,
    price_drop_filter_is_enabled_v278,
)
from .models import ListingPriceHistory


PRICE_DROP_PERIOD_FILTER_V280 = True
PRICE_DROP_PERIOD_PARAM_V280 = "price_drop_period"
PRICE_DROP_PERIODS_V280 = {
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}
PRICE_DROP_PERIOD_LABELS_V280 = {
    "24h": "Last 24 hours",
    "7d": "Last 7 days",
    "30d": "Last 30 days",
}
PRICE_DROP_CHANGED_AT_ANNOTATION_V280 = (
    "price_drop_changed_at_v280"
)


def normalize_price_drop_period_value_v280(value) -> str:
    value = str(value or "").strip()
    if value in PRICE_DROP_PERIODS_V280:
        return value
    return ""


def get_price_drop_period_value_v280(request) -> str:
    return normalize_price_drop_period_value_v280(
        request.GET.get(PRICE_DROP_PERIOD_PARAM_V280, "")
    )


def get_price_drop_period_label_v280(value) -> str:
    value = normalize_price_drop_period_value_v280(value)
    return PRICE_DROP_PERIOD_LABELS_V280.get(value, "")


def annotate_current_price_drop_time_v280(
    queryset: QuerySet,
    *,
    changed_at_annotation: str = PRICE_DROP_CHANGED_AT_ANNOTATION_V280,
) -> QuerySet:
    queryset = annotate_current_price_transition_v278(queryset)

    latest_transition = (
        ListingPriceHistory.objects
        .filter(
            listing_id=OuterRef("pk"),
            previous_price__isnull=False,
        )
        .order_by("-changed_at", "-pk")
    )

    return queryset.annotate(
        **{
            changed_at_annotation: Subquery(
                latest_transition.values("changed_at")[:1],
                output_field=DateTimeField(),
            )
        }
    )


def apply_price_drop_period_filter_v280(
    queryset: QuerySet,
    request,
    *,
    require_current_reduction: bool = False,
    now=None,
) -> QuerySet:
    """
    Apply v278 current-drop and v280 period semantics with one annotation set.

    ``require_current_reduction`` is used by the v279 recent-drop sort, which
    implicitly limits results to current reductions even without filter params.
    """

    period_value = get_price_drop_period_value_v280(request)
    v278_filter_enabled = price_drop_filter_is_enabled_v278(request)

    if not (
        period_value
        or v278_filter_enabled
        or require_current_reduction
    ):
        return queryset

    needs_changed_at = bool(period_value) or require_current_reduction
    if needs_changed_at:
        queryset = annotate_current_price_drop_time_v280(queryset)
    else:
        queryset = annotate_current_price_transition_v278(queryset)

    queryset = queryset.filter(
        **{
            PRICE_DROP_PREVIOUS_ANNOTATION_V278
            + "__gt": F(PRICE_DROP_TRANSITION_ANNOTATION_V278),
            PRICE_DROP_TRANSITION_ANNOTATION_V278: F("price"),
        }
    )

    if not period_value:
        return queryset

    reference_time = now if now is not None else timezone.now()
    if timezone.is_naive(reference_time):
        reference_time = timezone.make_aware(
            reference_time,
            timezone.get_current_timezone(),
        )

    cutoff = reference_time - PRICE_DROP_PERIODS_V280[period_value]
    return queryset.filter(
        **{
            PRICE_DROP_CHANGED_AT_ANNOTATION_V280
            + "__gte": cutoff,
        }
    )
