from django import template

from listings.listing_card_discount_presentation_v284 import (
    build_listing_card_discount_presentation_v284,
)


register = template.Library()


@register.simple_tag
def listing_card_discount_presentation_v284(discovery):
    return build_listing_card_discount_presentation_v284(
        discovery
    )
