from __future__ import annotations

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase

from listings.models import SavedSearch


V228_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_IMPLEMENTATION_CONTRACT = (
    "V228_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_IMPLEMENTATION_CONTRACT"
)

PROPOSED_MODEL = "SavedSearchNotificationAuditEvent"

EXPECTED_MIGRATION = (
    "listings/migrations/"
    "0016_savedsearchnotificationauditevent.py"
)

EXPECTED_MIGRATION_DEPENDENCY = (
    "listings",
    "0015_savedsearch_notifications",
)

EXPECTED_PERSISTENCE_MODULE = (
    "listings/saved_search_notification_audit_persistence.py"
)

EXPECTED_WRITE_FUNCTION = (
    "record_saved_search_notification_audit_event"
)

EXPECTED_RESULT_TYPE = "SavedSearchNotificationAuditWriteResult"

EXPECTED_IDEMPOTENCY_CONFLICT = (
    "SavedSearchNotificationAuditIdempotencyConflict"
)

MODEL_FIELD_CONTRACT = (
    (
        "id",
        "UUIDField",
        "primary_key=True, default=uuid.uuid4, editable=False",
    ),
    (
        "saved_search",
        "ForeignKey",
        (
            "SavedSearch, on_delete=PROTECT, "
            "related_name='notification_audit_events'"
        ),
    ),
    (
        "owner_id_snapshot",
        "CharField",
        "max_length=64",
    ),
    (
        "event_type",
        "CharField",
        "max_length=64, choices=EventType.choices",
    ),
    (
        "outcome",
        "CharField",
        "max_length=32, choices=Outcome.choices",
    ),
    (
        "reason_code",
        "CharField",
        "max_length=96, blank=True",
    ),
    (
        "occurred_at",
        "DateTimeField",
        "required, application supplied",
    ),
    (
        "created_at",
        "DateTimeField",
        "auto_now_add=True",
    ),
    (
        "batch_id",
        "UUIDField",
        "null=True, blank=True",
    ),
    (
        "correlation_id",
        "UUIDField",
        "required",
    ),
    (
        "delivery_attempt_id",
        "UUIDField",
        "null=True, blank=True",
    ),
    (
        "idempotency_key",
        "CharField",
        "max_length=128, unique=True",
    ),
    (
        "notification_fingerprint",
        "CharField",
        "max_length=64",
    ),
    (
        "rollback_of",
        "ForeignKey",
        (
            "'self', null=True, blank=True, on_delete=PROTECT, "
            "related_name='rollback_events'"
        ),
    ),
    (
        "actor_type",
        "CharField",
        "max_length=32, choices=ActorType.choices",
    ),
    (
        "actor_identifier",
        "CharField",
        "max_length=128, blank=True",
    ),
    (
        "source",
        "CharField",
        "max_length=128",
    ),
    (
        "checked_at_before",
        "DateTimeField",
        "null=True, blank=True",
    ),
    (
        "checked_at_after",
        "DateTimeField",
        "null=True, blank=True",
    ),
    (
        "sent_at_before",
        "DateTimeField",
        "null=True, blank=True",
    ),
    (
        "sent_at_after",
        "DateTimeField",
        "null=True, blank=True",
    ),
    (
        "metadata",
        "JSONField",
        "default=dict, blank=True",
    ),
)

EVENT_TYPE_VALUES = (
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

OUTCOME_VALUES = (
    "pending",
    "skipped",
    "succeeded",
    "failed",
    "rolled_back",
)

ACTOR_TYPE_VALUES = (
    "system",
    "scheduler",
    "operator",
    "management_command",
    "test_backend",
)

INDEX_CONTRACT = (
    (
        "ssna_saved_occ_idx",
        ("saved_search", "occurred_at"),
    ),
    (
        "ssna_event_occ_idx",
        ("event_type", "occurred_at"),
    ),
    (
        "ssna_outcome_occ_idx",
        ("outcome", "occurred_at"),
    ),
    (
        "ssna_batch_idx",
        ("batch_id",),
    ),
    (
        "ssna_corr_idx",
        ("correlation_id",),
    ),
    (
        "ssna_attempt_idx",
        ("delivery_attempt_id",),
    ),
    (
        "ssna_fingerprint_idx",
        ("notification_fingerprint",),
    ),
    (
        "ssna_rollback_idx",
        ("rollback_of",),
    ),
)

CHECK_CONSTRAINT_CONTRACT = (
    (
        "ssna_rollback_link_required",
        (
            "rollback_previewed and rollback_applied events "
            "require rollback_of"
        ),
    ),
    (
        "ssna_delivery_attempt_required",
        (
            "delivery_attempted, delivery_succeeded, and "
            "delivery_failed require delivery_attempt_id"
        ),
    ),
)

MODEL_META_CONTRACT = (
    (
        "db_table",
        "listings_savedsearchnotificationauditevent",
    ),
    (
        "ordering",
        ("-occurred_at", "-created_at"),
    ),
    (
        "get_latest_by",
        "occurred_at",
    ),
)

APPEND_ONLY_CONTRACT = (
    "model save rejects updates after insertion",
    "model delete rejects deletion",
    "queryset update rejects mutation",
    "queryset delete rejects deletion",
    "bulk_update is unavailable",
    "normal admin registration is absent",
    "existing event rows are never rewritten",
    "corrections create compensating events",
)

WRITE_SERVICE_CONTRACT = (
    "validate event taxonomy",
    "validate normalized outcome",
    "validate actor type",
    "validate required correlation identifier",
    "validate rollback linkage",
    "validate delivery attempt linkage",
    "validate metadata allow-list",
    "reject sensitive metadata",
    "use transaction.atomic",
    "get or create by idempotency key",
    "return created false for identical replay",
    "raise idempotency conflict for mismatched replay",
    "never deliver email",
    "never mutate SavedSearch notification timestamps",
)

METADATA_DENYLIST = (
    "password",
    "secret",
    "api_key",
    "authorization",
    "cookie",
    "session",
    "token",
    "smtp_password",
    "email_body",
    "html_body",
    "plain_text_body",
    "traceback",
)

IMPLEMENTATION_ACCEPTANCE_GATES = (
    "migration depends on listings 0015",
    "model is registered in listings app",
    "migration creates exactly one new model",
    "migration has no data migration",
    "idempotency key is unique",
    "all planned indexes are present",
    "append-only model guards are present",
    "write service is explicit and isolated",
    "write service is replay safe",
    "write service performs no delivery",
    "write service performs no SavedSearch timestamp mutation",
    "existing v223 through v228 guards remain green",
    "full regression remains green",
)


class SavedSearchNotificationAuditPersistenceImplementationContractV228Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read_backend(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v228_marker_declares_implementation_contract(self):
        self.assertEqual(
            V228_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_IMPLEMENTATION_CONTRACT,
            (
                "V228_SAVED_SEARCH_NOTIFICATION_AUDIT_"
                "PERSISTENCE_IMPLEMENTATION_CONTRACT"
            ),
        )

    def test_v228_contract_names_exact_model_migration_and_module(self):
        self.assertEqual(
            PROPOSED_MODEL,
            "SavedSearchNotificationAuditEvent",
        )
        self.assertEqual(
            EXPECTED_MIGRATION,
            (
                "listings/migrations/"
                "0016_savedsearchnotificationauditevent.py"
            ),
        )
        self.assertEqual(
            EXPECTED_MIGRATION_DEPENDENCY,
            (
                "listings",
                "0015_savedsearch_notifications",
            ),
        )
        self.assertEqual(
            EXPECTED_PERSISTENCE_MODULE,
            (
                "listings/"
                "saved_search_notification_audit_persistence.py"
            ),
        )
        self.assertEqual(
            EXPECTED_WRITE_FUNCTION,
            "record_saved_search_notification_audit_event",
        )

    def test_v228_contract_defines_exact_model_fields(self):
        expected_names = (
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

        self.assertEqual(
            tuple(field[0] for field in MODEL_FIELD_CONTRACT),
            expected_names,
        )
        self.assertEqual(
            len(MODEL_FIELD_CONTRACT),
            22,
        )

    def test_v228_contract_defines_stable_choices(self):
        self.assertEqual(
            EVENT_TYPE_VALUES,
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
            OUTCOME_VALUES,
            (
                "pending",
                "skipped",
                "succeeded",
                "failed",
                "rolled_back",
            ),
        )
        self.assertEqual(
            ACTOR_TYPE_VALUES,
            (
                "system",
                "scheduler",
                "operator",
                "management_command",
                "test_backend",
            ),
        )

    def test_v228_contract_defines_indexes_and_constraints(self):
        self.assertEqual(
            len(INDEX_CONTRACT),
            8,
        )

        index_names = tuple(index[0] for index in INDEX_CONTRACT)

        self.assertEqual(
            len(index_names),
            len(set(index_names)),
        )

        for index_name in index_names:
            with self.subTest(index_name=index_name):
                self.assertLessEqual(
                    len(index_name),
                    30,
                )

        self.assertEqual(
            tuple(item[0] for item in CHECK_CONSTRAINT_CONTRACT),
            (
                "ssna_rollback_link_required",
                "ssna_delivery_attempt_required",
            ),
        )

    def test_v228_contract_defines_model_meta(self):
        self.assertEqual(
            MODEL_META_CONTRACT,
            (
                (
                    "db_table",
                    "listings_savedsearchnotificationauditevent",
                ),
                (
                    "ordering",
                    ("-occurred_at", "-created_at"),
                ),
                (
                    "get_latest_by",
                    "occurred_at",
                ),
            ),
        )

    def test_v228_contract_requires_append_only_guards(self):
        self.assertEqual(
            APPEND_ONLY_CONTRACT,
            (
                "model save rejects updates after insertion",
                "model delete rejects deletion",
                "queryset update rejects mutation",
                "queryset delete rejects deletion",
                "bulk_update is unavailable",
                "normal admin registration is absent",
                "existing event rows are never rewritten",
                "corrections create compensating events",
            ),
        )

    def test_v228_contract_requires_replay_safe_write_service(self):
        for required in (
            "use transaction.atomic",
            "get or create by idempotency key",
            "return created false for identical replay",
            "raise idempotency conflict for mismatched replay",
            "never deliver email",
            "never mutate SavedSearch notification timestamps",
        ):
            self.assertIn(
                required,
                WRITE_SERVICE_CONTRACT,
            )

        self.assertEqual(
            EXPECTED_RESULT_TYPE,
            "SavedSearchNotificationAuditWriteResult",
        )
        self.assertEqual(
            EXPECTED_IDEMPOTENCY_CONFLICT,
            "SavedSearchNotificationAuditIdempotencyConflict",
        )

    def test_v228_contract_rejects_sensitive_metadata(self):
        for sensitive_name in (
            "password",
            "secret",
            "api_key",
            "authorization",
            "token",
            "smtp_password",
            "email_body",
            "html_body",
            "traceback",
        ):
            self.assertIn(
                sensitive_name,
                METADATA_DENYLIST,
            )

        self.assertIn(
            "reject sensitive metadata",
            WRITE_SERVICE_CONTRACT,
        )

    def test_v228_contract_defines_implementation_acceptance_gates(self):
        for required in (
            "migration depends on listings 0015",
            "migration creates exactly one new model",
            "migration has no data migration",
            "idempotency key is unique",
            "all planned indexes are present",
            "append-only model guards are present",
            "write service is replay safe",
            "write service performs no delivery",
            (
                "write service performs no SavedSearch "
                "timestamp mutation"
            ),
            "full regression remains green",
        ):
            self.assertIn(
                required,
                IMPLEMENTATION_ACCEPTANCE_GATES,
            )

    def test_v228_is_contract_only_and_has_no_implementation_yet(self):
        registered_models = {
            model.__name__
            for model in apps.get_app_config("listings").get_models()
        }

        v229_test_path = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_audit_"
                "persistence_model_migration_v229.py"
            )
        )

        migration_path = (
            self._backend_root()
            / EXPECTED_MIGRATION
        )

        persistence_module = (
            self._backend_root()
            / EXPECTED_PERSISTENCE_MODULE
        )

        if v229_test_path.exists():
            self.assertIn(
                PROPOSED_MODEL,
                registered_models,
            )
            self.assertTrue(
                migration_path.is_file(),
            )
        else:
            self.assertNotIn(
                PROPOSED_MODEL,
                registered_models,
            )
            self.assertFalse(
                migration_path.exists(),
            )

        self.assertFalse(
            persistence_module.exists(),
        )

    def test_v228_preserves_v227_design_and_existing_runtime_surfaces(self):
        required_paths = (
            (
                "listings/"
                "test_saved_search_notification_"
                "audit_persistence_design_v227.py"
            ),
            "listings/saved_search_notification_audit.py",
            "listings/saved_search_notification_observability.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/saved_search_notification_email_sender.py",
            "listings/saved_search_notification_email_renderer.py",
            (
                "listings/management/commands/"
                "process_saved_search_notifications.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_"
                "admin_operator_observability_v223.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_"
                "rollback_audit_hardening_v224.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_"
                "production_delivery_design_audit_v225.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_"
                "admin_ux_surfacing_v226.py"
            ),
        )

        for relative_path in required_paths:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file(),
                    relative_path,
                )

    def test_v228_preserves_saved_search_notification_fields(self):
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

    def test_v228_marker_does_not_leak_into_runtime_or_configuration(self):
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
            (
                "listings/management/commands/"
                "process_saved_search_notifications.py"
            ),
            "config/settings.py",
            "Dockerfile",
        )

        marker = (
            V228_SAVED_SEARCH_NOTIFICATION_AUDIT_PERSISTENCE_IMPLEMENTATION_CONTRACT
        )

        for relative_path in runtime_paths:
            with self.subTest(relative_path=relative_path):
                self.assertNotIn(
                    marker,
                    self._read_backend(relative_path),
                )

    def test_v228_backend_docs_directory_remains_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
        )

    def test_v228_next_lane_is_model_and_migration_implementation(self):
        next_lane = (
            "v229: saved-search notification audit persistence "
            "model and migration implementation"
        )

        self.assertEqual(
            next_lane,
            (
                "v229: saved-search notification audit persistence "
                "model and migration implementation"
            ),
        )

# v229: saved-search notification audit persistence model and migration implementation
