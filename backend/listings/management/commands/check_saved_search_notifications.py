# SAVED_SEARCH_MATCHER_FOUNDATION_V81
# SAVED_SEARCH_EMAIL_DELIVERY_SKELETON_V82
# SAVED_SEARCH_NOTIFICATION_OPERATIONAL_HARDENING_V83
# SAVED_SEARCH_NOTIFICATION_SCHEDULING_FILTERS_V84
# SAVED_SEARCH_NOTIFICATION_OBSERVABILITY_V85
# SAVED_SEARCH_NOTIFICATION_OPERATOR_UX_V87
from argparse import RawDescriptionHelpFormatter
from dataclasses import replace
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from listings.saved_search_notifications import (
    build_saved_search_email_message,
    get_saved_search_recipient_email,
    iter_enabled_saved_search_match_previews,
    mark_saved_search_checked,
    mark_saved_search_sent,
    send_saved_search_match_email,
)
from listings.notification_delivery_deduplication_v287 import (
    build_saved_search_event_specs_v287,
    claim_notification_events_v287,
    claimed_listing_ids_v287,
    mark_notification_events_failed_v287,
    mark_notification_events_sent_v287,
    mark_notification_events_skipped_v287,
)


class Command(BaseCommand):
    help = (
        "Preview or send matching approved listings for enabled saved-search email alerts. "
        "Dry-run is the default; pass --send to send email."
    )
    examples = """
Examples:
  Dry-run one saved search:
    python manage.py check_saved_search_notifications --saved-search-id 123 --site-base-url https://classifieds.local

  Send one saved search after dry-run verification:
    python manage.py check_saved_search_notifications --saved-search-id 123 --send --site-base-url https://classifieds.local

  Process only stale searches in a bounded batch:
    python manage.py check_saved_search_notifications --stale-before-hours 24 --max-searches 100

Safety notes:
  Dry-run is the default. Use --send only after reviewing output.
  Send failures are isolated per saved search and failed sends do not update timestamps.
""".strip()

    def add_arguments(self, parser):
        parser.formatter_class = RawDescriptionHelpFormatter
        parser.epilog = self.examples
        parser.add_argument(
            "--saved-search-id",
            action="append",
            dest="saved_search_ids",
            type=int,
            help="Limit the preview to one saved search ID. Can be passed more than once.",
        )
        parser.add_argument(
            "--limit-per-search",
            type=int,
            default=10,
            help="Maximum listing titles to print and include for each saved search.",
        )
        parser.add_argument(
            "--mark-checked",
            action="store_true",
            help="Update last_notification_checked_at after previewing matches.",
        )
        parser.add_argument(
            "--send",
            action="store_true",
            help="Actually send saved-search notification emails.",
        )
        parser.add_argument(
            "--site-base-url",
            default="",
            help="Optional base URL to prepend to listing and saved-search links.",
        )
        parser.add_argument(
            "--stale-before-hours",
            type=float,
            default=None,
            help="Only process searches never checked or checked at least this many hours ago.",
        )
        parser.add_argument(
            "--max-searches",
            type=int,
            default=None,
            help="Maximum number of enabled saved searches to process in this run.",
        )

    def handle(self, *args, **options):
        checked_at = timezone.now()
        max_searches = options.get("max_searches")
        stale_before_hours = options.get("stale_before_hours")
        limit_per_search = options["limit_per_search"]
        saved_search_ids = options.get("saved_search_ids") or []
        stale_before = None

        if limit_per_search <= 0:
            raise CommandError("--limit-per-search must be greater than 0.")

        if max_searches is not None and max_searches <= 0:
            raise CommandError("--max-searches must be greater than 0.")

        if stale_before_hours is not None:
            if stale_before_hours < 0:
                raise CommandError("--stale-before-hours must be zero or greater.")
            stale_before = checked_at - timedelta(hours=stale_before_hours)

        previews = list(
            iter_enabled_saved_search_match_previews(
                saved_search_ids=saved_search_ids,
                limit=limit_per_search,
                now=checked_at,
                stale_before=stale_before,
                max_searches=max_searches,
            )
        )

        if not previews:
            if stale_before is not None:
                self.stdout.write("No enabled saved searches found for the requested stale window.")
            else:
                self.stdout.write("No enabled saved searches found.")
            return

        total_matches = 0
        sent_emails = 0
        dry_run_email_candidates = 0
        marked_checked = 0
        skipped_zero_matches = 0
        skipped_no_recipient = 0
        send_failures = 0
        claimed_events = 0
        duplicates_suppressed = 0
        failed_saved_search_ids = []
        should_send = options["send"]
        should_mark_checked = options["mark_checked"]
        site_base_url = options.get("site_base_url") or None

        self.stdout.write(f"Mode: {'SEND' if should_send else 'DRY RUN'}")
        self.stdout.write(f"Limit per search: {limit_per_search} listing(s).")
        if saved_search_ids:
            self.stdout.write(
                "Saved search ID filter: " + ", ".join(str(pk) for pk in saved_search_ids)
            )
        if site_base_url:
            self.stdout.write(f"Site base URL: {site_base_url}")
        if should_send:
            self.stdout.write("Send safety: failures are isolated per saved search.")
        else:
            self.stdout.write("Dry-run safety: no emails will be sent.")
        if stale_before is not None:
            self.stdout.write(f"Stale filter: checked at or before {stale_before}.")
        if max_searches is not None:
            self.stdout.write(f"Run limit: processing at most {max_searches} saved search(es).")

        for preview in previews:
            saved_search = preview.saved_search
            total_matches += preview.match_count
            recipient_marker = (
                "" if saved_search.user.email else " for (no email)"
            )
            self.stdout.write(
                f"Saved search #{saved_search.pk}{recipient_marker}: "
                f"{preview.match_count} "
                f"{'new or newly reduced' if preview.includes_price_drops else 'new'} "
                "matching approved listing(s)."
            )
            self.stdout.write(f"  Checked since: {preview.checked_since}")

            for listing in preview.listings:
                self.stdout.write(f"  - #{listing.pk}: {listing.title}")

            if preview.match_count <= 0:
                skipped_zero_matches += 1
                self.stdout.write("  No new matches; email skipped and timestamps unchanged.")
                if should_mark_checked and not should_send:
                    self.stdout.write("  --mark-checked skipped because there were no matches.")
                continue

            delivery_preview = preview
            event_claim = None
            if should_send:
                specs = build_saved_search_event_specs_v287(preview)
                event_claim = claim_notification_events_v287(
                    specs,
                    now=checked_at,
                )
                claimed_events += len(event_claim.claimed_keys)
                duplicates_suppressed += (
                    len(event_claim.duplicate_keys)
                    + len(event_claim.busy_keys)
                    + len(event_claim.exhausted_keys)
                )
                claimed_listing_ids = claimed_listing_ids_v287(event_claim)
                claimed_listings = [
                    listing
                    for listing in preview.listings
                    if listing.pk in claimed_listing_ids
                ]
                if not claimed_listings:
                    self.stdout.write(
                        "  Delivery suppressed: no unclaimed logical events."
                    )
                    if not event_claim.busy_keys and not event_claim.exhausted_keys:
                        mark_saved_search_checked(
                            saved_search,
                            checked_at=checked_at,
                        )
                    continue
                delivery_preview = replace(
                    preview,
                    match_count=len(claimed_listings),
                    listings=claimed_listings,
                )

            recipient_email = get_saved_search_recipient_email(saved_search)
            if not recipient_email:
                skipped_no_recipient += 1
                if event_claim is not None:
                    mark_notification_events_skipped_v287(
                        event_claim,
                        reason="missing_recipient",
                    )
                self.stdout.write("  Email skipped: saved search user has no email address.")
                if should_mark_checked and not should_send:
                    self.stdout.write("  --mark-checked skipped because no email recipient is available.")
                continue

            message = build_saved_search_email_message(
                delivery_preview,
                site_base_url=site_base_url,
            )
            self.stdout.write(f"  Email subject: {message.subject}")
            self.stdout.write("  Email recipient: configured account address.")

            if should_send:
                try:
                    sent_count = send_saved_search_match_email(
                        delivery_preview,
                        site_base_url=site_base_url,
                    )
                except Exception as exc:
                    send_failures += 1
                    mark_notification_events_failed_v287(
                        event_claim,
                        error_category=exc.__class__.__name__,
                    )
                    failed_saved_search_ids.append(saved_search.pk)
                    self.stdout.write(
                        self.style.ERROR(
                            f"  Email send failed for saved search #{saved_search.pk}: "
                            f"{exc.__class__.__name__}: {exc}"
                        )
                    )
                    self.stdout.write("  Timestamps were not updated for this saved search.")
                    continue

                sent_emails += sent_count

                if sent_count:
                    mark_notification_events_sent_v287(
                        event_claim,
                        sent_at=checked_at,
                    )
                    mark_saved_search_sent(saved_search, sent_at=checked_at, mark_checked=True)
                    self.stdout.write("  Email sent and notification timestamps updated.")
                else:
                    mark_notification_events_failed_v287(
                        event_claim,
                        error_category="ZeroDelivery",
                    )
                    self.stdout.write("  Email send returned 0; timestamps were not updated.")
            else:
                dry_run_email_candidates += 1
                self.stdout.write("  Dry run: email not sent.")

                if should_mark_checked:
                    mark_saved_search_checked(saved_search, checked_at=checked_at)
                    marked_checked += 1
                    self.stdout.write("  Marked checked.")

        if should_send:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed {len(previews)} enabled saved search(es), "
                    f"{total_matches} total match(es), {sent_emails} email(s) sent, "
                    f"{send_failures} email failure(s), "
                    f"{skipped_zero_matches} zero-match search(es) skipped, "
                    f"{skipped_no_recipient} no-recipient search(es) skipped, "
                    f"{claimed_events} event(s) claimed, "
                    f"{duplicates_suppressed} duplicate(s) suppressed."
                )
            )
            if failed_saved_search_ids:
                self.stdout.write(
                    self.style.ERROR(
                        "Failed saved search ID(s): "
                        + ", ".join(str(pk) for pk in failed_saved_search_ids)
                    )
                )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Previewed {len(previews)} enabled saved search(es), "
                    f"{total_matches} total match(es), "
                    f"{dry_run_email_candidates} email candidate(s), "
                    f"{marked_checked} search(es) marked checked, "
                    f"{skipped_zero_matches} zero-match search(es) skipped, "
                    f"{skipped_no_recipient} no-recipient search(es) skipped. "
                    "No emails were sent. Pass --send to send."
                )
            )
