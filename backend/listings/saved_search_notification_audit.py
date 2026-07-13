from __future__ import annotations

import hashlib
import json
from typing import Any

from django.utils import timezone

from listings.models import SavedSearch


V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING = (
    "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING"
)


class SavedSearchNotificationRollbackBlocked(RuntimeError):
    pass


def _normalize_limit(limit) -> int:
    if limit is None:
        return 50
    try:
        value = int(limit)
    except (TypeError, ValueError):
        value = 50
    return max(value, 0)


def _iso_or_none(value):
    if value is None:
        return None
    isoformat = getattr(value, "isoformat", None)
    if callable(isoformat):
        return isoformat()
    return str(value)


def _user_email_for(saved_search) -> str:
    user = getattr(saved_search, "user", None)
    return str(getattr(user, "email", "") or "")


def _label_for(saved_search) -> str:
    name = str(getattr(saved_search, "name", "") or "").strip()
    if name:
        return name
    querystring = str(getattr(saved_search, "querystring", "") or "").strip()
    if querystring:
        return querystring
    return f"Saved search #{getattr(saved_search, 'pk', '')}"


def build_saved_search_notification_audit_event(
    *,
    action: str,
    saved_search=None,
    delivery_result: dict[str, Any] | None = None,
    rollback_result: dict[str, Any] | None = None,
    operator: str = "",
    reason: str = "",
) -> dict[str, Any]:
    delivery_result = dict(delivery_result or {})
    rollback_result = dict(rollback_result or {})

    saved_search_id = getattr(saved_search, "pk", None)
    if saved_search_id is None:
        saved_search_id = delivery_result.get("saved_search_id")
    if saved_search_id is None:
        saved_search_id = rollback_result.get("saved_search_id")

    recipient_email = ""
    if saved_search is not None:
        recipient_email = _user_email_for(saved_search)
    recipient_email = recipient_email or str(delivery_result.get("recipient_email") or "")
    recipient_email = recipient_email or str(rollback_result.get("recipient_email") or "")

    payload = {
        "marker": V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING,
        "schema_version": 1,
        "action": action,
        "operator": str(operator or ""),
        "reason": str(reason or ""),
        "saved_search_id": saved_search_id,
        "owner_id": getattr(saved_search, "user_id", None) if saved_search is not None else None,
        "recipient_email": recipient_email,
        "label": _label_for(saved_search) if saved_search is not None else "",
        "delivery_result": {
            "mode": delivery_result.get("mode"),
            "execute_send": bool(delivery_result.get("execute_send", False)),
            "delivery_enabled": bool(delivery_result.get("delivery_enabled", False)),
            "delivered_count": int(delivery_result.get("delivered_count") or 0),
            "sent_timestamp_before": _iso_or_none(delivery_result.get("sent_timestamp_before")),
            "sent_timestamp_after": _iso_or_none(delivery_result.get("sent_timestamp_after")),
        },
        "rollback_result": {
            "execute_rollback": bool(rollback_result.get("execute_rollback", False)),
            "rollback_applied": bool(rollback_result.get("rollback_applied", False)),
            "sent_timestamp_before": _iso_or_none(rollback_result.get("sent_timestamp_before")),
            "sent_timestamp_after": _iso_or_none(rollback_result.get("sent_timestamp_after")),
        },
    }

    canonical = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    payload["audit_fingerprint"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    return payload


def build_saved_search_notification_rollback_plan(
    *,
    saved_searches=None,
    owner=None,
    limit=50,
) -> dict[str, Any]:
    plan_limit = _normalize_limit(limit)

    if saved_searches is None:
        queryset = SavedSearch.objects.select_related("user").order_by("pk")
        if owner is not None:
            queryset = queryset.filter(user=owner)
        candidates = list(queryset[:plan_limit]) if plan_limit else []
    else:
        candidates = list(saved_searches)
        if owner is not None:
            owner_pk = getattr(owner, "pk", None)
            candidates = [
                saved_search
                for saved_search in candidates
                if getattr(saved_search, "user_id", None) == owner_pk
            ]
        candidates = candidates[:plan_limit] if plan_limit else []

    rollback_candidates = []
    untouched_candidates = []

    for saved_search in candidates:
        item = {
            "saved_search_id": saved_search.pk,
            "label": _label_for(saved_search),
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
        if getattr(saved_search, "last_notification_sent_at", None) is not None:
            rollback_candidates.append(item)
        else:
            untouched_candidates.append(item)

    return {
        "marker": V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING,
        "mode": "rollback_plan",
        "read_only": True,
        "mutation_allowed": False,
        "owner_scoped": owner is not None,
        "limit": plan_limit,
        "candidate_count": len(candidates),
        "rollback_candidate_count": len(rollback_candidates),
        "untouched_candidate_count": len(untouched_candidates),
        "rollback_candidates": rollback_candidates,
        "untouched_candidates": untouched_candidates,
    }


def format_saved_search_notification_rollback_plan_lines(plan: dict[str, Any]) -> list[str]:
    lines = [
        (
            f"{V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING} "
            f"mode=rollback_plan read_only=True mutation_allowed=False "
            f"owner_scoped={plan['owner_scoped']} "
            f"candidates={plan['candidate_count']} "
            f"rollback_candidates={plan['rollback_candidate_count']} "
            f"untouched={plan['untouched_candidate_count']}"
        )
    ]

    for item in plan["rollback_candidates"]:
        lines.append(
            (
                "ROLLBACK CANDIDATE saved_search "
                f"id={item['saved_search_id']} "
                f"owner_id={item['owner_id']} "
                f"recipient={item['recipient_email'] or '<missing>'} "
                f"sent_at={item['last_notification_sent_at'] or '<none>'} "
                f"label={item['label']}"
            )
        )

    return lines


def rollback_saved_search_notification_sent_timestamp(
    saved_search,
    *,
    previous_sent_at=None,
    execute_rollback=False,
    operator: str = "",
    reason: str = "",
) -> dict[str, Any]:
    if not execute_rollback:
        raise SavedSearchNotificationRollbackBlocked(
            "Explicit execute_rollback=True is required before saved-search notification timestamp rollback."
        )

    before_sent_at = getattr(saved_search, "last_notification_sent_at", None)
    before_checked_at = getattr(saved_search, "last_notification_checked_at", None)

    setattr(saved_search, "last_notification_sent_at", previous_sent_at)
    saved_search.save(update_fields=["last_notification_sent_at"])

    after_sent_at = getattr(saved_search, "last_notification_sent_at", None)

    rollback_result = {
        "marker": V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING,
        "mode": "execute_rollback",
        "execute_rollback": True,
        "rollback_applied": True,
        "saved_search_id": saved_search.pk,
        "recipient_email": _user_email_for(saved_search),
        "sent_timestamp_before": before_sent_at,
        "sent_timestamp_after": after_sent_at,
        "checked_timestamp_before": before_checked_at,
        "checked_timestamp_after": getattr(saved_search, "last_notification_checked_at", None),
    }

    rollback_result["audit_event"] = build_saved_search_notification_audit_event(
        action="rollback_sent_timestamp",
        saved_search=saved_search,
        rollback_result=rollback_result,
        operator=operator,
        reason=reason,
    )

    return rollback_result
