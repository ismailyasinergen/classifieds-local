"""
PUBLIC_DEALS_LANDING_PAGE_V296

Public, paginated listing discovery for genuine current price reductions.

This module deliberately reuses the established v278-v284 qualification,
database annotation, deterministic ordering, and listing-card presentation
contracts. It does not define a competing price-drop calculation.
"""

from __future__ import annotations

from types import SimpleNamespace

from django.db.models import QuerySet
from django.views.generic import ListView

from .listing_biggest_price_drop_sort_v281 import (
    apply_biggest_price_drop_sort_v281,
)
from .listing_visibility_helpers import active_approved_listings
from .models import Listing
from .public_deals_seo_metadata_v298 import (
    build_public_deals_seo_context_v298,
)


PUBLIC_DEALS_LANDING_PAGE_V296 = True
PUBLIC_DEALS_PAGE_SIZE_V296 = 12


def get_public_deals_queryset_v296(
    queryset: QuerySet,
) -> QuerySet:
    """
    Restrict and order listings using the established biggest-discount contract.

    The empty query mapping fixes the landing page to the complete eligible
    deals population. Pagination is handled separately by Django's ListView.
    """

    deals_request = SimpleNamespace(GET={})

    return apply_biggest_price_drop_sort_v281(
        queryset,
        deals_request,
    )


class PublicDealsListViewV296(ListView):
    model = Listing
    template_name = "listings/public_deals_landing_page_v296.html"
    context_object_name = "listings"
    paginate_by = PUBLIC_DEALS_PAGE_SIZE_V296

    def get_queryset(self):
        from .listing_card_promotions_v343 import (
            annotate_listing_card_promotions_v343,
        )

        queryset = annotate_listing_card_promotions_v343(
            Listing.objects
            .select_related(
                "category",
                "owner",
                "owner__profile",
                "owner__seller_store",
            )
            .prefetch_related("images")
        )

        queryset = active_approved_listings(queryset)

        return get_public_deals_queryset_v296(queryset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Deals"

        context.update(
            build_public_deals_seo_context_v298(
                request=self.request,
                page_obj=context["page_obj"],
                listings=context["listings"],
            )
        )

        return context
