from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from listings.listing_price_alerts_v285 import (
    LISTING_PRICE_ALERT_BATCH_LIMIT_V285,
    build_listing_price_alert_preview_v285,
    mark_listing_price_alert_sent_v285,
    send_listing_price_alert_v285,
)


class Command(BaseCommand):
    help = "Preview listing-specific price alerts; pass --send to deliver email."

    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true")
        parser.add_argument(
            "--limit",
            type=int,
            default=LISTING_PRICE_ALERT_BATCH_LIMIT_V285,
        )
        parser.add_argument("--site-base-url", default="")

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit <= 0 or limit > LISTING_PRICE_ALERT_BATCH_LIMIT_V285:
            raise CommandError(
                f"--limit must be between 1 and {LISTING_PRICE_ALERT_BATCH_LIMIT_V285}."
            )

        sent_at = timezone.now()
        preview = build_listing_price_alert_preview_v285(
            limit=limit,
            now=sent_at,
        )
        mode = "SEND" if options["send"] else "DRY RUN"
        self.stdout.write(f"Mode: {mode}")
        self.stdout.write(
            f"Found {preview.match_count} listing price alert candidate(s); "
            f"processing at most {limit}."
        )

        sent = 0
        skipped = 0
        failed = 0
        for alert in preview.alerts:
            self.stdout.write(
                f"- Alert #{alert.pk}: listing #{alert.listing_id} at "
                f"{alert.listing.price} TL"
            )
            if not options["send"]:
                continue
            if not str(alert.user.email or "").strip():
                skipped += 1
                self.stdout.write("  Skipped: subscriber has no email address.")
                continue
            try:
                delivered = send_listing_price_alert_v285(
                    alert,
                    site_base_url=options["site_base_url"],
                )
            except Exception as exc:
                failed += 1
                self.stderr.write(
                    f"  Delivery failed: {exc.__class__.__name__}: {exc}"
                )
                continue
            if delivered:
                mark_listing_price_alert_sent_v285(alert, sent_at=sent_at)
                sent += delivered

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(preview.alerts)} candidate(s): "
                f"{sent} sent, {skipped} skipped, {failed} failed."
            )
        )
