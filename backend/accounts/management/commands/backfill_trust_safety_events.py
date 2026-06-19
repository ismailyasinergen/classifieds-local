
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ModerationAppeal, TrustSafetyEvent, UserReport
from listings.models import ListingReport


class Command(BaseCommand):
    help = "Backfill TrustSafetyEvent records from existing reports and appeals."

    def _set_created_at(self, event, value):
        if value:
            TrustSafetyEvent.objects.filter(pk=event.pk).update(created_at=value)

    def handle(self, *args, **options):
        created = 0

        for appeal in ModerationAppeal.objects.select_related("appellant", "listing", "reviewed_by").all():
            if not TrustSafetyEvent.objects.filter(
                event_type=TrustSafetyEvent.EventType.APPEAL_SUBMITTED,
                appeal=appeal,
            ).exists():
                event = TrustSafetyEvent.objects.create(
                    event_type=TrustSafetyEvent.EventType.APPEAL_SUBMITTED,
                    title=f"Appeal #{appeal.pk} submitted",
                    actor=appeal.appellant,
                    target_user=appeal.appellant,
                    listing=appeal.listing,
                    appeal=appeal,
                    public_note=appeal.message or "",
                    metadata={"appeal_status": appeal.status},
                )
                self._set_created_at(event, appeal.created_at)
                created += 1

            if appeal.status in [
                ModerationAppeal.Status.APPROVED,
                ModerationAppeal.Status.REJECTED,
            ]:
                event_type = (
                    TrustSafetyEvent.EventType.APPEAL_APPROVED
                    if appeal.status == ModerationAppeal.Status.APPROVED
                    else TrustSafetyEvent.EventType.APPEAL_REJECTED
                )

                if not TrustSafetyEvent.objects.filter(event_type=event_type, appeal=appeal).exists():
                    event = TrustSafetyEvent.objects.create(
                        event_type=event_type,
                        title=f"Appeal #{appeal.pk} {appeal.status}",
                        actor=appeal.reviewed_by,
                        target_user=appeal.appellant,
                        listing=appeal.listing,
                        appeal=appeal,
                        public_note=appeal.decision_note or "",
                        internal_note=appeal.admin_note or "",
                        metadata={"appeal_status": appeal.status},
                    )
                    self._set_created_at(event, appeal.reviewed_at or appeal.created_at)
                    created += 1

        for report in ListingReport.objects.select_related("listing", "listing__owner", "reporter").exclude(status="pending"):
            action = report.action_taken or ""
            if action == "suspended":
                event_type = TrustSafetyEvent.EventType.LISTING_SUSPENDED
            elif action == "archived":
                event_type = TrustSafetyEvent.EventType.LISTING_ARCHIVED
            else:
                event_type = TrustSafetyEvent.EventType.LISTING_REPORT_REVIEWED

            if not TrustSafetyEvent.objects.filter(event_type=event_type, listing_report=report).exists():
                event = TrustSafetyEvent.objects.create(
                    event_type=event_type,
                    title=f"Listing report #{report.pk} {event_type}",
                    target_user=report.listing.owner if report.listing else None,
                    listing=report.listing,
                    listing_report=report,
                    public_note=report.reporter_note or "",
                    internal_note=report.admin_note or "",
                    metadata={
                        "status": report.status,
                        "action_taken": report.action_taken or "",
                        "reporter_id": report.reporter_id,
                    },
                )
                self._set_created_at(event, report.reviewed_at or report.created_at)
                created += 1

        for report in UserReport.objects.select_related("reported_user", "reporter", "source_listing").exclude(status="pending"):
            action = report.action_taken or ""

            if action == "warned_seller":
                event_type = TrustSafetyEvent.EventType.SELLER_WARNED
            elif action == "suspended_seller":
                event_type = TrustSafetyEvent.EventType.SELLER_SUSPENDED
            elif action == "removed_verification":
                event_type = TrustSafetyEvent.EventType.SELLER_VERIFICATION_REMOVED
            elif action == "archived_listings":
                event_type = TrustSafetyEvent.EventType.SELLER_LISTINGS_ARCHIVED
            elif action == "blocked_messaging":
                event_type = TrustSafetyEvent.EventType.SELLER_MESSAGING_BLOCKED
            else:
                event_type = TrustSafetyEvent.EventType.SELLER_REPORT_REVIEWED

            if not TrustSafetyEvent.objects.filter(event_type=event_type, user_report=report).exists():
                event = TrustSafetyEvent.objects.create(
                    event_type=event_type,
                    title=f"Seller report #{report.pk} {event_type}",
                    target_user=report.reported_user,
                    listing=report.source_listing,
                    user_report=report,
                    public_note=report.reporter_note or "",
                    internal_note=report.admin_note or "",
                    metadata={
                        "status": report.status,
                        "action_taken": report.action_taken or "",
                        "reporter_id": report.reporter_id,
                    },
                )
                self._set_created_at(event, getattr(report, "action_taken_at", None) or report.created_at)
                created += 1

        self.stdout.write(self.style.SUCCESS(f"TrustSafetyEvent backfill complete. Created {created} event(s)."))
