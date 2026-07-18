from __future__ import annotations

from django import template

from listings.listing_public_price_history_v283 import (
    PUBLIC_PRICE_HISTORY_CACHE_ATTRIBUTE_V283,
)


register = template.Library()

LISTING_PRICE_HISTORY_V275 = (
    "LISTING_PRICE_HISTORY_V275"
)

DEFAULT_PRICE_HISTORY_LIMIT_V275 = 10
MAX_PRICE_HISTORY_LIMIT_V275 = 25


def _empty_summary_v275():
    return {
        "marker": LISTING_PRICE_HISTORY_V275,
        "entries": [],
        "has_history": False,
        "has_changes": False,
        "latest_change": None,
        "is_drop": False,
        "previous_price": None,
        "drop_amount": None,
        "drop_percentage": None,
    }


@register.simple_tag
def listing_price_history_summary_v275(
    listing,
    limit=DEFAULT_PRICE_HISTORY_LIMIT_V275,
):
    if not getattr(listing, "pk", None):
        return _empty_summary_v275()

    try:
        limit = int(limit)
    except (TypeError, ValueError):
        limit = DEFAULT_PRICE_HISTORY_LIMIT_V275

    limit = max(
        1,
        min(
            limit,
            MAX_PRICE_HISTORY_LIMIT_V275,
        ),
    )

    cached_entries = getattr(
        listing,
        PUBLIC_PRICE_HISTORY_CACHE_ATTRIBUTE_V283,
        None,
    )
    if cached_entries is None:
        entries = list(
            listing.price_history.all()[:limit]
        )
    else:
        entries = list(cached_entries[:limit])

    current_price = listing.price

    latest_change = next(
        (
            entry
            for entry in entries
            if (
                not entry.is_baseline
                and entry.new_price == current_price
            )
        ),
        None,
    )

    is_drop = bool(
        latest_change
        and latest_change.is_price_drop
    )

    return {
        "marker": LISTING_PRICE_HISTORY_V275,
        "entries": entries,
        "has_history": bool(entries),
        "has_changes": any(
            not entry.is_baseline
            for entry in entries
        ),
        "latest_change": latest_change,
        "is_drop": is_drop,
        "previous_price": (
            latest_change.previous_price
            if is_drop
            else None
        ),
        "drop_amount": (
            latest_change.change_amount
            if is_drop
            else None
        ),
        "drop_percentage": (
            latest_change.change_percentage
            if is_drop
            else None
        ),
    }
