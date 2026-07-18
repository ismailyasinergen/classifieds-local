from __future__ import annotations

from django import template

from listings.listing_price_drop_discovery_v276 import (
    get_listing_card_price_drop_v276,
)


register = template.Library()


@register.simple_tag(takes_context=True)
def listing_card_price_drop_v276(
    context,
    listing,
):
    return get_listing_card_price_drop_v276(
        context,
        listing,
    )
