from __future__ import annotations

import json
import re
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from datetime import timezone as datetime_timezone
from typing import Any

from django.core.paginator import EmptyPage, Paginator
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import SavedSearchNotificationAuditEvent


V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE = (
    "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE"
)

DEFAULT_PAGE_SIZE = 50
MAXIMUM_PAGE_SIZE = 100
MAXIMUM_CSV_ROWS = 5000
MAXIMUM_METADATA_DEPTH = 6
MAXIMUM_METADATA_RENDERED_BYTES = 16384
METADATA_REDACTION_TEXT = "[redacted]"

SUPPORTED_FILTER_NAMES = frozenset(
    {
        "event_id",
        "saved_search_id",
        "owner_id_snapshot",
        "event_type",
        "outcome",
        "actor_type",
        "source",
        "reason_code",
        "batch_id",
        "correlation_id",
        "delivery_attempt_id",
        "idempotency_key",
        "notification_fingerprint",
        "rollback_linked",
        "occurred_from",
        "occurred_to",
        "page",
        "page_size",
        "format",
    }
)

CSV_HEADERS = (
    "event_id",
    "occurred_at",
    "created_at",
    "saved_search_id",
    "saved_search_label",
    "owner_id_snapshot",
    "event_type",
    "outcome",
    "reason_code",
    "source",
    "actor_type",
    "actor_identifier",
    "batch_id",
    "correlation_id",
    "delivery_attempt_id",
    "idempotency_key",
    "notification_fingerprint",
    "rollback_of_id",
    "checked_at_before",
    "checked_at_after",
    "sent_at_before",
    "sent_at_after",
    "metadata_json",
)

_SENSITIVE_KEY_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "api_token",
        "auth",
        "authentication",
        "authorization",
        "authorization_header",
        "client_secret",
        "cookie",
        "cookies",
        "credential",
        "credentials",
        "email_body",
        "email_subject",
        "exception_message",
        "owner_email",
        "password",
        "private_key",
        "recipient_email",
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

_SENSITIVE_KEY_SEGMENTS = frozenset(
    {
        "auth",
        "authentication",
        "authorization",
        "cookie",
        "cookies",
        "credential",
        "credentials",
        "password",
        "secret",
        "session",
        "token",
        "traceback",
    }
)


class SavedSearchNotificationAuditOperatorFilterError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SavedSearchNotificationAuditOperatorFilters:
    event_id: uuid.UUID | None = None
    saved_search_id: int | None = None
    owner_id_snapshot: str = ""
    event_type: str = ""
    outcome: str = ""
    actor_type: str = ""
    source: str = ""
    reason_code: str = ""
    batch_id: uuid.UUID | None = None
    correlation_id: uuid.UUID | None = None
    delivery_attempt_id: uuid.UUID | None = None
    idempotency_key: str = ""
    notification_fingerprint: str = ""
    rollback_linked: bool | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    output_format: str = "html"


@dataclass(frozen=True, slots=True)
class SavedSearchNotificationAuditOperatorPage:
    items: tuple[dict[str, Any], ...]
    number: int
    page_size: int
    total_count: int
    total_pages: int
    has_previous: bool
    has_next: bool
    previous_page_number: int | None
    next_page_number: int | None


def _raise_filter_error(message: str) -> None:
    raise SavedSearchNotificationAuditOperatorFilterError(
        message
    )


def _single_value(
    parameters: Mapping[str, Any],
    name: str,
) -> str:
    if hasattr(parameters, "getlist"):
        values = parameters.getlist(name)

        if len(values) > 1:
            _raise_filter_error(
                f"Duplicate filter values are not allowed: {name}"
            )

    value = parameters.get(name, "")

    if value is None:
        return ""

    return str(value).strip()


def _validate_parameter_names(
    parameters: Mapping[str, Any],
) -> None:
    keys = set(parameters.keys())
    unsupported = sorted(keys - SUPPORTED_FILTER_NAMES)

    if unsupported:
        _raise_filter_error(
            "Unsupported filter parameter."
        )


def _parse_uuid(
    raw_value: str,
    *,
    field_name: str,
) -> uuid.UUID | None:
    if not raw_value:
        return None

    try:
        return uuid.UUID(raw_value)
    except (TypeError, ValueError, AttributeError):
        _raise_filter_error(
            f"Invalid UUID filter: {field_name}"
        )


def _parse_positive_integer(
    raw_value: str,
    *,
    field_name: str,
    default: int | None = None,
    maximum: int | None = None,
) -> int | None:
    if not raw_value:
        return default

    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        _raise_filter_error(
            f"Invalid integer filter: {field_name}"
        )

    if value <= 0:
        _raise_filter_error(
            f"{field_name} must be a positive integer."
        )

    if maximum is not None and value > maximum:
        _raise_filter_error(
            f"{field_name} exceeds the maximum."
        )

    return value


def _parse_bounded_text(
    raw_value: str,
    *,
    field_name: str,
    maximum_length: int,
) -> str:
    if len(raw_value) > maximum_length:
        _raise_filter_error(
            f"{field_name} exceeds the maximum length."
        )

    return raw_value


def _parse_choice(
    raw_value: str,
    *,
    field_name: str,
    choices: Iterable[str],
    default: str = "",
) -> str:
    if not raw_value:
        return default

    allowed = set(choices)

    if raw_value not in allowed:
        _raise_filter_error(
            f"Invalid choice filter: {field_name}"
        )

    return raw_value


def _parse_boolean(
    raw_value: str,
    *,
    field_name: str,
) -> bool | None:
    if not raw_value:
        return None

    normalized = raw_value.casefold()

    if normalized in {
        "1",
        "true",
    }:
        return True

    if normalized in {
        "0",
        "false",
    }:
        return False

    _raise_filter_error(
        f"Invalid boolean filter: {field_name}"
    )


def _parse_aware_datetime(
    raw_value: str,
    *,
    field_name: str,
) -> datetime | None:
    if not raw_value:
        return None

    parsed = parse_datetime(raw_value)

    if parsed is None:
        _raise_filter_error(
            f"Invalid datetime filter: {field_name}"
        )

    if timezone.is_naive(parsed):
        _raise_filter_error(
            f"Timezone-aware datetime required: {field_name}"
        )

    return parsed


def parse_saved_search_notification_audit_operator_filters(
    parameters: Mapping[str, Any],
) -> SavedSearchNotificationAuditOperatorFilters:
    _validate_parameter_names(parameters)

    event_id = _parse_uuid(
        _single_value(parameters, "event_id"),
        field_name="event_id",
    )

    saved_search_id = _parse_positive_integer(
        _single_value(parameters, "saved_search_id"),
        field_name="saved_search_id",
    )

    owner_id_snapshot = _parse_bounded_text(
        _single_value(parameters, "owner_id_snapshot"),
        field_name="owner_id_snapshot",
        maximum_length=64,
    )

    event_type = _parse_choice(
        _single_value(parameters, "event_type"),
        field_name="event_type",
        choices=(
            SavedSearchNotificationAuditEvent
            .EventType
            .values
        ),
    )

    outcome = _parse_choice(
        _single_value(parameters, "outcome"),
        field_name="outcome",
        choices=(
            SavedSearchNotificationAuditEvent
            .Outcome
            .values
        ),
    )

    actor_type = _parse_choice(
        _single_value(parameters, "actor_type"),
        field_name="actor_type",
        choices=(
            SavedSearchNotificationAuditEvent
            .ActorType
            .values
        ),
    )

    source = _parse_bounded_text(
        _single_value(parameters, "source"),
        field_name="source",
        maximum_length=128,
    )

    reason_code = _parse_bounded_text(
        _single_value(parameters, "reason_code"),
        field_name="reason_code",
        maximum_length=96,
    )

    batch_id = _parse_uuid(
        _single_value(parameters, "batch_id"),
        field_name="batch_id",
    )

    correlation_id = _parse_uuid(
        _single_value(parameters, "correlation_id"),
        field_name="correlation_id",
    )

    delivery_attempt_id = _parse_uuid(
        _single_value(parameters, "delivery_attempt_id"),
        field_name="delivery_attempt_id",
    )

    idempotency_key = _parse_bounded_text(
        _single_value(parameters, "idempotency_key"),
        field_name="idempotency_key",
        maximum_length=128,
    )

    notification_fingerprint = _single_value(
        parameters,
        "notification_fingerprint",
    ).casefold()

    if notification_fingerprint:
        if not re.fullmatch(
            r"[0-9a-f]{64}",
            notification_fingerprint,
        ):
            _raise_filter_error(
                "Invalid notification fingerprint."
            )

    rollback_linked = _parse_boolean(
        _single_value(parameters, "rollback_linked"),
        field_name="rollback_linked",
    )

    occurred_from = _parse_aware_datetime(
        _single_value(parameters, "occurred_from"),
        field_name="occurred_from",
    )

    occurred_to = _parse_aware_datetime(
        _single_value(parameters, "occurred_to"),
        field_name="occurred_to",
    )

    if (
        occurred_from is not None
        and occurred_to is not None
        and occurred_from > occurred_to
    ):
        _raise_filter_error(
            "occurred_from must not be after occurred_to."
        )

    page = _parse_positive_integer(
        _single_value(parameters, "page"),
        field_name="page",
        default=1,
    )

    page_size = _parse_positive_integer(
        _single_value(parameters, "page_size"),
        field_name="page_size",
        default=DEFAULT_PAGE_SIZE,
        maximum=MAXIMUM_PAGE_SIZE,
    )

    output_format = _parse_choice(
        _single_value(parameters, "format"),
        field_name="format",
        choices=(
            "html",
            "csv",
        ),
        default="html",
    )

    return SavedSearchNotificationAuditOperatorFilters(
        event_id=event_id,
        saved_search_id=saved_search_id,
        owner_id_snapshot=owner_id_snapshot,
        event_type=event_type,
        outcome=outcome,
        actor_type=actor_type,
        source=source,
        reason_code=reason_code,
        batch_id=batch_id,
        correlation_id=correlation_id,
        delivery_attempt_id=delivery_attempt_id,
        idempotency_key=idempotency_key,
        notification_fingerprint=notification_fingerprint,
        rollback_linked=rollback_linked,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
        page=page or 1,
        page_size=page_size or DEFAULT_PAGE_SIZE,
        output_format=output_format,
    )


def build_saved_search_notification_audit_operator_queryset(
    filters: SavedSearchNotificationAuditOperatorFilters,
) -> QuerySet[SavedSearchNotificationAuditEvent]:
    queryset = (
        SavedSearchNotificationAuditEvent
        .objects
        .select_related("saved_search")
    )

    if filters.event_id is not None:
        queryset = queryset.filter(pk=filters.event_id)

    if filters.saved_search_id is not None:
        queryset = queryset.filter(
            saved_search_id=filters.saved_search_id
        )

    if filters.owner_id_snapshot:
        queryset = queryset.filter(
            owner_id_snapshot=filters.owner_id_snapshot
        )

    if filters.event_type:
        queryset = queryset.filter(
            event_type=filters.event_type
        )

    if filters.outcome:
        queryset = queryset.filter(
            outcome=filters.outcome
        )

    if filters.actor_type:
        queryset = queryset.filter(
            actor_type=filters.actor_type
        )

    if filters.source:
        queryset = queryset.filter(
            source=filters.source
        )

    if filters.reason_code:
        queryset = queryset.filter(
            reason_code=filters.reason_code
        )

    if filters.batch_id is not None:
        queryset = queryset.filter(
            batch_id=filters.batch_id
        )

    if filters.correlation_id is not None:
        queryset = queryset.filter(
            correlation_id=filters.correlation_id
        )

    if filters.delivery_attempt_id is not None:
        queryset = queryset.filter(
            delivery_attempt_id=filters.delivery_attempt_id
        )

    if filters.idempotency_key:
        queryset = queryset.filter(
            idempotency_key=filters.idempotency_key
        )

    if filters.notification_fingerprint:
        queryset = queryset.filter(
            notification_fingerprint=(
                filters.notification_fingerprint
            )
        )

    if filters.rollback_linked is True:
        queryset = queryset.filter(
            rollback_of__isnull=False
        )

    if filters.rollback_linked is False:
        queryset = queryset.filter(
            rollback_of__isnull=True
        )

    if filters.occurred_from is not None:
        queryset = queryset.filter(
            occurred_at__gte=filters.occurred_from
        )

    if filters.occurred_to is not None:
        queryset = queryset.filter(
            occurred_at__lte=filters.occurred_to
        )

    return queryset.order_by(
        "-occurred_at",
        "-created_at",
        "-id",
    )


def _normalize_metadata_key(raw_key: str) -> str:
    word_boundaries = re.sub(
        r"([a-z0-9])([A-Z])",
        r"\1_\2",
        raw_key,
    )

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        word_boundaries.casefold(),
    ).strip("_")


def _metadata_key_is_sensitive(raw_key: str) -> bool:
    normalized = _normalize_metadata_key(raw_key)

    if normalized in _SENSITIVE_KEY_NAMES:
        return True

    segments = {
        segment
        for segment in normalized.split("_")
        if segment
    }

    if segments.intersection(_SENSITIVE_KEY_SEGMENTS):
        return True

    if normalized.endswith("_api_key"):
        return True

    if normalized.endswith("_private_key"):
        return True

    if (
        "rendered" in segments
        and segments.intersection(
            {
                "body",
                "email",
                "html",
                "text",
            }
        )
    ):
        return True

    if "stack" in segments and "trace" in segments:
        return True

    return False


def sanitize_saved_search_notification_audit_metadata_for_operator(
    value: Any,
    *,
    _depth: int = 0,
) -> Any:
    if _depth >= MAXIMUM_METADATA_DEPTH:
        return METADATA_REDACTION_TEXT

    if isinstance(value, Mapping):
        sanitized: dict[str, Any] = {}

        for raw_key in sorted(
            value,
            key=lambda candidate: str(candidate),
        ):
            if not isinstance(raw_key, str):
                continue

            if _metadata_key_is_sensitive(raw_key):
                sanitized[raw_key] = METADATA_REDACTION_TEXT
                continue

            sanitized[raw_key] = (
                sanitize_saved_search_notification_audit_metadata_for_operator(
                    value[raw_key],
                    _depth=_depth + 1,
                )
            )

        return sanitized

    if isinstance(value, (list, tuple)):
        return [
            sanitize_saved_search_notification_audit_metadata_for_operator(
                item,
                _depth=_depth + 1,
            )
            for item in value
        ]

    if value is None or isinstance(
        value,
        (
            bool,
            int,
            float,
        ),
    ):
        return value

    if isinstance(value, str):
        if len(value) > 4096:
            return (
                value[:4096]
                + "…"
            )

        return value

    return METADATA_REDACTION_TEXT


def _canonical_metadata_json(
    metadata: Any,
) -> str:
    sanitized = (
        sanitize_saved_search_notification_audit_metadata_for_operator(
            metadata
        )
    )

    rendered = json.dumps(
        sanitized,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    rendered_size = len(
        rendered.encode("utf-8")
    )

    if rendered_size <= MAXIMUM_METADATA_RENDERED_BYTES:
        return rendered

    return json.dumps(
        {
            "_truncated": METADATA_REDACTION_TEXT,
            "original_bytes": rendered_size,
        },
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _iso_utc(
    value: datetime | None,
) -> str:
    if value is None:
        return ""

    if timezone.is_naive(value):
        value = timezone.make_aware(
            value,
            datetime_timezone.utc,
        )

    normalized = value.astimezone(
        datetime_timezone.utc
    )

    return normalized.isoformat().replace(
        "+00:00",
        "Z",
    )


def _saved_search_label(
    event: SavedSearchNotificationAuditEvent,
) -> str:
    saved_search = event.saved_search
    name = str(
        getattr(saved_search, "name", "")
        or ""
    ).strip()

    if name:
        return name

    return f"Saved search #{event.saved_search_id}"


def serialize_saved_search_notification_audit_event_for_operator(
    event: SavedSearchNotificationAuditEvent,
) -> dict[str, Any]:
    fingerprint = str(
        event.notification_fingerprint
        or ""
    )

    if len(fingerprint) > 16:
        fingerprint_short = (
            fingerprint[:12]
            + "…"
            + fingerprint[-4:]
        )
    else:
        fingerprint_short = fingerprint

    return {
        "event_id": str(event.pk),
        "occurred_at": _iso_utc(event.occurred_at),
        "created_at": _iso_utc(event.created_at),
        "saved_search_id": event.saved_search_id,
        "saved_search_label": _saved_search_label(event),
        "owner_id_snapshot": event.owner_id_snapshot,
        "event_type": event.event_type,
        "outcome": event.outcome,
        "reason_code": event.reason_code,
        "source": event.source,
        "actor_type": event.actor_type,
        "actor_identifier": event.actor_identifier,
        "batch_id": (
            str(event.batch_id)
            if event.batch_id is not None
            else ""
        ),
        "correlation_id": str(event.correlation_id),
        "delivery_attempt_id": (
            str(event.delivery_attempt_id)
            if event.delivery_attempt_id is not None
            else ""
        ),
        "idempotency_key": event.idempotency_key,
        "notification_fingerprint": fingerprint,
        "notification_fingerprint_short": fingerprint_short,
        "rollback_of_id": (
            str(event.rollback_of_id)
            if event.rollback_of_id is not None
            else ""
        ),
        "checked_at_before": _iso_utc(
            event.checked_at_before
        ),
        "checked_at_after": _iso_utc(
            event.checked_at_after
        ),
        "sent_at_before": _iso_utc(
            event.sent_at_before
        ),
        "sent_at_after": _iso_utc(
            event.sent_at_after
        ),
        "metadata_json": _canonical_metadata_json(
            event.metadata
        ),
    }


def paginate_saved_search_notification_audit_operator_events(
    queryset: QuerySet[SavedSearchNotificationAuditEvent],
    *,
    page_number: int,
    page_size: int,
) -> SavedSearchNotificationAuditOperatorPage:
    paginator = Paginator(
        queryset,
        page_size,
    )

    try:
        page = paginator.page(page_number)
    except EmptyPage:
        _raise_filter_error(
            "Requested page is outside the result range."
        )

    items = tuple(
        serialize_saved_search_notification_audit_event_for_operator(
            event
        )
        for event in page.object_list
    )

    return SavedSearchNotificationAuditOperatorPage(
        items=items,
        number=page.number,
        page_size=page_size,
        total_count=paginator.count,
        total_pages=paginator.num_pages,
        has_previous=page.has_previous(),
        has_next=page.has_next(),
        previous_page_number=(
            page.previous_page_number()
            if page.has_previous()
            else None
        ),
        next_page_number=(
            page.next_page_number()
            if page.has_next()
            else None
        ),
    )


def _csv_safe_cell(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)

    if text.startswith(
        (
            "=",
            "+",
            "-",
            "@",
        )
    ):
        return "'" + text

    return text


def iter_saved_search_notification_audit_csv_rows(
    queryset: QuerySet[SavedSearchNotificationAuditEvent],
    *,
    maximum_rows: int = MAXIMUM_CSV_ROWS,
):
    for event in queryset[:maximum_rows]:
        serialized = (
            serialize_saved_search_notification_audit_event_for_operator(
                event
            )
        )

        yield tuple(
            _csv_safe_cell(
                serialized[header]
            )
            for header in CSV_HEADERS
        )


__all__ = [
    "CSV_HEADERS",
    "DEFAULT_PAGE_SIZE",
    "MAXIMUM_CSV_ROWS",
    "MAXIMUM_METADATA_DEPTH",
    "MAXIMUM_METADATA_RENDERED_BYTES",
    "MAXIMUM_PAGE_SIZE",
    "METADATA_REDACTION_TEXT",
    "SUPPORTED_FILTER_NAMES",
    "SavedSearchNotificationAuditOperatorFilterError",
    "SavedSearchNotificationAuditOperatorFilters",
    "SavedSearchNotificationAuditOperatorPage",
    "V234_SAVED_SEARCH_NOTIFICATION_PERSISTENT_AUDIT_OPERATOR_READ_INTERFACE",
    "build_saved_search_notification_audit_operator_queryset",
    "iter_saved_search_notification_audit_csv_rows",
    "paginate_saved_search_notification_audit_operator_events",
    "parse_saved_search_notification_audit_operator_filters",
    "sanitize_saved_search_notification_audit_metadata_for_operator",
    "serialize_saved_search_notification_audit_event_for_operator",
]
