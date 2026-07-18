# SAVED_SEARCH_MATCHER_FOUNDATION_V81
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
from django.http import QueryDict
from django.utils import timezone

from categories.models import Category
from .attribute_filters import apply_attribute_filters
from .models import Listing, SavedSearch
from .saved_search_price_drop_notifications_v286 import (
    apply_saved_search_activity_window_v286,
    saved_search_watches_price_drops_v286,
)


@dataclass
class SavedSearchMatchPreview:
    saved_search: SavedSearch
    checked_since: object
    match_count: int
    listings: list
    includes_price_drops: bool = False


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
    )

    queryset, category_slug = _apply_saved_search_base_filters(queryset, querydict)

    request = _SavedSearchFilterRequest(querydict)
    queryset = apply_attribute_filters(queryset, request, category_slug)
    queryset, _includes_price_drops = apply_saved_search_activity_window_v286(
        queryset,
        request,
        checked_since=checked_since,
    )

    return queryset.distinct()


def build_saved_search_match_preview(saved_search, limit=10, now=None):
    querydict = _querydict_from_saved_search(saved_search)
    request = _SavedSearchFilterRequest(querydict)
    queryset = get_saved_search_matching_queryset(saved_search, now=now)
    checked_since = saved_search.last_notification_checked_at or saved_search.created_at

    return SavedSearchMatchPreview(
        saved_search=saved_search,
        checked_since=checked_since,
        match_count=queryset.count(),
        listings=list(queryset[:limit]),
        includes_price_drops=saved_search_watches_price_drops_v286(request),
    )


# SAVED_SEARCH_NOTIFICATION_SCHEDULING_FILTERS_V84
def iter_enabled_saved_search_match_previews(
    saved_search_ids=None,
    limit=10,
    now=None,
    stale_before=None,
    max_searches=None,
):
    queryset = (
        SavedSearch.objects
        .select_related("user")
        .filter(email_notifications_enabled=True)
        .order_by("pk")
    )

    if saved_search_ids:
        queryset = queryset.filter(pk__in=saved_search_ids)

    if stale_before is not None:
        queryset = queryset.filter(
            Q(last_notification_checked_at__isnull=True)
            | Q(last_notification_checked_at__lte=stale_before)
        )

    if max_searches is not None:
        queryset = queryset[:max_searches]

    for saved_search in queryset:
        yield build_saved_search_match_preview(saved_search, limit=limit, now=now)


def mark_saved_search_checked(saved_search, checked_at=None):
    checked_at = checked_at or timezone.now()
    saved_search.last_notification_checked_at = checked_at
    saved_search.save(update_fields=["last_notification_checked_at", "updated_at"])
    return saved_search


# SAVED_SEARCH_EMAIL_DELIVERY_SKELETON_V82
def _join_site_url(path, site_base_url=None):
    path = path or "/"
    site_base_url = (site_base_url or "").strip().rstrip("/")

    if site_base_url:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{site_base_url}{path}"

    return path


def _listing_url_for_email(listing, site_base_url=None):
    try:
        path = listing.get_absolute_url()
    except Exception:
        path = f"/listings/{listing.pk}/"

    return _join_site_url(path, site_base_url=site_base_url)


def _saved_search_url_for_email(saved_search, site_base_url=None):
    path = saved_search.path or "/listings/"
    querystring = saved_search.querystring or ""

    if querystring:
        separator = "&" if "?" in path else "?"
        path = f"{path}{separator}{querystring}"

    return _join_site_url(path, site_base_url=site_base_url)



# SAVED_SEARCH_NOTIFICATION_OPERATIONAL_HARDENING_V83
def get_saved_search_recipient_email(saved_search):
    return str(getattr(saved_search.user, "email", "") or "").strip()


def _saved_search_display_name(saved_search):
    display_name = getattr(saved_search, "display_name", None)
    if callable(display_name):
        display_name = display_name()

    return str(
        display_name
        or saved_search.name
        or f"Saved search #{saved_search.pk}"
    ).strip()

def build_saved_search_email_message(preview, from_email=None, site_base_url=None):
    saved_search = preview.saved_search
    user_email = get_saved_search_recipient_email(saved_search)
    if not user_email:
        raise ValueError("Saved search user has no email address.")

    saved_search_name = _saved_search_display_name(saved_search)

    match_description = (
        "new or newly reduced listing"
        if preview.includes_price_drops
        else "new listing"
    )
    subject = (
        f"{preview.match_count} {match_description}"
        f"{'' if preview.match_count == 1 else 's'} for {saved_search_name}"
    )

    lines = [
        "Hi,",
        "",
        (
            f"We found {preview.match_count} {match_description}"
            f"{'' if preview.match_count == 1 else 's'} matching your saved search:"
        ),
        f"{saved_search_name}",
        "",
        f"Checked since: {preview.checked_since}",
        "",
        "Matching listings:",
    ]

    for listing in preview.listings:
        lines.append(
            f"- {listing.title} — {listing.price} — {listing.location} — "
            f"{_listing_url_for_email(listing, site_base_url=site_base_url)}"
        )

    if preview.match_count > len(preview.listings):
        remaining = preview.match_count - len(preview.listings)
        lines.append(f"- And {remaining} more matching listing{'' if remaining == 1 else 's'}.")

    lines.extend(
        [
            "",
            f"Run this saved search: {_saved_search_url_for_email(saved_search, site_base_url=site_base_url)}",
            "",
            "You can disable email alerts from your saved searches page.",
            "",
            "No action is required if these listings are not relevant.",
        ]
    )

    return EmailMessage(
        subject=subject,
        body="\n".join(lines),
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=[user_email],
    )


def send_saved_search_match_email(preview, from_email=None, site_base_url=None):
    if preview.match_count <= 0:
        return 0

    if not get_saved_search_recipient_email(preview.saved_search):
        return 0

    message = build_saved_search_email_message(
        preview,
        from_email=from_email,
        site_base_url=site_base_url,
    )
    return message.send(fail_silently=False)


def mark_saved_search_sent(saved_search, sent_at=None, mark_checked=True):
    sent_at = sent_at or timezone.now()
    saved_search.last_notification_sent_at = sent_at
    update_fields = ["last_notification_sent_at", "updated_at"]

    if mark_checked:
        saved_search.last_notification_checked_at = sent_at
        update_fields.append("last_notification_checked_at")

    saved_search.save(update_fields=update_fields)
    return saved_search
