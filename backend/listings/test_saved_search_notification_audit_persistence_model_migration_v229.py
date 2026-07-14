from __future__ import annotations

import uuid
from pathlib import Path

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import (
    IntegrityError,
    connection,
    models,
    transaction,
)
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.operations.models import CreateModel
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from listings.models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
    SavedSearchNotificationAuditEventQuerySet,
)


V229_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_MODEL_MIGRATION = (
    "V229_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_MODEL_MIGRATION"
)

EXPECTED_MIGRATION = "0016_savedsearchnotificationauditevent"

EXPECTED_EVENT_TYPES = (
    "evaluation_started",
    "skipped_notifications_disabled",
    "skipped_missing_recipient",
    "dry_run_rendered",
    "delivery_attempted",
    "delivery_succeeded",
    "delivery_failed",
    "sent_timestamp_recorded",
    "rollback_previewed",
    "rollback_applied",
)

EXPECTED_OUTCOMES = (
    "pending",
    "skipped",
    "succeeded",
    "failed",
    "rolled_back",
)

EXPECTED_ACTOR_TYPES = (
    "system",
    "scheduler",
    "operator",
    "management_command",
    "test_backend",
)

EXPECTED_INDEXES = {
    "ssna_saved_occ_idx": (
        "saved_search",
        "occurred_at",
    ),
    "ssna_event_occ_idx": (
        "event_type",
        "occurred_at",
    ),
    "ssna_outcome_occ_idx": (
        "outcome",
        "occurred_at",
    ),
    "ssna_batch_idx": ("batch_id",),
    "ssna_corr_idx": ("correlation_id",),
    "ssna_attempt_idx": ("delivery_attempt_id",),
    "ssna_fingerprint_idx": (
        "notification_fingerprint",
    ),
    "ssna_rollback_idx": ("rollback_of",),
}

EXPECTED_CONSTRAINTS = {
    "ssna_rollback_link_required",
    "ssna_delivery_attempt_required",
}


class SavedSearchNotificationAuditPersistenceModelMigrationV229Tests(
    TestCase
):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()

        cls.user = user_model.objects.create_user(
            username="v229-audit-owner",
            email="v229-audit-owner@example.com",
            password="v229-test-password",
        )

        cls.saved_search = SavedSearch.objects.create(
            user=cls.user,
            name="V229 audit search",
            path="/listings/",
            query_params={"q": "v229"},
            querystring="q=v229",
        )

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _event_kwargs(self, **overrides):
        values = {
            "saved_search": self.saved_search,
            "owner_id_snapshot": str(self.user.pk),
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
            "idempotency_key": f"v229:{uuid.uuid4()}",
            "notification_fingerprint": "a" * 64,
            "actor_type": (
                SavedSearchNotificationAuditEvent
                .ActorType
                .SYSTEM
            ),
            "source": "v229-model-tests",
            "metadata": {
                "checkpoint": "v229",
            },
        }

        values.update(overrides)
        return values

    def _create_event(self, **overrides):
        return SavedSearchNotificationAuditEvent.objects.create(
            **self._event_kwargs(**overrides)
        )

    def test_v229_marker_declares_model_and_migration_checkpoint(self):
        self.assertEqual(
            V229_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_MODEL_MIGRATION,
            (
                "V229_SAVED_SEARCH_NOTIFICATION_AUDIT_"
                "PERSISTENCE_MODEL_MIGRATION"
            ),
        )

    def test_v229_model_is_registered_in_listings_app(self):
        self.assertEqual(
            SavedSearchNotificationAuditEvent._meta.app_label,
            "listings",
        )

        self.assertEqual(
            SavedSearchNotificationAuditEvent._meta.model_name,
            "savedsearchnotificationauditevent",
        )

    def test_v229_model_defines_exact_local_fields(self):
        expected = (
            "id",
            "saved_search",
            "owner_id_snapshot",
            "event_type",
            "outcome",
            "reason_code",
            "occurred_at",
            "created_at",
            "batch_id",
            "correlation_id",
            "delivery_attempt_id",
            "idempotency_key",
            "notification_fingerprint",
            "rollback_of",
            "actor_type",
            "actor_identifier",
            "source",
            "checked_at_before",
            "checked_at_after",
            "sent_at_before",
            "sent_at_after",
            "metadata",
        )

        actual = tuple(
            field.name
            for field in (
                SavedSearchNotificationAuditEvent
                ._meta
                .local_fields
            )
        )

        self.assertEqual(actual, expected)

    def test_v229_identity_and_relation_field_contract(self):
        model = SavedSearchNotificationAuditEvent

        id_field = model._meta.get_field("id")
        self.assertIsInstance(id_field, models.UUIDField)
        self.assertTrue(id_field.primary_key)
        self.assertFalse(id_field.editable)
        self.assertIs(id_field.default, uuid.uuid4)

        saved_search_field = model._meta.get_field(
            "saved_search"
        )
        self.assertIs(
            saved_search_field.remote_field.on_delete,
            models.PROTECT,
        )
        self.assertEqual(
            saved_search_field.remote_field.related_name,
            "notification_audit_events",
        )

        rollback_field = model._meta.get_field("rollback_of")
        self.assertIs(
            rollback_field.remote_field.on_delete,
            models.PROTECT,
        )
        self.assertTrue(rollback_field.null)
        self.assertTrue(rollback_field.blank)
        self.assertEqual(
            rollback_field.remote_field.related_name,
            "rollback_events",
        )

    def test_v229_field_lengths_and_required_options(self):
        model = SavedSearchNotificationAuditEvent

        expected_lengths = {
            "owner_id_snapshot": 64,
            "event_type": 64,
            "outcome": 32,
            "reason_code": 96,
            "idempotency_key": 128,
            "notification_fingerprint": 64,
            "actor_type": 32,
            "actor_identifier": 128,
            "source": 128,
        }

        for field_name, max_length in expected_lengths.items():
            with self.subTest(field_name=field_name):
                self.assertEqual(
                    model._meta.get_field(
                        field_name
                    ).max_length,
                    max_length,
                )

        self.assertTrue(
            model._meta.get_field(
                "idempotency_key"
            ).unique
        )

        self.assertTrue(
            model._meta.get_field("metadata").blank
        )

        self.assertIs(
            model._meta.get_field("metadata").default,
            dict,
        )

    def test_v229_event_outcome_and_actor_choices_are_stable(self):
        model = SavedSearchNotificationAuditEvent

        self.assertEqual(
            tuple(model.EventType.values),
            EXPECTED_EVENT_TYPES,
        )

        self.assertEqual(
            tuple(model.Outcome.values),
            EXPECTED_OUTCOMES,
        )

        self.assertEqual(
            tuple(model.ActorType.values),
            EXPECTED_ACTOR_TYPES,
        )

    def test_v229_model_meta_indexes_and_constraints_are_exact(self):
        model = SavedSearchNotificationAuditEvent

        self.assertEqual(
            model._meta.db_table,
            "listings_savedsearchnotificationauditevent",
        )

        self.assertEqual(
            model._meta.ordering,
            (
                "-occurred_at",
                "-created_at",
            ),
        )

        self.assertEqual(
            model._meta.get_latest_by,
            "occurred_at",
        )

        actual_indexes = {
            index.name: tuple(index.fields)
            for index in model._meta.indexes
        }

        self.assertEqual(
            actual_indexes,
            EXPECTED_INDEXES,
        )

        actual_constraints = {
            constraint.name
            for constraint in model._meta.constraints
        }

        self.assertEqual(
            actual_constraints,
            EXPECTED_CONSTRAINTS,
        )

    def test_v229_initial_event_create_succeeds(self):
        event = self._create_event()

        self.assertIsNotNone(event.pk)
        self.assertEqual(
            event.saved_search,
            self.saved_search,
        )
        self.assertEqual(
            event.owner_id_snapshot,
            str(self.user.pk),
        )
        self.assertEqual(
            event.metadata,
            {"checkpoint": "v229"},
        )

    def test_v229_instance_save_rejects_update(self):
        event = self._create_event()
        event.reason_code = "changed"

        with self.assertRaises(ValidationError):
            event.save(
                update_fields=["reason_code"],
            )

        event.refresh_from_db()

        self.assertEqual(
            event.reason_code,
            "",
        )

    def test_v229_instance_and_queryset_delete_are_rejected(self):
        event = self._create_event()

        with self.assertRaises(ValidationError):
            event.delete()

        with self.assertRaises(ValidationError):
            (
                SavedSearchNotificationAuditEvent
                .objects
                .filter(pk=event.pk)
                .delete()
            )

        self.assertTrue(
            SavedSearchNotificationAuditEvent.objects.filter(
                pk=event.pk
            ).exists()
        )

    def test_v229_queryset_update_and_bulk_update_are_rejected(self):
        event = self._create_event()

        with self.assertRaises(ValidationError):
            (
                SavedSearchNotificationAuditEvent
                .objects
                .filter(pk=event.pk)
                .update(reason_code="changed")
            )

        event.reason_code = "bulk-changed"

        with self.assertRaises(ValidationError):
            (
                SavedSearchNotificationAuditEvent
                .objects
                .bulk_update(
                    [event],
                    ["reason_code"],
                )
            )

        event.refresh_from_db()

        self.assertEqual(event.reason_code, "")

    def test_v229_manager_uses_append_only_queryset(self):
        queryset = (
            SavedSearchNotificationAuditEvent
            .objects
            .all()
        )

        self.assertIsInstance(
            queryset,
            SavedSearchNotificationAuditEventQuerySet,
        )

    def test_v229_saved_search_is_protected_after_audit_event(self):
        self._create_event()

        with self.assertRaises(ProtectedError):
            self.saved_search.delete()

        self.assertTrue(
            SavedSearch.objects.filter(
                pk=self.saved_search.pk
            ).exists()
        )

    def test_v229_idempotency_key_is_database_unique(self):
        idempotency_key = f"v229:{uuid.uuid4()}"

        self._create_event(
            idempotency_key=idempotency_key,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._create_event(
                    idempotency_key=idempotency_key,
                )

    def test_v229_rollback_events_require_rollback_link(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._create_event(
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
                )

    def test_v229_delivery_events_require_attempt_identifier(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._create_event(
                    event_type=(
                        SavedSearchNotificationAuditEvent
                        .EventType
                        .DELIVERY_ATTEMPTED
                    ),
                )

    def test_v229_valid_rollback_event_can_be_created(self):
        original = self._create_event()

        rollback = self._create_event(
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
            rollback.rollback_of,
            original,
        )

    def test_v229_model_choices_validate_with_full_clean(self):
        event = SavedSearchNotificationAuditEvent(
            **self._event_kwargs(
                event_type="invalid-event",
                outcome="invalid-outcome",
                actor_type="invalid-actor",
            )
        )

        with self.assertRaises(ValidationError) as context:
            event.full_clean()

        self.assertTrue(
            {
                "event_type",
                "outcome",
                "actor_type",
            }.issubset(
                context.exception.message_dict
            )
        )

    def test_v229_creating_event_does_not_mutate_saved_search_timestamps(self):
        checked_before = (
            self.saved_search
            .last_notification_checked_at
        )
        sent_before = (
            self.saved_search
            .last_notification_sent_at
        )

        self._create_event(
            checked_at_before=checked_before,
            sent_at_before=sent_before,
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

    def test_v229_model_is_not_registered_in_editable_admin(self):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

    def test_v229_persistence_write_service_is_still_deferred(self):
        persistence_module = (
            self._backend_root()
            / "listings"
            / (
                "saved_search_notification_"
                "audit_persistence.py"
            )
        )

        v230_test_path = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_audit_"
                "persistence_write_service_v230.py"
            )
        )

        if v230_test_path.exists():
            self.assertTrue(
                persistence_module.is_file(),
            )
        else:
            self.assertFalse(
                persistence_module.exists(),
            )

    def test_v229_migration_contract_is_exact(self):
        loader = MigrationLoader(
            connection,
            ignore_no_migrations=True,
        )

        migration = loader.disk_migrations[
            (
                "listings",
                EXPECTED_MIGRATION,
            )
        ]

        self.assertEqual(
            migration.dependencies,
            [
                (
                    "listings",
                    "0015_savedsearch_notifications",
                )
            ],
        )

        self.assertEqual(
            len(migration.operations),
            1,
        )

        operation = migration.operations[0]

        self.assertIsInstance(
            operation,
            CreateModel,
        )

        self.assertEqual(
            operation.name,
            "SavedSearchNotificationAuditEvent",
        )

        self.assertEqual(
            operation.options["db_table"],
            "listings_savedsearchnotificationauditevent",
        )

        self.assertEqual(
            {
                index.name
                for index in operation.options["indexes"]
            },
            set(EXPECTED_INDEXES),
        )

        self.assertEqual(
            {
                constraint.name
                for constraint
                in operation.options["constraints"]
            },
            EXPECTED_CONSTRAINTS,
        )

    def test_v229_v228_contract_transition_guard_remains_packaged(self):
        source = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_audit_"
                "persistence_implementation_contract_v228.py"
            )
        ).read_text(
            encoding="utf-8",
            errors="ignore",
        )

        self.assertIn(
            "persistence_model_migration_v229.py",
            source,
        )

        self.assertIn(
            "self.assertIn(",
            source,
        )

    def test_v229_next_lane_is_append_only_write_service(self):
        next_lane = "v230: saved-search notification audit append-only write service implementation"

        self.assertEqual(
            next_lane,
            (
                "v230: saved-search notification audit "
                "append-only write service implementation"
            ),
        )
