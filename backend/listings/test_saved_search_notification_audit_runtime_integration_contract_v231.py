from __future__ import annotations

from pathlib import Path

from django.contrib import admin
from django.test import SimpleTestCase

from listings.models import SavedSearchNotificationAuditEvent
from listings.saved_search_notification_audit_persistence import (
    SavedSearchNotificationAuditIdempotencyConflict,
    SavedSearchNotificationAuditWriteResult,
    record_saved_search_notification_audit_event,
)


V231_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION_CONTRACT = (
    "V231_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION_CONTRACT"
)

PROPOSED_RUNTIME_ADAPTER = (
    "listings/saved_search_notification_audit_runtime.py"
)

PROPOSED_RUNTIME_CONTEXT = (
    "SavedSearchNotificationAuditRuntimeContext"
)

PROPOSED_RECORD_FUNCTION = (
    "record_saved_search_notification_runtime_event"
)

PROPOSED_IDEMPOTENCY_FUNCTION = (
    "build_saved_search_notification_audit_idempotency_key"
)

PROPOSED_FINGERPRINT_FUNCTION = (
    "build_saved_search_notification_fingerprint"
)

RUNTIME_INTEGRATION_TARGETS = (
    "listings/saved_search_notification_scheduler.py",
    "listings/saved_search_notification_email_renderer.py",
    "listings/saved_search_notification_email_sender.py",
    "listings/saved_search_notification_audit.py",
    (
        "listings/management/commands/"
        "process_saved_search_notifications.py"
    ),
)

EVENT_INTEGRATION_CONTRACT = {
    "evaluation_started": {
        "outcome": "pending",
        "surface": (
            "listings/saved_search_notification_scheduler.py"
        ),
        "trigger": (
            "immediately before evaluating one persisted saved search"
        ),
        "requires": (
            "correlation_id",
            "notification_fingerprint",
            "checked_at_before",
        ),
    },
    "skipped_notifications_disabled": {
        "outcome": "skipped",
        "surface": (
            "listings/saved_search_notification_scheduler.py"
        ),
        "trigger": (
            "an explicitly selected saved search is disabled"
        ),
        "requires": (
            "correlation_id",
            "notification_fingerprint",
            "reason_code",
        ),
    },
    "skipped_missing_recipient": {
        "outcome": "skipped",
        "surface": (
            "listings/saved_search_notification_email_sender.py"
        ),
        "trigger": (
            "delivery is requested but no usable recipient exists"
        ),
        "requires": (
            "correlation_id",
            "notification_fingerprint",
            "reason_code",
        ),
    },
    "dry_run_rendered": {
        "outcome": "succeeded",
        "surface": (
            "listings/saved_search_notification_email_renderer.py"
        ),
        "trigger": (
            "an explicit preview or dry-run render completes"
        ),
        "requires": (
            "correlation_id",
            "notification_fingerprint",
            "metadata.match_count",
            "metadata.rendered_item_count",
        ),
    },
    "delivery_attempted": {
        "outcome": "pending",
        "surface": (
            "listings/saved_search_notification_email_sender.py"
        ),
        "trigger": (
            "immediately before invoking the email backend"
        ),
        "requires": (
            "correlation_id",
            "delivery_attempt_id",
            "notification_fingerprint",
        ),
    },
    "delivery_succeeded": {
        "outcome": "succeeded",
        "surface": (
            "listings/saved_search_notification_email_sender.py"
        ),
        "trigger": (
            "the email backend reports a successful delivery"
        ),
        "requires": (
            "correlation_id",
            "delivery_attempt_id",
            "notification_fingerprint",
        ),
    },
    "delivery_failed": {
        "outcome": "failed",
        "surface": (
            "listings/saved_search_notification_email_sender.py"
        ),
        "trigger": (
            "the email backend raises or reports failure"
        ),
        "requires": (
            "correlation_id",
            "delivery_attempt_id",
            "notification_fingerprint",
            "reason_code",
        ),
    },
    "sent_timestamp_recorded": {
        "outcome": "succeeded",
        "surface": (
            "listings/management/commands/"
            "process_saved_search_notifications.py"
        ),
        "trigger": (
            "last_notification_sent_at is persisted after delivery"
        ),
        "requires": (
            "correlation_id",
            "delivery_attempt_id",
            "notification_fingerprint",
            "sent_at_before",
            "sent_at_after",
        ),
    },
    "rollback_previewed": {
        "outcome": "succeeded",
        "surface": (
            "listings/saved_search_notification_audit.py"
        ),
        "trigger": (
            "an explicit rollback preview is generated"
        ),
        "requires": (
            "correlation_id",
            "notification_fingerprint",
            "rollback_of",
        ),
    },
    "rollback_applied": {
        "outcome": "rolled_back",
        "surface": (
            "listings/saved_search_notification_audit.py"
        ),
        "trigger": (
            "an explicit rollback restores a sent timestamp"
        ),
        "requires": (
            "correlation_id",
            "notification_fingerprint",
            "rollback_of",
            "sent_at_before",
            "sent_at_after",
        ),
    },
}

EVENT_ORDERING_CONTRACT = (
    (
        "evaluation_started",
        "dry_run_rendered",
    ),
    (
        "evaluation_started",
        "delivery_attempted",
    ),
    (
        "delivery_attempted",
        "delivery_succeeded",
    ),
    (
        "delivery_attempted",
        "delivery_failed",
    ),
    (
        "delivery_succeeded",
        "sent_timestamp_recorded",
    ),
    (
        "rollback_previewed",
        "rollback_applied",
    ),
)

RUNTIME_CONTEXT_CONTRACT = {
    "correlation_id": (
        "one UUID per command invocation or explicit single-search run"
    ),
    "batch_id": (
        "one optional UUID shared by all searches in one batch"
    ),
    "delivery_attempt_id": (
        "one new UUID created before each backend send attempt"
    ),
    "actor_type": (
        "scheduler, management_command, operator, test_backend, or system"
    ),
    "actor_identifier": (
        "non-secret operator, command, scheduler, or backend identifier"
    ),
    "source": (
        "stable dotted runtime surface identifier"
    ),
}

IDEMPOTENCY_KEY_CONTRACT = {
    "prefix": "ssna:v1:",
    "algorithm": "sha256",
    "canonical_json": {
        "sort_keys": True,
        "separators": (",", ":"),
        "allow_nan": False,
    },
    "identity_fields": (
        "saved_search_id",
        "event_type",
        "correlation_id",
        "batch_id",
        "delivery_attempt_id",
        "rollback_of_id",
        "operation_sequence",
    ),
    "maximum_length": 128,
    "identical_replay": "created=False",
    "conflicting_replay": (
        "SavedSearchNotificationAuditIdempotencyConflict"
    ),
}

NOTIFICATION_FINGERPRINT_CONTRACT = {
    "algorithm": "sha256",
    "canonical_fields": (
        "saved_search_id",
        "saved_search_path",
        "saved_search_querystring",
        "checked_at_before",
        "ordered_matching_listing_ids",
    ),
    "empty_match_policy": (
        "use an empty ordered_matching_listing_ids sequence"
    ),
    "delivery_chain_policy": (
        "reuse one fingerprint across render, attempt, result, "
        "and sent-timestamp events"
    ),
    "rollback_policy": (
        "inherit the original sent_timestamp_recorded fingerprint"
    ),
}

METADATA_ALLOWLIST_CONTRACT = {
    "evaluation_started": (
        "mode",
        "owner_scope",
        "batch_position",
    ),
    "skipped_notifications_disabled": (
        "mode",
        "skip_reason",
    ),
    "skipped_missing_recipient": (
        "mode",
        "skip_reason",
    ),
    "dry_run_rendered": (
        "mode",
        "match_count",
        "rendered_item_count",
    ),
    "delivery_attempted": (
        "mode",
        "match_count",
        "backend_kind",
    ),
    "delivery_succeeded": (
        "mode",
        "match_count",
        "backend_kind",
    ),
    "delivery_failed": (
        "mode",
        "match_count",
        "backend_kind",
        "error_code",
    ),
    "sent_timestamp_recorded": (
        "mode",
        "timestamp_changed",
    ),
    "rollback_previewed": (
        "mode",
        "preview_count",
    ),
    "rollback_applied": (
        "mode",
        "timestamp_changed",
    ),
}

METADATA_FORBIDDEN_PAYLOADS = (
    "recipient email address",
    "email subject",
    "rendered email body",
    "rendered html",
    "rendered text",
    "listing titles",
    "listing descriptions",
    "private listing URLs",
    "exception message",
    "traceback",
    "stack trace",
    "credentials",
    "cookies",
    "sessions",
    "tokens",
)

TRANSACTION_BOUNDARY_CONTRACT = {
    "delivery_attempted": (
        "must commit before the email backend is invoked"
    ),
    "sent_timestamp_recorded": (
        "must be written in the same database transaction as "
        "last_notification_sent_at"
    ),
    "rollback_applied": (
        "must be written in the same database transaction as "
        "the restored sent timestamp"
    ),
    "evaluation_events": (
        "must not mutate saved-search notification timestamps"
    ),
}

FAILURE_SEMANTICS_CONTRACT = {
    "pre_delivery_audit_failure": (
        "abort delivery and propagate the audit error"
    ),
    "delivery_backend_failure": (
        "persist delivery_failed and do not update sent timestamp"
    ),
    "post_delivery_audit_failure": (
        "surface an indeterminate delivery state, retain attempt id, "
        "and do not automatically retry"
    ),
    "timestamp_audit_failure": (
        "roll back the sent-timestamp database mutation"
    ),
    "rollback_audit_failure": (
        "roll back the restored-timestamp database mutation"
    ),
    "conflict": (
        "propagate SavedSearchNotificationAuditIdempotencyConflict"
    ),
    "swallowing": (
        "audit persistence exceptions must never be silently ignored"
    ),
}

ROLLBACK_LINK_CONTRACT = {
    "rollback_target_event": "sent_timestamp_recorded",
    "same_saved_search": True,
    "preview_is_read_only": True,
    "apply_requires_explicit_execute": True,
    "apply_outcome": "rolled_back",
}

IMPLEMENTATION_ACCEPTANCE_GATES = (
    "runtime adapter is the only new persistence-facing integration API",
    "runtime modules do not call the model manager directly",
    "runtime modules do not construct audit model instances directly",
    "delivery_attempted is durable before email backend invocation",
    "delivery failures never update last_notification_sent_at",
    (
        "sent timestamp mutation and sent_timestamp_recorded "
        "event are atomic"
    ),
    (
        "rollback timestamp mutation and rollback_applied "
        "event are atomic"
    ),
    "identical integration replay creates no duplicate event",
    "conflicting replay fails explicitly",
    "metadata remains allowlisted and privacy-minimized",
    "default command behavior remains non-delivery",
    "production delivery remains disabled",
    "no background worker is introduced",
    "no model or migration change is introduced",
)


class SavedSearchNotificationAuditRuntimeIntegrationContractV231Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _read_backend(self, relative_path: str) -> str:
        return (
            self._backend_root()
            / relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def test_v231_marker_declares_runtime_integration_contract(self):
        self.assertEqual(
            V231_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION_CONTRACT,
            (
                "V231_SAVED_SEARCH_NOTIFICATION_AUDIT_"
                "RUNTIME_INTEGRATION_CONTRACT"
            ),
        )

    def test_v231_names_exact_future_adapter_and_public_api(self):
        self.assertEqual(
            PROPOSED_RUNTIME_ADAPTER,
            "listings/saved_search_notification_audit_runtime.py",
        )
        self.assertEqual(
            PROPOSED_RUNTIME_CONTEXT,
            "SavedSearchNotificationAuditRuntimeContext",
        )
        self.assertEqual(
            PROPOSED_RECORD_FUNCTION,
            "record_saved_search_notification_runtime_event",
        )
        self.assertEqual(
            PROPOSED_IDEMPOTENCY_FUNCTION,
            "build_saved_search_notification_audit_idempotency_key",
        )
        self.assertEqual(
            PROPOSED_FINGERPRINT_FUNCTION,
            "build_saved_search_notification_fingerprint",
        )

    def test_v231_runtime_integration_targets_exist(self):
        for relative_path in RUNTIME_INTEGRATION_TARGETS:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file()
                )

    def test_v231_contract_covers_exact_persistent_event_taxonomy(self):
        self.assertEqual(
            set(EVENT_INTEGRATION_CONTRACT),
            set(
                SavedSearchNotificationAuditEvent
                .EventType
                .values
            ),
        )

    def test_v231_contract_uses_only_stable_outcomes(self):
        allowed_outcomes = set(
            SavedSearchNotificationAuditEvent
            .Outcome
            .values
        )

        actual_outcomes = {
            definition["outcome"]
            for definition in EVENT_INTEGRATION_CONTRACT.values()
        }

        self.assertTrue(
            actual_outcomes.issubset(allowed_outcomes)
        )

        self.assertEqual(
            EVENT_INTEGRATION_CONTRACT[
                "rollback_applied"
            ]["outcome"],
            "rolled_back",
        )

    def test_v231_each_event_has_surface_trigger_and_required_context(self):
        for event_type, definition in (
            EVENT_INTEGRATION_CONTRACT.items()
        ):
            with self.subTest(event_type=event_type):
                self.assertIn(
                    definition["surface"],
                    RUNTIME_INTEGRATION_TARGETS,
                )
                self.assertTrue(
                    definition["trigger"],
                )
                self.assertIn(
                    "correlation_id",
                    definition["requires"],
                )
                self.assertIn(
                    "notification_fingerprint",
                    definition["requires"],
                )

    def test_v231_event_ordering_contract_is_explicit(self):
        self.assertIn(
            (
                "delivery_attempted",
                "delivery_succeeded",
            ),
            EVENT_ORDERING_CONTRACT,
        )
        self.assertIn(
            (
                "delivery_attempted",
                "delivery_failed",
            ),
            EVENT_ORDERING_CONTRACT,
        )
        self.assertIn(
            (
                "delivery_succeeded",
                "sent_timestamp_recorded",
            ),
            EVENT_ORDERING_CONTRACT,
        )
        self.assertIn(
            (
                "rollback_previewed",
                "rollback_applied",
            ),
            EVENT_ORDERING_CONTRACT,
        )

    def test_v231_runtime_context_contract_separates_identifiers(self):
        self.assertEqual(
            set(RUNTIME_CONTEXT_CONTRACT),
            {
                "correlation_id",
                "batch_id",
                "delivery_attempt_id",
                "actor_type",
                "actor_identifier",
                "source",
            },
        )

    def test_v231_idempotency_contract_is_deterministic_and_bounded(self):
        self.assertEqual(
            IDEMPOTENCY_KEY_CONTRACT["prefix"],
            "ssna:v1:",
        )
        self.assertEqual(
            IDEMPOTENCY_KEY_CONTRACT["algorithm"],
            "sha256",
        )
        self.assertEqual(
            IDEMPOTENCY_KEY_CONTRACT["maximum_length"],
            128,
        )
        self.assertEqual(
            IDEMPOTENCY_KEY_CONTRACT["identical_replay"],
            "created=False",
        )
        self.assertEqual(
            IDEMPOTENCY_KEY_CONTRACT["conflicting_replay"],
            (
                "SavedSearchNotificationAudit"
                "IdempotencyConflict"
            ),
        )

    def test_v231_fingerprint_contract_is_stable_across_delivery_chain(self):
        self.assertEqual(
            NOTIFICATION_FINGERPRINT_CONTRACT["algorithm"],
            "sha256",
        )
        self.assertIn(
            "ordered_matching_listing_ids",
            NOTIFICATION_FINGERPRINT_CONTRACT[
                "canonical_fields"
            ],
        )
        self.assertIn(
            "reuse one fingerprint",
            NOTIFICATION_FINGERPRINT_CONTRACT[
                "delivery_chain_policy"
            ],
        )
        self.assertIn(
            "sent_timestamp_recorded",
            NOTIFICATION_FINGERPRINT_CONTRACT[
                "rollback_policy"
            ],
        )

    def test_v231_metadata_contract_is_allowlisted_for_every_event(self):
        self.assertEqual(
            set(METADATA_ALLOWLIST_CONTRACT),
            set(EVENT_INTEGRATION_CONTRACT),
        )

        for event_type, keys in (
            METADATA_ALLOWLIST_CONTRACT.items()
        ):
            with self.subTest(event_type=event_type):
                self.assertEqual(
                    len(keys),
                    len(set(keys)),
                )
                self.assertNotIn(
                    "recipient",
                    keys,
                )
                self.assertNotIn(
                    "email",
                    keys,
                )
                self.assertNotIn(
                    "traceback",
                    keys,
                )

    def test_v231_metadata_contract_forbids_sensitive_payloads(self):
        required_forbidden = {
            "recipient email address",
            "rendered email body",
            "exception message",
            "traceback",
            "credentials",
            "tokens",
        }

        self.assertTrue(
            required_forbidden.issubset(
                set(METADATA_FORBIDDEN_PAYLOADS)
            )
        )

    def test_v231_transaction_boundaries_protect_timestamp_mutations(self):
        self.assertIn(
            "same database transaction",
            TRANSACTION_BOUNDARY_CONTRACT[
                "sent_timestamp_recorded"
            ],
        )
        self.assertIn(
            "same database transaction",
            TRANSACTION_BOUNDARY_CONTRACT[
                "rollback_applied"
            ],
        )
        self.assertIn(
            "commit before",
            TRANSACTION_BOUNDARY_CONTRACT[
                "delivery_attempted"
            ],
        )

    def test_v231_failure_semantics_are_fail_closed_and_visible(self):
        self.assertIn(
            "abort delivery",
            FAILURE_SEMANTICS_CONTRACT[
                "pre_delivery_audit_failure"
            ],
        )
        self.assertIn(
            "do not automatically retry",
            FAILURE_SEMANTICS_CONTRACT[
                "post_delivery_audit_failure"
            ],
        )
        self.assertIn(
            "never be silently ignored",
            FAILURE_SEMANTICS_CONTRACT[
                "swallowing"
            ],
        )

    def test_v231_rollback_contract_targets_sent_timestamp_event(self):
        self.assertEqual(
            ROLLBACK_LINK_CONTRACT[
                "rollback_target_event"
            ],
            "sent_timestamp_recorded",
        )
        self.assertTrue(
            ROLLBACK_LINK_CONTRACT[
                "same_saved_search"
            ],
        )
        self.assertTrue(
            ROLLBACK_LINK_CONTRACT[
                "preview_is_read_only"
            ],
        )
        self.assertTrue(
            ROLLBACK_LINK_CONTRACT[
                "apply_requires_explicit_execute"
            ],
        )

    def test_v231_preserves_v230_persistence_public_api(self):
        self.assertTrue(
            callable(
                record_saved_search_notification_audit_event
            )
        )
        self.assertTrue(
            issubclass(
                SavedSearchNotificationAuditIdempotencyConflict,
                RuntimeError,
            )
        )
        self.assertEqual(
            tuple(
                SavedSearchNotificationAuditWriteResult
                .__dataclass_fields__
            ),
            (
                "event",
                "created",
            ),
        )

    def test_v231_is_contract_only_and_runtime_remains_unintegrated(self):
        adapter_path = (
            self._backend_root()
            / PROPOSED_RUNTIME_ADAPTER
        )

        v232_test_path = (
            self._backend_root()
            / "listings"
            / (
                "test_saved_search_notification_audit_"
                "runtime_integration_v232.py"
            )
        )

        direct_persistence_terms = (
            (
                "from .saved_search_notification_audit_"
                "persistence import"
            ),
            (
                "from listings.saved_search_notification_audit_"
                "persistence import"
            ),
            "record_saved_search_notification_audit_event(",
        )

        if v232_test_path.exists():
            self.assertTrue(
                adapter_path.is_file(),
            )

            adapter_source = adapter_path.read_text(
                encoding="utf-8",
                errors="strict",
            )

            self.assertIn(
                "record_saved_search_notification_audit_event",
                adapter_source,
            )

            for relative_path in RUNTIME_INTEGRATION_TARGETS:
                source = self._read_backend(relative_path)

                with self.subTest(
                    relative_path=relative_path,
                ):
                    self.assertIn(
                        "saved_search_notification_audit_runtime",
                        source,
                    )

                for forbidden in direct_persistence_terms:
                    with self.subTest(
                        relative_path=relative_path,
                        forbidden=forbidden,
                    ):
                        self.assertNotIn(
                            forbidden,
                            source,
                        )
        else:
            self.assertFalse(
                adapter_path.exists(),
            )

            forbidden_runtime_terms = (
                "V231_SAVED_SEARCH_NOTIFICATION_AUDIT_"
                "RUNTIME_INTEGRATION_CONTRACT",
                *direct_persistence_terms,
            )

            for relative_path in RUNTIME_INTEGRATION_TARGETS:
                source = self._read_backend(relative_path)

                for forbidden in forbidden_runtime_terms:
                    with self.subTest(
                        relative_path=relative_path,
                        forbidden=forbidden,
                    ):
                        self.assertNotIn(
                            forbidden,
                            source,
                        )

    def test_v231_adds_no_model_migration_or_editable_admin(self):
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

    def test_v231_acceptance_gates_cover_runtime_safety(self):
        required_gates = {
            (
                "delivery_attempted is durable before "
                "email backend invocation"
            ),
            (
                "delivery failures never update "
                "last_notification_sent_at"
            ),
            (
                "identical integration replay creates "
                "no duplicate event"
            ),
            (
                "default command behavior remains "
                "non-delivery"
            ),
            "production delivery remains disabled",
            "no background worker is introduced",
            "no model or migration change is introduced",
        }

        self.assertTrue(
            required_gates.issubset(
                set(IMPLEMENTATION_ACCEPTANCE_GATES)
            )
        )

    def test_v231_recent_persistence_checkpoints_remain_packaged(self):
        required_paths = (
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "persistence_design_v227.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "persistence_implementation_contract_v228.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "persistence_model_migration_v229.py"
            ),
            (
                "listings/"
                "test_saved_search_notification_audit_"
                "persistence_write_service_v230.py"
            ),
            (
                "listings/"
                "saved_search_notification_audit_persistence.py"
            ),
        )

        for relative_path in required_paths:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file()
                )

    def test_v231_next_lane_is_runtime_integration_implementation(self):
        next_lane = "v232: saved-search notification audit runtime integration implementation"

        self.assertEqual(
            next_lane,
            "v232: saved-search notification audit runtime integration implementation",
        )
