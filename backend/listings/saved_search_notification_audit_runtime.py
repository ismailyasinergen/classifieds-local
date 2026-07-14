from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
)
from .saved_search_notification_audit_persistence import (
    SavedSearchNotificationAuditWriteResult,
    record_saved_search_notification_audit_event,
)


V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION = (
    "V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION"
)

IDEMPOTENCY_PREFIX = "ssna:v1:"

EVENT_OUTCOMES = {
    "evaluation_started": "pending",
    "skipped_notifications_disabled": "skipped",
    "skipped_missing_recipient": "skipped",
    "dry_run_rendered": "succeeded",
    "delivery_attempted": "pending",
    "delivery_succeeded": "succeeded",
    "delivery_failed": "failed",
    "sent_timestamp_recorded": "succeeded",
    "rollback_previewed": "succeeded",
    "rollback_applied": "rolled_back",
}

RUNTIME_METADATA_ALLOWLIST = {
    "evaluation_started": frozenset(
        {
            "mode",
            "owner_scope",
            "batch_position",
        }
    ),
    "skipped_notifications_disabled": frozenset(
        {
            "mode",
            "skip_reason",
        }
    ),
    "skipped_missing_recipient": frozenset(
        {
            "mode",
            "skip_reason",
        }
    ),
    "dry_run_rendered": frozenset(
        {
            "mode",
            "match_count",
            "rendered_item_count",
        }
    ),
    "delivery_attempted": frozenset(
        {
            "mode",
            "match_count",
            "backend_kind",
        }
    ),
    "delivery_succeeded": frozenset(
        {
            "mode",
            "match_count",
            "backend_kind",
        }
    ),
    "delivery_failed": frozenset(
        {
            "mode",
            "match_count",
            "backend_kind",
            "error_code",
        }
    ),
    "sent_timestamp_recorded": frozenset(
        {
            "mode",
            "timestamp_changed",
        }
    ),
    "rollback_previewed": frozenset(
        {
            "mode",
            "preview_count",
        }
    ),
    "rollback_applied": frozenset(
        {
            "mode",
            "timestamp_changed",
        }
    ),
}


def _validation_error(
    field: str,
    message: str,
) -> ValidationError:
    return ValidationError(
        {
            field: [message],
        }
    )


def _normalize_uuid(
    value: uuid.UUID | str | None,
    *,
    field: str,
    required: bool,
) -> uuid.UUID | None:
    if value in (None, ""):
        if required:
            raise _validation_error(
                field,
                "This UUID is required.",
            )

        return None

    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise _validation_error(
            field,
            "Enter a valid UUID.",
        ) from exc


def _normalize_aware_datetime(
    value: datetime | None,
    *,
    field: str,
    required: bool,
) -> datetime | None:
    if value is None:
        if required:
            raise _validation_error(
                field,
                "This timestamp is required.",
            )

        return None

    if not isinstance(value, datetime):
        raise _validation_error(
            field,
            "Enter a valid datetime.",
        )

    if timezone.is_naive(value):
        raise _validation_error(
            field,
            "Timezone-aware datetime values are required.",
        )

    return value


def _canonical_default(value: Any) -> str:
    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    raise TypeError(
        f"Unsupported canonical JSON value: {type(value).__name__}"
    )


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        allow_nan=False,
        default=_canonical_default,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_canonical(payload: Mapping[str, Any]) -> str:
    canonical = _canonical_json(payload)

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _listing_identifier(item: Any) -> str | None:
    if isinstance(item, Mapping):
        value = item.get("id")

        if value is None:
            value = item.get("pk")
    else:
        value = getattr(item, "pk", None)

        if value is None:
            value = getattr(item, "id", None)

    if value is None:
        return None

    return str(value)


@dataclass(frozen=True, slots=True)
class SavedSearchNotificationAuditRuntimeContext:
    correlation_id: uuid.UUID
    batch_id: uuid.UUID | None
    actor_type: str
    actor_identifier: str
    source: str
    started_at: datetime
    mode: str

    @classmethod
    def create(
        cls,
        *,
        actor_type: str,
        source: str,
        actor_identifier: str = "",
        mode: str,
        correlation_id: uuid.UUID | str | None = None,
        batch_id: uuid.UUID | str | None = None,
        create_batch: bool = False,
        started_at: datetime | None = None,
    ) -> "SavedSearchNotificationAuditRuntimeContext":
        correlation_id = _normalize_uuid(
            correlation_id or uuid.uuid4(),
            field="correlation_id",
            required=True,
        )

        if batch_id is None and create_batch:
            batch_id = uuid.uuid4()

        normalized_batch_id = _normalize_uuid(
            batch_id,
            field="batch_id",
            required=False,
        )

        normalized_started_at = _normalize_aware_datetime(
            started_at or timezone.now(),
            field="started_at",
            required=True,
        )

        actor_type = str(actor_type or "").strip()
        source = str(source or "").strip()
        actor_identifier = str(actor_identifier or "").strip()
        mode = str(mode or "").strip()

        if actor_type not in (
            SavedSearchNotificationAuditEvent
            .ActorType
            .values
        ):
            raise _validation_error(
                "actor_type",
                f"Unsupported actor_type: {actor_type!r}.",
            )

        if not source:
            raise _validation_error(
                "source",
                "A stable runtime source is required.",
            )

        if not mode:
            raise _validation_error(
                "mode",
                "A runtime mode is required.",
            )

        return cls(
            correlation_id=correlation_id,
            batch_id=normalized_batch_id,
            actor_type=actor_type,
            actor_identifier=actor_identifier,
            source=source,
            started_at=normalized_started_at,
            mode=mode,
        )

    def for_surface(
        self,
        *,
        source: str,
        mode: str | None = None,
    ) -> "SavedSearchNotificationAuditRuntimeContext":
        source = str(source or "").strip()

        if not source:
            raise _validation_error(
                "source",
                "A stable runtime source is required.",
            )

        return replace(
            self,
            source=source,
            mode=str(mode or self.mode),
        )


def build_saved_search_notification_fingerprint(
    saved_search: SavedSearch,
    *,
    checked_at_before: datetime | None = None,
    matching_listings: Iterable[Any] | None = None,
) -> str:
    if not isinstance(saved_search, SavedSearch):
        raise _validation_error(
            "saved_search",
            "A SavedSearch instance is required.",
        )

    if saved_search.pk is None:
        raise _validation_error(
            "saved_search",
            "The SavedSearch must already be saved.",
        )

    if checked_at_before is None:
        checked_at_before = (
            saved_search.last_notification_checked_at
        )

    if checked_at_before is not None:
        checked_at_before = _normalize_aware_datetime(
            checked_at_before,
            field="checked_at_before",
            required=False,
        )

    ordered_matching_listing_ids = []

    for item in matching_listings or ():
        identifier = _listing_identifier(item)

        if identifier is not None:
            ordered_matching_listing_ids.append(identifier)

    payload = {
        "saved_search_id": str(saved_search.pk),
        "saved_search_path": str(saved_search.path or ""),
        "saved_search_querystring": str(
            saved_search.querystring or ""
        ),
        "checked_at_before": (
            checked_at_before.isoformat()
            if checked_at_before is not None
            else None
        ),
        "ordered_matching_listing_ids": (
            ordered_matching_listing_ids
        ),
    }

    return _sha256_canonical(payload)


def build_saved_search_notification_audit_idempotency_key(
    *,
    saved_search: SavedSearch,
    context: SavedSearchNotificationAuditRuntimeContext,
    event_type: str,
    operation_sequence: str,
    delivery_attempt_id: uuid.UUID | str | None = None,
    rollback_of: SavedSearchNotificationAuditEvent | None = None,
) -> str:
    if not isinstance(saved_search, SavedSearch):
        raise _validation_error(
            "saved_search",
            "A SavedSearch instance is required.",
        )

    if saved_search.pk is None:
        raise _validation_error(
            "saved_search",
            "The SavedSearch must already be saved.",
        )

    if not isinstance(
        context,
        SavedSearchNotificationAuditRuntimeContext,
    ):
        raise _validation_error(
            "context",
            "A runtime audit context is required.",
        )

    event_type = str(event_type or "").strip()

    if event_type not in EVENT_OUTCOMES:
        raise _validation_error(
            "event_type",
            f"Unsupported event_type: {event_type!r}.",
        )

    operation_sequence = str(
        operation_sequence or ""
    ).strip()

    if not operation_sequence:
        raise _validation_error(
            "operation_sequence",
            "A stable operation sequence is required.",
        )

    normalized_attempt_id = _normalize_uuid(
        delivery_attempt_id,
        field="delivery_attempt_id",
        required=False,
    )

    payload = {
        "saved_search_id": str(saved_search.pk),
        "event_type": event_type,
        "correlation_id": str(context.correlation_id),
        "batch_id": (
            str(context.batch_id)
            if context.batch_id is not None
            else None
        ),
        "delivery_attempt_id": (
            str(normalized_attempt_id)
            if normalized_attempt_id is not None
            else None
        ),
        "rollback_of_id": (
            str(rollback_of.pk)
            if rollback_of is not None
            else None
        ),
        "operation_sequence": operation_sequence,
    }

    return (
        IDEMPOTENCY_PREFIX
        + _sha256_canonical(payload)
    )


def _normalize_runtime_metadata(
    *,
    event_type: str,
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if metadata is None:
        return {}

    if not isinstance(metadata, Mapping):
        raise _validation_error(
            "metadata",
            "Runtime metadata must be a mapping.",
        )

    allowed_keys = RUNTIME_METADATA_ALLOWLIST[event_type]
    provided_keys = set(metadata)

    forbidden_keys = sorted(
        provided_keys - allowed_keys
    )

    if forbidden_keys:
        raise _validation_error(
            "metadata",
            (
                "Runtime metadata contains non-allowlisted "
                f"keys for {event_type}: "
                + ", ".join(forbidden_keys)
            ),
        )

    return dict(metadata)


def record_saved_search_notification_runtime_event(
    *,
    saved_search: SavedSearch,
    context: SavedSearchNotificationAuditRuntimeContext,
    event_type: str,
    notification_fingerprint: str,
    operation_sequence: str,
    outcome: str | None = None,
    reason_code: str = "",
    occurred_at: datetime | None = None,
    delivery_attempt_id: uuid.UUID | str | None = None,
    rollback_of: SavedSearchNotificationAuditEvent | None = None,
    checked_at_before: datetime | None = None,
    checked_at_after: datetime | None = None,
    sent_at_before: datetime | None = None,
    sent_at_after: datetime | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> SavedSearchNotificationAuditWriteResult:
    if not isinstance(
        context,
        SavedSearchNotificationAuditRuntimeContext,
    ):
        raise _validation_error(
            "context",
            "A runtime audit context is required.",
        )

    event_type = str(event_type or "").strip()

    if event_type not in EVENT_OUTCOMES:
        raise _validation_error(
            "event_type",
            f"Unsupported event_type: {event_type!r}.",
        )

    resolved_outcome = str(
        outcome or EVENT_OUTCOMES[event_type]
    ).strip()

    notification_fingerprint = str(
        notification_fingerprint or ""
    ).strip().casefold()

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        notification_fingerprint,
    ):
        raise _validation_error(
            "notification_fingerprint",
            (
                "A 64-character hexadecimal notification "
                "fingerprint is required."
            ),
        )

    normalized_metadata = _normalize_runtime_metadata(
        event_type=event_type,
        metadata=metadata,
    )

    idempotency_key = (
        build_saved_search_notification_audit_idempotency_key(
            saved_search=saved_search,
            context=context,
            event_type=event_type,
            operation_sequence=operation_sequence,
            delivery_attempt_id=delivery_attempt_id,
            rollback_of=rollback_of,
        )
    )

    return record_saved_search_notification_audit_event(
        saved_search=saved_search,
        event_type=event_type,
        outcome=resolved_outcome,
        occurred_at=occurred_at or context.started_at,
        correlation_id=context.correlation_id,
        batch_id=context.batch_id,
        delivery_attempt_id=delivery_attempt_id,
        idempotency_key=idempotency_key,
        notification_fingerprint=notification_fingerprint,
        rollback_of=rollback_of,
        actor_type=context.actor_type,
        actor_identifier=context.actor_identifier,
        source=context.source,
        reason_code=reason_code,
        checked_at_before=checked_at_before,
        checked_at_after=checked_at_after,
        sent_at_before=sent_at_before,
        sent_at_after=sent_at_after,
        metadata=normalized_metadata,
    )


def find_latest_saved_search_notification_sent_event(
    saved_search: SavedSearch,
) -> SavedSearchNotificationAuditEvent | None:
    if not isinstance(saved_search, SavedSearch):
        raise _validation_error(
            "saved_search",
            "A SavedSearch instance is required.",
        )

    if saved_search.pk is None:
        return None

    return (
        SavedSearchNotificationAuditEvent
        .objects
        .filter(
            saved_search=saved_search,
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .SENT_TIMESTAMP_RECORDED
            ),
            outcome=(
                SavedSearchNotificationAuditEvent
                .Outcome
                .SUCCEEDED
            ),
        )
        .order_by(
            "-occurred_at",
            "-created_at",
        )
        .first()
    )


__all__ = [
    "EVENT_OUTCOMES",
    "IDEMPOTENCY_PREFIX",
    "RUNTIME_METADATA_ALLOWLIST",
    "SavedSearchNotificationAuditRuntimeContext",
    "V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION",
    "build_saved_search_notification_audit_idempotency_key",
    "build_saved_search_notification_fingerprint",
    "find_latest_saved_search_notification_sent_event",
    "record_saved_search_notification_runtime_event",
]
