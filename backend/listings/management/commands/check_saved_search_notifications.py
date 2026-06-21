# SAVED_SEARCH_MATCHER_FOUNDATION_V81
from django.core.management.base import BaseCommand
from django.utils import timezone

from listings.saved_search_notifications import (
    iter_enabled_saved_search_match_previews,
    mark_saved_search_checked,
)


class Command(BaseCommand):
    help = (
        "Preview matching approved listings for enabled saved-search email alerts. "
        "This command does not send emails."
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
            help="Maximum listing titles to print for each saved search.",
        )
        parser.add_argument(
            "--mark-checked",
            action="store_true",
            help="Update last_notification_checked_at after previewing matches.",
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

            if options["mark_checked"]:
                mark_saved_search_checked(saved_search, checked_at=checked_at)
                self.stdout.write("  Marked checked.")

        self.stdout.write(
            self.style.SUCCESS(
                f"Previewed {len(previews)} enabled saved search(es), {total_matches} total match(es). "
                "No emails were sent."
            )
        )
