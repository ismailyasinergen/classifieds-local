"""User preference gates for the durable notification delivery pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from .models import NotificationDeliveryEvent, NotificationDeliveryPreference


NOTIFICATION_DELIVERY_PREFERENCES_V288 = True
PREFERENCE_SUPPRESSION_REASON_V288 = "preference_disabled"


@dataclass(frozen=True)
class NotificationPreferenceDecisionV288:
    allowed_specs: tuple
    suppressed_specs: tuple

    @property
    def suppressed_keys(self):
        return frozenset(spec.event_key for spec in self.suppressed_specs)


def load_notification_preference_map_v288(user_ids):
    ids = sorted({int(user_id) for user_id in user_ids if user_id})
    return {
        preference.user_id: preference
        for preference in NotificationDeliveryPreference.objects.filter(
            user_id__in=ids,
        )
    }


def notification_type_is_enabled_v288(notification_type, preference):
    if preference is None:
        return True
    field_by_type = {
        NotificationDeliveryEvent.NotificationType.LISTING_PRICE_DROP: (
            "listing_price_alert_email_enabled"
        ),
        NotificationDeliveryEvent.NotificationType.SAVED_SEARCH_NEW_LISTING: (
            "saved_search_new_listing_email_enabled"
        ),
        NotificationDeliveryEvent.NotificationType.SAVED_SEARCH_PRICE_DROP: (
            "saved_search_price_drop_email_enabled"
        ),
    }
    try:
        field_name = field_by_type[notification_type]
    except KeyError as exc:
        raise ValueError("Unsupported notification type.") from exc
    return bool(getattr(preference, field_name))


def notification_type_enabled_for_user_v288(
    user_id,
    notification_type,
    *,
    preference_map=None,
):
    preferences = (
        preference_map
        if preference_map is not None
        else load_notification_preference_map_v288([user_id])
    )
    return notification_type_is_enabled_v288(
        notification_type,
        preferences.get(user_id),
    )


def _suppressed_event_from_spec_v288(spec):
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
        status=NotificationDeliveryEvent.Status.SKIPPED,
        last_error_category=PREFERENCE_SUPPRESSION_REASON_V288,
    )


def apply_notification_preferences_v288(
    specs,
    *,
    preference_map=None,
    now=None,
):
    """Partition specs and durably suppress disabled logical events."""

    unique_specs = tuple({spec.event_key: spec for spec in specs}.values())
    preferences = (
        preference_map
        if preference_map is not None
        else load_notification_preference_map_v288(
            spec.recipient_id for spec in unique_specs
        )
    )
    allowed = []
    suppressed = []
    for spec in unique_specs:
        if notification_type_is_enabled_v288(
            spec.notification_type,
            preferences.get(spec.recipient_id),
        ):
            allowed.append(spec)
        else:
            suppressed.append(spec)

    if suppressed:
        suppressed_keys = [spec.event_key for spec in suppressed]
        NotificationDeliveryEvent.objects.bulk_create(
            [_suppressed_event_from_spec_v288(spec) for spec in suppressed],
            ignore_conflicts=True,
        )
        suppressed_at = now or timezone.now()
        (
            NotificationDeliveryEvent.objects
            .filter(event_key__in=suppressed_keys)
            .exclude(
                status__in=[
                    NotificationDeliveryEvent.Status.SENT,
                    NotificationDeliveryEvent.Status.SKIPPED,
                ]
            )
            .update(
                status=NotificationDeliveryEvent.Status.SKIPPED,
                claim_token=None,
                processing_started_at=None,
                last_error_category=PREFERENCE_SUPPRESSION_REASON_V288,
                updated_at=suppressed_at,
            )
        )

    return NotificationPreferenceDecisionV288(
        allowed_specs=tuple(allowed),
        suppressed_specs=tuple(suppressed),
    )
