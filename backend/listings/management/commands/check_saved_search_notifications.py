# SAVED_SEARCH_MATCHER_FOUNDATION_V81
# SAVED_SEARCH_EMAIL_DELIVERY_SKELETON_V82
from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.saved_search_notifications import (
    build_saved_search_email_message,
    iter_enabled_saved_search_match_previews,
    mark_saved_search_checked,
    mark_saved_search_sent,
    send_saved_search_match_email,
)


class Command(BaseCommand):
    help = (
        "Preview or send matching approved listings for enabled saved-search email alerts. "
        "Dry-run is the default; pass --send to send email."
    )

    def add_arguments(self, parser):
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

    def handle(self, *args, **options):
        checked_at = timezone.now()
        previews = list(
            iter_enabled_saved_search_match_previews(
                saved_search_ids=options.get("saved_search_ids"),
                limit=options["limit_per_search"],
                now=checked_at,
            )
        )

        if not previews:
            self.stdout.write("No enabled saved searches found.")
            return

        total_matches = 0
        sent_emails = 0
        should_send = options["send"]
        site_base_url = options.get("site_base_url") or None

        for preview in previews:
            saved_search = preview.saved_search
            total_matches += preview.match_count
            self.stdout.write(
                f"Saved search #{saved_search.pk} for {saved_search.user.email}: "
                f"{preview.match_count} new matching approved listing(s)."
            )
            self.stdout.write(f"  Checked since: {preview.checked_since}")

            for listing in preview.listings:
                self.stdout.write(f"  - #{listing.pk}: {listing.title}")

            if preview.match_count > 0:
                message = build_saved_search_email_message(
                    preview,
                    site_base_url=site_base_url,
                )
                self.stdout.write(f"  Email subject: {message.subject}")
                self.stdout.write(f"  Email to: {', '.join(message.to)}")

                if should_send:
                    sent_count = send_saved_search_match_email(
                        preview,
                        site_base_url=site_base_url,
                    )
                    sent_emails += sent_count

                    if sent_count:
                        mark_saved_search_sent(saved_search, sent_at=checked_at, mark_checked=True)
                        self.stdout.write("  Email sent and notification timestamps updated.")
                    else:
                        self.stdout.write("  Email send returned 0; timestamps were not updated.")
                else:
                    self.stdout.write("  Dry run: email not sent.")

            if options["mark_checked"] and not should_send:
                mark_saved_search_checked(saved_search, checked_at=checked_at)
                self.stdout.write("  Marked checked.")

        if should_send:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed {len(previews)} enabled saved search(es), "
                    f"{total_matches} total match(es), {sent_emails} email(s) sent."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Previewed {len(previews)} enabled saved search(es), "
                    f"{total_matches} total match(es). No emails were sent. Pass --send to send."
                )
            )
