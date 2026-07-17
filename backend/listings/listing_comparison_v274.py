"""
LISTING_COMPARISON_V274

Session-based listing comparison support.

Only listing primary keys are stored in the Django session. No permanent
browsing or comparison model is created.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from django.utils import timezone

from .models import Listing


if TYPE_CHECKING:
    from datetime import datetime

    from django.http import HttpRequest


LISTING_COMPARISON_V274 = True

LISTING_COMPARISON_SESSION_KEY_V274 = (
    "listing_comparison_ids_v274"
)

LISTING_COMPARISON_MIN_ITEMS_V274 = 2
LISTING_COMPARISON_MAX_ITEMS_V274 = 4


def normalize_comparison_listing_ids_v274(
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
            >= LISTING_COMPARISON_MAX_ITEMS_V274
        ):
            break

    return normalized


def comparison_listing_is_eligible_v274(
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

    active_at = (
        now
        if now is not None
        else timezone.now()
    )

    expires_at = getattr(
        listing,
        "expires_at",
        None,
    )

    return (
        expires_at is None
        or expires_at > active_at
    )


def get_comparison_listing_ids_v274(
    request: HttpRequest,
) -> list[int]:
    session = getattr(
        request,
        "session",
        None,
    )

    if session is None:
        return []

    return normalize_comparison_listing_ids_v274(
        session.get(
            LISTING_COMPARISON_SESSION_KEY_V274,
            (),
        )
    )


def set_comparison_listing_ids_v274(
    request: HttpRequest,
    listing_ids: object,
) -> list[int]:
    normalized = (
        normalize_comparison_listing_ids_v274(
            listing_ids
        )
    )

    session = getattr(
        request,
        "session",
        None,
    )

    if session is None:
        return normalized

    previous = (
        normalize_comparison_listing_ids_v274(
            session.get(
                LISTING_COMPARISON_SESSION_KEY_V274,
                (),
            )
        )
    )

    if normalized:
        session[
            LISTING_COMPARISON_SESSION_KEY_V274
        ] = normalized
    else:
        session.pop(
            LISTING_COMPARISON_SESSION_KEY_V274,
            None,
        )

    if normalized != previous and hasattr(
        session,
        "modified",
    ):
        session.modified = True

    return normalized


def toggle_comparison_listing_v274(
    request: HttpRequest,
    listing: Listing | None,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    selected_ids = (
        get_comparison_listing_ids_v274(
            request
        )
    )

    if not comparison_listing_is_eligible_v274(
        listing,
        now=now,
    ):
        return {
            "changed": False,
            "action": "unavailable",
            "reason": "listing_not_public",
            "listing_ids": selected_ids,
            "count": len(selected_ids),
        }

    listing_id = int(
        listing.pk
    )

    if listing_id in selected_ids:
        updated_ids = [
            selected_id
            for selected_id in selected_ids
            if selected_id != listing_id
        ]

        set_comparison_listing_ids_v274(
            request,
            updated_ids,
        )

        return {
            "changed": True,
            "action": "removed",
            "reason": "",
            "listing_ids": updated_ids,
            "count": len(updated_ids),
        }

    if (
        len(selected_ids)
        >= LISTING_COMPARISON_MAX_ITEMS_V274
    ):
        return {
            "changed": False,
            "action": "full",
            "reason": "comparison_limit_reached",
            "listing_ids": selected_ids,
            "count": len(selected_ids),
        }

    updated_ids = [
        *selected_ids,
        listing_id,
    ]

    set_comparison_listing_ids_v274(
        request,
        updated_ids,
    )

    return {
        "changed": True,
        "action": "added",
        "reason": "",
        "listing_ids": updated_ids,
        "count": len(updated_ids),
    }


def clear_comparison_listings_v274(
    request: HttpRequest,
) -> int:
    previous_count = len(
        get_comparison_listing_ids_v274(
            request
        )
    )

    set_comparison_listing_ids_v274(
        request,
        (),
    )

    return previous_count


def get_comparison_listings_v274(
    request: HttpRequest,
    *,
    now: datetime | None = None,
    prune_session: bool = True,
) -> list[Listing]:
    selected_ids = (
        get_comparison_listing_ids_v274(
            request
        )
    )

    if not selected_ids:
        return []

    active_at = (
        now
        if now is not None
        else timezone.now()
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
    )

    listings_by_id = {
        listing.pk: listing
        for listing in queryset
    }

    ordered_listings = [
        listings_by_id[listing_id]
        for listing_id in selected_ids
        if listing_id in listings_by_id
    ]

    valid_ids = [
        listing.pk
        for listing in ordered_listings
    ]

    if (
        prune_session
        and valid_ids != selected_ids
    ):
        set_comparison_listing_ids_v274(
            request,
            valid_ids,
        )

    return ordered_listings


def _display_attribute_pairs_v274(
    listing: Listing,
) -> list[tuple[str, str]]:
    raw_attributes = getattr(
        listing,
        "display_attributes",
        (),
    )

    if callable(
        raw_attributes
    ):
        raw_attributes = raw_attributes()

    pairs: list[tuple[str, str]] = []

    for item in raw_attributes or ():
        if (
            not isinstance(
                item,
                (
                    list,
                    tuple,
                ),
            )
            or len(item) != 2
        ):
            continue

        label = str(
            item[0]
            or ""
        ).strip()

        value = str(
            item[1]
            if item[1] is not None
            else ""
        ).strip()

        if not label:
            continue

        pairs.append(
            (
                label,
                value or "—",
            )
        )

    return pairs


def build_comparison_attribute_rows_v274(
    listings: list[Listing],
) -> list[dict[str, object]]:
    labels: list[str] = []
    values_by_listing: list[dict[str, str]] = []

    for listing in listings:
        listing_values: dict[str, str] = {}

        for label, value in (
            _display_attribute_pairs_v274(
                listing
            )
        ):
            if label not in labels:
                labels.append(
                    label
                )

            listing_values[
                label
            ] = value

        values_by_listing.append(
            listing_values
        )

    rows: list[dict[str, object]] = []

    for label in labels:
        values = [
            listing_values.get(
                label,
                "—",
            )
            for listing_values
            in values_by_listing
        ]

        rows.append(
            {
                "label": label,
                "values": values,
            }
        )

    return rows


def build_listing_comparison_context_v274(
    request: HttpRequest,
) -> dict[str, object]:
    listings = (
        get_comparison_listings_v274(
            request
        )
    )

    count = len(
        listings
    )

    return {
        "comparison_listings": listings,
        "comparison_listing_ids": [
            listing.pk
            for listing in listings
        ],
        "comparison_count": count,
        "comparison_ready": (
            count
            >= LISTING_COMPARISON_MIN_ITEMS_V274
        ),
        "comparison_slots_remaining": max(
            0,
            (
                LISTING_COMPARISON_MAX_ITEMS_V274
                - count
            ),
        ),
        "comparison_attribute_rows": (
            build_comparison_attribute_rows_v274(
                listings
            )
        ),
        "comparison_min_items": (
            LISTING_COMPARISON_MIN_ITEMS_V274
        ),
        "comparison_max_items": (
            LISTING_COMPARISON_MAX_ITEMS_V274
        ),
    }
