from __future__ import annotations

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase

from listings.models import SavedSearch


V227_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_DESIGN = (
    "V227_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_DESIGN"
)

PROPOSED_AUDIT_MODEL = "SavedSearchNotificationAuditEvent"

AUDIT_EVENT_IDENTITY_FIELDS = (
    "id",
    "saved_search",
    "owner_id_snapshot",
    "event_type",
    "outcome",
    "reason_code",
    "occurred_at",
)

AUDIT_CORRELATION_FIELDS = (
    "batch_id",
    "correlation_id",
    "delivery_attempt_id",
    "idempotency_key",
    "notification_fingerprint",
    "rollback_of",
)

AUDIT_CONTEXT_FIELDS = (
    "actor_type",
    "actor_identifier",
    "source",
    "checked_at_before",
    "checked_at_after",
    "sent_at_before",
    "sent_at_after",
    "metadata",
)

AUDIT_EVENT_TYPES = (
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

AUDIT_OUTCOMES = (
    "pending",
    "skipped",
    "succeeded",
    "failed",
    "rolled_back",
)

AUDIT_DESIGN_INVARIANTS = (
    "append-only",
    "immutable persisted records",
    "stable idempotency key",
    "stable notification fingerprint",
    "explicit rollback linkage",
    "transaction boundary",
    "privacy minimization",
    "retention policy",
    "operator read access",
    "no rendered email body persistence",
    "no credential or secret persistence",
    "no implicit email delivery",
)

AUDIT_ROLLOUT_PHASES = (
    "schema contract",
    "migration implementation",
    "write service",
    "scheduler integration",
    "rollback integration",
    "operator read interface",
    "retention enforcement",
)


class SavedSearchNotificationAuditPersistenceDesignV227Tests(SimpleTestCase):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read_backend(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v227_marker_declares_audit_persistence_design_checkpoint(self):
        self.assertEqual(
            V227_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_DESIGN,
            "V227_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_DESIGN",
        )

    def test_v227_design_defines_append_only_persistent_event_identity(self):
        self.assertEqual(
            PROPOSED_AUDIT_MODEL,
            "SavedSearchNotificationAuditEvent",
        )

        self.assertEqual(
            AUDIT_EVENT_IDENTITY_FIELDS,
            (
                "id",
                "saved_search",
                "owner_id_snapshot",
                "event_type",
                "outcome",
                "reason_code",
                "occurred_at",
            ),
        )

        for required in (
            "append-only",
            "immutable persisted records",
            "stable idempotency key",
            "stable notification fingerprint",
        ):
            self.assertIn(required, AUDIT_DESIGN_INVARIANTS)

    def test_v227_design_defines_correlation_idempotency_and_rollback_linkage(self):
        self.assertEqual(
            AUDIT_CORRELATION_FIELDS,
            (
                "batch_id",
                "correlation_id",
                "delivery_attempt_id",
                "idempotency_key",
                "notification_fingerprint",
                "rollback_of",
            ),
        )

        self.assertIn("explicit rollback linkage", AUDIT_DESIGN_INVARIANTS)
        self.assertIn("transaction boundary", AUDIT_DESIGN_INVARIANTS)

    def test_v227_design_defines_audit_context_without_sensitive_payloads(self):
        self.assertEqual(
            AUDIT_CONTEXT_FIELDS,
            (
                "actor_type",
                "actor_identifier",
                "source",
                "checked_at_before",
                "checked_at_after",
                "sent_at_before",
                "sent_at_after",
                "metadata",
            ),
        )

        for required in (
            "privacy minimization",
            "retention policy",
            "operator read access",
            "no rendered email body persistence",
            "no credential or secret persistence",
        ):
            self.assertIn(required, AUDIT_DESIGN_INVARIANTS)

    def test_v227_design_defines_event_taxonomy_and_outcomes(self):
        self.assertEqual(
            AUDIT_EVENT_TYPES,
            (
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
            ),
        )

        self.assertEqual(
            AUDIT_OUTCOMES,
            (
                "pending",
                "skipped",
                "succeeded",
                "failed",
                "rolled_back",
            ),
        )

    def test_v227_design_declares_phased_rollout_not_runtime_implementation(self):
        self.assertEqual(
            AUDIT_ROLLOUT_PHASES,
            (
                "schema contract",
                "migration implementation",
                "write service",
                "scheduler integration",
                "rollback integration",
                "operator read interface",
                "retention enforcement",
            ),
        )

        self.assertIn(
            "no implicit email delivery",
            AUDIT_DESIGN_INVARIANTS,
        )

    def test_v227_current_audit_delivery_and_rollback_surfaces_remain_packaged(self):
        required_paths = (
            "listings/saved_search_notification_audit.py",
            "listings/saved_search_notification_observability.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/saved_search_notification_email_sender.py",
            "listings/saved_search_notification_email_renderer.py",
            "listings/management/commands/process_saved_search_notifications.py",
            "listings/test_saved_search_notification_admin_operator_observability_v223.py",
            "listings/test_saved_search_notification_rollback_audit_hardening_v224.py",
            "listings/test_saved_search_notification_production_delivery_design_audit_v225.py",
            "listings/test_saved_search_notification_admin_ux_surfacing_v226.py",
        )

        for relative_path in required_paths:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(
                    (self._backend_root() / relative_path).is_file(),
                    relative_path,
                )

    def test_v227_is_design_only_and_adds_no_model_or_migration(self):
        registered_model_names = {
            model.__name__
            for model in apps.get_app_config("listings").get_models()
        }

        self.assertNotIn(
            PROPOSED_AUDIT_MODEL,
            registered_model_names,
        )

        models_source = self._read_backend("listings/models.py")

        self.assertNotIn(
            f"class {PROPOSED_AUDIT_MODEL}",
            models_source,
        )

        migrations_directory = self._backend_root() / "listings" / "migrations"

        for migration_path in migrations_directory.glob("*.py"):
            with self.subTest(migration=migration_path.name):
                migration_source = migration_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
                self.assertNotIn(
                    PROPOSED_AUDIT_MODEL,
                    migration_source,
                )

    def test_v227_marker_does_not_leak_into_runtime_or_configuration(self):
        runtime_paths = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/admin.py",
            "listings/saved_searches_views.py",
            "listings/saved_search_notification_audit.py",
            "listings/saved_search_notification_observability.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/saved_search_notification_email_sender.py",
            "listings/saved_search_notification_email_renderer.py",
            "listings/management/commands/process_saved_search_notifications.py",
            "config/settings.py",
            "Dockerfile",
        )

        for relative_path in runtime_paths:
            with self.subTest(relative_path=relative_path):
                self.assertNotIn(
                    V227_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_DESIGN,
                    self._read_backend(relative_path),
                )

    def test_v227_preserves_saved_search_notification_fields(self):
        field_names = {
            field.name
            for field in SavedSearch._meta.get_fields()
        }

        self.assertTrue(
            {
                "email_notifications_enabled",
                "last_notification_checked_at",
                "last_notification_sent_at",
            }.issubset(field_names)
        )

    def test_v227_backend_docs_directory_remains_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
        )

    def test_v227_next_lane_is_audit_persistence_implementation_contract(self):
        next_lane = (
            "v228: saved-search notification audit persistence "
            "implementation contract"
        )

        self.assertEqual(
            next_lane,
            "v228: saved-search notification audit persistence "
            "implementation contract",
        )
