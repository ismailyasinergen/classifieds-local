from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase


V241_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION_CONTRACT = (
    "V241_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_"
    "IMPLEMENTATION_CONTRACT"
)

V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION = (
    "V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_"
    "IMPLEMENTATION"
)

V240_CLOSEOUT_TEST_PATH = (
    "backend/listings/"
    "test_saved_search_notification_persistent_audit_operator_"
    "shared_shell_integration_closeout_audit_v240.py"
)

V225_DESIGN_AUDIT_TEST_PATH = (
    "backend/listings/"
    "test_saved_search_notification_production_delivery_"
    "design_audit_v225.py"
)

V224_ROLLBACK_TEST_PATH = (
    "backend/listings/"
    "test_saved_search_notification_rollback_audit_hardening_v224.py"
)

V222_TEST_BACKEND_PATH = (
    "backend/listings/"
    "test_saved_search_notification_explicit_send_test_backend_v222.py"
)

V242_TEST_PATH = (
    "backend/listings/"
    "test_saved_search_notification_production_delivery_"
    "implementation_v242.py"
)

V242_DOC_PATH = (
    "docs/"
    "saved_search_notification_production_delivery_"
    "implementation_v242.md"
)

V242_ALLOWED_SCOPE = (
    "backend/config/settings.py",
    "backend/listings/saved_search_notification_email_sender.py",
    (
        "backend/listings/management/commands/"
        "process_saved_search_notifications.py"
    ),
    "backend/listings/test_saved_search_notification_production_delivery_implementation_v242.py",
    "docs/saved_search_notification_production_delivery_implementation_v242.md",
)

PROTECTED_RUNTIME_PATHS = (
    "backend/listings/saved_search_notification_scheduler.py",
    "backend/listings/saved_search_notification_audit_runtime.py",
    "backend/listings/saved_search_notification_audit_persistence.py",
    "backend/listings/saved_search_notification_audit.py",
    "backend/listings/saved_search_notification_email_renderer.py",
    "backend/listings/saved_search_notification_audit_operator.py",
    "backend/listings/saved_search_notification_audit_operator_views.py",
    "backend/listings/models.py",
    "backend/listings/admin.py",
    "backend/listings/urls.py",
    "backend/templates/base.html",
    (
        "backend/listings/templates/listings/"
        "saved_search_notification_audit_events.html"
    ),
    (
        "backend/listings/migrations/"
        "0016_savedsearchnotificationauditevent.py"
    ),
)

FEATURE_GATE_CONTRACT = (
    "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED defaults to False",
    "production execution requires --execute-production-send",
    "production execution requires --confirm-production-delivery",
    "both command flags are required together",
    "disabled setting refuses delivery before email backend access",
    "dry-run remains the default command behavior",
)

COMMAND_CONTRACT = (
    "--owner-id is mandatory for production delivery",
    "--limit is mandatory and bounded",
    "maximum production batch size is 25",
    "duplicate production flags fail closed",
    "unknown owner fails closed",
    "zero eligible searches performs no delivery",
    "command prints a sanitized bounded summary",
    "command returns a non-zero status for configuration refusal",
)

BACKEND_POLICY = (
    "locmem backend is rejected for production delivery",
    "dummy backend is rejected for production delivery",
    "console backend is rejected for production delivery",
    "file backend is rejected for production delivery",
    "configured production backend must not be a known test backend",
    "backend validation occurs before recipient processing",
    "SMTP or a configured custom production backend may be accepted",
)

OWNER_AND_BATCH_CONTRACT = (
    "delivery is restricted to the requested owner",
    "only enabled saved searches are eligible",
    "only notification opt-in saved searches are eligible",
    "existing due and cooldown rules remain authoritative",
    "batch selection remains deterministic",
    "batch size never exceeds 25",
    "global all-owner production execution is forbidden in v242",
)

IDEMPOTENCY_CONTRACT = (
    "last_notification_sent_at changes only after successful delivery",
    "failed delivery does not advance last_notification_sent_at",
    "refused delivery does not advance last_notification_sent_at",
    "last_notification_checked_at keeps existing scheduler semantics",
    "the same due item is not delivered twice in one invocation",
    "retry behavior remains compatible with current rollback safeguards",
)

AUDIT_OUTCOME_CONTRACT = (
    "configuration refusal is persisted",
    "delivery attempt is persisted",
    "delivery success is persisted",
    "delivery failure is persisted",
    "existing SavedSearchNotificationAuditEvent model is reused",
    "audit metadata is sanitized and bounded",
    "audit event persistence does not require schema changes",
    "delivery fingerprint remains stable",
)

FAILURE_POLICY = (
    "one delivery failure does not abort later eligible items",
    "per-item failures are isolated",
    "successful items remain successful when another item fails",
    "summary counts include attempted succeeded failed and refused",
    "unexpected exceptions are sanitized before operator output",
    "provider response bodies are not written to logs",
)

PRIVACY_AND_SECRET_CONTRACT = (
    "no production credentials are committed",
    "credentials remain environment supplied",
    "recipient addresses are not printed in command summaries",
    "email body and saved-search query are not logged",
    "exception output excludes credentials and provider tokens",
    "settings.py may define only non-secret delivery gates",
    "documentation contains no real credential examples",
)

SCHEDULER_CONTRACT = (
    "no background worker is introduced",
    "no cron configuration is introduced",
    "no automatic scheduler execution is introduced",
    "production delivery remains operator invoked",
    "saved_search_notification_scheduler.py remains unchanged",
)

ROLLBACK_CONTRACT = (
    "existing rollback report remains read only",
    "existing explicit rollback behavior remains available",
    "production delivery does not weaken rollback authorization",
    "audit fingerprints remain compatible with rollback inspection",
    "partial batch failure remains operator-auditable",
)

ACCEPTANCE_GATES = (
    "exact clean v241 base",
    "feature gate defaults off",
    "double explicit command confirmation",
    "mandatory owner scope",
    "bounded batch of at most 25",
    "test and development backends rejected",
    "opt-in and due rules preserved",
    "successful delivery updates sent timestamp once",
    "failed and refused delivery preserve sent timestamp",
    "persistent sanitized audit outcomes",
    "per-item failure isolation",
    "no secret or recipient leakage",
    "no automatic scheduling",
    "no model migration admin template or URL changes",
    "v222 test-backend behavior remains green",
    "v224 rollback safeguards remain green",
    "v225 production design audit remains green",
    "v240 operator closeout remains green",
    "focused v242 implementation tests pass",
    "full regression passes",
)

NEXT_CHECKPOINT = (
    "v242: saved-search notification production delivery implementation"
)


class SavedSearchNotificationProductionDeliveryImplementationContractV241Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _resolve_repo_path(
        self,
        relative_path: str,
    ) -> Path:
        normalized = relative_path.replace("\\", "/")

        if normalized.startswith("backend/"):
            normalized = normalized[len("backend/"):]

        return (
            self._backend_root()
            / normalized
        )

    def _read_repo_path(
        self,
        relative_path: str,
    ) -> str:
        return self._resolve_repo_path(
            relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def test_v241_marker_is_stable(self):
        self.assertEqual(
            V241_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION_CONTRACT,
            (
                "V241_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_IMPLEMENTATION_CONTRACT"
            ),
        )

    def test_v241_historical_safety_package_is_present(self):
        required_paths = (
            V222_TEST_BACKEND_PATH,
            V224_ROLLBACK_TEST_PATH,
            V225_DESIGN_AUDIT_TEST_PATH,
            V240_CLOSEOUT_TEST_PATH,
        )

        for relative_path in required_paths:
            with self.subTest(
                relative_path=relative_path
            ):
                self.assertTrue(
                    self._resolve_repo_path(
                        relative_path
                    ).is_file()
                )

    def test_v241_v225_design_audit_guards_remain_packaged(self):
        source = self._read_repo_path(
            V225_DESIGN_AUDIT_TEST_PATH
        )

        required = (
            (
                "test_v225_current_sender_remains_test_backend_"
                "gated_not_production_delivery"
            ),
            (
                "test_v225_management_command_has_no_production_"
                "send_bypass_flags"
            ),
            (
                "test_v225_no_scheduler_auto_delivery_or_"
                "background_process_wiring_exists"
            ),
            (
                "test_v225_no_production_email_settings_or_"
                "secrets_are_wired"
            ),
            (
                "test_v225_rollback_and_audit_safeguards_remain_"
                "packaged_before_production_delivery"
            ),
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

    def test_v241_v240_points_to_this_contract_lane(self):
        source = self._read_repo_path(
            V240_CLOSEOUT_TEST_PATH
        )

        self.assertIn(
            "test_v240_next_lane_is_production_delivery_contract",
            source,
        )

        self.assertIn(
            (
                "v241: saved-search notification production "
                "delivery implementation contract"
            ),
            source,
        )

    def test_v241_v242_allowed_scope_is_exact(self):
        self.assertEqual(
            set(
                V242_ALLOWED_SCOPE
            ),
            {
                "backend/config/settings.py",
                (
                    "backend/listings/"
                    "saved_search_notification_email_sender.py"
                ),
                (
                    "backend/listings/management/commands/"
                    "process_saved_search_notifications.py"
                ),
                V242_TEST_PATH,
                V242_DOC_PATH,
            },
        )

    def test_v241_v242_scope_excludes_schema_ui_and_scheduler(self):
        forbidden = {
            "backend/listings/models.py",
            "backend/listings/admin.py",
            "backend/listings/urls.py",
            "backend/listings/saved_search_notification_scheduler.py",
            (
                "backend/listings/migrations/"
                "0016_savedsearchnotificationauditevent.py"
            ),
            "backend/templates/base.html",
            (
                "backend/listings/templates/listings/"
                "saved_search_notification_audit_events.html"
            ),
        }

        self.assertTrue(
            forbidden.isdisjoint(
                set(
                    V242_ALLOWED_SCOPE
                )
            )
        )

    def test_v241_feature_gate_contract_is_complete(self):
        required = {
            "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED defaults to False",
            "production execution requires --execute-production-send",
            "production execution requires --confirm-production-delivery",
            "both command flags are required together",
            "disabled setting refuses delivery before email backend access",
            "dry-run remains the default command behavior",
        }

        self.assertTrue(
            required.issubset(
                set(
                    FEATURE_GATE_CONTRACT
                )
            )
        )

    def test_v241_command_contract_is_owner_scoped_and_bounded(self):
        required = {
            "--owner-id is mandatory for production delivery",
            "--limit is mandatory and bounded",
            "maximum production batch size is 25",
            "global all-owner production execution is forbidden in v242",
        }

        combined = set(
            COMMAND_CONTRACT
        ) | set(
            OWNER_AND_BATCH_CONTRACT
        )

        self.assertTrue(
            required.issubset(
                combined
            )
        )

    def test_v241_backend_policy_rejects_test_backends(self):
        required = {
            "locmem backend is rejected for production delivery",
            "dummy backend is rejected for production delivery",
            "console backend is rejected for production delivery",
            "file backend is rejected for production delivery",
            "backend validation occurs before recipient processing",
        }

        self.assertTrue(
            required.issubset(
                set(
                    BACKEND_POLICY
                )
            )
        )

    def test_v241_owner_opt_in_and_due_contract_is_complete(self):
        required = {
            "delivery is restricted to the requested owner",
            "only enabled saved searches are eligible",
            "only notification opt-in saved searches are eligible",
            "existing due and cooldown rules remain authoritative",
            "batch size never exceeds 25",
        }

        self.assertTrue(
            required.issubset(
                set(
                    OWNER_AND_BATCH_CONTRACT
                )
            )
        )

    def test_v241_idempotency_contract_is_complete(self):
        required = {
            (
                "last_notification_sent_at changes only after "
                "successful delivery"
            ),
            (
                "failed delivery does not advance "
                "last_notification_sent_at"
            ),
            (
                "refused delivery does not advance "
                "last_notification_sent_at"
            ),
            (
                "the same due item is not delivered twice "
                "in one invocation"
            ),
        }

        self.assertTrue(
            required.issubset(
                set(
                    IDEMPOTENCY_CONTRACT
                )
            )
        )

    def test_v241_persistent_audit_contract_is_complete(self):
        required = {
            "configuration refusal is persisted",
            "delivery attempt is persisted",
            "delivery success is persisted",
            "delivery failure is persisted",
            "existing SavedSearchNotificationAuditEvent model is reused",
            "audit event persistence does not require schema changes",
        }

        self.assertTrue(
            required.issubset(
                set(
                    AUDIT_OUTCOME_CONTRACT
                )
            )
        )

    def test_v241_failure_isolation_contract_is_complete(self):
        required = {
            (
                "one delivery failure does not abort later "
                "eligible items"
            ),
            "per-item failures are isolated",
            (
                "summary counts include attempted succeeded "
                "failed and refused"
            ),
            (
                "unexpected exceptions are sanitized before "
                "operator output"
            ),
        }

        self.assertTrue(
            required.issubset(
                set(
                    FAILURE_POLICY
                )
            )
        )

    def test_v241_privacy_and_secret_contract_is_complete(self):
        required = {
            "no production credentials are committed",
            "credentials remain environment supplied",
            (
                "recipient addresses are not printed in "
                "command summaries"
            ),
            "email body and saved-search query are not logged",
            "settings.py may define only non-secret delivery gates",
        }

        self.assertTrue(
            required.issubset(
                set(
                    PRIVACY_AND_SECRET_CONTRACT
                )
            )
        )

    def test_v241_scheduler_contract_forbids_automation(self):
        required = {
            "no background worker is introduced",
            "no cron configuration is introduced",
            "no automatic scheduler execution is introduced",
            "production delivery remains operator invoked",
            (
                "saved_search_notification_scheduler.py "
                "remains unchanged"
            ),
        }

        self.assertTrue(
            required.issubset(
                set(
                    SCHEDULER_CONTRACT
                )
            )
        )

    def test_v241_rollback_contract_is_complete(self):
        required = {
            "existing rollback report remains read only",
            "existing explicit rollback behavior remains available",
            (
                "production delivery does not weaken "
                "rollback authorization"
            ),
            (
                "audit fingerprints remain compatible with "
                "rollback inspection"
            ),
        }

        self.assertTrue(
            required.issubset(
                set(
                    ROLLBACK_CONTRACT
                )
            )
        )

    def test_v241_contract_is_deferred_until_v242(self):
        implementation_test_path = self._resolve_repo_path(
            V242_TEST_PATH
        )

        if implementation_test_path.exists():
            implementation_source = (
                implementation_test_path.read_text(
                    encoding="utf-8",
                    errors="strict",
                )
            )

            self.assertIn(
                V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION,
                implementation_source,
            )
        else:
            self.assertFalse(
                implementation_test_path.exists()
            )

        self.assertIn(
            V242_DOC_PATH,
            V242_ALLOWED_SCOPE,
        )

        for relative_path in PROTECTED_RUNTIME_PATHS:
            source = self._read_repo_path(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION,
                    source,
                )

    def test_v241_marker_does_not_leak_into_runtime(self):
        for relative_path in PROTECTED_RUNTIME_PATHS:
            source = self._read_repo_path(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    V241_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION_CONTRACT,
                    source,
                )

    def test_v241_no_migration_0017_exists(self):
        migration_directory = self._resolve_repo_path(
            "backend/listings/migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )

    def test_v241_acceptance_gate_matrix_is_complete(self):
        required = {
            "feature gate defaults off",
            "double explicit command confirmation",
            "mandatory owner scope",
            "bounded batch of at most 25",
            "test and development backends rejected",
            "opt-in and due rules preserved",
            (
                "successful delivery updates sent "
                "timestamp once"
            ),
            (
                "failed and refused delivery preserve "
                "sent timestamp"
            ),
            "persistent sanitized audit outcomes",
            "per-item failure isolation",
            "no secret or recipient leakage",
            "no automatic scheduling",
            (
                "no model migration admin template or "
                "URL changes"
            ),
            "full regression passes",
        }

        self.assertTrue(
            required.issubset(
                set(
                    ACCEPTANCE_GATES
                )
            )
        )

    def test_v241_next_lane_is_v242_implementation(self):
        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v242: saved-search notification production "
                "delivery implementation"
            ),
        )
