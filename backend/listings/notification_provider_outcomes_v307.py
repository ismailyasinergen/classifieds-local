"""Provider-neutral notification outcome ingestion for v307."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
import hashlib
import hmac
import json

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.dateparse import parse_datetime
from django.utils.timezone import is_naive

from listings.models import (
    NotificationDeliveryEvent,
    NotificationProviderOutcomeReceipt,
)


V307_NOTIFICATION_PROVIDER_OUTCOME_CONTRACT = True

V307_PROVIDER_OUTCOME_MAX_BODY_BYTES = 64 * 1024

V307_PROVIDER_OUTCOME_PRIORITIES = {
    NotificationDeliveryEvent.ProviderOutcome.DELIVERED: 1,
    NotificationDeliveryEvent.ProviderOutcome.BOUNCED: 2,
    NotificationDeliveryEvent.ProviderOutcome.COMPLAINED: 3,
}


class NotificationProviderOutcomeErrorV307(ValueError):
    pass


class NotificationProviderOutcomeUnavailableV307(
    NotificationProviderOutcomeErrorV307
):
    pass


class NotificationProviderOutcomeAuthenticationErrorV307(
    NotificationProviderOutcomeErrorV307
):
    pass


class NotificationProviderOutcomePayloadErrorV307(
    NotificationProviderOutcomeErrorV307
):
    pass


class NotificationProviderOutcomeConflictV307(
    NotificationProviderOutcomeErrorV307
):
    pass


@dataclass(frozen=True)
class NotificationProviderOutcomePayloadV307:
    provider_name: str
    provider_event_id: str
    provider_message_id: str
    outcome: str
    occurred_at: object
    payload_digest: str


@dataclass(frozen=True)
class NotificationProviderOutcomeResultV307:
    created: bool
    duplicate: bool
    matched_event_count: int
    applied_event_count: int


def _clean_identifier_v307(
    value,
    *,
    field_name,
    max_length,
    casefold=False,
):
    text = str(value or "").strip()

    if (
        not text
        or len(text) > max_length
        or any(
            ord(character) < 32
            for character in text
        )
    ):
        raise NotificationProviderOutcomePayloadErrorV307(
            f"Invalid {field_name}."
        )

    if casefold:
        text = text.casefold()

    return text


def notification_provider_name_v307():
    return str(
        getattr(
            settings,
            "NOTIFICATION_PROVIDER_NAME",
            "",
        )
        or ""
    ).strip().casefold()


def notification_provider_webhook_secret_v307():
    return str(
        getattr(
            settings,
            "NOTIFICATION_PROVIDER_WEBHOOK_SECRET",
            "",
        )
        or ""
    ).strip()


def notification_provider_webhook_max_age_seconds_v307():
    value = getattr(
        settings,
        "NOTIFICATION_PROVIDER_WEBHOOK_MAX_AGE_SECONDS",
        300,
    )

    if isinstance(value, bool):
        return 300

    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return 300

    if normalized <= 0:
        return 300

    return min(
        normalized,
        3600,
    )


def build_notification_provider_signature_v307(
    *,
    timestamp,
    body,
    secret=None,
):
    secret_value = str(
        secret
        if secret is not None
        else notification_provider_webhook_secret_v307()
    ).strip()

    if not secret_value:
        raise NotificationProviderOutcomeUnavailableV307(
            "Provider outcome webhook is not configured."
        )

    timestamp_value = str(timestamp or "").strip()
    body_bytes = bytes(body)

    digest = hmac.new(
        secret_value.encode("utf-8"),
        timestamp_value.encode("ascii")
        + b"."
        + body_bytes,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def _authenticate_notification_provider_request_v307(
    *,
    body,
    timestamp,
    signature,
):
    provider_name = notification_provider_name_v307()
    secret = notification_provider_webhook_secret_v307()

    if not provider_name or not secret:
        raise NotificationProviderOutcomeUnavailableV307(
            "Provider outcome webhook is not configured."
        )

    body_bytes = bytes(body)

    if len(body_bytes) > V307_PROVIDER_OUTCOME_MAX_BODY_BYTES:
        raise NotificationProviderOutcomePayloadErrorV307(
            "Provider outcome payload is too large."
        )

    timestamp_text = str(timestamp or "").strip()

    try:
        timestamp_value = int(timestamp_text)
    except (TypeError, ValueError):
        raise NotificationProviderOutcomeAuthenticationErrorV307(
            "Invalid provider timestamp."
        )

    current_timestamp = int(
        timezone.now().timestamp()
    )

    if abs(
        current_timestamp - timestamp_value
    ) > notification_provider_webhook_max_age_seconds_v307():
        raise NotificationProviderOutcomeAuthenticationErrorV307(
            "Expired provider signature."
        )

    expected = build_notification_provider_signature_v307(
        timestamp=timestamp_text,
        body=body_bytes,
        secret=secret,
    )

    supplied = str(signature or "").strip()

    if not constant_time_compare(
        supplied,
        expected,
    ):
        raise NotificationProviderOutcomeAuthenticationErrorV307(
            "Invalid provider signature."
        )

    return provider_name


def _parse_notification_provider_payload_v307(
    *,
    body,
    configured_provider_name,
):
    body_bytes = bytes(body)

    try:
        decoded = body_bytes.decode("utf-8")
        payload = json.loads(decoded)
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise NotificationProviderOutcomePayloadErrorV307(
            "Invalid provider outcome JSON."
        )

    if not isinstance(payload, dict):
        raise NotificationProviderOutcomePayloadErrorV307(
            "Provider outcome payload must be an object."
        )

    provider_name = _clean_identifier_v307(
        payload.get("provider"),
        field_name="provider",
        max_length=64,
        casefold=True,
    )

    if not constant_time_compare(
        provider_name,
        configured_provider_name,
    ):
        raise NotificationProviderOutcomeAuthenticationErrorV307(
            "Unexpected provider."
        )

    provider_event_id = _clean_identifier_v307(
        payload.get("event_id"),
        field_name="event_id",
        max_length=255,
    )

    provider_message_id = _clean_identifier_v307(
        payload.get("message_id"),
        field_name="message_id",
        max_length=255,
    )

    outcome = _clean_identifier_v307(
        payload.get("outcome"),
        field_name="outcome",
        max_length=16,
        casefold=True,
    )

    if outcome not in V307_PROVIDER_OUTCOME_PRIORITIES:
        raise NotificationProviderOutcomePayloadErrorV307(
            "Unsupported provider outcome."
        )

    occurred_at = parse_datetime(
        str(
            payload.get("occurred_at")
            or ""
        )
    )

    if (
        occurred_at is None
        or is_naive(occurred_at)
    ):
        raise NotificationProviderOutcomePayloadErrorV307(
            "occurred_at must be timezone-aware ISO-8601."
        )

    occurred_at = occurred_at.astimezone(UTC)

    return NotificationProviderOutcomePayloadV307(
        provider_name=provider_name,
        provider_event_id=provider_event_id,
        provider_message_id=provider_message_id,
        outcome=outcome,
        occurred_at=occurred_at,
        payload_digest=hashlib.sha256(
            body_bytes
        ).hexdigest(),
    )


def authenticate_and_parse_notification_provider_outcome_v307(
    *,
    body,
    timestamp,
    signature,
):
    configured_provider_name = (
        _authenticate_notification_provider_request_v307(
            body=body,
            timestamp=timestamp,
            signature=signature,
        )
    )

    return _parse_notification_provider_payload_v307(
        body=body,
        configured_provider_name=(
            configured_provider_name
        ),
    )


def _receipt_semantics_match_v307(
    receipt,
    payload,
):
    return (
        receipt.provider_message_id
        == payload.provider_message_id
        and receipt.outcome
        == payload.outcome
        and receipt.occurred_at
        == payload.occurred_at
    )


def _apply_payload_to_event_v307(
    event,
    payload,
):
    current_priority = (
        V307_PROVIDER_OUTCOME_PRIORITIES.get(
            event.provider_outcome,
            0,
        )
    )

    incoming_priority = (
        V307_PROVIDER_OUTCOME_PRIORITIES[
            payload.outcome
        ]
    )

    if current_priority > incoming_priority:
        return False

    if (
        current_priority == incoming_priority
        and event.provider_outcome_at is not None
        and event.provider_outcome_at
        >= payload.occurred_at
    ):
        return False

    event.provider_outcome = payload.outcome
    event.provider_event_id = (
        payload.provider_event_id
    )
    event.provider_outcome_at = (
        payload.occurred_at
    )

    event.save(
        update_fields=[
            "provider_outcome",
            "provider_event_id",
            "provider_outcome_at",
            "updated_at",
        ]
    )

    return True


def ingest_notification_provider_outcome_v307(
    payload,
):
    with transaction.atomic():
        receipt, created = (
            NotificationProviderOutcomeReceipt
            .objects
            .get_or_create(
                provider_name=payload.provider_name,
                provider_event_id=(
                    payload.provider_event_id
                ),
                defaults={
                    "provider_message_id": (
                        payload.provider_message_id
                    ),
                    "outcome": payload.outcome,
                    "occurred_at": payload.occurred_at,
                    "payload_digest": (
                        payload.payload_digest
                    ),
                },
            )
        )

        if not created:
            if not _receipt_semantics_match_v307(
                receipt,
                payload,
            ):
                raise NotificationProviderOutcomeConflictV307(
                    "Provider event id was reused "
                    "with different semantics."
                )

            return NotificationProviderOutcomeResultV307(
                created=False,
                duplicate=True,
                matched_event_count=(
                    receipt.matched_event_count
                ),
                applied_event_count=0,
            )

        events = list(
            NotificationDeliveryEvent
            .objects
            .select_for_update()
            .filter(
                provider_name=payload.provider_name,
                provider_message_id=(
                    payload.provider_message_id
                ),
            )
        )

        applied_count = 0

        for event in events:
            if _apply_payload_to_event_v307(
                event,
                payload,
            ):
                applied_count += 1

        receipt.matched_event_count = len(events)

        receipt.save(
            update_fields=[
                "matched_event_count",
            ]
        )

        return NotificationProviderOutcomeResultV307(
            created=True,
            duplicate=False,
            matched_event_count=len(events),
            applied_event_count=applied_count,
        )


def extract_notification_provider_message_identity_v307(
    message,
):
    provider_name = notification_provider_name_v307()

    if not provider_name:
        return "", ""

    candidates = [
        getattr(
            message,
            "provider_message_id",
            "",
        ),
        getattr(
            message,
            "message_id",
            "",
        ),
    ]

    headers = getattr(
        message,
        "extra_headers",
        {},
    ) or {}

    candidates.extend(
        [
            headers.get(
                "X-Provider-Message-ID",
                "",
            ),
            headers.get(
                "Message-ID",
                "",
            ),
        ]
    )

    for candidate in candidates:
        text = str(
            candidate
            or ""
        ).strip()

        if (
            text
            and len(text) <= 255
            and not any(
                ord(character) < 32
                for character in text
            )
        ):
            return provider_name, text

    return "", ""


def record_notification_provider_message_identity_v307(
    *,
    event_keys,
    provider_name,
    provider_message_id,
):
    normalized_provider = _clean_identifier_v307(
        provider_name,
        field_name="provider_name",
        max_length=64,
        casefold=True,
    )

    normalized_message_id = _clean_identifier_v307(
        provider_message_id,
        field_name="provider_message_id",
        max_length=255,
    )

    keys = tuple(
        str(key)
        for key in event_keys
        if str(key)
    )

    if not keys:
        return 0

    with transaction.atomic():
        events = list(
            NotificationDeliveryEvent
            .objects
            .select_for_update()
            .filter(
                event_key__in=keys,
            )
        )

        recorded = 0

        for event in events:
            if (
                event.provider_message_id
                and (
                    event.provider_name
                    != normalized_provider
                    or event.provider_message_id
                    != normalized_message_id
                )
            ):
                continue

            event.provider_name = normalized_provider
            event.provider_message_id = (
                normalized_message_id
            )

            event.save(
                update_fields=[
                    "provider_name",
                    "provider_message_id",
                    "updated_at",
                ]
            )

            recorded += 1

        matching_events = list(
            NotificationDeliveryEvent
            .objects
            .select_for_update()
            .filter(
                provider_name=normalized_provider,
                provider_message_id=(
                    normalized_message_id
                ),
            )
        )

        receipts = list(
            NotificationProviderOutcomeReceipt
            .objects
            .select_for_update()
            .filter(
                provider_name=normalized_provider,
                provider_message_id=(
                    normalized_message_id
                ),
            )
            .order_by(
                "occurred_at",
                "created_at",
                "pk",
            )
        )

        matched_event_count = len(
            matching_events
        )

        for receipt in receipts:
            replay_payload = (
                NotificationProviderOutcomePayloadV307(
                    provider_name=(
                        receipt.provider_name
                    ),
                    provider_event_id=(
                        receipt.provider_event_id
                    ),
                    provider_message_id=(
                        receipt.provider_message_id
                    ),
                    outcome=receipt.outcome,
                    occurred_at=receipt.occurred_at,
                    payload_digest=(
                        receipt.payload_digest
                    ),
                )
            )

            for event in matching_events:
                _apply_payload_to_event_v307(
                    event,
                    replay_payload,
                )

            if (
                receipt.matched_event_count
                != matched_event_count
            ):
                receipt.matched_event_count = (
                    matched_event_count
                )
                receipt.save(
                    update_fields=[
                        "matched_event_count",
                    ]
                )

        return recorded


__all__ = [
    "V307_NOTIFICATION_PROVIDER_OUTCOME_CONTRACT",
    "NotificationProviderOutcomeAuthenticationErrorV307",
    "NotificationProviderOutcomeConflictV307",
    "NotificationProviderOutcomePayloadErrorV307",
    "NotificationProviderOutcomeResultV307",
    "NotificationProviderOutcomeUnavailableV307",
    "authenticate_and_parse_notification_provider_outcome_v307",
    "build_notification_provider_signature_v307",
    "extract_notification_provider_message_identity_v307",
    "ingest_notification_provider_outcome_v307",
    "record_notification_provider_message_identity_v307",
]
