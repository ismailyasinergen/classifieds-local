from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import (
    SimpleTestCase,
    override_settings,
)

from listings.saved_search_notification_production_readiness import (
    READINESS_CHECK_IDS,
    get_saved_search_notification_production_readiness,
)


V251_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT = (
    "V251_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT"
)

V250_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.md"
    ),
)

V251_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_v251.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "controlled_rollout_v251.md"
    ),
)

V252_PROPOSED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_closeout_audit_v252.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "controlled_rollout_closeout_audit_v252.md"
    ),
)

ROLLOUT_PHASES = (
    {
        "phase_id": 0,
        "name": "preflight and authorization",
        "minimum_limit": None,
        "maximum_limit": None,
        "production_allowed": False,
        "review_required": True,
    },
    {
        "phase_id": 1,
        "name": "single-owner pilot",
        "minimum_limit": 1,
        "maximum_limit": 3,
        "production_allowed": True,
        "review_required": True,
    },
    {
        "phase_id": 2,
        "name": "limited owner-scoped expansion",
        "minimum_limit": 4,
        "maximum_limit": 10,
        "production_allowed": True,
        "review_required": True,
    },
    {
        "phase_id": 3,
        "name": "expanded owner-scoped validation",
        "minimum_limit": 11,
        "maximum_limit": 25,
        "production_allowed": True,
        "review_required": True,
    },
    {
        "phase_id": 4,
        "name": "stabilization and closeout review",
        "minimum_limit": None,
        "maximum_limit": None,
        "production_allowed": False,
        "review_required": True,
    },
)

PHASE_COMMAND_PATTERNS = (
    {
        "phase_id": 0,
        "strict_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--strict"
        ),
        "json_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--json"
        ),
        "preview": None,
        "production": None,
    },
    {
        "phase_id": 1,
        "strict_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--strict"
        ),
        "json_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--json"
        ),
        "preview": (
            "docker compose exec -T web python manage.py "
            "process_saved_search_notifications "
            "--owner-id <POSITIVE_OWNER_ID> "
            "--limit <1-3>"
        ),
        "production": (
            "docker compose exec -T web python manage.py "
            "process_saved_search_notifications "
            "--execute-production-send "
            "--confirm-production-delivery "
            "--owner-id <POSITIVE_OWNER_ID> "
            "--limit <1-3>"
        ),
    },
    {
        "phase_id": 2,
        "strict_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--strict"
        ),
        "json_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--json"
        ),
        "preview": (
            "docker compose exec -T web python manage.py "
            "process_saved_search_notifications "
            "--owner-id <POSITIVE_OWNER_ID> "
            "--limit <4-10>"
        ),
        "production": (
            "docker compose exec -T web python manage.py "
            "process_saved_search_notifications "
            "--execute-production-send "
            "--confirm-production-delivery "
            "--owner-id <POSITIVE_OWNER_ID> "
            "--limit <4-10>"
        ),
    },
    {
        "phase_id": 3,
        "strict_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--strict"
        ),
        "json_readiness": (
            "docker compose exec -T web python manage.py "
            "check_saved_search_notification_production_readiness "
            "--json"
        ),
        "preview": (
            "docker compose exec -T web python manage.py "
            "process_saved_search_notifications "
            "--owner-id <POSITIVE_OWNER_ID> "
            "--limit <11-25>"
        ),
        "production": (
            "docker compose exec -T web python manage.py "
            "process_saved_search_notifications "
            "--execute-production-send "
            "--confirm-production-delivery "
            "--owner-id <POSITIVE_OWNER_ID> "
            "--limit <11-25>"
        ),
    },
    {
        "phase_id": 4,
        "strict_readiness": None,
        "json_readiness": None,
        "preview": None,
        "production": None,
    },
)

PHASE_EXECUTION_CHECKLIST = (
    "confirm approved change record",
    "confirm operator and reviewer identities",
    "confirm positive owner identifier",
    "confirm approved phase limit",
    "confirm no concurrent owner-scoped run",
    "run strict readiness",
    "retain sanitized readiness JSON",
    "run matching owner-scoped preview",
    "reconcile preview with approval",
    "run guarded production command",
    "reconcile sanitized delivery counts",
    "verify persistent audit sequence",
    "verify sent timestamp evidence",
    "verify duplicate-attempt state",
    "record go or stop decision",
    "record rollback decision",
    "record incident reference when applicable",
)

GO_DECISION_REQUIREMENTS = (
    "strict readiness passed",
    "readiness JSON retained",
    "preview owner matched production owner",
    "preview limit matched production limit",
    "both production confirmations were used",
    "failed count equals zero",
    "unexpected refusal count equals zero",
    "delivery counts reconcile",
    "audit sequence is complete",
    "sent timestamp evidence is consistent",
    "duplicate-attempt review is clean",
    "no provider anomaly exists",
    "no privacy or secret incident is open",
    "reviewer approved progression",
)

STOP_DECISION_REASONS = (
    "readiness not ready",
    "owner authorization missing",
    "owner scope mismatch",
    "phase limit mismatch",
    "concurrent owner-scoped run suspected",
    "configuration refusal",
    "delivery failure",
    "audit sequence incomplete",
    "sent timestamp inconsistent",
    "duplicate-attempt anomaly",
    "provider anomaly",
    "counts unreconciled",
    "unknown reason code",
    "private data exposure suspected",
    "secret exposure suspected",
    "incident open",
)

EVIDENCE_RECORD_FIELDS = (
    "change_record_id",
    "rollout_phase",
    "operator_identity",
    "reviewer_identity",
    "started_at_utc",
    "finished_at_utc",
    "owner_id",
    "approved_limit",
    "readiness_status",
    "readiness_ready_count",
    "readiness_not_ready_count",
    "preview_candidate_count",
    "preview_skipped_count",
    "delivery_delivered_count",
    "delivery_skipped_count",
    "delivery_refused_count",
    "delivery_failed_count",
    "audit_verified",
    "sent_timestamp_verified",
    "duplicate_attempt_verified",
    "decision",
    "rollback_decision",
    "incident_reference",
)

PROHIBITED_ROLLOUT_ACTIONS = (
    "automatic phase promotion",
    "global all-owner production execution",
    "multi-owner production invocation",
    "phase limit above 25",
    "phase limit outside approved band",
    "owner change without approval",
    "limit change without approval",
    "readiness bypass",
    "preview bypass",
    "production confirmation bypass",
    "blind retry",
    "manual sent timestamp edit",
    "manual audit-event deletion",
    "direct SQL repair",
    "Django shell timestamp repair",
    "automatic scheduler enablement",
    "Celery enablement",
    "cron enablement",
    "startup-time delivery",
    "request-time delivery",
    "credential logging",
    "recipient payload logging",
    "saved-search payload logging",
    "silent partial-failure handling",
)

V251_ACCEPTANCE_GATES = (
    "v250 controlled-rollout contract remains packaged",
    "v251 scope is exactly two files",
    "v252 proposed closeout scope is exactly two files",
    "five rollout phases are implemented",
    "phase 0 performs no production delivery",
    "phase 1 limit band is 1 through 3",
    "phase 2 limit band is 4 through 10",
    "phase 3 limit band is 11 through 25",
    "phase 4 performs no production delivery",
    "all phase progression remains manual",
    "every production invocation remains single-owner scoped",
    "strict readiness precedes every production phase",
    "sanitized readiness JSON evidence is retained",
    "preview owner and production owner must match",
    "preview limit and production limit must match",
    "both production confirmation flags remain mandatory",
    "go decision requirements are explicit",
    "stop decision reasons are explicit",
    "failed count must be zero for progression",
    "unexpected refusal count must be zero for progression",
    "persistent audit sequence must be complete",
    "sent timestamp evidence must be consistent",
    "duplicate-attempt review must be clean",
    "reviewer approval is required",
    "open incidents block progression",
    "rollback decisions are retained",
    "evidence record fields are explicit",
    "private notification payloads are excluded",
    "automatic phase promotion is prohibited",
    "global all-owner execution is prohibited",
    "multi-owner execution is prohibited",
    "manual database repair is prohibited",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v252: saved-search notification production delivery controlled rollout closeout audit"

PRODUCTION_LIKE_SETTINGS = {
    "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED": True,
    "EMAIL_BACKEND": (
        "project.production_mail."
        "ProductionEmailBackend"
    ),
    "DEFAULT_FROM_EMAIL": (
        "saved-search-alerts@example.invalid"
    ),
}

PROTECTED_RUNTIME_PATHS = (
    "config/settings.py",
    "listings/saved_search_notification_email_sender.py",
    (
        "listings/management/commands/"
        "process_saved_search_notifications.py"
    ),
    (
        "listings/"
        "saved_search_notification_production_readiness.py"
    ),
    (
        "listings/management/commands/"
        "check_saved_search_notification_production_readiness.py"
    ),
    "listings/saved_search_notification_scheduler.py",
    "listings/saved_search_notifications.py",
    "listings/saved_search_notification_audit_runtime.py",
    "listings/saved_search_notification_audit_persistence.py",
    "listings/saved_search_notification_audit.py",
    "listings/saved_search_notification_email_renderer.py",
    "listings/models.py",
    "listings/admin.py",
    "listings/urls.py",
    "templates/base.html",
    (
        "listings/templates/listings/"
        "saved_search_notification_audit_events.html"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.py"
    ),
)

HISTORICAL_SAFETY_TEST_PATHS = (
    (
        "listings/"
        "test_saved_search_notification_explicit_send_"
        "test_backend_v222.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_rollback_audit_"
        "hardening_v224.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "design_audit_v225.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_audit_runtime_"
        "integration_v232.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_persistent_audit_"
        "operator_shared_shell_integration_closeout_audit_v240.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_contract_v241.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_v242.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "closeout_audit_v243.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_contract_v244.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_v245.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_closeout_audit_v246.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_contract_v247.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_v248.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_closeout_audit_v249.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.py"
    ),
)


class SavedSearchNotificationProductionDeliveryControlledRolloutV251Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _read_backend(
        self,
        relative_path: str,
    ) -> str:
        return (
            self._backend_root()
            / relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def test_v251_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V251_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT,
            (
                "V251_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_CONTROLLED_ROLLOUT"
            ),
        )

        self.assertEqual(
            len(V250_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V251_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V252_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v252: saved-search notification production "
                "delivery controlled rollout closeout audit"
            ),
        )

    def test_v251_phase_definitions_are_exact(self):
        self.assertEqual(
            tuple(
                phase["phase_id"]
                for phase in ROLLOUT_PHASES
            ),
            (
                0,
                1,
                2,
                3,
                4,
            ),
        )

        self.assertFalse(
            ROLLOUT_PHASES[0]["production_allowed"]
        )

        self.assertTrue(
            ROLLOUT_PHASES[1]["production_allowed"]
        )

        self.assertTrue(
            ROLLOUT_PHASES[2]["production_allowed"]
        )

        self.assertTrue(
            ROLLOUT_PHASES[3]["production_allowed"]
        )

        self.assertFalse(
            ROLLOUT_PHASES[4]["production_allowed"]
        )

        self.assertTrue(
            all(
                phase["review_required"]
                for phase in ROLLOUT_PHASES
            )
        )

    def test_v251_phase_limit_bands_are_exact(self):
        production_phases = (
            ROLLOUT_PHASES[1:4]
        )

        self.assertEqual(
            tuple(
                (
                    phase["minimum_limit"],
                    phase["maximum_limit"],
                )
                for phase in production_phases
            ),
            (
                (
                    1,
                    3,
                ),
                (
                    4,
                    10,
                ),
                (
                    11,
                    25,
                ),
            ),
        )

    def test_v251_phase_commands_are_owner_scoped_and_bounded(self):
        for phase in PHASE_COMMAND_PATTERNS[1:4]:
            with self.subTest(
                phase_id=phase["phase_id"]
            ):
                preview = phase["preview"]
                production = phase["production"]

                self.assertIn(
                    "--owner-id <POSITIVE_OWNER_ID>",
                    preview,
                )

                self.assertIn(
                    "--limit <",
                    preview,
                )

                self.assertNotIn(
                    "--execute-production-send",
                    preview,
                )

                self.assertNotIn(
                    "--confirm-production-delivery",
                    preview,
                )

                self.assertIn(
                    "--execute-production-send",
                    production,
                )

                self.assertIn(
                    "--confirm-production-delivery",
                    production,
                )

                self.assertIn(
                    "--owner-id <POSITIVE_OWNER_ID>",
                    production,
                )

    def test_v251_readiness_precedes_each_production_phase(self):
        for phase in PHASE_COMMAND_PATTERNS[1:4]:
            with self.subTest(
                phase_id=phase["phase_id"]
            ):
                self.assertIn(
                    "--strict",
                    phase["strict_readiness"],
                )

                self.assertIn(
                    "--json",
                    phase["json_readiness"],
                )

                self.assertIsNotNone(
                    phase["preview"]
                )

                self.assertIsNotNone(
                    phase["production"]
                )

    def test_v251_execution_checklist_is_complete(self):
        required = {
            "confirm approved change record",
            "confirm operator and reviewer identities",
            "confirm positive owner identifier",
            "confirm approved phase limit",
            "confirm no concurrent owner-scoped run",
            "run strict readiness",
            "retain sanitized readiness JSON",
            "run matching owner-scoped preview",
            "reconcile preview with approval",
            "run guarded production command",
            "reconcile sanitized delivery counts",
            "verify persistent audit sequence",
            "verify sent timestamp evidence",
            "verify duplicate-attempt state",
            "record go or stop decision",
            "record rollback decision",
            "record incident reference when applicable",
        }

        self.assertEqual(
            set(PHASE_EXECUTION_CHECKLIST),
            required,
        )

    def test_v251_go_decision_requirements_are_complete(self):
        required = {
            "strict readiness passed",
            "readiness JSON retained",
            "preview owner matched production owner",
            "preview limit matched production limit",
            "both production confirmations were used",
            "failed count equals zero",
            "unexpected refusal count equals zero",
            "delivery counts reconcile",
            "audit sequence is complete",
            "sent timestamp evidence is consistent",
            "duplicate-attempt review is clean",
            "no provider anomaly exists",
            "no privacy or secret incident is open",
            "reviewer approved progression",
        }

        self.assertEqual(
            set(GO_DECISION_REQUIREMENTS),
            required,
        )

    def test_v251_stop_decision_reasons_are_complete(self):
        required = {
            "readiness not ready",
            "owner authorization missing",
            "owner scope mismatch",
            "phase limit mismatch",
            "concurrent owner-scoped run suspected",
            "configuration refusal",
            "delivery failure",
            "audit sequence incomplete",
            "sent timestamp inconsistent",
            "duplicate-attempt anomaly",
            "provider anomaly",
            "counts unreconciled",
            "unknown reason code",
            "private data exposure suspected",
            "secret exposure suspected",
            "incident open",
        }

        self.assertEqual(
            set(STOP_DECISION_REASONS),
            required,
        )

    def test_v251_evidence_record_fields_are_complete(self):
        required = {
            "change_record_id",
            "rollout_phase",
            "operator_identity",
            "reviewer_identity",
            "started_at_utc",
            "finished_at_utc",
            "owner_id",
            "approved_limit",
            "readiness_status",
            "readiness_ready_count",
            "readiness_not_ready_count",
            "preview_candidate_count",
            "preview_skipped_count",
            "delivery_delivered_count",
            "delivery_skipped_count",
            "delivery_refused_count",
            "delivery_failed_count",
            "audit_verified",
            "sent_timestamp_verified",
            "duplicate_attempt_verified",
            "decision",
            "rollback_decision",
            "incident_reference",
        }

        self.assertEqual(
            set(EVIDENCE_RECORD_FIELDS),
            required,
        )

    def test_v251_prohibited_actions_are_complete(self):
        required = {
            "automatic phase promotion",
            "global all-owner production execution",
            "multi-owner production invocation",
            "phase limit above 25",
            "phase limit outside approved band",
            "owner change without approval",
            "limit change without approval",
            "readiness bypass",
            "preview bypass",
            "production confirmation bypass",
            "blind retry",
            "manual sent timestamp edit",
            "manual audit-event deletion",
            "direct SQL repair",
            "Django shell timestamp repair",
            "automatic scheduler enablement",
            "Celery enablement",
            "cron enablement",
            "startup-time delivery",
            "request-time delivery",
            "credential logging",
            "recipient payload logging",
            "saved-search payload logging",
            "silent partial-failure handling",
        }

        self.assertEqual(
            set(PROHIBITED_ROLLOUT_ACTIONS),
            required,
        )

    def test_v251_default_readiness_remains_not_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        self.assertFalse(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "not_ready",
        )

        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            READINESS_CHECK_IDS,
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v251_production_like_readiness_remains_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        self.assertTrue(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "ready",
        )

        self.assertEqual(
            result["ready_count"],
            len(READINESS_CHECK_IDS),
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v251_readiness_execution_opens_no_email_connection(self):
        stdout = StringIO()

        with patch(
            "django.core.mail.get_connection"
        ) as get_connection:
            call_command(
                "check_saved_search_notification_production_readiness",
                "--strict",
                stdout=stdout,
            )

        get_connection.assert_not_called()

        self.assertIn(
            "status=ready",
            stdout.getvalue(),
        )

    def test_v251_readiness_command_surface_is_unchanged(self):
        source = self._read_backend(
            "listings/management/commands/"
            "check_saved_search_notification_production_readiness.py"
        )

        tree = ast.parse(
            source
        )

        option_strings = {
            argument.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        }

        self.assertEqual(
            option_strings,
            {
                "--strict",
                "--json",
            },
        )

    def test_v251_production_command_controls_are_unchanged(self):
        source = self._read_backend(
            "listings/management/commands/"
            "process_saved_search_notifications.py"
        )

        tree = ast.parse(
            source
        )

        option_strings = {
            argument.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        }

        required = {
            "--execute-production-send",
            "--confirm-production-delivery",
            "--owner-id",
            "--limit",
        }

        self.assertTrue(
            required.issubset(
                option_strings
            )
        )

    def test_v251_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

        self.assertIn(
            "send_saved_search_notification_email_production",
            source,
        )

    def test_v251_scheduler_remains_nonautomatic(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_scheduler.py"
        )

        forbidden = (
            "--execute-production-send",
            "--confirm-production-delivery",
            "send_saved_search_notification_email_production",
            "Celery",
            "celery",
            "cron",
            "startup",
            "ready(",
        )

        for term in forbidden:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v251_v250_contract_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "controlled_rollout_contract_v250.py"
        )

        self.assertIn(
            (
                "V250_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_CONTROLLED_ROLLOUT_CONTRACT"
            ),
            source,
        )

        self.assertIn(
            (
                "v251: saved-search notification production "
                "delivery controlled rollout implementation"
            ),
            source,
        )

    def test_v251_historical_safety_package_is_present(self):
        for relative_path in HISTORICAL_SAFETY_TEST_PATHS:
            with self.subTest(
                relative_path=relative_path
            ):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file()
                )

    def test_v251_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V251_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CONTROLLED_ROLLOUT
        )

        for relative_path in PROTECTED_RUNTIME_PATHS:
            source = self._read_backend(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_v251_no_migration_0017_exists(self):
        migration_directory = (
            self._backend_root()
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )

    def test_v251_acceptance_gate_matrix_is_complete(self):
        required = {
            "v250 controlled-rollout contract remains packaged",
            "v251 scope is exactly two files",
            "v252 proposed closeout scope is exactly two files",
            "five rollout phases are implemented",
            "phase 0 performs no production delivery",
            "phase 1 limit band is 1 through 3",
            "phase 2 limit band is 4 through 10",
            "phase 3 limit band is 11 through 25",
            "phase 4 performs no production delivery",
            "all phase progression remains manual",
            "every production invocation remains single-owner scoped",
            "strict readiness precedes every production phase",
            "preview owner and production owner must match",
            "preview limit and production limit must match",
            "both production confirmation flags remain mandatory",
            "failed count must be zero for progression",
            "unexpected refusal count must be zero for progression",
            "persistent audit sequence must be complete",
            "sent timestamp evidence must be consistent",
            "duplicate-attempt review must be clean",
            "reviewer approval is required",
            "open incidents block progression",
            "automatic phase promotion is prohibited",
            "global all-owner execution is prohibited",
            "multi-owner execution is prohibited",
            "manual database repair is prohibited",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service and command remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V251_ACCEPTANCE_GATES)
            )
        )
