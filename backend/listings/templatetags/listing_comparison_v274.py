"""
LISTING_COMPARISON_V274

Small template helpers for listing cards and listing details.
"""

from django import template

from listings.listing_comparison_v274 import (
    comparison_listing_is_eligible_v274,
    get_comparison_listing_ids_v274,
)


register = template.Library()

LISTING_COMPARISON_V274 = True


@register.simple_tag
def comparison_selected_v274(
    request,
    listing,
):
    listing_id = getattr(
        listing,
        "pk",
        None,
    )

    if listing_id is None:
        return False

    return int(
        listing_id
    ) in get_comparison_listing_ids_v274(
        request
    )


@register.simple_tag
def comparison_count_v274(
    request,
):
    return len(
        get_comparison_listing_ids_v274(
            request
        )
    )


@register.simple_tag
def comparison_eligible_v274(
    listing,
):
    return comparison_listing_is_eligible_v274(
        listing
    )
