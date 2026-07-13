from __future__ import annotations

from typing import Any

from listings.models import SavedSearch


V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY = (
    "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY"
)


def _normalize_observability_limit(limit) -> int:
    if limit is None:
        return 50
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 50
    return max(value, 0)


def _user_email_for(saved_search) -> str:
    user = getattr(saved_search, "user", None)
    return str(getattr(user, "email", "") or "")


def _iso_or_none(value):
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _saved_search_label(saved_search) -> str:
    name = str(getattr(saved_search, "name", "") or "").strip()
    if name:
        return name
    querystring = str(getattr(saved_search, "querystring", "") or "").strip()
    if querystring:
        return querystring
    return f"Saved search #{getattr(saved_search, 'pk', '')}"


def build_saved_search_notification_observability_snapshot(
    *,
    owner=None,
    limit=50,
    include_samples=True,
) -> dict[str, Any]:
    sample_limit = _normalize_observability_limit(limit)

    queryset = SavedSearch.objects.select_related("user").order_by("pk")
    if owner is not None:
        queryset = queryset.filter(user=owner)

    total_count = queryset.count()
    enabled_count = queryset.filter(email_notifications_enabled=True).count()
    disabled_count = queryset.filter(email_notifications_enabled=False).count()
    checked_timestamp_count = queryset.exclude(last_notification_checked_at__isnull=True).count()
    sent_timestamp_count = queryset.exclude(last_notification_sent_at__isnull=True).count()

    enabled_rows = list(queryset.filter(email_notifications_enabled=True))
    enabled_with_email_count = sum(1 for saved_search in enabled_rows if _user_email_for(saved_search))
    missing_recipient_email_count = max(enabled_count - enabled_with_email_count, 0)

    samples = []
    if include_samples and sample_limit:
        for saved_search in list(queryset[:sample_limit]):
            samples.append(
                {
                    "saved_search_id": saved_search.pk,
                    "label": _saved_search_label(saved_search),
                    "owner_id": getattr(saved_search, "user_id", None),
                    "recipient_email": _user_email_for(saved_search),
                    "email_notifications_enabled": bool(
                        getattr(saved_search, "email_notifications_enabled", False)
                    ),
                    "last_notification_checked_at": _iso_or_none(
                        getattr(saved_search, "last_notification_checked_at", None)
                    ),
                    "last_notification_sent_at": _iso_or_none(
                        getattr(saved_search, "last_notification_sent_at", None)
                    ),
                }
            )

    return {
        "marker": V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY,
        "mode": "observability",
        "read_only": True,
        "delivery_enabled": False,
        "mutation_allowed": False,
        "owner_scoped": owner is not None,
        "limit": sample_limit,
        "total_count": total_count,
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
        "enabled_with_email_count": enabled_with_email_count,
        "missing_recipient_email_count": missing_recipient_email_count,
        "checked_timestamp_count": checked_timestamp_count,
        "sent_timestamp_count": sent_timestamp_count,
        "sample_count": len(samples),
        "samples": samples,
    }


def format_saved_search_notification_observability_lines(snapshot: dict[str, Any]) -> list[str]:
    lines = [
        (
            f"{V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY} "
            f"mode=observability read_only=True delivery_enabled=False "
            f"mutation_allowed=False owner_scoped={snapshot['owner_scoped']} "
            f"total={snapshot['total_count']} enabled={snapshot['enabled_count']} "
            f"disabled={snapshot['disabled_count']} "
            f"enabled_with_email={snapshot['enabled_with_email_count']} "
            f"missing_recipient_email={snapshot['missing_recipient_email_count']} "
            f"checked_timestamps={snapshot['checked_timestamp_count']} "
            f"sent_timestamps={snapshot['sent_timestamp_count']} "
            f"samples={snapshot['sample_count']}"
        )
    ]

    for sample in snapshot["samples"]:
        lines.append(
            (
                "OBSERVABILITY saved_search "
                f"id={sample['saved_search_id']} "
                f"owner_id={sample['owner_id']} "
                f"enabled={sample['email_notifications_enabled']} "
                f"recipient={sample['recipient_email'] or '<missing>'} "
                f"checked_at={sample['last_notification_checked_at'] or '<none>'} "
                f"sent_at={sample['last_notification_sent_at'] or '<none>'} "
                f"label={sample['label']}"
            )
        )

    return lines
