"""
DEAL_AWARE_LISTING_COMPARISON_V297

Batch current-discount presentation for the public listing comparison page.

This module reuses the established v276 discovery and v284 presentation
contracts. It does not define a competing discount calculation and does not
persist comparison or discount state.
"""

from __future__ import annotations

from collections.abc import Sequence

from .listing_card_discount_presentation_v284 import (
    build_listing_card_discount_presentation_v284,
)
from .listing_price_drop_discovery_v276 import (
    get_current_listing_price_drops_v276,
)
from .models import Listing


DEAL_AWARE_LISTING_COMPARISON_V297 = True

LISTING_COMPARISON_DISCOUNT_ATTRIBUTE_V297 = (
    "comparison_discount_v297"
)


def attach_listing_comparison_discounts_v297(
    listings: Sequence[Listing],
) -> None:
    """
    Attach display-ready current discounts using one batched discovery query.

    Listings without a valid public current reduction receive ``None``. The
    transient attribute exists only on the in-memory objects rendered for the
    current comparison response.
    """

    listing_ids = [
        int(listing.pk)
        for listing in listings
        if getattr(listing, "pk", None)
    ]

    discoveries = get_current_listing_price_drops_v276(
        listing_ids
    )

    for listing in listings:
        discovery = discoveries.get(
            int(listing.pk)
        )

        presentation = (
            build_listing_card_discount_presentation_v284(
                discovery
            )
        )

        setattr(
            listing,
            LISTING_COMPARISON_DISCOUNT_ATTRIBUTE_V297,
            presentation,
        )
