from __future__ import annotations
from listings.saved_search_notification_observability import (
    build_saved_search_notification_observability_snapshot,
    format_saved_search_notification_observability_lines,
)
from listings.saved_search_notification_email_sender import (
    V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND,
    send_saved_search_notification_email_batch,
)
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
            "--notification-observability-report",
            action="store_true",
            help=(
                "Print a read-only saved-search notification observability report. "
                "No email is delivered and no timestamps are changed."
            ),
        )
        parser.add_argument(
            "--execute-email-send",
            action="store_true",
            help=(
                "Explicitly deliver saved-search notification emails. "
                "Requires the Django locmem test email backend."
            ),
        )
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
        if options.get("notification_observability_report"):
            snapshot = build_saved_search_notification_observability_snapshot(
                limit=options.get("limit"),
            )
            for line in format_saved_search_notification_observability_lines(snapshot):
                self.stdout.write(line)
            return

        if options.get("execute_email_send"):
            result = send_saved_search_notification_email_batch(
                limit=options.get("limit"),
                execute_send=True,
                require_test_email_backend=True,
            )
            self.stdout.write(
                (
                    f"{V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND} "
                    f"execute_send=True delivery_enabled=True "
                    f"attempted={result['attempted_count']} "
                    f"delivered={result['delivered_count']} "
                    f"email_backend={result['email_backend']}"
                )
            )
            for item in result["results"]:
                self.stdout.write(
                    (
                        "EXECUTE SEND email delivery "
                        f"saved_search_id={item['saved_search_id']} "
                        f"recipient={item['recipient_email']} "
                        f"delivered={item['delivered_count']} "
                        f"subject={item['subject']}"
                    )
                )
            return

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
