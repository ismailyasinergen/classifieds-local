from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
)


V230_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_WRITE_SERVICE = (
    "V230_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_WRITE_SERVICE"
)


METADATA_DENYLIST = frozenset(
    {
        "access_token",
        "api_key",
        "api_token",
        "auth",
        "auth_header",
        "authentication",
        "authorization",
        "authorization_header",
        "client_secret",
        "cookie",
        "cookies",
        "email_body",
        "password",
        "refresh_token",
        "rendered_body",
        "rendered_email",
        "rendered_html",
        "rendered_text",
        "secret",
        "session",
        "session_id",
        "smtp_password",
        "stack_trace",
        "stacktrace",
        "token",
        "traceback",
    }
)

_METADATA_DENIED_SEGMENTS = frozenset(
    {
        "auth",
        "authentication",
        "authorization",
        "cookie",
        "cookies",
        "password",
        "secret",
        "session",
        "token",
        "traceback",
    }
)

_ROLLBACK_EVENT_TYPES = frozenset(
    {
        SavedSearchNotificationAuditEvent.EventType.ROLLBACK_PREVIEWED,
        SavedSearchNotificationAuditEvent.EventType.ROLLBACK_APPLIED,
    }
)

_DELIVERY_EVENT_TYPES = frozenset(
    {
        SavedSearchNotificationAuditEvent.EventType.DELIVERY_ATTEMPTED,
        SavedSearchNotificationAuditEvent.EventType.DELIVERY_SUCCEEDED,
        SavedSearchNotificationAuditEvent.EventType.DELIVERY_FAILED,
    }
)

_REPLAY_FIELDS = (
    "saved_search_id",
    "owner_id_snapshot",
    "event_type",
    "outcome",
    "reason_code",
    "occurred_at",
    "batch_id",
    "correlation_id",
    "delivery_attempt_id",
    "notification_fingerprint",
    "rollback_of_id",
    "actor_type",
    "actor_identifier",
    "source",
    "checked_at_before",
    "checked_at_after",
    "sent_at_before",
    "sent_at_after",
    "metadata",
)


class SavedSearchNotificationAuditIdempotencyConflict(RuntimeError):
    def __init__(
        self,
        *,
        idempotency_key: str,
        differing_fields: tuple[str, ...],
    ) -> None:
        self.idempotency_key = idempotency_key
        self.differing_fields = differing_fields

        fields = ", ".join(differing_fields)

        super().__init__(
            "Saved-search notification audit idempotency conflict "
            f"for key {idempotency_key!r}; differing fields: {fields}."
        )


@dataclass(frozen=True, slots=True)
class SavedSearchNotificationAuditWriteResult:
    event: SavedSearchNotificationAuditEvent
    created: bool


def _validation_error(
    field: str,
    message: str,
) -> ValidationError:
    return ValidationError(
        {
            field: [message],
        }
    )


def _normalize_text(
    value: Any,
    *,
    field: str,
    max_length: int,
    required: bool,
) -> str:
    normalized = str(value or "").strip()

    if required and not normalized:
        raise _validation_error(
            field,
            "This value is required.",
        )

    if len(normalized) > max_length:
        raise _validation_error(
            field,
            f"Ensure this value has at most {max_length} characters.",
        )

    return normalized


def _normalize_uuid(
    value: Any,
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


def _normalize_datetime(
    value: Any,
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
            "Enter a valid datetime value.",
        )

    if timezone.is_naive(value):
        raise _validation_error(
            field,
            "Timezone-aware datetime values are required.",
        )

    return value


def _normalize_metadata_key(key: str) -> str:
    with_word_boundaries = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1_\2",
        key,
    )

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        with_word_boundaries.casefold(),
    ).strip("_")


def _assert_metadata_keys_are_safe(
    value: Any,
    *,
    path: str = "metadata",
) -> None:
    if isinstance(value, Mapping):
        for raw_key, nested_value in value.items():
            if not isinstance(raw_key, str):
                raise _validation_error(
                    "metadata",
                    f"{path} contains a non-string key.",
                )

            normalized_key = _normalize_metadata_key(raw_key)
            segments = {
                segment
                for segment in normalized_key.split("_")
                if segment
            }

            rendered_payload = (
                "rendered" in segments
                and bool(
                    segments.intersection(
                        {
                            "body",
                            "email",
                            "html",
                            "text",
                        }
                    )
                )
            )

            stack_payload = (
                "stack" in segments
                and "trace" in segments
            )

            if (
                normalized_key in METADATA_DENYLIST
                or bool(
                    segments.intersection(
                        _METADATA_DENIED_SEGMENTS
                    )
                )
                or rendered_payload
                or stack_payload
                or normalized_key.endswith("_api_key")
                or normalized_key.endswith("_private_key")
            ):
                raise _validation_error(
                    "metadata",
                    (
                        "Sensitive metadata key is not permitted: "
                        f"{path}.{raw_key}"
                    ),
                )

            _assert_metadata_keys_are_safe(
                nested_value,
                path=f"{path}.{raw_key}",
            )

        return

    if isinstance(value, (list, tuple)):
        for index, nested_value in enumerate(value):
            _assert_metadata_keys_are_safe(
                nested_value,
                path=f"{path}[{index}]",
            )


def _normalize_metadata(
    metadata: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if metadata is None:
        return {}

    if not isinstance(metadata, Mapping):
        raise _validation_error(
            "metadata",
            "Metadata must be a mapping.",
        )

    _assert_metadata_keys_are_safe(metadata)

    try:
        encoded = json.dumps(
            metadata,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise _validation_error(
            "metadata",
            "Metadata must contain JSON-serializable values.",
        ) from exc

    normalized = json.loads(encoded)

    if not isinstance(normalized, dict):
        raise _validation_error(
            "metadata",
            "Metadata must normalize to a JSON object.",
        )

    return normalized


def _validate_saved_search(
    saved_search: SavedSearch,
) -> SavedSearch:
    if not isinstance(saved_search, SavedSearch):
        raise _validation_error(
            "saved_search",
            "A SavedSearch instance is required.",
        )

    if saved_search.pk is None:
        raise _validation_error(
            "saved_search",
            "The SavedSearch instance must already be saved.",
        )

    if saved_search.user_id is None:
        raise _validation_error(
            "saved_search",
            "The SavedSearch must have an owner.",
        )

    return saved_search


def _validate_choice(
    value: str,
    *,
    field: str,
    allowed_values: tuple[str, ...] | list[str],
) -> str:
    if value not in allowed_values:
        raise _validation_error(
            field,
            f"Unsupported {field}: {value!r}.",
        )

    return value


def _build_expected_replay_values(
    *,
    saved_search: SavedSearch,
    owner_id_snapshot: str,
    event_type: str,
    outcome: str,
    reason_code: str,
    occurred_at: datetime,
    batch_id: uuid.UUID | None,
    correlation_id: uuid.UUID,
    delivery_attempt_id: uuid.UUID | None,
    notification_fingerprint: str,
    rollback_of: SavedSearchNotificationAuditEvent | None,
    actor_type: str,
    actor_identifier: str,
    source: str,
    checked_at_before: datetime | None,
    checked_at_after: datetime | None,
    sent_at_before: datetime | None,
    sent_at_after: datetime | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    return {
        "saved_search_id": saved_search.pk,
        "owner_id_snapshot": owner_id_snapshot,
        "event_type": event_type,
        "outcome": outcome,
        "reason_code": reason_code,
        "occurred_at": occurred_at,
        "batch_id": batch_id,
        "correlation_id": correlation_id,
        "delivery_attempt_id": delivery_attempt_id,
        "notification_fingerprint": notification_fingerprint,
        "rollback_of_id": (
            rollback_of.pk
            if rollback_of is not None
            else None
        ),
        "actor_type": actor_type,
        "actor_identifier": actor_identifier,
        "source": source,
        "checked_at_before": checked_at_before,
        "checked_at_after": checked_at_after,
        "sent_at_before": sent_at_before,
        "sent_at_after": sent_at_after,
        "metadata": metadata,
    }


def _assert_replay_matches(
    *,
    event: SavedSearchNotificationAuditEvent,
    expected: dict[str, Any],
    idempotency_key: str,
) -> None:
    differing_fields = tuple(
        field_name
        for field_name in _REPLAY_FIELDS
        if getattr(event, field_name) != expected[field_name]
    )

    if differing_fields:
        raise SavedSearchNotificationAuditIdempotencyConflict(
            idempotency_key=idempotency_key,
            differing_fields=differing_fields,
        )


def record_saved_search_notification_audit_event(
    *,
    saved_search: SavedSearch,
    event_type: str,
    outcome: str,
    occurred_at: datetime,
    correlation_id: uuid.UUID | str,
    idempotency_key: str,
    notification_fingerprint: str,
    actor_type: str,
    source: str,
    reason_code: str = "",
    batch_id: uuid.UUID | str | None = None,
    delivery_attempt_id: uuid.UUID | str | None = None,
    rollback_of: SavedSearchNotificationAuditEvent | None = None,
    actor_identifier: str = "",
    checked_at_before: datetime | None = None,
    checked_at_after: datetime | None = None,
    sent_at_before: datetime | None = None,
    sent_at_after: datetime | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> SavedSearchNotificationAuditWriteResult:
    saved_search = _validate_saved_search(saved_search)

    event_type = _normalize_text(
        event_type,
        field="event_type",
        max_length=64,
        required=True,
    )

    event_type = _validate_choice(
        event_type,
        field="event_type",
        allowed_values=(
            SavedSearchNotificationAuditEvent.EventType.values
        ),
    )

    outcome = _normalize_text(
        outcome,
        field="outcome",
        max_length=32,
        required=True,
    )

    outcome = _validate_choice(
        outcome,
        field="outcome",
        allowed_values=(
            SavedSearchNotificationAuditEvent.Outcome.values
        ),
    )

    actor_type = _normalize_text(
        actor_type,
        field="actor_type",
        max_length=32,
        required=True,
    )

    actor_type = _validate_choice(
        actor_type,
        field="actor_type",
        allowed_values=(
            SavedSearchNotificationAuditEvent.ActorType.values
        ),
    )

    reason_code = _normalize_text(
        reason_code,
        field="reason_code",
        max_length=96,
        required=False,
    )

    idempotency_key = _normalize_text(
        idempotency_key,
        field="idempotency_key",
        max_length=128,
        required=True,
    )

    notification_fingerprint = _normalize_text(
        notification_fingerprint,
        field="notification_fingerprint",
        max_length=64,
        required=True,
    ).casefold()

    if not re.fullmatch(
        r"[0-9a-f]{64}",
        notification_fingerprint,
    ):
        raise _validation_error(
            "notification_fingerprint",
            "A 64-character lowercase hexadecimal fingerprint is required.",
        )

    actor_identifier = _normalize_text(
        actor_identifier,
        field="actor_identifier",
        max_length=128,
        required=False,
    )

    source = _normalize_text(
        source,
        field="source",
        max_length=128,
        required=True,
    )

    occurred_at = _normalize_datetime(
        occurred_at,
        field="occurred_at",
        required=True,
    )

    checked_at_before = _normalize_datetime(
        checked_at_before,
        field="checked_at_before",
        required=False,
    )

    checked_at_after = _normalize_datetime(
        checked_at_after,
        field="checked_at_after",
        required=False,
    )

    sent_at_before = _normalize_datetime(
        sent_at_before,
        field="sent_at_before",
        required=False,
    )

    sent_at_after = _normalize_datetime(
        sent_at_after,
        field="sent_at_after",
        required=False,
    )

    correlation_id = _normalize_uuid(
        correlation_id,
        field="correlation_id",
        required=True,
    )

    batch_id = _normalize_uuid(
        batch_id,
        field="batch_id",
        required=False,
    )

    delivery_attempt_id = _normalize_uuid(
        delivery_attempt_id,
        field="delivery_attempt_id",
        required=False,
    )

    if rollback_of is not None:
        if not isinstance(
            rollback_of,
            SavedSearchNotificationAuditEvent,
        ):
            raise _validation_error(
                "rollback_of",
                "rollback_of must be an audit event instance.",
            )

        if rollback_of.pk is None:
            raise _validation_error(
                "rollback_of",
                "rollback_of must already be saved.",
            )

        if rollback_of.saved_search_id != saved_search.pk:
            raise _validation_error(
                "rollback_of",
                (
                    "Rollback events must reference an event "
                    "for the same saved search."
                ),
            )

    if event_type in _ROLLBACK_EVENT_TYPES and rollback_of is None:
        raise _validation_error(
            "rollback_of",
            "Rollback audit events require rollback_of.",
        )

    if event_type in _DELIVERY_EVENT_TYPES and delivery_attempt_id is None:
        raise _validation_error(
            "delivery_attempt_id",
            "Delivery audit events require delivery_attempt_id.",
        )

    normalized_metadata = _normalize_metadata(metadata)
    owner_id_snapshot = str(saved_search.user_id)

    expected_replay_values = _build_expected_replay_values(
        saved_search=saved_search,
        owner_id_snapshot=owner_id_snapshot,
        event_type=event_type,
        outcome=outcome,
        reason_code=reason_code,
        occurred_at=occurred_at,
        batch_id=batch_id,
        correlation_id=correlation_id,
        delivery_attempt_id=delivery_attempt_id,
        notification_fingerprint=notification_fingerprint,
        rollback_of=rollback_of,
        actor_type=actor_type,
        actor_identifier=actor_identifier,
        source=source,
        checked_at_before=checked_at_before,
        checked_at_after=checked_at_after,
        sent_at_before=sent_at_before,
        sent_at_after=sent_at_after,
        metadata=normalized_metadata,
    )

    defaults = {
        key: value
        for key, value in expected_replay_values.items()
        if key not in {
            "saved_search_id",
            "rollback_of_id",
        }
    }

    defaults["saved_search"] = saved_search
    defaults["rollback_of"] = rollback_of

    candidate = SavedSearchNotificationAuditEvent(
        idempotency_key=idempotency_key,
        **defaults,
    )

    candidate.full_clean(
        validate_unique=False,
        validate_constraints=True,
    )

    with transaction.atomic():
        event, created = (
            SavedSearchNotificationAuditEvent.objects.get_or_create(
                idempotency_key=idempotency_key,
                defaults=defaults,
            )
        )

        if not created:
            _assert_replay_matches(
                event=event,
                expected=expected_replay_values,
                idempotency_key=idempotency_key,
            )

    return SavedSearchNotificationAuditWriteResult(
        event=event,
        created=created,
    )


__all__ = [
    "METADATA_DENYLIST",
    "SavedSearchNotificationAuditIdempotencyConflict",
    "SavedSearchNotificationAuditWriteResult",
    "record_saved_search_notification_audit_event",
]
