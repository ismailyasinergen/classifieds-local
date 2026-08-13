"""
RELATED_LISTINGS_RECOMMENDATIONS_V271

User-visible related-listing discovery for the listing-detail page.

The service is read-only, category-scoped and limited. It returns only
currently active, approved listings and never includes the current listing.
"""

from datetime import datetime

from django.db.models import (
    Case,
    IntegerField,
    Q,
    Value,
    When,
)
from django.utils import timezone

from .models import Listing


RELATED_LISTINGS_RECOMMENDATIONS_V271 = True
RELATED_LISTINGS_DEFAULT_LIMIT_V271 = 4
RELATED_LISTINGS_MAX_LIMIT_V271 = 8


def normalize_related_listings_limit_v271(
    limit: object,
) -> int:
    try:
        normalized = int(limit)
    except (
        TypeError,
        ValueError,
    ):
        return RELATED_LISTINGS_DEFAULT_LIMIT_V271

    return max(
        1,
        min(
            normalized,
            RELATED_LISTINGS_MAX_LIMIT_V271,
        ),
    )


def get_related_listings_v271(
    listing: Listing | None,
    *,
    limit: int = RELATED_LISTINGS_DEFAULT_LIMIT_V271,
    now: datetime | None = None,
) -> list[Listing]:
    """
    Return active approved listings from the same category.

    Ranking:
    1. Exact location match when the current listing has a location.
    2. Higher top-listing priority.
    3. Featured listings.
    4. Newer listings.
    5. Stable primary-key tie-breaker.
    """

    if (
        listing is None
        or not getattr(
            listing,
            "pk",
            None,
        )
        or not getattr(
            listing,
            "category_id",
            None,
        )
    ):
        return []

    effective_limit = normalize_related_listings_limit_v271(
        limit
    )

    active_at = (
        now
        if now is not None
        else timezone.now()
    )

    location = str(
        getattr(
            listing,
            "location",
            "",
        )
        or ""
    ).strip()

    if location:
        same_location_expression = Case(
            When(
                location__iexact=location,
                then=Value(1),
            ),
            default=Value(0),
            output_field=IntegerField(),
        )
    else:
        same_location_expression = Value(
            0,
            output_field=IntegerField(),
        )

    queryset = (
        Listing.objects
        .select_related(
            "category",
            "owner",
            "owner__profile",
            "owner__seller_store",
        )
        .prefetch_related(
            "images",
        )
        .filter(
            category_id=listing.category_id,
            status=Listing.Status.APPROVED,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=active_at)
        )
        .exclude(
            pk=listing.pk,
        )
        .annotate(
            related_same_location_v271=(
                same_location_expression
            ),
        )
        .order_by(
            "-related_same_location_v271",
            "-top_listing_priority",
            "-is_featured",
            "-created_at",
            "pk",
        )
    )

    from .listing_card_promotions_v343 import (
        annotate_listing_card_promotions_v343,
    )

    queryset = annotate_listing_card_promotions_v343(
        queryset,
        now=active_at,
    )

    return list(
        queryset[:effective_limit]
    )
