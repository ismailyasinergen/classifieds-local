from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from django.template.loader import render_to_string
from django.urls import NoReverseMatch, reverse


V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING = (
    "V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING"
)


@dataclass(frozen=True)
class SavedSearchNotificationEmailRenderResult:
    subject: str
    text_body: str
    html_body: str
    context: dict[str, Any]


def _safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _join_site_url(site_url: str, path: str) -> str:
    clean_path = path or "/"
    if not site_url:
        return clean_path
    return site_url.rstrip("/") + "/" + clean_path.lstrip("/")


def _default_manage_path() -> str:
    try:
        return reverse("saved_search_list")
    except NoReverseMatch:
        return "/listings/saved-searches/"


def _owner_username(owner: Any) -> str:
    get_username = getattr(owner, "get_username", None)
    if callable(get_username):
        username = get_username()
        if username:
            return username
    return _safe_text(getattr(owner, "username", ""), "there") or "there"


def _normalize_listing_summary(item: Any, *, site_url: str) -> dict[str, str]:
    if isinstance(item, dict):
        title = _safe_text(item.get("title"), "Listing")
        url = _safe_text(item.get("url"), "")
        price = _safe_text(item.get("price"), "")
    else:
        title = _safe_text(getattr(item, "title", ""), "Listing")
        price = _safe_text(getattr(item, "price", ""), "")
        get_absolute_url = getattr(item, "get_absolute_url", None)
        url = _safe_text(get_absolute_url() if callable(get_absolute_url) else "", "")

    return {
        "title": title,
        "url": _join_site_url(site_url, url) if url else "",
        "price": price,
    }


def build_saved_search_notification_email_context(
    saved_search: Any,
    *,
    match_count: int,
    matching_listings: Iterable[Any] | None = None,
    site_url: str = "",
    manage_path: str | None = None,
) -> dict[str, Any]:
    if hasattr(saved_search, "email_notifications_enabled"):
        if not saved_search.email_notifications_enabled:
            raise ValueError("Saved search email notifications are disabled.")

    owner = getattr(saved_search, "user", None)
    match_total = max(int(match_count or 0), 0)
    resolved_manage_path = manage_path or _default_manage_path()
    listing_items = list(matching_listings or ())[:10]

    saved_search_name = (
        _safe_text(getattr(saved_search, "name", ""), "").strip() or "Saved search"
    )

    return {
        "recipient_email": _safe_text(getattr(owner, "email", ""), ""),
        "recipient_username": _owner_username(owner),
        "saved_search_id": getattr(saved_search, "pk", None),
        "saved_search_name": saved_search_name,
        "saved_search_querystring": _safe_text(
            getattr(saved_search, "querystring", ""),
            "",
        ),
        "match_count": match_total,
        "match_label": "match" if match_total == 1 else "matches",
        "subject_prefix": "New matches for your saved search",
        "manage_url": _join_site_url(site_url, resolved_manage_path),
        "unsubscribe_guidance": (
            "Manage saved-search email notifications from Saved Searches."
        ),
        "matching_listings": [
            _normalize_listing_summary(item, site_url=site_url)
            for item in listing_items
        ],
    }


def render_saved_search_notification_email(
    saved_search: Any,
    *,
    match_count: int,
    matching_listings: Iterable[Any] | None = None,
    site_url: str = "",
    manage_path: str | None = None,
) -> SavedSearchNotificationEmailRenderResult:
    context = build_saved_search_notification_email_context(
        saved_search,
        match_count=match_count,
        matching_listings=matching_listings,
        site_url=site_url,
        manage_path=manage_path,
    )

    subject = f'{context["subject_prefix"]}: {context["saved_search_name"]}'
    text_body = render_to_string(
        "listings/email/saved_search_notification.txt",
        context,
    ).strip()
    html_body = render_to_string(
        "listings/email/saved_search_notification.html",
        context,
    ).strip()

    return SavedSearchNotificationEmailRenderResult(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        context=context,
    )

# V232 saved-search notification audit runtime renderer integration.
from .saved_search_notification_audit_runtime import (
    SavedSearchNotificationAuditRuntimeContext,
    build_saved_search_notification_fingerprint,
    record_saved_search_notification_runtime_event,
)


V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_RENDERER_INTEGRATION = (
    "V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_RENDERER_INTEGRATION"
)

_v232_original_render_saved_search_notification_email = (
    render_saved_search_notification_email
)


def render_saved_search_notification_email(
    saved_search: Any,
    *,
    match_count: int,
    matching_listings: Iterable[Any] | None = None,
    site_url: str = "",
    manage_path: str | None = None,
    audit_runtime_context: (
        SavedSearchNotificationAuditRuntimeContext | None
    ) = None,
    notification_fingerprint: str | None = None,
    audit_operation_sequence: str | None = None,
    audit_metadata: dict[str, Any] | None = None,
) -> SavedSearchNotificationEmailRenderResult:
    listing_items = list(matching_listings or ())

    rendered = (
        _v232_original_render_saved_search_notification_email(
            saved_search,
            match_count=match_count,
            matching_listings=listing_items,
            site_url=site_url,
            manage_path=manage_path,
        )
    )

    if audit_runtime_context is not None:
        renderer_context = audit_runtime_context.for_surface(
            source="saved_search.renderer.preview",
            mode="dry_run",
        )

        fingerprint = (
            notification_fingerprint
            or build_saved_search_notification_fingerprint(
                saved_search,
                checked_at_before=getattr(
                    saved_search,
                    "last_notification_checked_at",
                    None,
                ),
                matching_listings=listing_items,
            )
        )

        metadata = {
            "mode": "dry_run",
            "match_count": int(
                rendered.context["match_count"]
            ),
            "rendered_item_count": len(
                rendered.context["matching_listings"]
            ),
        }

        if audit_metadata:
            metadata.update(audit_metadata)

        record_saved_search_notification_runtime_event(
            saved_search=saved_search,
            context=renderer_context,
            event_type="dry_run_rendered",
            notification_fingerprint=fingerprint,
            operation_sequence=(
                audit_operation_sequence
                or (
                    "render:"
                    f"{saved_search.pk}:"
                    "dry_run_rendered"
                )
            ),
            metadata=metadata,
        )

    return rendered
