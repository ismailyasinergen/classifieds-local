from __future__ import annotations

import hashlib
import json
from typing import Any

from listings.notification_recipient_output_redaction_v305 import (
    redact_notification_recipient_for_operator_v305,
)

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
            "recipient_email": (
                redact_notification_recipient_for_operator_v305(
                    _user_email_for(saved_search)
                )
            ),
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
        recipient_output = (
            redact_notification_recipient_for_operator_v305(
                item.get("recipient_email")
            )
        )
        lines.append(
            (
                "ROLLBACK CANDIDATE saved_search "
                f"id={item['saved_search_id']} "
                f"owner_id={item['owner_id']} "
                f"recipient={recipient_output} "
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

# V232 persistent audit integration for rollback preview and apply.
from django.db import transaction as _v232_transaction

from .saved_search_notification_audit_runtime import (
    SavedSearchNotificationAuditRuntimeContext,
    find_latest_saved_search_notification_sent_event,
    record_saved_search_notification_runtime_event,
)


V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_ROLLBACK_INTEGRATION = (
    "V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_ROLLBACK_INTEGRATION"
)

_v232_original_build_saved_search_notification_rollback_plan = (
    build_saved_search_notification_rollback_plan
)

_v232_original_rollback_saved_search_notification_sent_timestamp = (
    rollback_saved_search_notification_sent_timestamp
)


def _v232_rollback_runtime_context(
    runtime_context,
    *,
    source,
    mode,
    create_batch=False,
    operator="",
):
    if runtime_context is None:
        runtime_context = (
            SavedSearchNotificationAuditRuntimeContext.create(
                actor_type="operator",
                actor_identifier=str(
                    operator
                    or "saved-search-rollback"
                ),
                source=source,
                mode=mode,
                create_batch=create_batch,
            )
        )

    return runtime_context.for_surface(
        source=source,
        mode=mode,
    )


def build_saved_search_notification_rollback_plan(
    *,
    saved_searches=None,
    owner=None,
    limit=50,
    runtime_context=None,
    record_persistent_audit=False,
) -> dict[str, Any]:
    plan = (
        _v232_original_build_saved_search_notification_rollback_plan(
            saved_searches=saved_searches,
            owner=owner,
            limit=limit,
        )
    )

    if not record_persistent_audit:
        return plan

    rollback_context = _v232_rollback_runtime_context(
        runtime_context,
        source="saved_search.rollback.preview",
        mode="rollback_preview",
        create_batch=True,
    )

    persistent_preview_count = 0

    for item in plan["rollback_candidates"]:
        saved_search = (
            SavedSearch
            .objects
            .select_related("user")
            .get(pk=item["saved_search_id"])
        )

        rollback_target = (
            find_latest_saved_search_notification_sent_event(
                saved_search
            )
        )

        if rollback_target is None:
            item["persistent_audit_status"] = (
                "missing_sent_timestamp_event"
            )
            continue

        preview_write = (
            record_saved_search_notification_runtime_event(
                saved_search=saved_search,
                context=rollback_context,
                event_type="rollback_previewed",
                notification_fingerprint=(
                    rollback_target
                    .notification_fingerprint
                ),
                operation_sequence=(
                    "rollback:"
                    f"{rollback_target.pk}:"
                    "previewed"
                ),
                rollback_of=rollback_target,
                metadata={
                    "mode": "rollback_preview",
                    "preview_count": 1,
                },
            )
        )

        item["persistent_audit_status"] = "recorded"
        item["persistent_audit_event_id"] = str(
            preview_write.event.pk
        )
        item["rollback_of_event_id"] = str(
            rollback_target.pk
        )

        persistent_preview_count += 1

    plan["persistent_audit_enabled"] = True
    plan["persistent_preview_count"] = (
        persistent_preview_count
    )
    plan["audit_correlation_id"] = str(
        rollback_context.correlation_id
    )
    plan["audit_batch_id"] = (
        str(rollback_context.batch_id)
        if rollback_context.batch_id is not None
        else None
    )

    return plan


def rollback_saved_search_notification_sent_timestamp(
    saved_search,
    *,
    previous_sent_at=None,
    execute_rollback=False,
    operator: str = "",
    reason: str = "",
    runtime_context=None,
    rollback_of=None,
    notification_fingerprint=None,
) -> dict[str, Any]:
    if not execute_rollback:
        return (
            _v232_original_rollback_saved_search_notification_sent_timestamp(
                saved_search,
                previous_sent_at=previous_sent_at,
                execute_rollback=False,
                operator=operator,
                reason=reason,
            )
        )

    rollback_target = (
        rollback_of
        or find_latest_saved_search_notification_sent_event(
            saved_search
        )
    )

    if rollback_target is None:
        return (
            _v232_original_rollback_saved_search_notification_sent_timestamp(
                saved_search,
                previous_sent_at=previous_sent_at,
                execute_rollback=True,
                operator=operator,
                reason=reason,
            )
        )

    rollback_context = _v232_rollback_runtime_context(
        runtime_context,
        source="saved_search.rollback.apply",
        mode="execute_rollback",
        operator=operator,
    )

    fingerprint = (
        notification_fingerprint
        or rollback_target.notification_fingerprint
    )

    before_sent_at = getattr(
        saved_search,
        "last_notification_sent_at",
        None,
    )

    try:
        with _v232_transaction.atomic():
            rollback_result = (
                _v232_original_rollback_saved_search_notification_sent_timestamp(
                    saved_search,
                    previous_sent_at=previous_sent_at,
                    execute_rollback=True,
                    operator=operator,
                    reason=reason,
                )
            )

            rollback_write = (
                record_saved_search_notification_runtime_event(
                    saved_search=saved_search,
                    context=rollback_context,
                    event_type="rollback_applied",
                    notification_fingerprint=fingerprint,
                    operation_sequence=(
                        "rollback:"
                        f"{rollback_target.pk}:"
                        "applied"
                    ),
                    reason_code="explicit_rollback",
                    rollback_of=rollback_target,
                    sent_at_before=before_sent_at,
                    sent_at_after=previous_sent_at,
                    metadata={
                        "mode": "execute_rollback",
                        "timestamp_changed": (
                            before_sent_at
                            != previous_sent_at
                        ),
                    },
                )
            )
    except Exception:
        setattr(
            saved_search,
            "last_notification_sent_at",
            before_sent_at,
        )
        raise

    rollback_result["persistent_audit_event_id"] = str(
        rollback_write.event.pk
    )
    rollback_result["rollback_of_event_id"] = str(
        rollback_target.pk
    )
    rollback_result["audit_correlation_id"] = str(
        rollback_context.correlation_id
    )
    rollback_result["notification_fingerprint"] = (
        fingerprint
    )

    return rollback_result
