from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import (
    MigrationExecutor,
)


V310_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_PREFLIGHT = (
    "notification_delivery_migration_rollout_preflight_v310"
)

V310_TARGET_MIGRATION_NODES = (
    (
        "accounts",
        "0016_emailverificationstate_v306",
    ),
    (
        "listings",
        "0024_notification_provider_outcomes_v307",
    ),
    (
        "listings",
        "0025_notification_delivery_retention_v308",
    ),
)

V310_TARGET_MIGRATIONS = tuple(
    f"{app_label}.{migration_name}"
    for app_label, migration_name
    in V310_TARGET_MIGRATION_NODES
)

V310_MIGRATION_TARGETS = (
    V310_TARGET_MIGRATION_NODES[0],
    V310_TARGET_MIGRATION_NODES[-1],
)

V310_TARGET_TABLES = frozenset(
    {
        "accounts_emailverificationstate",
        "listings_notificationprovideroutcomereceipt",
        "listings_notificationdeliveryretentionevidence",
    }
)

V310_NOTIFICATION_EVENT_TABLE = (
    "listings_notificationdeliveryevent"
)

V310_TARGET_EVENT_COLUMNS = frozenset(
    {
        "provider_event_id",
        "provider_message_id",
        "provider_name",
        "provider_outcome",
        "provider_outcome_at",
        "legal_hold",
        "legal_hold_reason",
        "legal_hold_set_at",
        "legal_hold_set_by_id",
        "retention_tombstoned_at",
        "retention_evidence_id",
    }
)

V310_TARGET_INDEX_NAMES = frozenset(
    {
        "notif_provider_msg_idx",
        "notif_receipt_msg_idx",
        "notif_receipt_out_idx",
        "notif_retention_scan_idx",
    }
)

V310_TARGET_CONSTRAINT_NAMES = frozenset(
    {
        "notif_provider_event_uniq",
        "notif_legal_hold_metadata",
        "notif_retention_evidence_req",
    }
)


def _migration_label_v310(
    migration_node: tuple[str, str],
) -> str:
    return (
        f"{migration_node[0]}."
        f"{migration_node[1]}"
    )


def _sorted_values_v310(
    values: Iterable[str],
) -> list[str]:
    return sorted(
        {
            str(value)
            for value in values
        }
    )


def _check_v310(
    *,
    check_id: str,
    ready: bool,
    blocking: bool,
    ready_reason: str,
    blocked_reason: str,
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": (
            "ready"
            if ready
            else "blocked"
        ),
        "ready": bool(ready),
        "blocking": bool(blocking),
        "reason_code": (
            ready_reason
            if ready
            else blocked_reason
        ),
    }


def build_notification_delivery_migration_rollout_preflight_v310(
    *,
    database_vendor: str,
    applied_migrations: Iterable[str],
    pending_plan: Iterable[str],
    present_tables: Iterable[str],
    present_event_columns: Iterable[str],
    present_relations: Iterable[str],
    present_constraints: Iterable[str],
    auth_user_count: int,
    auth_users_without_email: int,
    notification_delivery_event_rows: int | None,
) -> dict[str, Any]:
    applied_set = {
        str(value)
        for value in applied_migrations
    }

    pending_list = [
        str(value)
        for value in pending_plan
    ]

    present_table_set = {
        str(value)
        for value in present_tables
    }

    present_event_column_set = {
        str(value)
        for value in present_event_columns
    }

    present_relation_set = {
        str(value)
        for value in present_relations
    }

    present_constraint_set = {
        str(value)
        for value in present_constraints
    }

    applied_targets = [
        migration
        for migration in V310_TARGET_MIGRATIONS
        if migration in applied_set
    ]

    pending_targets = [
        migration
        for migration in V310_TARGET_MIGRATIONS
        if migration in pending_list
    ]

    unexpected_plan_migrations = [
        migration
        for migration in pending_list
        if migration not in V310_TARGET_MIGRATIONS
    ]

    if not applied_targets:
        migration_mode = "pre_apply"
        migration_state_ready = True
        migration_state_reason = (
            "all_target_migrations_pending"
        )
    elif (
        len(applied_targets)
        == len(V310_TARGET_MIGRATIONS)
    ):
        migration_mode = "post_apply"
        migration_state_ready = True
        migration_state_reason = (
            "all_target_migrations_applied"
        )
    else:
        migration_mode = "partial"
        migration_state_ready = False
        migration_state_reason = (
            "partial_target_application"
        )

    expected_pre_apply_plan = list(
        V310_TARGET_MIGRATIONS
    )

    if migration_mode == "pre_apply":
        migration_plan_ready = (
            pending_list
            == expected_pre_apply_plan
        )
        migration_plan_ready_reason = (
            "target_plan_exact"
        )
        migration_plan_blocked_reason = (
            "target_plan_unexpected"
        )
    elif migration_mode == "post_apply":
        migration_plan_ready = not pending_list
        migration_plan_ready_reason = (
            "target_plan_empty_after_application"
        )
        migration_plan_blocked_reason = (
            "pending_plan_remains_after_application"
        )
    else:
        migration_plan_ready = False
        migration_plan_ready_reason = (
            "target_plan_exact"
        )
        migration_plan_blocked_reason = (
            "partial_application_plan_blocked"
        )

    collision_tables = _sorted_values_v310(
        V310_TARGET_TABLES
        & present_table_set
    )

    collision_columns = _sorted_values_v310(
        V310_TARGET_EVENT_COLUMNS
        & present_event_column_set
    )

    collision_relations = _sorted_values_v310(
        V310_TARGET_INDEX_NAMES
        & present_relation_set
    )

    collision_constraints = _sorted_values_v310(
        V310_TARGET_CONSTRAINT_NAMES
        & present_constraint_set
    )

    missing_tables = _sorted_values_v310(
        V310_TARGET_TABLES
        - present_table_set
    )

    missing_columns = _sorted_values_v310(
        V310_TARGET_EVENT_COLUMNS
        - present_event_column_set
    )

    missing_relations = _sorted_values_v310(
        V310_TARGET_INDEX_NAMES
        - present_relation_set
    )

    missing_constraints = _sorted_values_v310(
        V310_TARGET_CONSTRAINT_NAMES
        - present_constraint_set
    )

    if migration_mode == "pre_apply":
        schema_ready = not any(
            (
                collision_tables,
                collision_columns,
                collision_relations,
                collision_constraints,
            )
        )
        schema_ready_reason = (
            "future_schema_objects_absent"
        )
        schema_blocked_reason = (
            "future_schema_object_collision"
        )
    elif migration_mode == "post_apply":
        schema_ready = not any(
            (
                missing_tables,
                missing_columns,
                missing_relations,
                missing_constraints,
            )
        )
        schema_ready_reason = (
            "target_schema_objects_present"
        )
        schema_blocked_reason = (
            "target_schema_object_missing"
        )
    else:
        schema_ready = False
        schema_ready_reason = (
            "target_schema_objects_present"
        )
        schema_blocked_reason = (
            "partial_application_schema_blocked"
        )

    backend_ready = (
        str(database_vendor).strip().lower()
        == "postgresql"
    )

    counts_ready = (
        isinstance(auth_user_count, int)
        and not isinstance(auth_user_count, bool)
        and auth_user_count >= 0
        and isinstance(
            auth_users_without_email,
            int,
        )
        and not isinstance(
            auth_users_without_email,
            bool,
        )
        and 0
        <= auth_users_without_email
        <= auth_user_count
    )

    event_volume_ready = (
        notification_delivery_event_rows is not None
        and isinstance(
            notification_delivery_event_rows,
            int,
        )
        and not isinstance(
            notification_delivery_event_rows,
            bool,
        )
        and notification_delivery_event_rows >= 0
    )

    checks = [
        _check_v310(
            check_id="database_backend",
            ready=backend_ready,
            blocking=True,
            ready_reason="postgresql_backend_available",
            blocked_reason="postgresql_backend_required",
        ),
        _check_v310(
            check_id="migration_state",
            ready=migration_state_ready,
            blocking=True,
            ready_reason=migration_state_reason,
            blocked_reason=migration_state_reason,
        ),
        _check_v310(
            check_id="migration_plan",
            ready=(
                migration_plan_ready
                and not unexpected_plan_migrations
            ),
            blocking=True,
            ready_reason=migration_plan_ready_reason,
            blocked_reason=migration_plan_blocked_reason,
        ),
        _check_v310(
            check_id="schema_objects",
            ready=schema_ready,
            blocking=True,
            ready_reason=schema_ready_reason,
            blocked_reason=schema_blocked_reason,
        ),
        _check_v310(
            check_id="accounts_backfill_volume",
            ready=counts_ready,
            blocking=True,
            ready_reason="backfill_volume_counted",
            blocked_reason="backfill_volume_unavailable",
        ),
        _check_v310(
            check_id="notification_event_volume",
            ready=event_volume_ready,
            blocking=False,
            ready_reason="delivery_event_volume_counted",
            blocked_reason="delivery_event_volume_unavailable",
        ),
    ]

    blocking_not_ready_count = sum(
        1
        for check in checks
        if (
            check["blocking"]
            and not check["ready"]
        )
    )

    ready = (
        blocking_not_ready_count == 0
    )

    if ready and migration_mode == "pre_apply":
        status = "ready_to_apply"
    elif ready and migration_mode == "post_apply":
        status = "already_applied"
    elif migration_mode == "partial":
        status = "partial_application_blocked"
    else:
        status = "blocked"

    return {
        "marker": (
            V310_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_PREFLIGHT
        ),
        "schema_version": 1,
        "status": status,
        "ready": ready,
        "read_only": True,
        "mutation_allowed": False,
        "migration_mode": migration_mode,
        "target_migration_count": len(
            V310_TARGET_MIGRATIONS
        ),
        "applied_target_count": len(
            applied_targets
        ),
        "pending_target_count": len(
            pending_targets
        ),
        "applied_target_migrations": (
            applied_targets
        ),
        "pending_target_migrations": (
            pending_targets
        ),
        "pending_plan": pending_list,
        "unexpected_plan_migrations": (
            unexpected_plan_migrations
        ),
        "collision_tables": collision_tables,
        "collision_columns": collision_columns,
        "collision_relations": collision_relations,
        "collision_constraints": (
            collision_constraints
        ),
        "missing_tables": missing_tables,
        "missing_columns": missing_columns,
        "missing_relations": missing_relations,
        "missing_constraints": (
            missing_constraints
        ),
        "auth_user_count": auth_user_count,
        "auth_users_without_email": (
            auth_users_without_email
        ),
        "accounts_backfill_expected_rows": (
            auth_user_count
            if migration_mode == "pre_apply"
            else 0
        ),
        "notification_delivery_event_rows": (
            notification_delivery_event_rows
        ),
        "checks": checks,
        "blocking_not_ready_count": (
            blocking_not_ready_count
        ),
    }


def _relation_names_v310(
    names: Iterable[str],
) -> set[str]:
    names = tuple(
        sorted(
            {
                str(name)
                for name in names
            }
        )
    )

    if not names:
        return set()

    placeholders = ", ".join(
        ["%s"] * len(names)
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT class.relname
            FROM pg_class AS class
            JOIN pg_namespace AS namespace
              ON namespace.oid = class.relnamespace
            WHERE
                namespace.nspname = ANY (
                    current_schemas(false)
                )
                AND class.relname IN ({placeholders})
            """,
            list(names),
        )

        return {
            str(row[0])
            for row in cursor.fetchall()
        }


def _constraint_names_v310(
    names: Iterable[str],
) -> set[str]:
    names = tuple(
        sorted(
            {
                str(name)
                for name in names
            }
        )
    )

    if not names:
        return set()

    placeholders = ", ".join(
        ["%s"] * len(names)
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT constraint_record.conname
            FROM pg_constraint AS constraint_record
            JOIN pg_namespace AS namespace
              ON namespace.oid =
                 constraint_record.connamespace
            WHERE
                namespace.nspname = ANY (
                    current_schemas(false)
                )
                AND constraint_record.conname
                    IN ({placeholders})
            """,
            list(names),
        )

        return {
            str(row[0])
            for row in cursor.fetchall()
        }


def _table_columns_v310(
    table_name: str,
    *,
    present_tables: set[str],
) -> set[str]:
    if table_name not in present_tables:
        return set()

    with connection.cursor() as cursor:
        description = (
            connection.introspection
            .get_table_description(
                cursor,
                table_name,
            )
        )

    return {
        str(column.name)
        for column in description
    }


def _row_count_v310(
    table_name: str,
    *,
    present_tables: set[str],
) -> int | None:
    if table_name not in present_tables:
        return None

    quoted_table = (
        connection.ops.quote_name(
            table_name
        )
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) FROM {quoted_table}"
        )
        return int(cursor.fetchone()[0])


def _auth_user_counts_v310() -> tuple[int, int]:
    User = get_user_model()

    table_name = User._meta.db_table
    email_column = (
        User._meta.get_field("email").column
    )

    quoted_table = (
        connection.ops.quote_name(
            table_name
        )
    )

    quoted_email = (
        connection.ops.quote_name(
            email_column
        )
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT
                COUNT(*),
                COUNT(*) FILTER (
                    WHERE BTRIM(
                        COALESCE(
                            {quoted_email},
                            ''
                        )
                    ) = ''
                )
            FROM {quoted_table}
            """
        )

        total, without_email = (
            cursor.fetchone()
        )

    return (
        int(total),
        int(without_email),
    )


def get_notification_delivery_migration_rollout_preflight_v310(
) -> dict[str, Any]:
    try:
        executor = MigrationExecutor(
            connection
        )

        applied_nodes = set(
            executor.loader.applied_migrations
        )

        applied_migrations = {
            _migration_label_v310(node)
            for node in applied_nodes
        }

        plan = executor.migration_plan(
            list(V310_MIGRATION_TARGETS)
        )

        pending_plan = [
            _migration_label_v310(
                (
                    migration.app_label,
                    migration.name,
                )
            )
            for migration, backwards in plan
            if not backwards
        ]

        present_tables = set(
            connection.introspection.table_names()
        )

        present_event_columns = (
            _table_columns_v310(
                V310_NOTIFICATION_EVENT_TABLE,
                present_tables=present_tables,
            )
        )

        present_relations = (
            _relation_names_v310(
                V310_TARGET_INDEX_NAMES
            )
        )

        present_constraints = (
            _constraint_names_v310(
                V310_TARGET_CONSTRAINT_NAMES
            )
        )

        (
            auth_user_count,
            auth_users_without_email,
        ) = _auth_user_counts_v310()

        delivery_event_rows = (
            _row_count_v310(
                V310_NOTIFICATION_EVENT_TABLE,
                present_tables=present_tables,
            )
        )

        return (
            build_notification_delivery_migration_rollout_preflight_v310(
                database_vendor=connection.vendor,
                applied_migrations=applied_migrations,
                pending_plan=pending_plan,
                present_tables=present_tables,
                present_event_columns=(
                    present_event_columns
                ),
                present_relations=present_relations,
                present_constraints=(
                    present_constraints
                ),
                auth_user_count=auth_user_count,
                auth_users_without_email=(
                    auth_users_without_email
                ),
                notification_delivery_event_rows=(
                    delivery_event_rows
                ),
            )
        )
    except Exception:
        checks = [
            _check_v310(
                check_id="repository_inspection",
                ready=False,
                blocking=True,
                ready_reason="repository_inspection_complete",
                blocked_reason="repository_inspection_failed",
            )
        ]

        return {
            "marker": (
                V310_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_PREFLIGHT
            ),
            "schema_version": 1,
            "status": "inspection_failed",
            "ready": False,
            "read_only": True,
            "mutation_allowed": False,
            "migration_mode": "unknown",
            "target_migration_count": len(
                V310_TARGET_MIGRATIONS
            ),
            "applied_target_count": 0,
            "pending_target_count": 0,
            "applied_target_migrations": [],
            "pending_target_migrations": [],
            "pending_plan": [],
            "unexpected_plan_migrations": [],
            "collision_tables": [],
            "collision_columns": [],
            "collision_relations": [],
            "collision_constraints": [],
            "missing_tables": [],
            "missing_columns": [],
            "missing_relations": [],
            "missing_constraints": [],
            "auth_user_count": 0,
            "auth_users_without_email": 0,
            "accounts_backfill_expected_rows": 0,
            "notification_delivery_event_rows": None,
            "checks": checks,
            "blocking_not_ready_count": 1,
        }
