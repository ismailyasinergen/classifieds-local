from __future__ import annotations

from io import StringIO
import json
from unittest.mock import patch

from django.core.management import (
    call_command,
)
from django.core.management.base import (
    CommandError,
)
from django.test import (
    SimpleTestCase,
    TestCase,
)

from listings.notification_delivery_migration_rollout_preflight_v310 import (
    V310_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_PREFLIGHT,
    V310_TARGET_CONSTRAINT_NAMES,
    V310_TARGET_EVENT_COLUMNS,
    V310_TARGET_INDEX_NAMES,
    V310_TARGET_MIGRATIONS,
    V310_TARGET_TABLES,
    build_notification_delivery_migration_rollout_preflight_v310,
    get_notification_delivery_migration_rollout_preflight_v310,
)


class NotificationDeliveryMigrationRolloutBuilderV310Tests(
    SimpleTestCase
):
    maxDiff = None

    def _build(
        self,
        **overrides,
    ):
        values = {
            "database_vendor": "postgresql",
            "applied_migrations": [],
            "pending_plan": list(
                V310_TARGET_MIGRATIONS
            ),
            "present_tables": [],
            "present_event_columns": [],
            "present_relations": [],
            "present_constraints": [],
            "auth_user_count": 12,
            "auth_users_without_email": 0,
            "notification_delivery_event_rows": 0,
        }

        values.update(overrides)

        return (
            build_notification_delivery_migration_rollout_preflight_v310(
                **values
            )
        )

    def test_exact_pending_plan_is_ready_to_apply(
        self,
    ):
        result = self._build()

        self.assertTrue(
            result["ready"]
        )
        self.assertEqual(
            result["status"],
            "ready_to_apply",
        )
        self.assertEqual(
            result["migration_mode"],
            "pre_apply",
        )
        self.assertTrue(
            result["read_only"]
        )
        self.assertFalse(
            result["mutation_allowed"]
        )
        self.assertEqual(
            result["accounts_backfill_expected_rows"],
            12,
        )

    def test_partial_application_is_blocked(
        self,
    ):
        result = self._build(
            applied_migrations=[
                V310_TARGET_MIGRATIONS[0]
            ],
            pending_plan=list(
                V310_TARGET_MIGRATIONS[1:]
            ),
        )

        self.assertFalse(
            result["ready"]
        )
        self.assertEqual(
            result["status"],
            "partial_application_blocked",
        )
        self.assertEqual(
            result["migration_mode"],
            "partial",
        )

    def test_future_schema_collision_is_blocked(
        self,
    ):
        table = next(
            iter(V310_TARGET_TABLES)
        )

        result = self._build(
            present_tables=[table],
        )

        self.assertFalse(
            result["ready"]
        )
        self.assertIn(
            table,
            result["collision_tables"],
        )

    def test_unexpected_plan_dependency_is_blocked(
        self,
    ):
        result = self._build(
            pending_plan=[
                "accounts.0016_emailverificationstate_v306",
                "listings.0099_unexpected",
                "listings.0024_notification_provider_outcomes_v307",
                "listings.0025_notification_delivery_retention_v308",
            ],
        )

        self.assertFalse(
            result["ready"]
        )
        self.assertEqual(
            result["unexpected_plan_migrations"],
            [
                "listings.0099_unexpected"
            ],
        )

    def test_fully_applied_schema_is_ready(
        self,
    ):
        result = self._build(
            applied_migrations=list(
                V310_TARGET_MIGRATIONS
            ),
            pending_plan=[],
            present_tables=list(
                V310_TARGET_TABLES
            ),
            present_event_columns=list(
                V310_TARGET_EVENT_COLUMNS
            ),
            present_relations=list(
                V310_TARGET_INDEX_NAMES
            ),
            present_constraints=list(
                V310_TARGET_CONSTRAINT_NAMES
            ),
        )

        self.assertTrue(
            result["ready"]
        )
        self.assertEqual(
            result["status"],
            "already_applied",
        )
        self.assertEqual(
            result["migration_mode"],
            "post_apply",
        )
        self.assertEqual(
            result["accounts_backfill_expected_rows"],
            0,
        )

    def test_applied_migration_with_missing_schema_is_blocked(
        self,
    ):
        result = self._build(
            applied_migrations=list(
                V310_TARGET_MIGRATIONS
            ),
            pending_plan=[],
        )

        self.assertFalse(
            result["ready"]
        )
        self.assertEqual(
            set(result["missing_tables"]),
            set(V310_TARGET_TABLES),
        )

    def test_non_postgresql_backend_fails_closed(
        self,
    ):
        result = self._build(
            database_vendor="sqlite",
        )

        self.assertFalse(
            result["ready"]
        )

        backend_check = next(
            check
            for check in result["checks"]
            if check["check_id"]
            == "database_backend"
        )

        self.assertEqual(
            backend_check["reason_code"],
            "postgresql_backend_required",
        )


class NotificationDeliveryMigrationRolloutCommandV310Tests(
    SimpleTestCase
):
    def _ready_result(self):
        return (
            build_notification_delivery_migration_rollout_preflight_v310(
                database_vendor="postgresql",
                applied_migrations=[],
                pending_plan=list(
                    V310_TARGET_MIGRATIONS
                ),
                present_tables=[],
                present_event_columns=[],
                present_relations=[],
                present_constraints=[],
                auth_user_count=12,
                auth_users_without_email=0,
                notification_delivery_event_rows=0,
            )
        )

    def test_text_command_is_sanitized_and_read_only(
        self,
    ):
        with patch(
            (
                "listings.management.commands."
                "check_notification_delivery_migration_rollout."
                "get_notification_delivery_migration_rollout_preflight_v310"
            ),
            return_value=self._ready_result(),
        ):
            output = StringIO()

            call_command(
                "check_notification_delivery_migration_rollout",
                stdout=output,
            )

        rendered = output.getvalue()

        self.assertIn(
            V310_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_PREFLIGHT,
            rendered,
        )
        self.assertIn(
            "status=ready_to_apply",
            rendered,
        )
        self.assertIn(
            "read_only=true",
            rendered,
        )
        self.assertIn(
            "mutation_allowed=false",
            rendered,
        )
        self.assertNotIn(
            "@",
            rendered,
        )

    def test_json_command_is_structured(
        self,
    ):
        with patch(
            (
                "listings.management.commands."
                "check_notification_delivery_migration_rollout."
                "get_notification_delivery_migration_rollout_preflight_v310"
            ),
            return_value=self._ready_result(),
        ):
            output = StringIO()

            call_command(
                "check_notification_delivery_migration_rollout",
                "--json",
                stdout=output,
            )

        result = json.loads(
            output.getvalue()
        )

        self.assertTrue(
            result["ready"]
        )
        self.assertTrue(
            result["read_only"]
        )
        self.assertFalse(
            result["mutation_allowed"]
        )
        self.assertEqual(
            result["target_migration_count"],
            3,
        )

    def test_strict_command_blocks_unsafe_state(
        self,
    ):
        blocked = self._ready_result()
        blocked["ready"] = False
        blocked["status"] = "blocked"
        blocked["blocking_not_ready_count"] = 1

        with patch(
            (
                "listings.management.commands."
                "check_notification_delivery_migration_rollout."
                "get_notification_delivery_migration_rollout_preflight_v310"
            ),
            return_value=blocked,
        ):
            with self.assertRaises(
                CommandError
            ):
                call_command(
                    "check_notification_delivery_migration_rollout",
                    "--strict",
                    stdout=StringIO(),
                    stderr=StringIO(),
                )

    def test_inspection_failure_is_sanitized_and_blocked(
        self,
    ):
        with patch(
            (
                "listings."
                "notification_delivery_migration_rollout_preflight_v310."
                "MigrationExecutor"
            ),
            side_effect=RuntimeError(
                "person@example.test"
            ),
        ):
            result = (
                get_notification_delivery_migration_rollout_preflight_v310()
            )

        serialized = json.dumps(
            result,
            sort_keys=True,
        )

        self.assertFalse(
            result["ready"]
        )
        self.assertEqual(
            result["status"],
            "inspection_failed",
        )
        self.assertEqual(
            result["migration_mode"],
            "unknown",
        )
        self.assertTrue(
            result["read_only"]
        )
        self.assertFalse(
            result["mutation_allowed"]
        )
        self.assertEqual(
            result["blocking_not_ready_count"],
            1,
        )
        self.assertNotIn(
            "person@example.test",
            serialized,
        )
        self.assertNotIn(
            "@",
            serialized,
        )


class NotificationDeliveryMigrationRolloutRepositoryV310Tests(
    TestCase
):
    def test_migrated_test_database_reports_already_applied(
        self,
    ):
        result = (
            get_notification_delivery_migration_rollout_preflight_v310()
        )

        self.assertTrue(
            result["ready"]
        )
        self.assertEqual(
            result["status"],
            "already_applied",
        )
        self.assertEqual(
            result["applied_target_count"],
            3,
        )
        self.assertEqual(
            result["pending_target_count"],
            0,
        )
        self.assertEqual(
            result["blocking_not_ready_count"],
            0,
        )
