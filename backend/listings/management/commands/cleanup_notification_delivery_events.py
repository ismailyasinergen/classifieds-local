from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from listings.notification_delivery_retention_v308 import (
    NotificationDeliveryRetentionConfigurationErrorV308,
    cleanup_notification_delivery_events_v308,
)


class Command(BaseCommand):
    help = (
        "Preview notification delivery event retention. "
        "Dry-run is the default. Confirmed tombstoning is "
        "available only when explicitly enabled in settings."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--apply",
            action="store_true",
            help=(
                "Apply bounded tombstoning. Requires both "
                "--confirm-retention-cleanup and the default-off "
                "retention apply feature gate."
            ),
        )

        parser.add_argument(
            "--confirm-retention-cleanup",
            action="store_true",
            help=(
                "Explicitly confirm an --apply run. "
                "Has no effect without --apply."
            ),
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help=(
                "Optional bounded batch size between 1 and 1000. "
                "The configured default is used when omitted."
            ),
        )

        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Print sanitized structured output.",
        )

    def handle(
        self,
        *args,
        **options,
    ):
        apply_changes = bool(
            options["apply"]
        )

        confirm = bool(
            options[
                "confirm_retention_cleanup"
            ]
        )

        try:
            result = (
                cleanup_notification_delivery_events_v308(
                    apply=apply_changes,
                    confirm=confirm,
                    limit=options["limit"],
                    source="management_command",
                )
            )
        except (
            NotificationDeliveryRetentionConfigurationErrorV308,
            ValueError,
            RuntimeError,
        ) as exc:
            raise CommandError(
                str(exc)
            ) from exc

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
            return

        self.stdout.write(
            result["marker"]
        )

        self.stdout.write(
            (
                f"mode={result['mode']} "
                f"dry_run={str(result['dry_run']).lower()} "
                f"mutation_allowed="
                f"{str(result['mutation_allowed']).lower()} "
                f"apply_enabled="
                f"{str(result['apply_enabled']).lower()} "
                f"retention_days={result['retention_days']} "
                f"batch_limit={result['batch_limit']} "
                f"eligible={result['eligible_count']} "
                f"candidates={result['candidate_count']} "
                f"held={result['held_count']} "
                f"non_terminal={result['non_terminal_count']} "
                f"remaining={result['remaining_eligible_count']} "
                f"tombstoned={result['tombstoned_count']} "
                f"backup_policy={result['backup_policy']}"
            )
        )

        if result["evidence_id"]:
            self.stdout.write(
                (
                    f"evidence_id={result['evidence_id']} "
                    f"evidence_digest="
                    f"{result['evidence_digest']}"
                )
            )

        if result["dry_run"]:
            self.stdout.write(
                "Dry-run safety: no delivery event, legal hold "
                "or retention evidence row was mutated."
            )
