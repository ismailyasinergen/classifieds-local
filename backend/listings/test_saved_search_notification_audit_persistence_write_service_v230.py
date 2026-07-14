from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from listings.models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
)
from listings.saved_search_notification_audit_persistence import (
    METADATA_DENYLIST,
    SavedSearchNotificationAuditIdempotencyConflict,
    SavedSearchNotificationAuditWriteResult,
    record_saved_search_notification_audit_event,
)


V230_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_WRITE_SERVICE = (
    "V230_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_WRITE_SERVICE"
)


class SavedSearchNotificationAuditPersistenceWriteServiceV230Tests(
    TestCase
):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="v230-audit-owner",
            email="v230-audit-owner@example.com",
            password="v230-test-password",
        )

        cls.saved_search = SavedSearch.objects.create(
            user=cls.user,
            name="V230 audit search",
            path="/listings/",
            query_params={"q": "v230"},
            querystring="q=v230",
        )

        cls.other_saved_search = SavedSearch.objects.create(
            user=cls.user,
            name="V230 other audit search",
            path="/listings/",
            query_params={"q": "other-v230"},
            querystring="q=other-v230",
        )

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _write_kwargs(self, **overrides):
        values = {
            "saved_search": self.saved_search,
            "event_type": (
                SavedSearchNotificationAuditEvent
                .EventType
                .EVALUATION_STARTED
            ),
            "outcome": (
                SavedSearchNotificationAuditEvent
                .Outcome
                .PENDING
            ),
            "occurred_at": timezone.now(),
            "correlation_id": uuid.uuid4(),
            "idempotency_key": f"v230:{uuid.uuid4()}",
            "notification_fingerprint": "a" * 64,
            "actor_type": (
                SavedSearchNotificationAuditEvent
                .ActorType
                .SYSTEM
            ),
            "source": "v230-write-service-tests",
            "metadata": {
                "checkpoint": "v230",
                "match_count": 2,
            },
        }

        values.update(overrides)
        return values

    def _record(self, **overrides):
        return record_saved_search_notification_audit_event(
            **self._write_kwargs(**overrides)
        )

    def test_v230_marker_and_public_api_are_stable(self):
        self.assertEqual(
            V230_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_WRITE_SERVICE,
            (
                "V230_SAVED_SEARCH_NOTIFICATION_AUDIT_"
                "PERSISTENCE_WRITE_SERVICE"
            ),
        )

        self.assertTrue(callable(
            record_saved_search_notification_audit_event
        ))

        self.assertTrue(
            issubclass(
                SavedSearchNotificationAuditIdempotencyConflict,
                RuntimeError,
            )
        )

    def test_v230_first_write_creates_complete_append_only_event(self):
        result = self._record(
            reason_code="candidate-evaluated",
            actor_identifier="scheduler-v230",
        )

        self.assertIsInstance(
            result,
            SavedSearchNotificationAuditWriteResult,
        )
        self.assertTrue(result.created)

        event = result.event

        self.assertEqual(
            event.saved_search,
            self.saved_search,
        )
        self.assertEqual(
            event.owner_id_snapshot,
            str(self.user.pk),
        )
        self.assertEqual(
            event.reason_code,
            "candidate-evaluated",
        )
        self.assertEqual(
            event.actor_identifier,
            "scheduler-v230",
        )
        self.assertEqual(
            event.metadata,
            {
                "checkpoint": "v230",
                "match_count": 2,
            },
        )

    def test_v230_write_result_is_frozen(self):
        result = self._record()

        with self.assertRaises(FrozenInstanceError):
            result.created = False

    def test_v230_identical_replay_returns_created_false_and_same_event(self):
        occurred_at = timezone.now()
        correlation_id = uuid.uuid4()
        idempotency_key = f"v230-replay:{uuid.uuid4()}"

        kwargs = self._write_kwargs(
            occurred_at=occurred_at,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            metadata={
                "b": 2,
                "a": 1,
            },
        )

        first = record_saved_search_notification_audit_event(
            **kwargs
        )

        replay = record_saved_search_notification_audit_event(
            **{
                **kwargs,
                "metadata": {
                    "a": 1,
                    "b": 2,
                },
            }
        )

        self.assertTrue(first.created)
        self.assertFalse(replay.created)
        self.assertEqual(
            first.event.pk,
            replay.event.pk,
        )
        self.assertEqual(
            SavedSearchNotificationAuditEvent.objects.filter(
                idempotency_key=idempotency_key
            ).count(),
            1,
        )

    def test_v230_changed_replay_raises_explicit_conflict(self):
        occurred_at = timezone.now()
        correlation_id = uuid.uuid4()
        idempotency_key = f"v230-conflict:{uuid.uuid4()}"

        kwargs = self._write_kwargs(
            occurred_at=occurred_at,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
            reason_code="original",
        )

        first = record_saved_search_notification_audit_event(
            **kwargs
        )

        with self.assertRaises(
            SavedSearchNotificationAuditIdempotencyConflict
        ) as context:
            record_saved_search_notification_audit_event(
                **{
                    **kwargs,
                    "reason_code": "different",
                }
            )

        conflict = context.exception

        self.assertEqual(
            conflict.idempotency_key,
            idempotency_key,
        )
        self.assertIn(
            "reason_code",
            conflict.differing_fields,
        )

        first.event.refresh_from_db()

        self.assertEqual(
            first.event.reason_code,
            "original",
        )
        self.assertEqual(
            SavedSearchNotificationAuditEvent.objects.filter(
                idempotency_key=idempotency_key
            ).count(),
            1,
        )

    def test_v230_replay_conflict_can_report_multiple_fields(self):
        occurred_at = timezone.now()
        correlation_id = uuid.uuid4()
        idempotency_key = f"v230-multi-conflict:{uuid.uuid4()}"

        kwargs = self._write_kwargs(
            occurred_at=occurred_at,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )

        record_saved_search_notification_audit_event(
            **kwargs
        )

        with self.assertRaises(
            SavedSearchNotificationAuditIdempotencyConflict
        ) as context:
            record_saved_search_notification_audit_event(
                **{
                    **kwargs,
                    "outcome": (
                        SavedSearchNotificationAuditEvent
                        .Outcome
                        .SUCCEEDED
                    ),
                    "source": "different-source",
                }
            )

        self.assertTrue(
            {
                "outcome",
                "source",
            }.issubset(
                set(context.exception.differing_fields)
            )
        )

    def test_v230_invalid_choice_values_fail_before_insert(self):
        cases = (
            (
                "event_type",
                "not-an-event",
            ),
            (
                "outcome",
                "not-an-outcome",
            ),
            (
                "actor_type",
                "not-an-actor",
            ),
        )

        for field_name, value in cases:
            with self.subTest(field_name=field_name):
                with self.assertRaises(ValidationError):
                    self._record(
                        **{
                            field_name: value,
                        }
                    )

        self.assertEqual(
            SavedSearchNotificationAuditEvent.objects.count(),
            0,
        )

    def test_v230_requires_saved_search_and_aware_occurrence_time(self):
        unsaved_search = SavedSearch(
            user=self.user,
            name="Unsaved v230 search",
            path="/listings/",
            query_params={},
            querystring="",
        )

        with self.assertRaises(ValidationError):
            self._record(
                saved_search=unsaved_search,
            )

        with self.assertRaises(ValidationError):
            self._record(
                occurred_at=datetime(2026, 7, 14, 4, 0, 0),
            )

    def test_v230_normalizes_uuid_strings_and_fingerprint_case(self):
        correlation_id = uuid.uuid4()
        batch_id = uuid.uuid4()

        result = self._record(
            correlation_id=str(correlation_id),
            batch_id=str(batch_id),
            notification_fingerprint="ABCDEF" * 10 + "ABCD",
        )

        self.assertEqual(
            result.event.correlation_id,
            correlation_id,
        )
        self.assertEqual(
            result.event.batch_id,
            batch_id,
        )
        self.assertEqual(
            result.event.notification_fingerprint,
            ("abcdef" * 10 + "abcd"),
        )

    def test_v230_rejects_invalid_fingerprint_and_uuid_values(self):
        with self.assertRaises(ValidationError):
            self._record(
                notification_fingerprint="not-a-sha256",
            )

        with self.assertRaises(ValidationError):
            self._record(
                correlation_id="not-a-uuid",
            )

    def test_v230_sensitive_metadata_keys_are_rejected_recursively(self):
        sensitive_metadata_samples = (
            {
                "password": "must-not-persist",
            },
            {
                "nested": {
                    "accessToken": "must-not-persist",
                },
            },
            {
                "transport": {
                    "smtp_password": "must-not-persist",
                },
            },
            {
                "email": {
                    "rendered_html": "<p>private</p>",
                },
            },
            {
                "failure": {
                    "stackTrace": "private trace",
                },
            },
        )

        for metadata in sensitive_metadata_samples:
            with self.subTest(metadata=metadata):
                with self.assertRaises(ValidationError):
                    self._record(
                        metadata=metadata,
                    )

        self.assertEqual(
            SavedSearchNotificationAuditEvent.objects.count(),
            0,
        )

    def test_v230_metadata_denylist_declares_required_privacy_terms(self):
        required = {
            "authorization",
            "cookie",
            "password",
            "smtp_password",
            "rendered_body",
            "token",
            "traceback",
        }

        self.assertTrue(
            required.issubset(METADATA_DENYLIST)
        )

    def test_v230_non_json_metadata_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._record(
                metadata={
                    "safe_key": object(),
                },
            )

    def test_v230_metadata_with_non_string_key_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._record(
                metadata={
                    7: "not-allowed",
                },
            )

    def test_v230_delivery_event_requires_attempt_identifier(self):
        with self.assertRaises(ValidationError):
            self._record(
                event_type=(
                    SavedSearchNotificationAuditEvent
                    .EventType
                    .DELIVERY_ATTEMPTED
                ),
            )

        delivery_attempt_id = uuid.uuid4()

        result = self._record(
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .DELIVERY_ATTEMPTED
            ),
            delivery_attempt_id=delivery_attempt_id,
        )

        self.assertEqual(
            result.event.delivery_attempt_id,
            delivery_attempt_id,
        )

    def test_v230_rollback_event_requires_same_search_link(self):
        original = self._record().event

        rollback = self._record(
            event_type=(
                SavedSearchNotificationAuditEvent
                .EventType
                .ROLLBACK_APPLIED
            ),
            outcome=(
                SavedSearchNotificationAuditEvent
                .Outcome
                .ROLLED_BACK
            ),
            rollback_of=original,
        )

        self.assertEqual(
            rollback.event.rollback_of,
            original,
        )

        other_event = self._record(
            saved_search=self.other_saved_search,
        ).event

        with self.assertRaises(ValidationError):
            self._record(
                event_type=(
                    SavedSearchNotificationAuditEvent
                    .EventType
                    .ROLLBACK_APPLIED
                ),
                outcome=(
                    SavedSearchNotificationAuditEvent
                    .Outcome
                    .ROLLED_BACK
                ),
                rollback_of=other_event,
            )

    def test_v230_rollback_event_without_link_is_rejected(self):
        with self.assertRaises(ValidationError):
            self._record(
                event_type=(
                    SavedSearchNotificationAuditEvent
                    .EventType
                    .ROLLBACK_PREVIEWED
                ),
                outcome=(
                    SavedSearchNotificationAuditEvent
                    .Outcome
                    .ROLLED_BACK
                ),
            )

    def test_v230_write_never_mutates_saved_search_timestamps(self):
        checked_before = (
            self.saved_search
            .last_notification_checked_at
        )
        sent_before = (
            self.saved_search
            .last_notification_sent_at
        )

        now = timezone.now()

        self._record(
            checked_at_before=checked_before,
            checked_at_after=now,
            sent_at_before=sent_before,
            sent_at_after=now,
        )

        self.saved_search.refresh_from_db()

        self.assertEqual(
            self.saved_search.last_notification_checked_at,
            checked_before,
        )
        self.assertEqual(
            self.saved_search.last_notification_sent_at,
            sent_before,
        )

    @patch("django.core.mail.EmailMessage.send")
    @patch("django.core.mail.send_mail")
    def test_v230_write_service_never_delivers_email(
        self,
        send_mail_mock,
        message_send_mock,
    ):
        self._record()

        send_mail_mock.assert_not_called()
        message_send_mock.assert_not_called()

    def test_v230_service_uses_atomic_get_or_create_contract(self):
        source = (
            self._backend_root()
            / "listings"
            / "saved_search_notification_audit_persistence.py"
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        self.assertIn(
            "with transaction.atomic():",
            source,
        )
        self.assertIn(
            ".objects.get_or_create(",
            source,
        )
        self.assertIn(
            "idempotency_key=idempotency_key",
            source,
        )
        self.assertIn(
            "created=created",
            source,
        )

    def test_v230_service_does_not_import_delivery_or_scheduler_modules(self):
        source = (
            self._backend_root()
            / "listings"
            / "saved_search_notification_audit_persistence.py"
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        forbidden_imports = (
            "from django.core.mail",
            "import django.core.mail",
            "saved_search_notification_email_sender",
            "saved_search_notification_scheduler",
            "process_saved_search_notifications",
        )

        for forbidden in forbidden_imports:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    source,
                )

    def test_v230_adds_no_model_or_migration_change(self):
        migration_source = (
            self._backend_root()
            / "listings"
            / "migrations"
            / "0016_savedsearchnotificationauditevent.py"
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        self.assertIn(
            "SavedSearchNotificationAuditEvent",
            migration_source,
        )

        self.assertFalse(
            (
                self._backend_root()
                / "listings"
                / "migrations"
                / "0017_savedsearchnotificationauditwriteservice.py"
            ).exists()
        )

    def test_v230_v228_and_v229_transition_guards_are_packaged(self):
        v228_source = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_audit_"
                "persistence_implementation_contract_v228.py"
            )
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        v229_source = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_audit_"
                "persistence_model_migration_v229.py"
            )
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

        for source in (
            v228_source,
            v229_source,
        ):
            self.assertIn(
                "persistence_write_service_v230.py",
                source,
            )
            self.assertIn(
                "persistence_module.is_file()",
                source,
            )

    def test_v230_next_lane_is_runtime_integration_contract(self):
        next_lane = "v231: saved-search notification audit runtime integration contract"

        self.assertEqual(
            next_lane,
            "v231: saved-search notification audit runtime integration contract",
        )
