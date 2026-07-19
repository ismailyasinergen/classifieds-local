"""
Central listing-card price-drop discovery introduced in v276.

The shared card template is used by public browse, seller stores, related
listings, recently viewed listings, home-page sections, saved listings and
account dashboards.

This module deliberately batches card price-history lookups at render time.
It does not perform one price-history query per listing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db.models import (
    CharField,
    DecimalField,
    OuterRef,
    Q,
    Subquery,
)
from django.db.models.query import QuerySet
from django.utils import timezone

from .models import Listing, ListingPriceHistory


V276_LISTING_CARD_PRICE_DROP_DISCOVERY = True

LISTING_CARD_PRICE_DROP_CONTEXT_LIMIT_V276 = 1000

_V276_REQUEST_CACHE_ATTRIBUTE = (
    "_listing_card_price_drop_cache_v276"
)

_V276_RENDER_CACHE_KEY = (
    "listing_card_price_drop_cache_v276"
)

_V276_CONTEXT_LISTING_KEYS = (
    "listings",
    "object_list",
    "my_listings",
    "featured_listings",
    "latest_listings",
    "related_listings",
    "recently_viewed_listings",
    "pinned_store_listings",
    "page_obj",
    "category_sections",
    "section",
)


@dataclass(frozen=True)
class ListingCardPriceDropV276:
    listing_id: int
    previous_price: Decimal
    current_price: Decimal
    saving_amount: Decimal
    saving_percentage: Decimal | None

    @property
    def has_percentage(self) -> bool:
        return self.saving_percentage is not None


def _normalize_listing_ids_v276(
    listing_ids: Any,
) -> tuple[int, ...]:
    normalized: list[int] = []
    seen: set[int] = set()

    for raw_value in listing_ids or ():
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            continue

        if value <= 0 or value in seen:
            continue

        seen.add(value)
        normalized.append(value)

        if (
            len(normalized)
            >= LISTING_CARD_PRICE_DROP_CONTEXT_LIMIT_V276
        ):
            break

    return tuple(normalized)


def get_current_listing_price_drops_v276(
    listing_ids: Any,
) -> dict[int, ListingCardPriceDropV276]:
    """
    Return current active price drops for the supplied listings.

    A card is considered reduced only when:

    * the listing is active and approved;
    * its most recent real transition is a reduction;
    * its persisted current price still matches that transition's new price.
    * v293 has not restricted the reduction from public discount promotion.

    The entire lookup is executed as one Listing query containing correlated
    subqueries for the latest transition.
    """

    normalized_ids = _normalize_listing_ids_v276(
        listing_ids
    )

    if not normalized_ids:
        return {}

    decimal_output = DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    latest_transition = (
        ListingPriceHistory.objects
        .filter(
            listing_id=OuterRef("pk"),
            previous_price__isnull=False,
        )
        .order_by(
            "-changed_at",
            "-pk",
        )
    )

    rows = (
        Listing.objects
        .filter(
            pk__in=normalized_ids,
            status=Listing.Status.APPROVED,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        )
        .annotate(
            price_drop_previous_price_v276=Subquery(
                latest_transition.values(
                    "previous_price"
                )[:1],
                output_field=decimal_output,
            ),
            price_drop_transition_price_v276=Subquery(
                latest_transition.values(
                    "new_price"
                )[:1],
                output_field=decimal_output,
            ),
            price_drop_guardrail_status_v293=Subquery(
                latest_transition.values(
                    "discount_guardrail_status"
                )[:1],
                output_field=CharField(max_length=32),
            ),
        )
        .values(
            "pk",
            "price",
            "price_drop_previous_price_v276",
            "price_drop_transition_price_v276",
            "price_drop_guardrail_status_v293",
        )
    )

    discoveries: dict[
        int,
        ListingCardPriceDropV276,
    ] = {}

    percentage_quantum = Decimal("0.01")

    for row in rows:
        previous_price = row[
            "price_drop_previous_price_v276"
        ]

        transition_price = row[
            "price_drop_transition_price_v276"
        ]

        if (
            previous_price is None
            or transition_price is None
        ):
            continue

        current_price = Decimal(row["price"])
        previous_price = Decimal(previous_price)
        transition_price = Decimal(transition_price)

        if current_price != transition_price:
            continue

        if transition_price >= previous_price:
            continue

        if row["price_drop_guardrail_status_v293"]:
            continue

        saving_amount = (
            previous_price - transition_price
        )

        saving_percentage = None

        if previous_price > 0:
            saving_percentage = (
                (
                    saving_amount
                    / previous_price
                    * Decimal("100")
                )
                .quantize(
                    percentage_quantum,
                    rounding=ROUND_HALF_UP,
                )
            )

        listing_id = int(row["pk"])

        discoveries[listing_id] = (
            ListingCardPriceDropV276(
                listing_id=listing_id,
                previous_price=previous_price,
                current_price=current_price,
                saving_amount=saving_amount,
                saving_percentage=saving_percentage,
            )
        )

    return discoveries


def _append_listing_ids_from_value_v276(
    value: Any,
    destination: list[int],
    seen_ids: set[int],
    *,
    depth: int = 0,
) -> None:
    if (
        value is None
        or depth > 4
        or len(destination)
        >= LISTING_CARD_PRICE_DROP_CONTEXT_LIMIT_V276
    ):
        return

    if isinstance(value, Listing):
        if value.pk:
            listing_id = int(value.pk)

            if listing_id not in seen_ids:
                seen_ids.add(listing_id)
                destination.append(listing_id)

        return

    object_list = getattr(
        value,
        "object_list",
        None,
    )

    if object_list is not None:
        _append_listing_ids_from_value_v276(
            object_list,
            destination,
            seen_ids,
            depth=depth + 1,
        )
        return

    if isinstance(value, Mapping):
        preferred_values = []

        for key in (
            "listing",
            "listings",
            "object_list",
        ):
            if key in value:
                preferred_values.append(value[key])

        if preferred_values:
            for nested_value in preferred_values:
                _append_listing_ids_from_value_v276(
                    nested_value,
                    destination,
                    seen_ids,
                    depth=depth + 1,
                )
        else:
            for nested_value in value.values():
                _append_listing_ids_from_value_v276(
                    nested_value,
                    destination,
                    seen_ids,
                    depth=depth + 1,
                )

        return

    if isinstance(
        value,
        (
            QuerySet,
            list,
            tuple,
            set,
        ),
    ):
        for nested_value in value:
            _append_listing_ids_from_value_v276(
                nested_value,
                destination,
                seen_ids,
                depth=depth + 1,
            )

            if (
                len(destination)
                >= LISTING_CARD_PRICE_DROP_CONTEXT_LIMIT_V276
            ):
                break


def collect_listing_ids_from_template_context_v276(
    context: Any,
    current_listing: Listing | None = None,
) -> tuple[int, ...]:
    try:
        flattened = context.flatten()
    except AttributeError:
        flattened = dict(context or {})

    destination: list[int] = []
    seen_ids: set[int] = set()

    if current_listing is not None:
        _append_listing_ids_from_value_v276(
            current_listing,
            destination,
            seen_ids,
        )

    for key in _V276_CONTEXT_LISTING_KEYS:
        if key not in flattened:
            continue

        _append_listing_ids_from_value_v276(
            flattened[key],
            destination,
            seen_ids,
        )

    return tuple(destination)


def _get_render_cache_v276(
    context: Any,
) -> dict[str, Any]:
    request = getattr(
        context,
        "request",
        None,
    )

    if request is None:
        try:
            request = context.get("request")
        except (AttributeError, KeyError):
            request = None

    if request is not None:
        cache = getattr(
            request,
            _V276_REQUEST_CACHE_ATTRIBUTE,
            None,
        )

        if cache is None:
            cache = {
                "loaded_ids": set(),
                "discoveries": {},
            }

            setattr(
                request,
                _V276_REQUEST_CACHE_ATTRIBUTE,
                cache,
            )

        return cache

    render_context = getattr(
        context,
        "render_context",
        None,
    )

    if render_context is None:
        return {
            "loaded_ids": set(),
            "discoveries": {},
        }

    cache = render_context.get(
        _V276_RENDER_CACHE_KEY
    )

    if cache is None:
        cache = {
            "loaded_ids": set(),
            "discoveries": {},
        }

        render_context[
            _V276_RENDER_CACHE_KEY
        ] = cache

    return cache


def get_listing_card_price_drop_v276(
    context: Any,
    listing: Listing,
) -> ListingCardPriceDropV276 | None:
    if (
        listing is None
        or not getattr(listing, "pk", None)
    ):
        return None

    listing_ids = (
        collect_listing_ids_from_template_context_v276(
            context,
            listing,
        )
    )

    cache = _get_render_cache_v276(context)

    loaded_ids: set[int] = cache["loaded_ids"]
    discoveries: dict[
        int,
        ListingCardPriceDropV276,
    ] = cache["discoveries"]

    missing_ids = [
        listing_id
        for listing_id in listing_ids
        if listing_id not in loaded_ids
    ]

    if missing_ids:
        discoveries.update(
            get_current_listing_price_drops_v276(
                missing_ids
            )
        )

        loaded_ids.update(missing_ids)

    return discoveries.get(int(listing.pk))
