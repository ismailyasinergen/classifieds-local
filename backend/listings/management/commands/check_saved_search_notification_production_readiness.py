from __future__ import annotations

import json

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from listings.saved_search_notification_production_readiness import (
    get_saved_search_notification_production_readiness,
)


class Command(BaseCommand):
    help = (
        "Report saved-search production-delivery operational "
        "readiness without delivery, provider access or mutation."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--strict",
            action="store_true",
            help=(
                "Fail with CommandError when the sanitized "
                "readiness result is not ready."
            ),
        )

        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help=(
                "Print the sanitized structured readiness result "
                "as JSON."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        result = (
            get_saved_search_notification_production_readiness()
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
                    f"ready_count={result['ready_count']} "
                    f"not_ready_count={result['not_ready_count']} "
                    f"warning_count={result['warning_count']}"
                )
            )

            for check in result["checks"]:
                self.stdout.write(
                    (
                        f"check={check['check_id']} "
                        f"status={check['status']} "
                        f"passed={str(check['passed']).lower()} "
                        f"reason={check['reason_code']}"
                    )
                )

        if (
            options["strict"]
            and not result["ready"]
        ):
            raise CommandError(
                "Saved-search production-delivery readiness "
                "check failed."
            )

        return None
