from __future__ import annotations

from datetime import timedelta
from io import StringIO
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from listings.models import (
    NotificationDeliveryEvent,
    NotificationDeliveryRetentionEvidence,
)
from listings.notification_delivery_retention_v308 import (
    NotificationDeliveryRetentionConfigurationErrorV308,
    V308_RETENTION_BACKUP_POLICY,
    apply_notification_delivery_retention_v308,
    preview_notification_delivery_retention_v308,
    release_notification_delivery_event_legal_hold_v308,
    set_notification_delivery_event_legal_hold_v308,
)


@override_settings(
    NOTIFICATION_DELIVERY_EVENT_RETENTION_DAYS=90,
    NOTIFICATION_DELIVERY_RETENTION_BACKUP_POLICY=(
        V308_RETENTION_BACKUP_POLICY
    ),
    NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED=False,
    NOTIFICATION_DELIVERY_RETENTION_DEFAULT_LIMIT=100,
)
class NotificationDeliveryRetentionV308Tests(
    TestCase
):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="v308-user",
            email="v308-user@example.test",
            password="test-pass-123",
        )

        self.sequence = 0

    def _event(
        self,
        *,
        status=NotificationDeliveryEvent.Status.SENT,
        age_days=120,
        recipient=True,
        provider=True,
    ):
        self.sequence += 1

        event = NotificationDeliveryEvent.objects.create(
            recipient=(
                self.user
                if recipient
                else None
            ),
            notification_type=(
                NotificationDeliveryEvent
                .NotificationType
                .SAVED_SEARCH_NEW_LISTING
            ),
            event_key=(
                f"{self.sequence:064x}"
            ),
            status=status,
            sent_at=(
                timezone.now()
                if status
                == NotificationDeliveryEvent.Status.SENT
                else None
            ),
            provider_name=(
                "provider-test"
                if provider
                else ""
            ),
            provider_message_id=(
                f"provider-message-{self.sequence}"
                if provider
                else ""
            ),
            provider_event_id=(
                f"provider-event-{self.sequence}"
                if provider
                else ""
            ),
            provider_outcome=(
                NotificationDeliveryEvent
                .ProviderOutcome
                .DELIVERED
                if provider
                else ""
            ),
            provider_outcome_at=(
                timezone.now()
                if provider
                else None
            ),
        )

        NotificationDeliveryEvent.objects.filter(
            pk=event.pk
        ).update(
            created_at=(
                timezone.now()
                - timedelta(days=age_days)
            )
        )

        event.refresh_from_db()

        return event

    def _evidence(self):
        return (
            NotificationDeliveryRetentionEvidence
            .objects
            .create(
                cutoff_at=timezone.now(),
                retention_days=90,
                eligible_count=1,
                candidate_count=1,
                held_count=0,
                non_terminal_count=0,
                tombstoned_count=1,
                batch_limit=100,
                backup_policy=(
                    V308_RETENTION_BACKUP_POLICY
                ),
                evidence_digest="e" * 64,
                source="test",
            )
        )

    def test_model_contract_contains_hold_tombstone_and_evidence_fields(
        self,
    ):
        event_fields = {
            field.name
            for field in (
                NotificationDeliveryEvent
                ._meta
                .get_fields()
            )
        }

        evidence_fields = {
            field.name
            for field in (
                NotificationDeliveryRetentionEvidence
                ._meta
                .get_fields()
            )
        }

        self.assertTrue(
            {
                "legal_hold",
                "legal_hold_reason",
                "legal_hold_set_at",
                "legal_hold_set_by",
                "retention_tombstoned_at",
                "retention_evidence",
            }
            <= event_fields
        )

        self.assertTrue(
            {
                "run_id",
                "cutoff_at",
                "retention_days",
                "candidate_count",
                "tombstoned_count",
                "backup_policy",
                "evidence_digest",
            }
            <= evidence_fields
        )

    def test_evidence_is_immutable(
        self,
    ):
        evidence = self._evidence()

        evidence.source = "changed"

        with self.assertRaises(
            ValidationError
        ):
            evidence.save()

        with self.assertRaises(
            ValidationError
        ):
            (
                NotificationDeliveryRetentionEvidence
                .objects
                .filter(pk=evidence.pk)
                .update(source="changed")
            )

        with self.assertRaises(
            ValidationError
        ):
            evidence.delete()

    def test_preview_is_read_only_and_sanitized(
        self,
    ):
        event = self._event()

        result = (
            preview_notification_delivery_retention_v308()
        )

        event.refresh_from_db()

        self.assertTrue(
            result["dry_run"]
        )
        self.assertFalse(
            result["mutation_allowed"]
        )
        self.assertEqual(
            result["candidate_count"],
            1,
        )
        self.assertEqual(
            result["tombstoned_count"],
            0,
        )
        self.assertIsNone(
            event.retention_tombstoned_at
        )
        self.assertEqual(
            event.recipient_id,
            self.user.pk,
        )
        self.assertFalse(
            NotificationDeliveryRetentionEvidence
            .objects
            .exists()
        )

        serialized = json.dumps(
            result,
            sort_keys=True,
        )

        self.assertNotIn(
            self.user.email,
            serialized,
        )
        self.assertNotIn(
            event.provider_message_id,
            serialized,
        )

    def test_preview_excludes_legal_hold(
        self,
    ):
        event = self._event()

        set_notification_delivery_event_legal_hold_v308(
            event,
            reason="Regulatory preservation",
            actor=self.user,
        )

        result = (
            preview_notification_delivery_retention_v308()
        )

        self.assertEqual(
            result["eligible_count"],
            0,
        )
        self.assertEqual(
            result["candidate_count"],
            0,
        )
        self.assertEqual(
            result["held_count"],
            1,
        )

    def test_release_legal_hold_restores_eligibility(
        self,
    ):
        event = self._event()

        held = (
            set_notification_delivery_event_legal_hold_v308(
                event,
                reason="Temporary hold",
                actor=self.user,
            )
        )

        released = (
            release_notification_delivery_event_legal_hold_v308(
                held
            )
        )

        self.assertFalse(
            released.legal_hold
        )
        self.assertEqual(
            released.legal_hold_reason,
            "",
        )
        self.assertIsNone(
            released.legal_hold_set_at
        )
        self.assertIsNone(
            released.legal_hold_set_by_id
        )

        self.assertEqual(
            preview_notification_delivery_retention_v308()[
                "candidate_count"
            ],
            1,
        )

    def test_non_terminal_events_are_not_candidates(
        self,
    ):
        self._event(
            status=(
                NotificationDeliveryEvent
                .Status
                .FAILED
            ),
        )

        result = (
            preview_notification_delivery_retention_v308()
        )

        self.assertEqual(
            result["candidate_count"],
            0,
        )
        self.assertEqual(
            result["non_terminal_count"],
            1,
        )

    def test_apply_is_disabled_by_default(
        self,
    ):
        self._event()

        with self.assertRaises(
            NotificationDeliveryRetentionConfigurationErrorV308
        ):
            apply_notification_delivery_retention_v308(
                confirm=True
            )

    @override_settings(
        NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED=True
    )
    def test_apply_requires_confirmation(
        self,
    ):
        self._event()

        with self.assertRaisesMessage(
            ValueError,
            "requires explicit confirmation",
        ):
            apply_notification_delivery_retention_v308(
                confirm=False
            )

    @override_settings(
        NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED=True
    )
    def test_apply_tombstones_and_writes_evidence(
        self,
    ):
        event = self._event()
        original_key = event.event_key

        result = (
            apply_notification_delivery_retention_v308(
                confirm=True,
                source="test_suite",
            )
        )

        event.refresh_from_db()

        evidence = (
            NotificationDeliveryRetentionEvidence
            .objects
            .get()
        )

        self.assertEqual(
            result["tombstoned_count"],
            1,
        )
        self.assertEqual(
            result["evidence_id"],
            str(evidence.pk),
        )
        self.assertEqual(
            event.event_key,
            original_key,
        )
        self.assertEqual(
            event.status,
            NotificationDeliveryEvent.Status.SENT,
        )
        self.assertIsNone(
            event.recipient_id
        )
        self.assertIsNone(
            event.listing_id
        )
        self.assertIsNone(
            event.saved_search_id
        )
        self.assertEqual(
            event.provider_name,
            "",
        )
        self.assertEqual(
            event.provider_message_id,
            "",
        )
        self.assertEqual(
            event.provider_event_id,
            "",
        )
        self.assertEqual(
            event.provider_outcome,
            "",
        )
        self.assertIsNone(
            event.provider_outcome_at
        )
        self.assertIsNone(
            event.sent_at
        )
        self.assertIsNotNone(
            event.retention_tombstoned_at
        )
        self.assertEqual(
            event.retention_evidence_id,
            evidence.pk,
        )
        self.assertEqual(
            evidence.backup_policy,
            V308_RETENTION_BACKUP_POLICY,
        )
        self.assertEqual(
            evidence.tombstoned_count,
            1,
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED=True
    )
    def test_tombstone_preserves_dedup_key(
        self,
    ):
        event = self._event()
        event_key = event.event_key

        apply_notification_delivery_retention_v308(
            confirm=True
        )

        NotificationDeliveryEvent.objects.bulk_create(
            [
                NotificationDeliveryEvent(
                    notification_type=(
                        NotificationDeliveryEvent
                        .NotificationType
                        .SAVED_SEARCH_NEW_LISTING
                    ),
                    event_key=event_key,
                    status=(
                        NotificationDeliveryEvent
                        .Status
                        .PENDING
                    ),
                )
            ],
            ignore_conflicts=True,
        )

        self.assertEqual(
            NotificationDeliveryEvent.objects.filter(
                event_key=event_key
            ).count(),
            1,
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RETENTION_BACKUP_POLICY="unsupported"
    )
    def test_backup_policy_mismatch_fails_closed(
        self,
    ):
        with self.assertRaises(
            NotificationDeliveryRetentionConfigurationErrorV308
        ):
            preview_notification_delivery_retention_v308()

    def test_command_defaults_to_dry_run(
        self,
    ):
        event = self._event()
        output = StringIO()

        call_command(
            "cleanup_notification_delivery_events",
            stdout=output,
        )

        event.refresh_from_db()

        rendered = output.getvalue()

        self.assertIn(
            "mode=dry_run",
            rendered,
        )
        self.assertIn(
            "mutation_allowed=false",
            rendered,
        )
        self.assertIn(
            "Dry-run safety",
            rendered,
        )
        self.assertIsNone(
            event.retention_tombstoned_at
        )
        self.assertFalse(
            NotificationDeliveryRetentionEvidence
            .objects
            .exists()
        )
        self.assertNotIn(
            "@",
            rendered,
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED=True
    )
    def test_command_apply_requires_confirmation(
        self,
    ):
        self._event()

        with self.assertRaisesMessage(
            CommandError,
            "requires explicit confirmation",
        ):
            call_command(
                "cleanup_notification_delivery_events",
                "--apply",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    @override_settings(
        NOTIFICATION_DELIVERY_RETENTION_APPLY_ENABLED=True
    )
    def test_command_confirmed_apply_writes_evidence(
        self,
    ):
        event = self._event()
        output = StringIO()

        call_command(
            "cleanup_notification_delivery_events",
            "--apply",
            "--confirm-retention-cleanup",
            "--limit",
            "1",
            stdout=output,
        )

        event.refresh_from_db()

        rendered = output.getvalue()

        self.assertIn(
            "mode=apply",
            rendered,
        )
        self.assertIn(
            "tombstoned=1",
            rendered,
        )
        self.assertIn(
            "evidence_id=",
            rendered,
        )
        self.assertIsNotNone(
            event.retention_tombstoned_at
        )
        self.assertEqual(
            NotificationDeliveryRetentionEvidence
            .objects
            .count(),
            1,
        )
        self.assertNotIn(
            "@",
            rendered,
        )

    def test_command_json_is_sanitized(
        self,
    ):
        event = self._event()
        output = StringIO()

        call_command(
            "cleanup_notification_delivery_events",
            "--json",
            stdout=output,
        )

        result = json.loads(
            output.getvalue()
        )

        self.assertTrue(
            result["dry_run"]
        )
        self.assertEqual(
            result["candidate_count"],
            1,
        )
        self.assertNotIn(
            self.user.email,
            output.getvalue(),
        )
        self.assertNotIn(
            event.provider_message_id,
            output.getvalue(),
        )
