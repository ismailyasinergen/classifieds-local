from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from listings.saved_search_notification_scheduler import (
    V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE_MARKER,
    run_saved_search_notification_scheduler,
)


class Command(BaseCommand):
    help = (
        "Run the local saved-search notification scheduler spike. "
        "Defaults to dry-run and does not send email."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute",
            action="store_true",
            help=(
                "Persist scheduler check timestamps. "
                "Email sending is intentionally not implemented in v214."
            ),
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional maximum number of opt-in saved searches to inspect.",
        )

    def handle(self, *args, **options):
        limit = options.get("limit")
        execute = bool(options.get("execute"))

        if limit is not None and limit < 0:
            raise CommandError("--limit must be zero or a positive integer.")

        result = run_saved_search_notification_scheduler(
            dry_run=not execute,
            limit=limit,
        )

        self.stdout.write(
            self.style.SUCCESS(
                (
                    f"{V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE_MARKER} "
                    f"checked={result.checked} "
                    f"sent={result.sent} "
                    f"dry_run={result.dry_run}"
                )
            )
        )
