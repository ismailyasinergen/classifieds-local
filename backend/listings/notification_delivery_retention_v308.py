from __future__ import annotations

from datetime import timedelta
import hashlib
import json
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from listings.models import (
    NotificationDeliveryEvent,
    NotificationDeliveryRetentionEvidence,
)


V308_NOTIFICATION_DELIVERY_RETENTION_FOUNDATION = (
    "V308_NOTIFICATION_DELIVERY_RETENTION_FOUNDATION"
)

V308_RETENTION_BACKUP_POLICY = (
    "restore_requires_recleanup"
)

V308_RETENTION_DRY_RUN_CONTRACT = (
    "dry_run_default_explicit_confirmed_apply"
)

V308_RETENTION_TERMINAL_STATUSES = (
    NotificationDeliveryEvent.Status.SENT,
    NotificationDeliveryEvent.Status.SKIPPED,
)


class NotificationDeliveryRetentionConfigurationErrorV308(
    ValueError
):
    pass


def _positive_integer_v308(
    value,
    *,
    field_name,
):
    if isinstance(value, bool):
        raise NotificationDeliveryRetentionConfigurationErrorV308(
            f"{field_name} must be a positive integer."
        )

    try:
        normalized = int(value)
    except (TypeError, ValueError):
        raise NotificationDeliveryRetentionConfigurationErrorV308(
            f"{field_name} must be a positive integer."
        )

    if normalized <= 0:
        raise NotificationDeliveryRetentionConfigurationErrorV308(
            f"{field_name} must be a positive integer."
        )

    return normalized


def notification_delivery_retention_days_v308():
    return _positive_integer_v308(
        getattr(
            settings,
            "NOTIFICATION_DELIVERY_EVENT_RETENTION_DAYS",
            None,
        ),
        field_name=(
            "NOTIFICATION_DELIVERY_EVENT_RETENTION_DAYS"
        ),
    )


def notification_delivery_retention_limit_v308(
    limit=None,
):
    configured = (
        limit
        if limit is not None
        else getattr(
            settings,
            "NOTIFICATION_DELIVERY_RETENTION_DEFAULT_LIMIT",
            100,
        )
    )

    normalized = _positive_integer_v308(
        configured,
        field_name="retention cleanup limit",
    )

    if normalized > 1000:
        raise NotificationDeliveryRetentionConfigurationErrorV308(
            "Retention cleanup limit must not exceed 1000."
        )

    return normalized


def notification_delivery_retention_backup_policy_v308():
    policy = str(
        getattr(
            settings,
            "NOTIFICATION_DELIVERY_RETENTION_BACKUP_POLICY",
            "",
        )
        or ""
    ).strip().casefold()

    if policy != V308_RETENTION_BACKUP_POLICY:
        raise NotificationDeliveryRetentionConfigurationErrorV308(
            "Notification delivery retention backup policy "
            "is unavailable or unsupported."
        )

    return policy


def notification_delivery_retention_apply_enabled_v308():
    return bool(
        getattr(
            settings,
            "NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED",
            False,
        )
    )


def set_notification_delivery_event_legal_hold_v308(
    event,
    *,
    reason,
    actor=None,
    now=None,
):
    cleaned_reason = str(
        reason
        or ""
    ).strip()

    if not cleaned_reason:
        raise ValueError(
            "Legal hold reason is required."
        )

    if len(cleaned_reason) > 255:
        raise ValueError(
            "Legal hold reason must not exceed 255 characters."
        )

    reference_time = now or timezone.now()

    with transaction.atomic():
        locked = (
            NotificationDeliveryEvent
            .objects
            .select_for_update()
            .get(pk=event.pk)
        )

        if locked.retention_tombstoned_at is not None:
            raise ValueError(
                "A tombstoned delivery event cannot be "
                "placed on legal hold."
            )

        locked.legal_hold = True
        locked.legal_hold_reason = cleaned_reason
        locked.legal_hold_set_at = reference_time
        locked.legal_hold_set_by = actor

        locked.save(
            update_fields=[
                "legal_hold",
                "legal_hold_reason",
                "legal_hold_set_at",
                "legal_hold_set_by",
                "updated_at",
            ]
        )

    return locked


def release_notification_delivery_event_legal_hold_v308(
    event,
):
    with transaction.atomic():
        locked = (
            NotificationDeliveryEvent
            .objects
            .select_for_update()
            .get(pk=event.pk)
        )

        locked.legal_hold = False
        locked.legal_hold_reason = ""
        locked.legal_hold_set_at = None
        locked.legal_hold_set_by = None

        locked.save(
            update_fields=[
                "legal_hold",
                "legal_hold_reason",
                "legal_hold_set_at",
                "legal_hold_set_by",
                "updated_at",
            ]
        )

    return locked


def _retention_context_v308(
    *,
    now=None,
    limit=None,
):
    reference_time = now or timezone.now()
    retention_days = (
        notification_delivery_retention_days_v308()
    )
    batch_limit = (
        notification_delivery_retention_limit_v308(
            limit
        )
    )
    backup_policy = (
        notification_delivery_retention_backup_policy_v308()
    )
    cutoff_at = (
        reference_time
        - timedelta(days=retention_days)
    )

    return {
        "reference_time": reference_time,
        "retention_days": retention_days,
        "batch_limit": batch_limit,
        "backup_policy": backup_policy,
        "cutoff_at": cutoff_at,
    }


def _aged_delivery_events_v308(
    *,
    cutoff_at,
):
    return (
        NotificationDeliveryEvent
        .objects
        .filter(
            created_at__lt=cutoff_at,
            retention_tombstoned_at__isnull=True,
        )
    )


def _retention_counts_v308(
    *,
    cutoff_at,
):
    aged = _aged_delivery_events_v308(
        cutoff_at=cutoff_at
    )

    terminal = aged.filter(
        status__in=(
            V308_RETENTION_TERMINAL_STATUSES
        )
    )

    eligible_count = terminal.filter(
        legal_hold=False
    ).count()

    held_count = terminal.filter(
        legal_hold=True
    ).count()

    non_terminal_count = aged.exclude(
        status__in=(
            V308_RETENTION_TERMINAL_STATUSES
        )
    ).count()

    return {
        "eligible_count": eligible_count,
        "held_count": held_count,
        "non_terminal_count": non_terminal_count,
    }


def _sanitized_result_v308(
    *,
    mode,
    context,
    counts,
    candidate_count,
    tombstoned_count,
    evidence=None,
):
    return {
        "marker": (
            V308_NOTIFICATION_DELIVERY_RETENTION_FOUNDATION
        ),
        "mode": mode,
        "dry_run": mode == "dry_run",
        "mutation_allowed": mode == "apply",
        "apply_enabled": (
            notification_delivery_retention_apply_enabled_v308()
        ),
        "retention_days": context[
            "retention_days"
        ],
        "cutoff_at": context[
            "cutoff_at"
        ].isoformat(),
        "batch_limit": context[
            "batch_limit"
        ],
        "backup_policy": context[
            "backup_policy"
        ],
        "eligible_count": counts[
            "eligible_count"
        ],
        "candidate_count": candidate_count,
        "held_count": counts[
            "held_count"
        ],
        "non_terminal_count": counts[
            "non_terminal_count"
        ],
        "remaining_eligible_count": max(
            counts["eligible_count"]
            - candidate_count,
            0,
        ),
        "tombstoned_count": tombstoned_count,
        "evidence_id": (
            str(evidence.pk)
            if evidence is not None
            else ""
        ),
        "evidence_digest": (
            evidence.evidence_digest
            if evidence is not None
            else ""
        ),
    }


def preview_notification_delivery_retention_v308(
    *,
    now=None,
    limit=None,
):
    context = _retention_context_v308(
        now=now,
        limit=limit,
    )

    counts = _retention_counts_v308(
        cutoff_at=context["cutoff_at"]
    )

    candidate_count = min(
        counts["eligible_count"],
        context["batch_limit"],
    )

    return _sanitized_result_v308(
        mode="dry_run",
        context=context,
        counts=counts,
        candidate_count=candidate_count,
        tombstoned_count=0,
    )


def apply_notification_delivery_retention_v308(
    *,
    confirm=False,
    now=None,
    limit=None,
    source="management_command",
):
    if not confirm:
        raise ValueError(
            "Retention cleanup apply requires explicit confirmation."
        )

    if not (
        notification_delivery_retention_apply_enabled_v308()
    ):
        raise NotificationDeliveryRetentionConfigurationErrorV308(
            "Retention cleanup apply is disabled by configuration."
        )

    context = _retention_context_v308(
        now=now,
        limit=limit,
    )

    cleaned_source = str(
        source
        or "management_command"
    ).strip()[:64]

    with transaction.atomic():
        counts = _retention_counts_v308(
            cutoff_at=context["cutoff_at"]
        )

        candidates = list(
            _aged_delivery_events_v308(
                cutoff_at=context["cutoff_at"]
            )
            .filter(
                status__in=(
                    V308_RETENTION_TERMINAL_STATUSES
                ),
                legal_hold=False,
            )
            .select_for_update()
            .order_by(
                "created_at",
                "pk",
            )[
                :context["batch_limit"]
            ]
        )

        if not candidates:
            return _sanitized_result_v308(
                mode="apply",
                context=context,
                counts=counts,
                candidate_count=0,
                tombstoned_count=0,
            )

        run_id = uuid.uuid4()

        event_key_digest = hashlib.sha256(
            "\n".join(
                sorted(
                    event.event_key
                    for event in candidates
                )
            ).encode("utf-8")
        ).hexdigest()

        canonical_evidence = json.dumps(
            {
                "backup_policy": context[
                    "backup_policy"
                ],
                "batch_limit": context[
                    "batch_limit"
                ],
                "candidate_count": len(
                    candidates
                ),
                "cutoff_at": context[
                    "cutoff_at"
                ].isoformat(),
                "eligible_count": counts[
                    "eligible_count"
                ],
                "event_key_digest": event_key_digest,
                "held_count": counts[
                    "held_count"
                ],
                "non_terminal_count": counts[
                    "non_terminal_count"
                ],
                "retention_days": context[
                    "retention_days"
                ],
                "run_id": str(run_id),
                "source": cleaned_source,
            },
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        )

        evidence = (
            NotificationDeliveryRetentionEvidence
            .objects
            .create(
                run_id=run_id,
                cutoff_at=context[
                    "cutoff_at"
                ],
                retention_days=context[
                    "retention_days"
                ],
                eligible_count=counts[
                    "eligible_count"
                ],
                candidate_count=len(
                    candidates
                ),
                held_count=counts[
                    "held_count"
                ],
                non_terminal_count=counts[
                    "non_terminal_count"
                ],
                tombstoned_count=len(
                    candidates
                ),
                batch_limit=context[
                    "batch_limit"
                ],
                backup_policy=context[
                    "backup_policy"
                ],
                evidence_digest=hashlib.sha256(
                    canonical_evidence.encode(
                        "utf-8"
                    )
                ).hexdigest(),
                source=cleaned_source,
            )
        )

        candidate_ids = [
            event.pk
            for event in candidates
        ]

        tombstoned_count = (
            NotificationDeliveryEvent
            .objects
            .filter(
                pk__in=candidate_ids,
                retention_tombstoned_at__isnull=True,
                legal_hold=False,
            )
            .update(
                recipient=None,
                listing=None,
                listing_price_alert=None,
                saved_search=None,
                price_transition=None,
                target_price=None,
                transition_changed_at=None,
                claim_token=None,
                processing_started_at=None,
                sent_at=None,
                last_error_category="",
                provider_name="",
                provider_message_id="",
                provider_outcome="",
                provider_event_id="",
                provider_outcome_at=None,
                legal_hold=False,
                legal_hold_reason="",
                legal_hold_set_at=None,
                legal_hold_set_by=None,
                retention_tombstoned_at=context[
                    "reference_time"
                ],
                retention_evidence=evidence,
                updated_at=context[
                    "reference_time"
                ],
            )
        )

        if tombstoned_count != len(
            candidates
        ):
            raise RuntimeError(
                "Retention cleanup candidate count changed "
                "inside the locked transaction."
            )

        return _sanitized_result_v308(
            mode="apply",
            context=context,
            counts=counts,
            candidate_count=len(
                candidates
            ),
            tombstoned_count=(
                tombstoned_count
            ),
            evidence=evidence,
        )


def cleanup_notification_delivery_events_v308(
    *,
    apply=False,
    confirm=False,
    now=None,
    limit=None,
    source="management_command",
):
    if apply:
        return apply_notification_delivery_retention_v308(
            confirm=confirm,
            now=now,
            limit=limit,
            source=source,
        )

    if confirm:
        raise ValueError(
            "Retention cleanup confirmation is only valid "
            "together with apply mode."
        )

    return preview_notification_delivery_retention_v308(
        now=now,
        limit=limit,
    )
