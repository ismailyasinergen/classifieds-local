"""Price-drop activity windows for saved-search notifications in v286."""

from __future__ import annotations

from django.db.models import DateTimeField, F, Q
from django.db.models.functions import Coalesce, Greatest

from .listing_biggest_price_drop_sort_v281 import (
    BIGGEST_PRICE_DROP_SORT_VALUE_V281,
)
from .listing_price_drop_filter_v278 import (
    price_drop_filter_is_enabled_v278,
)
from .listing_price_drop_period_filter_v280 import (
    PRICE_DROP_CHANGED_AT_ANNOTATION_V280,
    annotate_current_price_drop_time_v280,
    get_price_drop_period_value_v280,
)
from .listing_price_drop_sort_v279 import (
    RECENT_PRICE_DROP_SORT_VALUE_V279,
    apply_public_listing_sort_v279,
)
from .listing_price_drop_threshold_filter_v282 import (
    get_min_price_drop_amount_value_v282,
    get_min_price_drop_percent_value_v282,
)


SAVED_SEARCH_PRICE_DROP_NOTIFICATIONS_V286 = True
SAVED_SEARCH_NOTIFICATION_ACTIVITY_ANNOTATION_V286 = (
    "saved_search_notification_activity_at_v286"
)


def saved_search_watches_price_drops_v286(request) -> bool:
    """Return whether valid saved parameters imply current-reduction results."""

    sort_value = str(request.GET.get("sort", "") or "").strip()
    return bool(
        price_drop_filter_is_enabled_v278(request)
        or get_price_drop_period_value_v280(request)
        or get_min_price_drop_amount_value_v282(request)
        or get_min_price_drop_percent_value_v282(request)
        or sort_value
        in {
            RECENT_PRICE_DROP_SORT_VALUE_V279,
            BIGGEST_PRICE_DROP_SORT_VALUE_V281,
        }
    )


def apply_saved_search_activity_window_v286(
    queryset,
    request,
    *,
    checked_since,
):
    """Apply public filtering plus the correct notification activity window."""

    queryset = apply_public_listing_sort_v279(queryset, request)
    watches_price_drops = saved_search_watches_price_drops_v286(request)

    if not watches_price_drops:
        return (
            queryset
            .filter(created_at__gt=checked_since)
            .order_by("-created_at", "-pk")
        ), False

    queryset = annotate_current_price_drop_time_v280(queryset)
    queryset = queryset.filter(
        Q(created_at__gt=checked_since)
        | Q(
            **{
                PRICE_DROP_CHANGED_AT_ANNOTATION_V280
                + "__gt": checked_since,
            }
        )
    ).annotate(
        **{
            SAVED_SEARCH_NOTIFICATION_ACTIVITY_ANNOTATION_V286: Greatest(
                F("created_at"),
                Coalesce(
                    F(PRICE_DROP_CHANGED_AT_ANNOTATION_V280),
                    F("created_at"),
                    output_field=DateTimeField(),
                ),
            )
        }
    )

    return queryset.order_by(
        f"-{SAVED_SEARCH_NOTIFICATION_ACTIVITY_ANNOTATION_V286}",
        "-pk",
    ), True
