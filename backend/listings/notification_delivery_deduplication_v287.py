"""Durable notification identities and short atomic delivery claims for v287."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
import hashlib
import json
import re
import uuid

from django.http import QueryDict
from django.db.models import F, Q
from django.utils import timezone

from .models import (
    ListingPriceAlert,
    ListingPriceHistory,
    NotificationDeliveryEvent,
)
from .saved_search_price_drop_notifications_v286 import (
    saved_search_watches_price_drops_v286,
)


NOTIFICATION_DELIVERY_DEDUPLICATION_V287 = True
NOTIFICATION_EVENT_KEY_VERSION_V287 = "v1"
NOTIFICATION_EVENT_MAX_ATTEMPTS_V287 = 5
NOTIFICATION_EVENT_STALE_AFTER_V287 = timedelta(minutes=15)


@dataclass(frozen=True)
class NotificationEventSpecV287:
    notification_type: str
    recipient_id: int
    listing_id: int
    event_key: str
    listing_price_alert_id: int | None = None
    saved_search_id: int | None = None
    price_transition_id: int | None = None
    target_price: Decimal | None = None
    transition_changed_at: object | None = None


@dataclass(frozen=True)
class NotificationEventBatchClaimV287:
    claim_token: uuid.UUID
    specs: tuple[NotificationEventSpecV287, ...]
    events_by_key: dict[str, NotificationDeliveryEvent]
    claimed_keys: frozenset[str]
    duplicate_keys: frozenset[str]
    busy_keys: frozenset[str]
    exhausted_keys: frozenset[str]

    @property
    def claimed_specs(self):
        return tuple(
            spec for spec in self.specs if spec.event_key in self.claimed_keys
        )

    @property
    def claimed_events(self):
        return tuple(
            self.events_by_key[key]
            for key in self.claimed_keys
            if key in self.events_by_key
        )


class _SavedSearchPreferenceRequestV287:
    def __init__(self, querydict):
        self.GET = querydict


def saved_search_includes_price_drops_v287(saved_search):
    querydict = QueryDict("", mutable=True)
    source = saved_search.query_params or {}
    if source:
        for key, value in source.items():
            if isinstance(value, (list, tuple)):
                querydict.setlist(key, [str(item) for item in value])
            else:
                querydict[key] = str(value)
    elif saved_search.querystring:
        querydict = QueryDict(saved_search.querystring, mutable=True)
    return saved_search_watches_price_drops_v286(
        _SavedSearchPreferenceRequestV287(querydict)
    )


def build_notification_event_key_v287(
    *,
    notification_type,
    recipient_id,
    listing_id,
    listing_price_alert_id=None,
    saved_search_id=None,
    price_transition_id=None,
    channel="email",
):
    """Hash only stable logical identity fields, never delivery-attempt data."""

    identity = {
        "channel": str(channel),
        "listing": int(listing_id),
        "notification_type": str(notification_type),
        "recipient": int(recipient_id),
        "version": NOTIFICATION_EVENT_KEY_VERSION_V287,
    }
    if notification_type == NotificationDeliveryEvent.NotificationType.LISTING_PRICE_DROP:
        identity["listing_price_alert"] = int(listing_price_alert_id)
        identity["price_transition"] = int(price_transition_id)
    elif notification_type == NotificationDeliveryEvent.NotificationType.SAVED_SEARCH_PRICE_DROP:
        identity["saved_search"] = int(saved_search_id)
        identity["price_transition"] = int(price_transition_id)
    elif notification_type == NotificationDeliveryEvent.NotificationType.SAVED_SEARCH_NEW_LISTING:
        identity["saved_search"] = int(saved_search_id)
    else:
        raise ValueError("Unsupported notification type.")

    payload = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _latest_transitions_by_listing_v287(listing_ids):
    ids = sorted({int(pk) for pk in listing_ids if pk})
    if not ids:
        return {}

    transitions = (
        ListingPriceHistory.objects
        .filter(
            listing_id__in=ids,
            previous_price__isnull=False,
        )
        .order_by("listing_id", "-changed_at", "-pk")
        .distinct("listing_id")
        .only("id", "listing_id", "new_price", "changed_at")
    )
    return {transition.listing_id: transition for transition in transitions}


def build_listing_price_alert_event_specs_v287(alerts):
    alert_items = list(alerts)
    transitions = _latest_transitions_by_listing_v287(
        alert.listing_id for alert in alert_items
    )
    specs = []
    for alert in alert_items:
        transition = transitions.get(alert.listing_id)
        if transition is None:
            continue
        event_key = build_notification_event_key_v287(
            notification_type=(
                NotificationDeliveryEvent.NotificationType.LISTING_PRICE_DROP
            ),
            recipient_id=alert.user_id,
            listing_id=alert.listing_id,
            listing_price_alert_id=alert.pk,
            price_transition_id=transition.pk,
        )
        specs.append(
            NotificationEventSpecV287(
                notification_type=(
                    NotificationDeliveryEvent.NotificationType.LISTING_PRICE_DROP
                ),
                recipient_id=alert.user_id,
                listing_id=alert.listing_id,
                listing_price_alert_id=alert.pk,
                price_transition_id=transition.pk,
                target_price=alert.listing.price,
                transition_changed_at=transition.changed_at,
                event_key=event_key,
            )
        )
    return specs


def build_saved_search_event_specs_v287(preview):
    listings = list(preview.listings)
    notification_type = (
        NotificationDeliveryEvent.NotificationType.SAVED_SEARCH_PRICE_DROP
        if preview.includes_price_drops
        else NotificationDeliveryEvent.NotificationType.SAVED_SEARCH_NEW_LISTING
    )
    transitions = {}
    if preview.includes_price_drops:
        transitions = _latest_transitions_by_listing_v287(
            listing.pk for listing in listings
        )

    specs = []
    for listing in listings:
        transition = transitions.get(listing.pk)
        if preview.includes_price_drops and transition is None:
            continue
        transition_id = transition.pk if transition is not None else None
        event_key = build_notification_event_key_v287(
            notification_type=notification_type,
            recipient_id=preview.saved_search.user_id,
            listing_id=listing.pk,
            saved_search_id=preview.saved_search.pk,
            price_transition_id=transition_id,
        )
        specs.append(
            NotificationEventSpecV287(
                notification_type=notification_type,
                recipient_id=preview.saved_search.user_id,
                listing_id=listing.pk,
                saved_search_id=preview.saved_search.pk,
                price_transition_id=transition_id,
                target_price=listing.price,
                transition_changed_at=(
                    transition.changed_at if transition is not None else None
                ),
                event_key=event_key,
            )
        )
    return specs


def _event_from_spec_v287(spec):
    return NotificationDeliveryEvent(
        recipient_id=spec.recipient_id,
        listing_id=spec.listing_id,
        listing_price_alert_id=spec.listing_price_alert_id,
        saved_search_id=spec.saved_search_id,
        price_transition_id=spec.price_transition_id,
        notification_type=spec.notification_type,
        event_key=spec.event_key,
        target_price=spec.target_price,
        transition_changed_at=spec.transition_changed_at,
    )


def claim_notification_events_v287(specs, *, now=None):
    """Create identities and claim all eligible events with one batch token."""

    unique_specs = tuple({spec.event_key: spec for spec in specs}.values())
    claim_token = uuid.uuid4()
    if not unique_specs:
        return NotificationEventBatchClaimV287(
            claim_token=claim_token,
            specs=(),
            events_by_key={},
            claimed_keys=frozenset(),
            duplicate_keys=frozenset(),
            busy_keys=frozenset(),
            exhausted_keys=frozenset(),
        )

    reference_time = now or timezone.now()
    keys = [spec.event_key for spec in unique_specs]
    NotificationDeliveryEvent.objects.bulk_create(
        [_event_from_spec_v287(spec) for spec in unique_specs],
        ignore_conflicts=True,
    )

    stale_before = reference_time - NOTIFICATION_EVENT_STALE_AFTER_V287
    claimable = (
        Q(status__in=[
            NotificationDeliveryEvent.Status.PENDING,
            NotificationDeliveryEvent.Status.FAILED,
        ])
        | Q(
            status=NotificationDeliveryEvent.Status.PROCESSING,
            processing_started_at__lte=stale_before,
        )
    )
    (
        NotificationDeliveryEvent.objects
        .filter(event_key__in=keys)
        .filter(claimable)
        .filter(attempt_count__lt=NOTIFICATION_EVENT_MAX_ATTEMPTS_V287)
        .update(
            status=NotificationDeliveryEvent.Status.PROCESSING,
            attempt_count=F("attempt_count") + 1,
            claim_token=claim_token,
            processing_started_at=reference_time,
            last_error_category="",
            updated_at=reference_time,
        )
    )

    events_by_key = {
        event.event_key: event
        for event in NotificationDeliveryEvent.objects.filter(event_key__in=keys)
    }
    claimed = set()
    duplicates = set()
    busy = set()
    exhausted = set()
    for key, event in events_by_key.items():
        if event.claim_token == claim_token:
            claimed.add(key)
        elif event.status in {
            NotificationDeliveryEvent.Status.SENT,
            NotificationDeliveryEvent.Status.SKIPPED,
        }:
            duplicates.add(key)
        elif (
            event.status == NotificationDeliveryEvent.Status.FAILED
            and event.attempt_count >= NOTIFICATION_EVENT_MAX_ATTEMPTS_V287
        ):
            exhausted.add(key)
        else:
            busy.add(key)

    return NotificationEventBatchClaimV287(
        claim_token=claim_token,
        specs=unique_specs,
        events_by_key=events_by_key,
        claimed_keys=frozenset(claimed),
        duplicate_keys=frozenset(duplicates),
        busy_keys=frozenset(busy),
        exhausted_keys=frozenset(exhausted),
    )


def _claimed_event_queryset_v287(claim):
    return NotificationDeliveryEvent.objects.filter(
        event_key__in=claim.claimed_keys,
        status=NotificationDeliveryEvent.Status.PROCESSING,
        claim_token=claim.claim_token,
    )


def mark_notification_events_sent_v287(claim, *, sent_at=None):
    completed_at = sent_at or timezone.now()
    return _claimed_event_queryset_v287(claim).update(
        status=NotificationDeliveryEvent.Status.SENT,
        sent_at=completed_at,
        claim_token=None,
        processing_started_at=None,
        last_error_category="",
        updated_at=completed_at,
    )


def _safe_error_category_v287(value):
    text = str(value or "DeliveryError")
    return re.sub(r"[^A-Za-z0-9_.-]", "_", text)[:64]


def mark_notification_events_failed_v287(claim, *, error_category, failed_at=None):
    completed_at = failed_at or timezone.now()
    return _claimed_event_queryset_v287(claim).update(
        status=NotificationDeliveryEvent.Status.FAILED,
        claim_token=None,
        processing_started_at=None,
        last_error_category=_safe_error_category_v287(error_category),
        updated_at=completed_at,
    )


def mark_notification_events_skipped_v287(claim, *, reason, skipped_at=None):
    completed_at = skipped_at or timezone.now()
    return _claimed_event_queryset_v287(claim).update(
        status=NotificationDeliveryEvent.Status.SKIPPED,
        claim_token=None,
        processing_started_at=None,
        last_error_category=_safe_error_category_v287(reason),
        updated_at=completed_at,
    )


def claimed_listing_ids_v287(claim):
    return {
        spec.listing_id
        for spec in claim.claimed_specs
    }


def subset_notification_claim_v287(claim, event_keys):
    selected = frozenset(event_keys) & claim.claimed_keys
    return NotificationEventBatchClaimV287(
        claim_token=claim.claim_token,
        specs=tuple(
            spec for spec in claim.specs if spec.event_key in selected
        ),
        events_by_key={
            key: event
            for key, event in claim.events_by_key.items()
            if key in selected
        },
        claimed_keys=selected,
        duplicate_keys=frozenset(),
        busy_keys=frozenset(),
        exhausted_keys=frozenset(),
    )
