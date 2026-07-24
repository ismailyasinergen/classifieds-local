"""
RECENTLY_VIEWED_LISTINGS_V272

Session-based recently-viewed listing history.

The feature stores only listing primary keys in the visitor's Django
session. It creates no model, migration or permanent browsing-history row.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import (
    Case,
    IntegerField,
    Q,
    Value,
    When,
)
from django.utils import timezone

from .models import Listing


if TYPE_CHECKING:
    from datetime import datetime

    from django.http import HttpRequest


RECENTLY_VIEWED_LISTINGS_V272 = True

RECENTLY_VIEWED_SESSION_KEY_V272 = (
    "recently_viewed_listing_ids_v272"
)

RECENTLY_VIEWED_DISPLAY_LIMIT_V272 = 4
RECENTLY_VIEWED_HISTORY_LIMIT_V272 = 12
RECENTLY_VIEWED_MAX_DISPLAY_LIMIT_V272 = 8


def normalize_recently_viewed_listing_ids_v272(
    values: object,
) -> list[int]:
    if not isinstance(
        values,
        (
            list,
            tuple,
        ),
    ):
        return []

    normalized: list[int] = []
    seen: set[int] = set()

    for value in values:
        if isinstance(
            value,
            bool,
        ):
            continue

        try:
            listing_id = int(
                value
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            listing_id <= 0
            or listing_id in seen
        ):
            continue

        seen.add(
            listing_id
        )
        normalized.append(
            listing_id
        )

        if (
            len(normalized)
            >= RECENTLY_VIEWED_HISTORY_LIMIT_V272
        ):
            break

    return normalized


def normalize_recently_viewed_display_limit_v272(
    limit: object,
) -> int:
    try:
        normalized = int(
            limit
        )
    except (
        TypeError,
        ValueError,
    ):
        return RECENTLY_VIEWED_DISPLAY_LIMIT_V272

    return max(
        1,
        min(
            normalized,
            RECENTLY_VIEWED_MAX_DISPLAY_LIMIT_V272,
        ),
    )


def listing_is_publicly_viewable_v272(
    listing: Listing | None,
    *,
    now: datetime | None = None,
) -> bool:
    if (
        listing is None
        or not getattr(
            listing,
            "pk",
            None,
        )
        or getattr(
            listing,
            "status",
            None,
        )
        != Listing.Status.APPROVED
    ):
        return False

    expires_at = getattr(
        listing,
        "expires_at",
        None,
    )

    active_at = (
        now
        if now is not None
        else timezone.now()
    )

    return (
        expires_at is None
        or expires_at > active_at
    )


def get_recently_viewed_listings_v272(
    request: HttpRequest,
    *,
    current_listing: Listing | None = None,
    limit: int = RECENTLY_VIEWED_DISPLAY_LIMIT_V272,
    now: datetime | None = None,
) -> list[Listing]:
    session = getattr(
        request,
        "session",
        None,
    )

    if session is None:
        return []

    listing_ids = (
        normalize_recently_viewed_listing_ids_v272(
            session.get(
                RECENTLY_VIEWED_SESSION_KEY_V272,
                (),
            )
        )
    )

    current_listing_id = getattr(
        current_listing,
        "pk",
        None,
    )

    listing_ids = [
        listing_id
        for listing_id in listing_ids
        if listing_id
        != current_listing_id
    ]

    if not listing_ids:
        return []

    display_limit = (
        normalize_recently_viewed_display_limit_v272(
            limit
        )
    )

    selected_ids = listing_ids[
        :display_limit
    ]

    active_at = (
        now
        if now is not None
        else timezone.now()
    )

    rank_expression = Case(
        *[
            When(
                pk=listing_id,
                then=Value(index),
            )
            for index, listing_id
            in enumerate(
                selected_ids
            )
        ],
        default=Value(
            len(selected_ids)
        ),
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
            pk__in=selected_ids,
            status=Listing.Status.APPROVED,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=active_at)
        )
        .annotate(
            recently_viewed_rank_v272=(
                rank_expression
            ),
        )
        .order_by(
            "recently_viewed_rank_v272",
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
        queryset
    )


def record_recently_viewed_listing_v272(
    request: HttpRequest,
    listing: Listing | None,
    *,
    now: datetime | None = None,
) -> bool:
    session = getattr(
        request,
        "session",
        None,
    )

    if (
        session is None
        or not listing_is_publicly_viewable_v272(
            listing,
            now=now,
        )
    ):
        return False

    listing_id = int(
        listing.pk
    )

    previous = (
        normalize_recently_viewed_listing_ids_v272(
            session.get(
                RECENTLY_VIEWED_SESSION_KEY_V272,
                (),
            )
        )
    )

    updated = [
        listing_id,
        *[
            previous_id
            for previous_id in previous
            if previous_id
            != listing_id
        ],
    ][
        :RECENTLY_VIEWED_HISTORY_LIMIT_V272
    ]

    if updated == previous:
        return False

    session[
        RECENTLY_VIEWED_SESSION_KEY_V272
    ] = updated

    if hasattr(
        session,
        "modified",
    ):
        session.modified = True

    return True
