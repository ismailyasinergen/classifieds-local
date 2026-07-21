from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import DatabaseError

from accounts.models import EmailVerificationState


V309_NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT = (
    "V309_NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT"
)

V309_RUNTIME_ENFORCEMENT_SETTING = (
    "NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED"
)


@dataclass(frozen=True)
class NotificationDeliveryRecipientDecisionV309:
    enforcement_enabled: bool
    allowed: bool
    reason_code: str
    recipient_email: str
    verification_state_available: bool
    recipient_verified: bool


def notification_delivery_runtime_enforcement_enabled_v309() -> bool:
    return bool(
        getattr(
            settings,
            V309_RUNTIME_ENFORCEMENT_SETTING,
            False,
        )
    )


def notification_delivery_recipient_decision_v309(
    user,
) -> NotificationDeliveryRecipientDecisionV309:
    recipient_email = str(
        getattr(user, "email", "")
        or ""
    ).strip()

    enforcement_enabled = (
        notification_delivery_runtime_enforcement_enabled_v309()
    )

    if not recipient_email:
        return NotificationDeliveryRecipientDecisionV309(
            enforcement_enabled=enforcement_enabled,
            allowed=False,
            reason_code="missing_recipient",
            recipient_email="",
            verification_state_available=True,
            recipient_verified=False,
        )

    if not enforcement_enabled:
        return NotificationDeliveryRecipientDecisionV309(
            enforcement_enabled=False,
            allowed=True,
            reason_code="runtime_enforcement_disabled",
            recipient_email=recipient_email,
            verification_state_available=True,
            recipient_verified=False,
        )

    user_id = getattr(user, "pk", None)

    if user_id is None:
        return NotificationDeliveryRecipientDecisionV309(
            enforcement_enabled=True,
            allowed=False,
            reason_code="recipient_owner_not_persisted",
            recipient_email="",
            verification_state_available=True,
            recipient_verified=False,
        )

    try:
        verification_state = (
            EmailVerificationState.objects
            .filter(user_id=user_id)
            .only(
                "email_snapshot",
                "verified_at",
            )
            .first()
        )
    except DatabaseError:
        return NotificationDeliveryRecipientDecisionV309(
            enforcement_enabled=True,
            allowed=False,
            reason_code="verification_state_unavailable",
            recipient_email="",
            verification_state_available=False,
            recipient_verified=False,
        )

    recipient_verified = bool(
        verification_state is not None
        and verification_state.verified_at is not None
        and str(
            verification_state.email_snapshot
            or ""
        ).strip()
        == recipient_email
    )

    if not recipient_verified:
        return NotificationDeliveryRecipientDecisionV309(
            enforcement_enabled=True,
            allowed=False,
            reason_code="recipient_unverified",
            recipient_email="",
            verification_state_available=True,
            recipient_verified=False,
        )

    return NotificationDeliveryRecipientDecisionV309(
        enforcement_enabled=True,
        allowed=True,
        reason_code="recipient_verified",
        recipient_email=recipient_email,
        verification_state_available=True,
        recipient_verified=True,
    )


def notification_delivery_recipient_email_v309(
    user,
) -> str:
    return (
        notification_delivery_recipient_decision_v309(
            user
        ).recipient_email
    )


__all__ = [
    "NotificationDeliveryRecipientDecisionV309",
    "V309_NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT",
    "V309_RUNTIME_ENFORCEMENT_SETTING",
    "notification_delivery_recipient_decision_v309",
    "notification_delivery_recipient_email_v309",
    "notification_delivery_runtime_enforcement_enabled_v309",
]
