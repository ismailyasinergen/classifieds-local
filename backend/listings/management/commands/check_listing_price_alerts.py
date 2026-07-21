from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from listings.listing_price_alerts_v285 import (
    LISTING_PRICE_ALERT_BATCH_LIMIT_V285,
    build_listing_price_alert_preview_v285,
    mark_listing_price_alert_sent_v285,
    send_listing_price_alert_v285,
)
from listings.models import ListingPriceAlert
from listings.notification_delivery_deduplication_v287 import (
    build_listing_price_alert_event_specs_v287,
    claim_notification_events_v287,
    mark_notification_events_failed_v287,
    mark_notification_events_sent_v287,
    mark_notification_events_skipped_v287,
    subset_notification_claim_v287,
)
from listings.notification_delivery_preferences_v288 import (
    apply_notification_preferences_v288,
)
from listings.notification_delivery_runtime_enforcement_v309 import (
    notification_delivery_recipient_decision_v309,
)
from listings.notification_scheduler_lease_v301 import (
    LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301,
    notification_scheduler_lease_v301,
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
        if not options.get("send"):
            return self._handle_with_scheduler_lease_v301(
                *args,
                **options,
            )

        with notification_scheduler_lease_v301(
            LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301
        ) as lease:
            if not lease.acquired:
                self.stdout.write(
                    self.style.WARNING(
                        "Scheduler lease unavailable: another "
                        "listing-price-alert run is active; no "
                        "candidates were scanned and no email was sent."
                    )
                )
                return

            return self._handle_with_scheduler_lease_v301(
                *args,
                **options,
            )

    def _handle_with_scheduler_lease_v301(
        self,
        *args,
        **options,
    ):
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

        if not options["send"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed {len(preview.alerts)} candidate(s): 0 claimed, "
                    "0 sent, 0 skipped, 0 failed, 0 duplicates suppressed."
                )
            )
            return

        specs = build_listing_price_alert_event_specs_v287(preview.alerts)
        preference_decision = apply_notification_preferences_v288(
            specs,
            now=sent_at,
        )
        claim = claim_notification_events_v287(
            preference_decision.allowed_specs,
            now=sent_at,
        )
        spec_by_alert_id = {
            spec.listing_price_alert_id: spec
            for spec in claim.claimed_specs
        }
        active_alert_ids = set(
            ListingPriceAlert.objects.filter(
                pk__in=spec_by_alert_id,
            ).values_list("pk", flat=True)
        )

        sent = 0
        skipped = 0
        failed = 0
        for alert in preview.alerts:
            self.stdout.write(
                f"- Alert #{alert.pk}: listing #{alert.listing_id} at "
                f"{alert.listing.price} TL"
            )
            spec = spec_by_alert_id.get(alert.pk)
            if spec is None:
                continue
            item_claim = subset_notification_claim_v287(
                claim,
                [spec.event_key],
            )
            if alert.pk not in active_alert_ids:
                skipped += 1
                mark_notification_events_skipped_v287(
                    item_claim,
                    reason="subscription_removed",
                )
                self.stdout.write("  Skipped: subscription is no longer active.")
                continue
            recipient_decision_v309 = (
                notification_delivery_recipient_decision_v309(
                    alert.user
                )
            )
            if not recipient_decision_v309.allowed:
                skipped += 1
                reason_code_v309 = (
                    recipient_decision_v309.reason_code
                    or "recipient_unavailable"
                )
                mark_notification_events_skipped_v287(
                    item_claim,
                    reason=reason_code_v309,
                )
                if reason_code_v309 == "missing_recipient":
                    self.stdout.write(
                        "  Skipped: subscriber has no email address."
                    )
                else:
                    self.stdout.write(
                        "  Skipped: subscriber has no eligible "
                        "verified recipient address."
                    )
                continue
            try:
                delivered = send_listing_price_alert_v285(
                    alert,
                    site_base_url=options["site_base_url"],
                )
            except Exception as exc:
                failed += 1
                mark_notification_events_failed_v287(
                    item_claim,
                    error_category=exc.__class__.__name__,
                )
                self.stderr.write(
                    f"  Delivery failed: {exc.__class__.__name__}: {exc}"
                )
                continue
            if delivered:
                mark_notification_events_sent_v287(
                    item_claim,
                    sent_at=sent_at,
                )
                mark_listing_price_alert_sent_v285(alert, sent_at=sent_at)
                sent += delivered
            else:
                failed += 1
                mark_notification_events_failed_v287(
                    item_claim,
                    error_category="ZeroDelivery",
                )

        duplicates = (
            len(claim.duplicate_keys)
            + len(claim.busy_keys)
            + len(claim.exhausted_keys)
        )
        preference_suppressed = len(preference_decision.suppressed_specs)
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(preview.alerts)} candidate(s): "
                f"{len(claim.claimed_keys)} claimed, {sent} sent, "
                f"{skipped} skipped, {failed} failed, "
                f"{duplicates} duplicates suppressed, "
                f"{preference_suppressed} preference-suppressed."
            )
        )
