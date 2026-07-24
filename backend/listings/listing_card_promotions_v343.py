"""Active promotion annotations for shared listing cards."""

from __future__ import annotations

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone


LISTING_CARD_PROMOTIONS_V343 = True


def annotate_listing_card_promotions_v343(
    queryset,
    *,
    now=None,
):
    """
    Add active card-promotion flags without per-listing queries.

    The annotations fail closed when a promotion is inactive, has not
    started, or has already ended.
    """
    from promotions.doping_catalog_v342 import PromotionCodeV342
    from promotions.models import ListingPromotion

    effective_now = now or timezone.now()

    active_started_promotions = (
        ListingPromotion.objects.filter(
            listing_id=OuterRef("pk"),
            status=ListingPromotion.Status.ACTIVE,
            starts_at__isnull=False,
            starts_at__lte=effective_now,
        )
    )

    active_listing_lifetime = (
        Q(ends_at__isnull=True)
        | Q(ends_at__gt=effective_now)
    )

    return queryset.annotate(
        has_small_photo_promotion_v343=Exists(
            active_started_promotions.filter(
                promotion_code_snapshot=(
                    PromotionCodeV342.SMALL_PHOTO
                ),
            ).filter(
                active_listing_lifetime
            )
        ),
        has_urgent_promotion_v343=Exists(
            active_started_promotions.filter(
                promotion_code_snapshot=(
                    PromotionCodeV342.URGENT
                ),
                ends_at__isnull=False,
                ends_at__gt=effective_now,
            )
        ),
        has_colorful_title_promotion_v343=Exists(
            active_started_promotions.filter(
                promotion_code_snapshot=(
                    PromotionCodeV342.COLORFUL_TITLE
                ),
            ).filter(
                active_listing_lifetime
            )
        ),
    )
