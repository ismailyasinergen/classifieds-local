"""Display-ready listing-card discount values for v284."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .listing_price_drop_discovery_v276 import (
    ListingCardPriceDropV276,
)
from .listing_price_drop_threshold_filter_v282 import (
    format_price_drop_threshold_v282,
)


ENHANCED_LISTING_CARD_DISCOUNT_V284 = True


@dataclass(frozen=True)
class ListingCardDiscountPresentationV284:
    listing_id: int
    previous_price: Decimal
    current_price: Decimal
    saving_amount: Decimal
    saving_percentage: Decimal
    saving_percentage_display: str

    @property
    def has_percentage(self) -> bool:
        return bool(self.saving_percentage_display)

    @property
    def accessible_explanation(self) -> str:
        return (
            f"Price dropped from {self.previous_price} TL to "
            f"{self.current_price} TL. You save {self.saving_amount} TL "
            f"({self.saving_percentage_display} percent)."
        )


def build_listing_card_discount_presentation_v284(
    discovery: ListingCardPriceDropV276 | None,
) -> ListingCardDiscountPresentationV284 | None:
    """Refine the shared v276 discovery for v284 percentage presentation."""

    if (
        discovery is None
        or discovery.previous_price <= 0
        or discovery.saving_percentage is None
    ):
        return None

    percentage_display = format_price_drop_threshold_v282(
        discovery.saving_percentage
    )
    if not percentage_display:
        return None

    return ListingCardDiscountPresentationV284(
        listing_id=discovery.listing_id,
        previous_price=discovery.previous_price,
        current_price=discovery.current_price,
        saving_amount=discovery.saving_amount,
        saving_percentage=discovery.saving_percentage,
        saving_percentage_display=percentage_display,
    )
