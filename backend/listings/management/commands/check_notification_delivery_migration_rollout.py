from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from listings.notification_delivery_migration_rollout_preflight_v310 import (
    get_notification_delivery_migration_rollout_preflight_v310,
)


class Command(BaseCommand):
    help = (
        "Inspect the notification-delivery migration rollout "
        "without applying migrations or mutating application data."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--strict",
            action="store_true",
            help=(
                "Fail with CommandError unless the target migrations "
                "are either safely ready to apply or fully applied."
            ),
        )

        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help=(
                "Print sanitized structured rollout-preflight JSON."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        result = (
            get_notification_delivery_migration_rollout_preflight_v310()
        )

        if options["json_output"]:
            self.stdout.write(
                json.dumps(
                    result,
                    sort_keys=True,
                    separators=(
                        ",",
                        ":",
                    ),
                )
            )
        else:
            self.stdout.write(
                result["marker"]
            )

            self.stdout.write(
                (
                    f"status={result['status']} "
                    f"ready={str(result['ready']).lower()} "
                    f"read_only="
                    f"{str(result['read_only']).lower()} "
                    f"mutation_allowed="
                    f"{str(result['mutation_allowed']).lower()} "
                    f"migration_mode="
                    f"{result['migration_mode']} "
                    f"applied_target_count="
                    f"{result['applied_target_count']} "
                    f"pending_target_count="
                    f"{result['pending_target_count']} "
                    f"blocking_not_ready_count="
                    f"{result['blocking_not_ready_count']}"
                )
            )

            for check in result["checks"]:
                self.stdout.write(
                    (
                        f"check={check['check_id']} "
                        f"status={check['status']} "
                        f"ready="
                        f"{str(check['ready']).lower()} "
                        f"blocking="
                        f"{str(check['blocking']).lower()} "
                        f"reason={check['reason_code']}"
                    )
                )

            self.stdout.write(
                (
                    f"auth_user_count="
                    f"{result['auth_user_count']} "
                    f"auth_users_without_email="
                    f"{result['auth_users_without_email']} "
                    f"accounts_backfill_expected_rows="
                    f"{result['accounts_backfill_expected_rows']} "
                    f"notification_delivery_event_rows="
                    f"{result['notification_delivery_event_rows']}"
                )
            )

            self.stdout.write(
                (
                    f"collision_count="
                    f"{sum(len(result[key]) for key in (
                        'collision_tables',
                        'collision_columns',
                        'collision_relations',
                        'collision_constraints',
                    ))} "
                    f"missing_schema_count="
                    f"{sum(len(result[key]) for key in (
                        'missing_tables',
                        'missing_columns',
                        'missing_relations',
                        'missing_constraints',
                    ))}"
                )
            )

        if (
            options["strict"]
            and not result["ready"]
        ):
            raise CommandError(
                "Notification-delivery migration rollout "
                "preflight is blocked."
            )

        return None
