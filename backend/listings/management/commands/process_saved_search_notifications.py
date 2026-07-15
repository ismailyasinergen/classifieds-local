from __future__ import annotations

from listings.saved_search_notification_audit_runtime import (
    SavedSearchNotificationAuditRuntimeContext,
    V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION,
)

from listings.saved_search_notification_audit import (
    build_saved_search_notification_rollback_plan,
    format_saved_search_notification_rollback_plan_lines,
)
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


from django.contrib.auth import (
    get_user_model as _v242_get_user_model,
)
from django.core.management.base import (
    CommandError as _V242CommandError,
)

from listings.saved_search_notification_email_sender import (
    V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION,
    send_saved_search_notification_email_production_batch,
)

V242_LEGACY_LIMIT_DEFAULT = None

class Command(BaseCommand):
    help = (
        "Run the local saved-search notification scheduler spike. "
        "Defaults to dry-run and does not send email."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--execute-production-send",
            action="store_true",
        )
        parser.add_argument(
            "--confirm-production-delivery",
            action="store_true",
        )
        parser.add_argument(
            "--owner-id",
            type=int,
            default=None,
        )
        parser.add_argument(
            "--notification-rollback-report",
            action="store_true",
            help=(
                "Print a read-only saved-search notification rollback report. "
                "No timestamps are changed."
            ),
        )
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
        execute_production_send = bool(
            options.get("execute_production_send")
        )
        confirm_production_delivery = bool(
            options.get("confirm_production_delivery")
        )

        production_requested = (
            execute_production_send
            or confirm_production_delivery
        )

        if production_requested:
            if not (
                execute_production_send
                and confirm_production_delivery
            ):
                raise _V242CommandError(
                    "Production delivery requires both "
                    "--execute-production-send and "
                    "--confirm-production-delivery."
                )

            owner_id = options.get("owner_id")
            production_limit = options.get("limit")

            if (
                isinstance(owner_id, bool)
                or owner_id is None
                or int(owner_id) <= 0
            ):
                raise _V242CommandError(
                    "Production delivery requires a positive "
                    "--owner-id."
                )

            if (
                isinstance(production_limit, bool)
                or production_limit is None
            ):
                raise _V242CommandError(
                    "Production delivery requires an explicit "
                    "--limit between 1 and 25."
                )

            try:
                production_limit = int(
                    production_limit
                )
            except (TypeError, ValueError):
                raise _V242CommandError(
                    "Production limit must be an integer."
                )

            if not 1 <= production_limit <= 25:
                raise _V242CommandError(
                    "Production limit must be between 1 and 25."
                )

            owner = (
                _v242_get_user_model()
                .objects
                .filter(pk=owner_id)
                .first()
            )

            if owner is None:
                raise _V242CommandError(
                    "Production delivery owner was not found."
                )

            result = (
                send_saved_search_notification_email_production_batch(
                    owner=owner,
                    limit=production_limit,
                    execute_production_send=True,
                    confirm_production_delivery=True,
                )
            )

            self.stdout.write(
                (
                    f"{V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION} "
                    f"attempted={result['attempted_count']} "
                    f"succeeded={result['succeeded_count']} "
                    f"failed={result['failed_count']} "
                    f"refused={result['refused_count']} "
                    f"skipped={result['skipped_count']} "
                    f"delivered={result['delivered_count']}"
                )
            )

            if result["configuration_refused"]:
                raise _V242CommandError(
                    "Production delivery was refused by policy."
                )

            if result["failed_count"]:
                raise _V242CommandError(
                    "Production delivery completed with "
                    "isolated item failures."
                )

            return

        if options.get("limit") is None:
            options["limit"] = (
                V242_LEGACY_LIMIT_DEFAULT
            )

        audit_runtime_context = (
            SavedSearchNotificationAuditRuntimeContext.create(
                actor_type="management_command",
                actor_identifier=(
                    "process_saved_search_notifications"
                ),
                source="saved_search.command.process",
                mode="management_command",
                create_batch=True,
            )
        )

        if options.get("notification_rollback_report"):
            rollback_plan = build_saved_search_notification_rollback_plan(
                limit=options.get("limit"),
                runtime_context=audit_runtime_context,
                record_persistent_audit=True,
            )
            for line in format_saved_search_notification_rollback_plan_lines(rollback_plan):
                self.stdout.write(line)
            return

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
                runtime_context=audit_runtime_context,
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
                runtime_context=audit_runtime_context,
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

V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_COMMAND_INTEGRATION = V232_SAVED_SEARCH_NOTIFICATION_AUDIT_RUNTIME_INTEGRATION
