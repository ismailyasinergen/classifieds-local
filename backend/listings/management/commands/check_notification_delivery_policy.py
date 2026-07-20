from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from listings.notification_delivery_policy_v304 import (
    get_notification_delivery_policy_baseline_v304,
)


class Command(BaseCommand):
    help = (
        "Report the sanitized notification-delivery policy "
        "baseline without delivery, provider access or mutation."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--strict",
            action="store_true",
            help=(
                "Fail with CommandError while blocking policy "
                "capabilities are not implementation-ready."
            ),
        )

        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help=(
                "Print the sanitized structured policy baseline "
                "as JSON."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        result = (
            get_notification_delivery_policy_baseline_v304()
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
                    f"policy_defined="
                    f"{str(result['policy_defined']).lower()} "
                    f"read_only="
                    f"{str(result['read_only']).lower()} "
                    f"runtime_enforcement_ready="
                    f"{str(result['runtime_enforcement_ready']).lower()} "
                    f"runtime_enforcement_enabled="
                    f"{str(result['runtime_enforcement_enabled']).lower()} "
                    f"ready_count={result['ready_count']} "
                    f"not_ready_count={result['not_ready_count']} "
                    f"blocking_not_ready_count="
                    f"{result['blocking_not_ready_count']}"
                )
            )

            for check in result["checks"]:
                self.stdout.write(
                    (
                        f"check={check['check_id']} "
                        f"status={check['status']} "
                        f"ready={str(check['ready']).lower()} "
                        f"blocking={str(check['blocking']).lower()} "
                        f"enforcement_enabled="
                        f"{str(check['enforcement_enabled']).lower()} "
                        f"reason={check['reason_code']}"
                    )
                )

            self.stdout.write(
                (
                    "legacy_recipient_output_surface_count="
                    f"{result['legacy_recipient_output_surface_count']}"
                )
            )

        if (
            options["strict"]
            and not result[
                "runtime_enforcement_ready"
            ]
        ):
            raise CommandError(
                "Notification-delivery policy baseline is "
                "defined, but blocking implementation "
                "capabilities remain unavailable."
            )

        return None
