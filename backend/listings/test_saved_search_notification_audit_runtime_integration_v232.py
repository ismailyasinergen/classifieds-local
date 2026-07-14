from __future__ import annotations

import uuid
from io import StringIO
from pathlib import Path
from unittest.mock import Mock, patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from listings.models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
)
from listings.saved_search_notification_audit import (
    build_saved_search_notification_rollback_plan,
    rollback_saved_search_notification_sent_timestamp,
)
from listings.saved_search_notification_audit_runtime import (
    IDEMPOTENCY_PREFIX,
    SavedSearchNotificationAuditRuntimeContext,
    V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION,
    build_saved_search_notification_audit_idempotency_key,
    build_saved_search_notification_fingerprint,
    record_saved_search_notification_runtime_event,
)
from listings.saved_search_notification_email_renderer import (
    render_saved_search_notification_email,
)
from listings.saved_search_notification_email_sender import (
    SavedSearchNotificationEmailDeliveryBlocked,
    send_saved_search_notification_email,
)
from listings.saved_search_notification_scheduler import (
    build_saved_search_notification_email_dry_run_preview,
)


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    )
)
class SavedSearchNotificationAuditRuntimeIntegrationV232Tests(
    TestCase
):
    maxDiff = None

    def setUp(self):
        user_model = get_user_model()

        self.user = user_model.objects.create_user(
            username="v232-runtime-owner",
            email="v232-runtime-owner@example.com",
            password="v232-password",
        )

        self.saved_search = SavedSearch.objects.create(
            user=self.user,
            name="V232 runtime search",
            path="/listings/",
            query_params={"q": "v232"},
            querystring="q=v232",
            email_notifications_enabled=True,
        )

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _context(
        self,
        *,
        source="saved_search.test.v232",
        mode="test",
        actor_type="test_backend",
        create_batch=False,
    ):
        return SavedSearchNotificationAuditRuntimeContext.create(
            actor_type=actor_type,
            actor_identifier="v232-tests",
            source=source,
            mode=mode,
            create_batch=create_batch,
        )

    def _fingerprint(self, listing_ids=(11, 22)):
        return build_saved_search_notification_fingerprint(
            self.saved_search,
            matching_listings=[
                {
                    "id": listing_id,
                    "title": f"Listing {listing_id}",
                }
                for listing_id in listing_ids
            ],
        )

    def _create_sent_timestamp_event(
        self,
        *,
        sent_at,
        context=None,
    ):
        context = context or self._context(
            source="saved_search.sender.test_backend",
            mode="execute_send",
        )

        return record_saved_search_notification_runtime_event(
            saved_search=self.saved_search,
            context=context,
            event_type="sent_timestamp_recorded",
            notification_fingerprint=self._fingerprint(),
            operation_sequence=(
                "test:"
                f"{self.saved_search.pk}:"
                "sent_timestamp_recorded"
            ),
            delivery_attempt_id=uuid.uuid4(),
            sent_at_before=None,
            sent_at_after=sent_at,
            metadata={
                "mode": "execute_send",
                "timestamp_changed": True,
            },
        ).event

    def test_v232_marker_and_public_adapter_api_are_stable(self):
        self.assertEqual(
            V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION,
            (
                "V232_SAVED_SEARCH_NOTIFICATION_AUDIT_"
                "RUNTIME_INTEGRATION"
            ),
        )

        self.assertEqual(
            IDEMPOTENCY_PREFIX,
            "ssna:v1:",
        )

    def test_v232_context_derivation_preserves_run_identity(self):
        context = self._context(create_batch=True)

        derived = context.for_surface(
            source="saved_search.renderer.preview",
            mode="dry_run",
        )

        self.assertEqual(
            derived.correlation_id,
            context.correlation_id,
        )
        self.assertEqual(
            derived.batch_id,
            context.batch_id,
        )
        self.assertEqual(
            derived.started_at,
            context.started_at,
        )
        self.assertEqual(
            derived.source,
            "saved_search.renderer.preview",
        )

    def test_v232_fingerprint_is_deterministic_and_order_sensitive(self):
        first = self._fingerprint((11, 22))
        replay = self._fingerprint((11, 22))
        reordered = self._fingerprint((22, 11))

        self.assertEqual(first, replay)
        self.assertNotEqual(first, reordered)
        self.assertRegex(first, r"^[a-f0-9]{64}$")

    def test_v232_idempotency_key_is_deterministic_and_bounded(self):
        context = self._context(create_batch=True)
        attempt_id = uuid.uuid4()

        first = build_saved_search_notification_audit_idempotency_key(
            saved_search=self.saved_search,
            context=context,
            event_type="delivery_attempted",
            operation_sequence="delivery:1:attempted",
            delivery_attempt_id=attempt_id,
        )

        replay = build_saved_search_notification_audit_idempotency_key(
            saved_search=self.saved_search,
            context=context,
            event_type="delivery_attempted",
            operation_sequence="delivery:1:attempted",
            delivery_attempt_id=attempt_id,
        )

        self.assertEqual(first, replay)
        self.assertTrue(first.startswith("ssna:v1:"))
        self.assertLessEqual(len(first), 128)

    def test_v232_runtime_metadata_is_strictly_allowlisted(self):
        context = self._context()

        with self.assertRaises(ValidationError):
            record_saved_search_notification_runtime_event(
                saved_search=self.saved_search,
                context=context,
                event_type="evaluation_started",
                notification_fingerprint=self._fingerprint(),
                operation_sequence="test:metadata",
                metadata={
                    "mode": "test",
                    "recipient": self.user.email,
                },
            )

        self.assertEqual(
            SavedSearchNotificationAuditEvent.objects.count(),
            0,
        )

    def test_v232_scheduler_preview_records_evaluation_and_render(self):
        before_checked = (
            self.saved_search
            .last_notification_checked_at
        )
        before_sent = (
            self.saved_search
            .last_notification_sent_at
        )

        result = (
            build_saved_search_notification_email_dry_run_preview(
                self.saved_search,
                match_count=2,
                matching_listings=[
                    {
                        "id": 11,
                        "title": "First",
                    },
                    {
                        "id": 22,
                        "title": "Second",
                    },
                ],
            )
        )

        events = list(
            SavedSearchNotificationAuditEvent
            .objects
            .filter(saved_search=self.saved_search)
            .order_by("created_at")
        )

        self.assertEqual(
            [event.event_type for event in events],
            [
                "evaluation_started",
                "dry_run_rendered",
            ],
        )
        self.assertEqual(
            events[0].correlation_id,
            events[1].correlation_id,
        )
        self.assertEqual(
            events[0].notification_fingerprint,
            events[1].notification_fingerprint,
        )
        self.assertEqual(
            result["notification_fingerprint"],
            events[0].notification_fingerprint,
        )

        self.saved_search.refresh_from_db()

        self.assertEqual(
            self.saved_search.last_notification_checked_at,
            before_checked,
        )
        self.assertEqual(
            self.saved_search.last_notification_sent_at,
            before_sent,
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_v232_disabled_preview_records_skip_and_preserves_error(self):
        self.saved_search.email_notifications_enabled = False
        self.saved_search.save(
            update_fields=["email_notifications_enabled"]
        )

        with self.assertRaisesMessage(
            ValueError,
            "disabled",
        ):
            build_saved_search_notification_email_dry_run_preview(
                self.saved_search,
            )

        event = (
            SavedSearchNotificationAuditEvent
            .objects
            .get(saved_search=self.saved_search)
        )

        self.assertEqual(
            event.event_type,
            "skipped_notifications_disabled",
        )
        self.assertEqual(event.outcome, "skipped")

    def test_v232_renderer_can_record_dry_run_event_directly(self):
        context = self._context(
            source="saved_search.renderer.preview",
            mode="dry_run",
        )

        render_saved_search_notification_email(
            self.saved_search,
            match_count=1,
            matching_listings=[
                {
                    "id": 91,
                    "title": "Renderer item",
                },
            ],
            audit_runtime_context=context,
        )

        event = (
            SavedSearchNotificationAuditEvent
            .objects
            .get(saved_search=self.saved_search)
        )

        self.assertEqual(
            event.event_type,
            "dry_run_rendered",
        )
        self.assertEqual(
            event.metadata,
            {
                "mode": "dry_run",
                "match_count": 1,
                "rendered_item_count": 1,
            },
        )

    def test_v232_successful_send_records_attempt_success_and_timestamp(self):
        result = send_saved_search_notification_email(
            self.saved_search,
            match_count=1,
            matching_listings=[
                {
                    "id": 31,
                    "title": "Delivery item",
                },
            ],
            execute_send=True,
            require_test_email_backend=True,
        )

        events = list(
            SavedSearchNotificationAuditEvent
            .objects
            .filter(saved_search=self.saved_search)
            .order_by("created_at")
        )

        self.assertEqual(
            [event.event_type for event in events],
            [
                "delivery_attempted",
                "delivery_succeeded",
                "sent_timestamp_recorded",
            ],
        )

        self.assertEqual(
            len(
                {
                    event.delivery_attempt_id
                    for event in events
                }
            ),
            1,
        )

        self.assertEqual(
            len(
                {
                    event.notification_fingerprint
                    for event in events
                }
            ),
            1,
        )

        self.assertEqual(result["delivered_count"], 1)
        self.assertEqual(len(mail.outbox), 1)

        self.saved_search.refresh_from_db()

        self.assertIsNotNone(
            self.saved_search.last_notification_sent_at
        )

        self.assertEqual(
            events[-1].sent_at_after,
            self.saved_search.last_notification_sent_at,
        )

    def test_v232_missing_recipient_records_skip_without_send(self):
        self.user.email = ""
        self.user.save(update_fields=["email"])

        with self.assertRaises(
            SavedSearchNotificationEmailDeliveryBlocked
        ):
            send_saved_search_notification_email(
                self.saved_search,
                execute_send=True,
            )

        event = (
            SavedSearchNotificationAuditEvent
            .objects
            .get(saved_search=self.saved_search)
        )

        self.assertEqual(
            event.event_type,
            "skipped_missing_recipient",
        )
        self.assertEqual(len(mail.outbox), 0)

        self.saved_search.refresh_from_db()

        self.assertIsNone(
            self.saved_search.last_notification_sent_at
        )

    def test_v232_backend_exception_records_failure_without_timestamp(self):
        message = Mock()
        message.send.side_effect = RuntimeError(
            "private backend failure"
        )

        with patch(
            (
                "listings.saved_search_notification_"
                "email_sender._build_email_message"
            ),
            return_value=message,
        ):
            with self.assertRaises(RuntimeError):
                send_saved_search_notification_email(
                    self.saved_search,
                    execute_send=True,
                )

        events = list(
            SavedSearchNotificationAuditEvent
            .objects
            .filter(saved_search=self.saved_search)
            .order_by("created_at")
        )

        self.assertEqual(
            [event.event_type for event in events],
            [
                "delivery_attempted",
                "delivery_failed",
            ],
        )

        self.assertEqual(
            events[-1].reason_code,
            "email_backend_exception",
        )
        self.assertEqual(
            events[-1].metadata["error_code"],
            "RuntimeError",
        )

        serialized_metadata = str(events[-1].metadata)

        self.assertNotIn(
            "private backend failure",
            serialized_metadata,
        )

        self.saved_search.refresh_from_db()

        self.assertIsNone(
            self.saved_search.last_notification_sent_at
        )

    def test_v232_duplicate_attempt_is_blocked_before_second_send(self):
        context = self._context(
            source="saved_search.sender.test_backend",
            mode="execute_send",
        )
        attempt_id = uuid.uuid4()

        first = send_saved_search_notification_email(
            self.saved_search,
            execute_send=True,
            runtime_context=context,
            delivery_attempt_id=attempt_id,
        )

        with self.assertRaisesMessage(
            SavedSearchNotificationEmailDeliveryBlocked,
            "already recorded",
        ):
            send_saved_search_notification_email(
                self.saved_search,
                execute_send=True,
                runtime_context=context,
                delivery_attempt_id=attempt_id,
            )

        self.assertEqual(first["delivered_count"], 1)
        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(
            SavedSearchNotificationAuditEvent
            .objects
            .filter(
                saved_search=self.saved_search,
                event_type="delivery_attempted",
            )
            .count(),
            1,
        )

    def test_v232_timestamp_audit_failure_rolls_back_timestamp(self):
        from listings import (
            saved_search_notification_audit_runtime
            as runtime_module
        )

        original_record = (
            runtime_module
            .record_saved_search_notification_runtime_event
        )

        def record_side_effect(**kwargs):
            if (
                kwargs.get("event_type")
                == "sent_timestamp_recorded"
            ):
                raise ValidationError(
                    "forced timestamp audit failure"
                )

            return original_record(**kwargs)

        with patch(
            (
                "listings.saved_search_notification_"
                "email_sender."
                "record_saved_search_notification_runtime_event"
            ),
            side_effect=record_side_effect,
        ):
            with self.assertRaises(ValidationError):
                send_saved_search_notification_email(
                    self.saved_search,
                    execute_send=True,
                )

        self.saved_search.refresh_from_db()

        self.assertIsNone(
            self.saved_search.last_notification_sent_at
        )

        self.assertEqual(len(mail.outbox), 1)

        self.assertEqual(
            set(
                SavedSearchNotificationAuditEvent
                .objects
                .filter(saved_search=self.saved_search)
                .values_list("event_type", flat=True)
            ),
            {
                "delivery_attempted",
                "delivery_succeeded",
            },
        )

    def test_v232_rollback_preview_and_apply_link_to_sent_event(self):
        sent_at = timezone.now()

        self.saved_search.last_notification_sent_at = sent_at
        self.saved_search.save(
            update_fields=["last_notification_sent_at"]
        )

        target = self._create_sent_timestamp_event(
            sent_at=sent_at,
        )

        context = self._context(
            source="saved_search.rollback.preview",
            mode="rollback_preview",
            actor_type="operator",
            create_batch=True,
        )

        plan = build_saved_search_notification_rollback_plan(
            saved_searches=[self.saved_search],
            runtime_context=context,
            record_persistent_audit=True,
        )

        self.assertEqual(
            plan["persistent_preview_count"],
            1,
        )

        result = (
            rollback_saved_search_notification_sent_timestamp(
                self.saved_search,
                previous_sent_at=None,
                execute_rollback=True,
                operator="v232-tests",
                runtime_context=context,
                rollback_of=target,
            )
        )

        self.saved_search.refresh_from_db()

        self.assertIsNone(
            self.saved_search.last_notification_sent_at
        )

        rollback_events = list(
            SavedSearchNotificationAuditEvent
            .objects
            .filter(
                saved_search=self.saved_search,
                event_type__in=(
                    "rollback_previewed",
                    "rollback_applied",
                ),
            )
            .order_by("created_at")
        )

        self.assertEqual(
            [event.event_type for event in rollback_events],
            [
                "rollback_previewed",
                "rollback_applied",
            ],
        )

        self.assertTrue(
            all(
                event.rollback_of_id == target.pk
                for event in rollback_events
            )
        )

        self.assertEqual(
            result["rollback_of_event_id"],
            str(target.pk),
        )

    def test_v232_rollback_audit_failure_rolls_back_timestamp_restore(self):
        sent_at = timezone.now()

        self.saved_search.last_notification_sent_at = sent_at
        self.saved_search.save(
            update_fields=["last_notification_sent_at"]
        )

        target = self._create_sent_timestamp_event(
            sent_at=sent_at,
        )

        from listings import (
            saved_search_notification_audit_runtime
            as runtime_module
        )

        original_record = (
            runtime_module
            .record_saved_search_notification_runtime_event
        )

        def record_side_effect(**kwargs):
            if kwargs.get("event_type") == "rollback_applied":
                raise ValidationError(
                    "forced rollback audit failure"
                )

            return original_record(**kwargs)

        with patch(
            (
                "listings.saved_search_notification_"
                "audit."
                "record_saved_search_notification_runtime_event"
            ),
            side_effect=record_side_effect,
        ):
            with self.assertRaises(ValidationError):
                rollback_saved_search_notification_sent_timestamp(
                    self.saved_search,
                    previous_sent_at=None,
                    execute_rollback=True,
                    operator="v232-tests",
                    rollback_of=target,
                )

        self.saved_search.refresh_from_db()

        self.assertEqual(
            self.saved_search.last_notification_sent_at,
            sent_at,
        )

        self.assertFalse(
            SavedSearchNotificationAuditEvent
            .objects
            .filter(
                saved_search=self.saved_search,
                event_type="rollback_applied",
            )
            .exists()
        )

    def test_v232_management_command_preview_uses_persistent_audit(self):
        output = StringIO()

        call_command(
            "process_saved_search_notifications",
            render_email_previews=True,
            limit=1,
            stdout=output,
        )

        self.assertIn(
            "DRY RUN email preview",
            output.getvalue(),
        )
        self.assertEqual(len(mail.outbox), 0)

        self.assertEqual(
            set(
                SavedSearchNotificationAuditEvent
                .objects
                .filter(saved_search=self.saved_search)
                .values_list("event_type", flat=True)
            ),
            {
                "evaluation_started",
                "dry_run_rendered",
            },
        )

    def test_v232_runtime_targets_use_adapter_not_persistence_directly(self):
        adapter_source = (
            self._backend_root()
            / "listings"
            / "saved_search_notification_audit_runtime.py"
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        self.assertIn(
            "saved_search_notification_audit_persistence import",
            adapter_source,
        )

        runtime_paths = (
            "saved_search_notification_scheduler.py",
            "saved_search_notification_email_renderer.py",
            "saved_search_notification_email_sender.py",
            "saved_search_notification_audit.py",
            (
                "management/commands/"
                "process_saved_search_notifications.py"
            ),
        )

        for relative_path in runtime_paths:
            source = (
                self._backend_root()
                / "listings"
                / relative_path
            ).read_text(
                encoding="utf-8",
                errors="strict",
            )

            with self.subTest(relative_path=relative_path):
                self.assertIn(
                    "saved_search_notification_audit_runtime",
                    source,
                )
                self.assertNotIn(
                    "saved_search_notification_audit_persistence import",
                    source,
                )
                self.assertNotIn(
                    (
                        "record_saved_search_notification_"
                        "audit_event("
                    ),
                    source,
                )

    def test_v232_adds_no_model_migration_or_editable_admin(self):
        self.assertFalse(
            (
                self._backend_root()
                / "listings"
                / "migrations"
                / "0017_savedsearchnotificationauditruntime.py"
            ).exists()
        )

        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

    def test_v232_v231_transition_guard_is_packaged(self):
        source = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_audit_"
                "runtime_integration_contract_v231.py"
            )
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        self.assertIn(
            "runtime_integration_v232.py",
            source,
        )
        self.assertIn(
            "adapter_path.is_file()",
            source,
        )
        self.assertIn(
            "saved_search_notification_audit_runtime",
            source,
        )

    def test_v232_next_lane_is_operator_read_interface_contract(self):
        next_lane = "v233: saved-search notification persistent audit operator read-interface contract"

        self.assertEqual(
            next_lane,
            "v233: saved-search notification persistent audit operator read-interface contract",
        )
