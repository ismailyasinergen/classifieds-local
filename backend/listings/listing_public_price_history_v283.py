"""Public listing price-history timeline queries and display values for v283."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import F


PUBLIC_LISTING_PRICE_HISTORY_TIMELINE_V283 = True
PUBLIC_PRICE_HISTORY_LIMIT_V283 = 20
PUBLIC_PRICE_HISTORY_CACHE_ATTRIBUTE_V283 = (
    "_public_price_history_rows_v283"
)
PUBLIC_PRICE_HISTORY_PERCENTAGE_QUANTUM_V283 = Decimal("0.0001")


@dataclass(frozen=True)
class PublicPriceHistoryEntryV283:
    previous_price: Decimal
    new_price: Decimal
    absolute_change: Decimal
    percentage_change: Decimal | None
    percentage_display: str
    changed_at: datetime
    direction: str
    direction_label: str
    amount_label: str
    is_current: bool


def _format_percentage_v283(value: Decimal) -> str:
    rounded = value.quantize(
        PUBLIC_PRICE_HISTORY_PERCENTAGE_QUANTUM_V283,
        rounding=ROUND_HALF_UP,
    )
    return format(rounded, "f").rstrip("0").rstrip(".")


def get_public_price_history_v283(listing) -> list[PublicPriceHistoryEntryV283]:
    """Return the latest 20 meaningful transitions without exposing row metadata."""

    if not getattr(listing, "pk", None):
        return []

    history_rows = list(
        listing.price_history
        .filter(
            previous_price__isnull=False,
            new_price__isnull=False,
        )
        .exclude(previous_price=F("new_price"))
        .only(
            "listing_id",
            "previous_price",
            "new_price",
            "changed_at",
        )
        .order_by("-changed_at", "-pk")[:PUBLIC_PRICE_HISTORY_LIMIT_V283]
    )

    setattr(
        listing,
        PUBLIC_PRICE_HISTORY_CACHE_ATTRIBUTE_V283,
        history_rows,
    )

    entries = []
    for index, history_row in enumerate(history_rows):
        previous_price = history_row.previous_price
        new_price = history_row.new_price
        is_reduction = new_price < previous_price
        absolute_change = abs(new_price - previous_price)

        percentage_change = None
        percentage_display = ""
        if previous_price > 0:
            percentage_change = (
                absolute_change
                / previous_price
                * Decimal("100")
            )
            percentage_display = _format_percentage_v283(
                percentage_change
            )

        entries.append(
            PublicPriceHistoryEntryV283(
                previous_price=previous_price,
                new_price=new_price,
                absolute_change=absolute_change,
                percentage_change=percentage_change,
                percentage_display=percentage_display,
                changed_at=history_row.changed_at,
                direction=("reduction" if is_reduction else "increase"),
                direction_label=(
                    "Price reduced" if is_reduction else "Price increased"
                ),
                amount_label=(
                    "Amount saved" if is_reduction else "Increase amount"
                ),
                is_current=(
                    index == 0
                    and new_price == listing.price
                ),
            )
        )

    return entries


class PublicPriceHistoryContextMixinV283:
    """Add display-ready public history to an authorized detail response."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["public_price_history_v283"] = (
            get_public_price_history_v283(
                getattr(self, "object", None)
            )
        )
        return context
