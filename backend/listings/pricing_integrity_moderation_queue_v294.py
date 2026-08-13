"""Staff-only pricing-integrity moderation queue for v294."""

from __future__ import annotations

from dataclasses import dataclass

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import BooleanField, Case, F, OuterRef, Q, Subquery, Value, When

from .listing_price_integrity_v293 import (
    DISCOUNT_GUARDRAIL_CHOICES_V293,
    DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
)
from .models import Listing, ListingPriceHistory


PRICING_INTEGRITY_MODERATION_QUEUE_V294 = True
PRICING_INTEGRITY_QUEUE_PAGE_SIZE_V294 = 50
PRICING_INTEGRITY_SEARCH_MAX_LENGTH_V294 = 100

STATE_CURRENT_V294 = "current"
STATE_HISTORICAL_V294 = "historical"
STATE_CHOICES_V294 = (
    (STATE_CURRENT_V294, "Current restriction"),
    (STATE_HISTORICAL_V294, "Historical restriction"),
)

GUARDRAIL_FILTER_RECENT_INCREASE_V294 = "recent_price_increase"
GUARDRAIL_FILTER_TO_STATUS_V294 = {
    GUARDRAIL_FILTER_RECENT_INCREASE_V294: (
        DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293
    ),
}
GUARDRAIL_LABELS_BY_STATUS_V294 = dict(DISCOUNT_GUARDRAIL_CHOICES_V293)
GUARDRAIL_CHOICES_V294 = tuple(
    (
        filter_value,
        GUARDRAIL_LABELS_BY_STATUS_V294[status],
    )
    for filter_value, status in GUARDRAIL_FILTER_TO_STATUS_V294.items()
)
GUARDRAIL_VALUES_V294 = set(GUARDRAIL_FILTER_TO_STATUS_V294)
GUARDRAIL_STATUSES_V294 = set(GUARDRAIL_FILTER_TO_STATUS_V294.values())
LISTING_STATUS_VALUES_V294 = {value for value, _label in Listing.Status.choices}
STATE_VALUES_V294 = {value for value, _label in STATE_CHOICES_V294}


@dataclass(frozen=True)
class PricingIntegrityQueueFiltersV294:
    query: str = ""
    guardrail_status: str = ""
    listing_status: str = ""
    state: str = ""


def parse_pricing_integrity_queue_filters_v294(params):
    query = str(params.get("q", "") or "").strip()
    query = query[:PRICING_INTEGRITY_SEARCH_MAX_LENGTH_V294]

    guardrail_status = str(params.get("guardrail", "") or "").strip()
    if guardrail_status not in GUARDRAIL_VALUES_V294:
        guardrail_status = ""

    listing_status = str(params.get("listing_status", "") or "").strip()
    if listing_status not in LISTING_STATUS_VALUES_V294:
        listing_status = ""

    state = str(params.get("state", "") or "").strip()
    if state not in STATE_VALUES_V294:
        state = ""

    return PricingIntegrityQueueFiltersV294(
        query=query,
        guardrail_status=guardrail_status,
        listing_status=listing_status,
        state=state,
    )


def build_pricing_integrity_queue_queryset_v294(filters):
    latest_transition_id = (
        ListingPriceHistory.objects
        .filter(
            listing_id=OuterRef("listing_id"),
            previous_price__isnull=False,
        )
        .order_by("-changed_at", "-pk")
        .values("pk")[:1]
    )

    queryset = (
        ListingPriceHistory.objects
        .filter(discount_guardrail_status__in=GUARDRAIL_STATUSES_V294)
        .select_related(
            "listing",
            "listing__owner",
            "listing__category",
        )
        .annotate(
            latest_transition_id_v294=Subquery(latest_transition_id),
        )
        .annotate(
            is_current_restriction_v294=Case(
                When(
                    Q(pk=F("latest_transition_id_v294"))
                    & Q(new_price=F("listing__price")),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
    )

    if filters.guardrail_status:
        queryset = queryset.filter(
            discount_guardrail_status=(
                GUARDRAIL_FILTER_TO_STATUS_V294[filters.guardrail_status]
            ),
        )

    if filters.listing_status:
        queryset = queryset.filter(listing__status=filters.listing_status)

    if filters.state == STATE_CURRENT_V294:
        queryset = queryset.filter(is_current_restriction_v294=True)
    elif filters.state == STATE_HISTORICAL_V294:
        queryset = queryset.filter(is_current_restriction_v294=False)

    if filters.query:
        queryset = queryset.filter(
            Q(listing__title__icontains=filters.query)
            | Q(listing__owner__username__icontains=filters.query)
        )

    return queryset.order_by("-changed_at", "-pk")


def paginate_pricing_integrity_queue_v294(queryset, page_number):
    paginator = Paginator(queryset, PRICING_INTEGRITY_QUEUE_PAGE_SIZE_V294)
    try:
        return paginator.page(page_number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


__all__ = [
    "GUARDRAIL_CHOICES_V294",
    "PRICING_INTEGRITY_MODERATION_QUEUE_V294",
    "PRICING_INTEGRITY_QUEUE_PAGE_SIZE_V294",
    "PricingIntegrityQueueFiltersV294",
    "STATE_CHOICES_V294",
    "build_pricing_integrity_queue_queryset_v294",
    "paginate_pricing_integrity_queue_v294",
    "parse_pricing_integrity_queue_filters_v294",
]
