from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from django.db import transaction
from django.utils import timezone

from listings.models import SavedSearch


V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE_MARKER = (
    "V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE"
)


@dataclass(frozen=True)
class SavedSearchNotificationSchedulerResult:
    checked: int
    sent: int
    dry_run: bool


def get_saved_search_notification_candidates() -> Iterable[SavedSearch]:
    """Return opt-in saved searches eligible for a local scheduler pass.

    This v214 implementation spike only identifies opt-in saved searches and
    records check timestamps. It deliberately does not send email yet.
    """

    return (
        SavedSearch.objects.filter(email_notifications_enabled=True)
        .select_related("user")
        .order_by("pk")
    )


def run_saved_search_notification_scheduler(
    *,
    dry_run: bool = True,
    limit: int | None = None,
) -> SavedSearchNotificationSchedulerResult:
    """Run one local saved-search notification scheduler pass.

    v214 is intentionally conservative:
    - default mode is dry-run;
    - disabled saved-search notifications are excluded;
    - no email is sent;
    - execute mode only records last_notification_checked_at.
    """

    candidates = get_saved_search_notification_candidates()

    if limit is not None:
        candidates = candidates[:limit]

    checked = 0
    checked_ids: list[int] = []

    for saved_search in candidates:
        checked += 1
        checked_ids.append(saved_search.pk)

    if not dry_run and checked_ids:
        checked_at = timezone.now()
        with transaction.atomic():
            SavedSearch.objects.filter(pk__in=checked_ids).update(
                last_notification_checked_at=checked_at
            )

    return SavedSearchNotificationSchedulerResult(
        checked=checked,
        sent=0,
        dry_run=dry_run,
    )

# v221 saved-search email preview integration.
#
# This intentionally renders email previews for operator-visible dry-run review
# only. It does not send email, does not create a sender module, does not add a
# background worker, and does not mutate notification sent timestamps.
from listings.models import SavedSearch as _V221SavedSearch
from listings.saved_search_notification_email_renderer import (
    render_saved_search_notification_email as _v221_render_saved_search_notification_email,
)


V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION = (
    "V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION"
)


def _v221_normalize_preview_limit(limit):
    if limit is None:
        return 50
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return 50
    return max(value, 0)


def build_saved_search_notification_email_dry_run_preview(
    saved_search,
    *,
    match_count=0,
    matching_listings=None,
    site_url="",
    manage_path=None,
):
    rendered = _v221_render_saved_search_notification_email(
        saved_search,
        match_count=match_count,
        matching_listings=matching_listings,
        site_url=site_url,
        manage_path=manage_path,
    )

    return {
        "marker": V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION,
        "mode": "dry_run",
        "dry_run": True,
        "would_send": False,
        "delivery_enabled": False,
        "requires_explicit_execute": True,
        "saved_search_id": rendered.context["saved_search_id"],
        "recipient_email": rendered.context["recipient_email"],
        "subject": rendered.subject,
        "text_body": rendered.text_body,
        "html_body": rendered.html_body,
        "match_count": rendered.context["match_count"],
        "checked_timestamp_mutation_allowed": False,
        "sent_timestamp_mutation_allowed": False,
    }


def build_saved_search_notification_scheduler_email_previews(
    *,
    saved_searches=None,
    owner=None,
    limit=50,
    match_count=0,
    matching_listings=None,
    site_url="",
    manage_path=None,
):
    preview_limit = _v221_normalize_preview_limit(limit)
    if preview_limit == 0:
        return []

    if saved_searches is None:
        candidates = _V221SavedSearch.objects.filter(
            email_notifications_enabled=True,
        ).select_related("user").order_by("pk")
        if owner is not None:
            candidates = candidates.filter(user=owner)
        candidates = list(candidates[:preview_limit])
    else:
        candidates = list(saved_searches)
        if owner is not None:
            owner_pk = getattr(owner, "pk", None)
            candidates = [
                saved_search
                for saved_search in candidates
                if getattr(saved_search, "user_id", None) == owner_pk
            ]
        candidates = [
            saved_search
            for saved_search in candidates
            if getattr(saved_search, "email_notifications_enabled", False)
        ][:preview_limit]

    previews = []
    for saved_search in candidates:
        previews.append(
            build_saved_search_notification_email_dry_run_preview(
                saved_search,
                match_count=match_count,
                matching_listings=matching_listings,
                site_url=site_url,
                manage_path=manage_path,
            )
        )

    return previews
