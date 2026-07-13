from __future__ import annotations
from listings.saved_search_notification_scheduler import (
    V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION,
    build_saved_search_notification_scheduler_email_previews,
)

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
            "--render-email-previews",
            action="store_true",
            help=(
                "Render saved-search notification email previews in dry-run mode. "
                "No email is sent and sent timestamps are not updated."
            ),
        )
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
        if options.get("render_email_previews"):
            previews = build_saved_search_notification_scheduler_email_previews(
                limit=options.get("limit"),
            )
            self.stdout.write(
                (
                    f"{V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION} "
                    f"dry_run=True delivery_enabled=False sent=0 previews={len(previews)}"
                )
            )
            for preview in previews:
                self.stdout.write(
                    (
                        "DRY RUN email preview "
                        f"saved_search_id={preview['saved_search_id']} "
                        f"recipient={preview['recipient_email']} "
                        f"subject={preview['subject']}"
                    )
                )
            return

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
