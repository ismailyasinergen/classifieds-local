"""Owner-scoped seller pricing dashboard for v290."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import (
    CharField,
    Count,
    DateTimeField,
    DecimalField,
    F,
    OuterRef,
    Q,
    Subquery,
)
from django.shortcuts import render

from listings.models import Listing, ListingPriceHistory
from listings.listing_price_integrity_v293 import guardrail_warning_v293


SELLER_PRICING_DASHBOARD_V290 = True
SELLER_PRICING_PAGE_SIZE_V290 = 20
SELLER_PRICING_DEFAULT_SORT_V290 = "recent_change"

SELLER_PRICING_SORT_OPTIONS_V290 = (
    ("recent_change", "Recent price change"),
    ("newest", "Newest listing"),
    ("price_low", "Price: low to high"),
    ("price_high", "Price: high to low"),
)

INITIAL_PRICE_ANNOTATION_V290 = "seller_initial_price_v290"
LATEST_PREVIOUS_PRICE_ANNOTATION_V290 = "seller_latest_previous_price_v290"
LATEST_NEW_PRICE_ANNOTATION_V290 = "seller_latest_new_price_v290"
LATEST_CHANGED_AT_ANNOTATION_V290 = "seller_latest_changed_at_v290"
LATEST_REASON_ANNOTATION_V292 = "seller_latest_reason_v292"
LATEST_GUARDRAIL_ANNOTATION_V293 = "seller_latest_guardrail_v293"
LATEST_REFERENCE_PRICE_ANNOTATION_V293 = "seller_latest_reference_price_v293"


@dataclass(frozen=True)
class SellerPricingEntryV290:
    listing: Listing
    initial_price: Decimal | None
    previous_price: Decimal | None
    transition_price: Decimal | None
    changed_at: object | None
    direction_label: str
    absolute_change: Decimal | None
    percentage_display: str
    history_matches_current_price: bool
    reason_label: str
    guardrail_warning: str

    @property
    def has_price_change(self) -> bool:
        return self.previous_price is not None and self.transition_price is not None


@dataclass(frozen=True)
class SellerPricingDashboardV290:
    page_obj: object
    entries: tuple[SellerPricingEntryV290, ...]
    summary: dict[str, int]
    status_filter: str
    sort_value: str


def _normalize_status_v290(value) -> str:
    normalized = str(value or "").strip()
    valid_statuses = {choice for choice, _label in Listing.Status.choices}
    return normalized if normalized in valid_statuses else ""


def _normalize_sort_v290(value) -> str:
    normalized = str(value or "").strip()
    valid_sorts = {choice for choice, _label in SELLER_PRICING_SORT_OPTIONS_V290}
    if normalized in valid_sorts:
        return normalized
    return SELLER_PRICING_DEFAULT_SORT_V290


def get_seller_pricing_queryset_v290(user, *, status="", sort=""):
    """Return owner-only listings with bounded-query pricing annotations."""

    latest_transition = (
        ListingPriceHistory.objects
        .filter(
            listing_id=OuterRef("pk"),
            previous_price__isnull=False,
            new_price__isnull=False,
        )
        .exclude(previous_price=F("new_price"))
        .order_by("-changed_at", "-pk")
    )
    baseline = (
        ListingPriceHistory.objects
        .filter(
            listing_id=OuterRef("pk"),
            previous_price__isnull=True,
        )
        .order_by("changed_at", "pk")
    )

    queryset = (
        Listing.objects
        .filter(owner=user)
        .select_related("category")
        .annotate(
            **{
                INITIAL_PRICE_ANNOTATION_V290: Subquery(
                    baseline.values("new_price")[:1],
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                LATEST_PREVIOUS_PRICE_ANNOTATION_V290: Subquery(
                    latest_transition.values("previous_price")[:1],
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                LATEST_NEW_PRICE_ANNOTATION_V290: Subquery(
                    latest_transition.values("new_price")[:1],
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                LATEST_CHANGED_AT_ANNOTATION_V290: Subquery(
                    latest_transition.values("changed_at")[:1],
                    output_field=DateTimeField(),
                ),
                LATEST_REASON_ANNOTATION_V292: Subquery(
                    latest_transition.values("reason")[:1],
                    output_field=CharField(max_length=32),
                ),
                LATEST_GUARDRAIL_ANNOTATION_V293: Subquery(
                    latest_transition.values("discount_guardrail_status")[:1],
                    output_field=CharField(max_length=32),
                ),
                LATEST_REFERENCE_PRICE_ANNOTATION_V293: Subquery(
                    latest_transition.values("discount_reference_price")[:1],
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
            }
        )
    )

    normalized_status = _normalize_status_v290(status)
    if normalized_status:
        queryset = queryset.filter(status=normalized_status)

    normalized_sort = _normalize_sort_v290(sort)
    if normalized_sort == "newest":
        return queryset.order_by("-created_at", "-pk")
    if normalized_sort == "price_low":
        return queryset.order_by("price", "pk")
    if normalized_sort == "price_high":
        return queryset.order_by("-price", "-pk")

    return queryset.order_by(
        F(LATEST_CHANGED_AT_ANNOTATION_V290).desc(nulls_last=True),
        "-pk",
    )


def _format_percentage_v290(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return format(rounded, "f").rstrip("0").rstrip(".")


def _build_entry_v290(listing: Listing) -> SellerPricingEntryV290:
    previous_price = getattr(listing, LATEST_PREVIOUS_PRICE_ANNOTATION_V290)
    transition_price = getattr(listing, LATEST_NEW_PRICE_ANNOTATION_V290)
    changed_at = getattr(listing, LATEST_CHANGED_AT_ANNOTATION_V290)

    direction_label = ""
    absolute_change = None
    percentage_display = ""
    if previous_price is not None and transition_price is not None:
        absolute_change = abs(transition_price - previous_price)
        direction_label = (
            "Price reduced"
            if transition_price < previous_price
            else "Price increased"
        )
        if previous_price > 0:
            percentage_display = _format_percentage_v290(
                absolute_change / previous_price * Decimal("100")
            )

    return SellerPricingEntryV290(
        listing=listing,
        initial_price=getattr(listing, INITIAL_PRICE_ANNOTATION_V290),
        previous_price=previous_price,
        transition_price=transition_price,
        changed_at=changed_at,
        direction_label=direction_label,
        absolute_change=absolute_change,
        percentage_display=percentage_display,
        history_matches_current_price=(
            transition_price is not None and transition_price == listing.price
        ),
        reason_label=dict(ListingPriceHistory.Reason.choices).get(
            getattr(listing, LATEST_REASON_ANNOTATION_V292) or "",
            "",
        ),
        guardrail_warning=(
            guardrail_warning_v293(
                getattr(listing, LATEST_REFERENCE_PRICE_ANNOTATION_V293)
            )
            if getattr(listing, LATEST_GUARDRAIL_ANNOTATION_V293)
            else ""
        ),
    )


def _get_seller_pricing_summary_v290(user) -> dict[str, int]:
    return Listing.objects.filter(owner=user).aggregate(
        total=Count("pk"),
        approved=Count("pk", filter=Q(status=Listing.Status.APPROVED)),
        pending=Count("pk", filter=Q(status=Listing.Status.PENDING)),
        archived=Count("pk", filter=Q(status=Listing.Status.ARCHIVED)),
    )


def build_seller_pricing_dashboard_v290(
    user,
    *,
    page_number=None,
    status="",
    sort="",
) -> SellerPricingDashboardV290:
    normalized_status = _normalize_status_v290(status)
    normalized_sort = _normalize_sort_v290(sort)
    paginator = Paginator(
        get_seller_pricing_queryset_v290(
            user,
            status=normalized_status,
            sort=normalized_sort,
        ),
        SELLER_PRICING_PAGE_SIZE_V290,
    )
    page_obj = paginator.get_page(page_number)
    return SellerPricingDashboardV290(
        page_obj=page_obj,
        entries=tuple(_build_entry_v290(listing) for listing in page_obj.object_list),
        summary=_get_seller_pricing_summary_v290(user),
        status_filter=normalized_status,
        sort_value=normalized_sort,
    )


@login_required
def seller_pricing_dashboard_v290(request):
    dashboard = build_seller_pricing_dashboard_v290(
        request.user,
        page_number=request.GET.get("page"),
        status=request.GET.get("status"),
        sort=request.GET.get("sort"),
    )
    return render(
        request,
        "accounts/seller_pricing_dashboard_v290.html",
        {
            "page_title": "Seller pricing",
            "pricing_entries_v290": dashboard.entries,
            "page_obj": dashboard.page_obj,
            "pricing_summary_v290": dashboard.summary,
            "status_filter_v290": dashboard.status_filter,
            "sort_value_v290": dashboard.sort_value,
            "status_options_v290": Listing.Status.choices,
            "sort_options_v290": SELLER_PRICING_SORT_OPTIONS_V290,
        },
    )
