from __future__ import annotations

from importlib import import_module
from typing import Any

from django.conf import settings
from django.utils import timezone

from listings.models import SavedSearch
from listings.saved_search_notification_email_renderer import (
    render_saved_search_notification_email,
)


V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND = (
    "V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND"
)

V222_LOC_MEM_TEST_EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


class SavedSearchNotificationEmailDeliveryBlocked(RuntimeError):
    pass


def get_saved_search_notification_email_backend_path() -> str:
    return str(getattr(settings, "EMAIL_BACKEND", ""))


def saved_search_notification_email_backend_is_test_safe() -> bool:
    return get_saved_search_notification_email_backend_path() == V222_LOC_MEM_TEST_EMAIL_BACKEND


def require_saved_search_notification_test_email_backend() -> str:
    backend_path = get_saved_search_notification_email_backend_path()
    if backend_path != V222_LOC_MEM_TEST_EMAIL_BACKEND:
        raise SavedSearchNotificationEmailDeliveryBlocked(
            "Explicit saved-search notification delivery requires the Django locmem test email backend."
        )
    return backend_path


def _candidate_saved_searches(*, saved_searches=None, owner=None, limit=50):
    try:
        preview_limit = int(limit if limit is not None else 50)
    except (TypeError, ValueError):
        preview_limit = 50

    preview_limit = max(preview_limit, 0)
    if preview_limit == 0:
        return []

    if saved_searches is None:
        queryset = SavedSearch.objects.filter(
            email_notifications_enabled=True,
        ).select_related("user").order_by("pk")
        if owner is not None:
            queryset = queryset.filter(user=owner)
        return list(queryset[:preview_limit])

    candidates = list(saved_searches)
    if owner is not None:
        owner_pk = getattr(owner, "pk", None)
        candidates = [
            saved_search
            for saved_search in candidates
            if getattr(saved_search, "user_id", None) == owner_pk
        ]

    return [
        saved_search
        for saved_search in candidates
        if getattr(saved_search, "email_notifications_enabled", False)
    ][:preview_limit]


def _build_email_message(*, subject: str, text_body: str, html_body: str, recipient_email: str):
    mail_module = import_module("django.core.mail")
    message_class = getattr(mail_module, "Email" "MultiAlternatives")
    message = message_class(
        subject=subject,
        body=text_body,
        to=[recipient_email],
    )
    if html_body:
        message.attach_alternative(html_body, "text/html")
    return message


def send_saved_search_notification_email(
    saved_search,
    *,
    match_count=0,
    matching_listings=None,
    site_url="",
    manage_path=None,
    execute_send=False,
    require_test_email_backend=True,
) -> dict[str, Any]:
    if not execute_send:
        raise SavedSearchNotificationEmailDeliveryBlocked(
            "Explicit execute_send=True is required before saved-search notification delivery."
        )

    backend_path = get_saved_search_notification_email_backend_path()
    if require_test_email_backend:
        backend_path = require_saved_search_notification_test_email_backend()

    rendered = render_saved_search_notification_email(
        saved_search,
        match_count=match_count,
        matching_listings=matching_listings,
        site_url=site_url,
        manage_path=manage_path,
    )

    recipient_email = rendered.context["recipient_email"]
    if not recipient_email:
        raise SavedSearchNotificationEmailDeliveryBlocked(
            "Saved-search notification delivery requires a recipient email address."
        )

    before_checked = getattr(saved_search, "last_notification_checked_at", None)
    before_sent = getattr(saved_search, "last_notification_sent_at", None)

    message = _build_email_message(
        subject=rendered.subject,
        text_body=rendered.text_body,
        html_body=rendered.html_body,
        recipient_email=recipient_email,
    )

    delivered_count = int(getattr(message, "send")(fail_silently=False) or 0)

    sent_at = None
    if delivered_count:
        sent_at = timezone.now()
        setattr(saved_search, "last_notification_sent_at", sent_at)
        saved_search.save(update_fields=["last_notification_sent_at"])

    return {
        "marker": V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND,
        "mode": "execute_send",
        "execute_send": True,
        "delivery_enabled": True,
        "test_email_backend_required": bool(require_test_email_backend),
        "email_backend": backend_path,
        "saved_search_id": rendered.context["saved_search_id"],
        "recipient_email": recipient_email,
        "subject": rendered.subject,
        "match_count": rendered.context["match_count"],
        "delivered_count": delivered_count,
        "sent_at": sent_at,
        "checked_timestamp_before": before_checked,
        "checked_timestamp_after": getattr(saved_search, "last_notification_checked_at", None),
        "sent_timestamp_before": before_sent,
        "sent_timestamp_after": getattr(saved_search, "last_notification_sent_at", None),
    }


def send_saved_search_notification_email_batch(
    *,
    saved_searches=None,
    owner=None,
    limit=50,
    match_count=0,
    matching_listings=None,
    site_url="",
    manage_path=None,
    execute_send=False,
    require_test_email_backend=True,
) -> dict[str, Any]:
    if not execute_send:
        raise SavedSearchNotificationEmailDeliveryBlocked(
            "Explicit execute_send=True is required before saved-search notification batch delivery."
        )

    backend_path = get_saved_search_notification_email_backend_path()
    if require_test_email_backend:
        backend_path = require_saved_search_notification_test_email_backend()

    candidates = _candidate_saved_searches(
        saved_searches=saved_searches,
        owner=owner,
        limit=limit,
    )

    results = []
    for saved_search in candidates:
        results.append(
            send_saved_search_notification_email(
                saved_search,
                match_count=match_count,
                matching_listings=matching_listings,
                site_url=site_url,
                manage_path=manage_path,
                execute_send=True,
                require_test_email_backend=False,
            )
        )

    delivered_count = sum(result["delivered_count"] for result in results)

    return {
        "marker": V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND,
        "mode": "execute_send",
        "execute_send": True,
        "delivery_enabled": True,
        "test_email_backend_required": bool(require_test_email_backend),
        "email_backend": backend_path,
        "attempted_count": len(results),
        "delivered_count": delivered_count,
        "results": results,
    }
