# SAVED_SEARCH_MATCHER_FOUNDATION_V81
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.http import QueryDict
from django.utils import timezone

from categories.models import Category
from .attribute_filters import apply_attribute_filters
from .models import Listing, SavedSearch


@dataclass
class SavedSearchMatchPreview:
    saved_search: SavedSearch
    checked_since: object
    match_count: int
    listings: list


class _SavedSearchFilterRequest:
    def __init__(self, querydict):
        self.GET = querydict
        self.path = "/listings/"


def _querydict_from_saved_search(saved_search):
    querydict = QueryDict("", mutable=True)

    source = saved_search.query_params or {}
    if source:
        for key, value in source.items():
            if isinstance(value, (list, tuple)):
                querydict.setlist(key, [str(item) for item in value if str(item or "").strip()])
            elif str(value or "").strip():
                querydict[key] = str(value).strip()
    elif saved_search.querystring:
        querydict = QueryDict(saved_search.querystring, mutable=True)

    return querydict


def _decimal_from_query(querydict, key):
    value = str(querydict.get(key, "") or "").strip()
    if not value:
        return None

    try:
        return Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return None


def _category_ids_for_slug(category_slug):
    category_slug = str(category_slug or "").strip()
    if not category_slug:
        return []

    root = Category.objects.filter(slug=category_slug).first()
    if not root:
        return []

    category_ids = [root.pk]
    pending_ids = [root.pk]

    while pending_ids:
        child_ids = list(
            Category.objects
            .filter(parent_id__in=pending_ids)
            .values_list("pk", flat=True)
        )
        child_ids = [pk for pk in child_ids if pk not in category_ids]
        category_ids.extend(child_ids)
        pending_ids = child_ids

    return category_ids


def _apply_saved_search_base_filters(queryset, querydict):
    category_slug = str(querydict.get("category", "") or "").strip()
    category_ids = _category_ids_for_slug(category_slug)
    if category_ids:
        queryset = queryset.filter(category_id__in=category_ids)

    keyword = str(querydict.get("q", "") or "").strip()
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(location__icontains=keyword)
        )

    location = str(querydict.get("location", "") or "").strip()
    if location:
        queryset = queryset.filter(location__icontains=location)

    minimum_price = _decimal_from_query(querydict, "min_price")
    if minimum_price is not None:
        queryset = queryset.filter(price__gte=minimum_price)

    maximum_price = _decimal_from_query(querydict, "max_price")
    if maximum_price is not None:
        queryset = queryset.filter(price__lte=maximum_price)

    return queryset, category_slug


def get_saved_search_matching_queryset(saved_search, now=None):
    now = now or timezone.now()
    querydict = _querydict_from_saved_search(saved_search)
    checked_since = saved_search.last_notification_checked_at or saved_search.created_at

    queryset = (
        Listing.objects
        .filter(status=Listing.Status.APPROVED)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .filter(created_at__gt=checked_since)
    )

    queryset, category_slug = _apply_saved_search_base_filters(queryset, querydict)

    request = _SavedSearchFilterRequest(querydict)
    queryset = apply_attribute_filters(queryset, request, category_slug)

    return queryset.distinct().order_by("-created_at")


def build_saved_search_match_preview(saved_search, limit=10, now=None):
    queryset = get_saved_search_matching_queryset(saved_search, now=now)
    checked_since = saved_search.last_notification_checked_at or saved_search.created_at

    return SavedSearchMatchPreview(
        saved_search=saved_search,
        checked_since=checked_since,
        match_count=queryset.count(),
        listings=list(queryset[:limit]),
    )


def iter_enabled_saved_search_match_previews(saved_search_ids=None, limit=10, now=None):
    queryset = (
        SavedSearch.objects
        .select_related("user")
        .filter(email_notifications_enabled=True)
        .order_by("pk")
    )

    if saved_search_ids:
        queryset = queryset.filter(pk__in=saved_search_ids)

    for saved_search in queryset:
        yield build_saved_search_match_preview(saved_search, limit=limit, now=now)


def mark_saved_search_checked(saved_search, checked_at=None):
    checked_at = checked_at or timezone.now()
    saved_search.last_notification_checked_at = checked_at
    saved_search.save(update_fields=["last_notification_checked_at", "updated_at"])
    return saved_search
