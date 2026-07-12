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
