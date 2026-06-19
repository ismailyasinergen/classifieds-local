from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationNotice


class Command(BaseCommand):
    help = "Send reminder/overdue notices for appeal extra-evidence deadlines."

    def handle(self, *args, **options):
        now = timezone.now()
        reminder_window = now + timedelta(days=15)

        pending = (
            ModerationAppeal.objects.select_related(
                "appellant",
                "listing",
                "listing_report",
                "user_report",
            )
            .filter(
                status=ModerationAppeal.Status.PENDING,
                extra_evidence_requested_at__isnull=False,
                extra_evidence_due_at__isnull=False,
                extra_evidence_fulfilled_at__isnull=True,
            )
            .order_by("extra_evidence_due_at")
        )

        User = get_user_model()
        staff_users = list(User.objects.filter(is_staff=True, is_active=True))

        reminder_count = 0
        overdue_count = 0

        for appeal in pending:
            due_at = appeal.extra_evidence_due_at
            due_display = timezone.localtime(due_at).strftime("%Y-%m-%d %H:%M")

            if due_at <= now:
                if appeal.extra_evidence_overdue_notice_sent_at:
                    continue

                ModerationNotice.objects.create(
                    recipient=appeal.appellant,
                    title="Extra evidence deadline passed",
                    body=(
                        f"The deadline to upload extra evidence for appeal #{appeal.pk} has passed. "
                        "Trust & Safety may now make a final decision based on the available information."
                    ),
                    notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                    listing=appeal.listing,
                    listing_report=appeal.listing_report,
                    user_report=appeal.user_report,
                )

                for staff_user in staff_users:
                    ModerationNotice.objects.create(
                        recipient=staff_user,
                        title="Appeal extra evidence deadline passed",
                        body=(
                            f"Appeal #{appeal.pk} extra evidence deadline passed at {due_display}. "
                            "Admin can now continue the final decision process."
                        ),
                        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                        listing=appeal.listing,
                        listing_report=appeal.listing_report,
                        user_report=appeal.user_report,
                    )

                appeal.extra_evidence_overdue_notice_sent_at = now
                appeal.save(update_fields=["extra_evidence_overdue_notice_sent_at"])
                overdue_count += 1
                continue

            if due_at <= reminder_window and not appeal.extra_evidence_reminder_sent_at:
                ModerationNotice.objects.create(
                    recipient=appeal.appellant,
                    title="Extra evidence deadline reminder",
                    body=(
                        f"Reminder: extra evidence for appeal #{appeal.pk} is due by {due_display}. "
                        "Upload the requested evidence before the deadline if you want it included in the final review."
                    ),
                    notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                    listing=appeal.listing,
                    listing_report=appeal.listing_report,
                    user_report=appeal.user_report,
                )

                for staff_user in staff_users:
                    ModerationNotice.objects.create(
                        recipient=staff_user,
                        title="Appeal extra evidence deadline is within 15 days",
                        body=(
                            f"Appeal #{appeal.pk} extra evidence deadline is within 15 days: {due_display}. "
                            "Final decision remains blocked until seller uploads evidence or the deadline passes."
                        ),
                        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                        listing=appeal.listing,
                        listing_report=appeal.listing_report,
                        user_report=appeal.user_report,
                    )

                appeal.extra_evidence_reminder_sent_at = now
                appeal.save(update_fields=["extra_evidence_reminder_sent_at"])
                reminder_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Appeal evidence reminders complete. Sent {reminder_count} reminder(s), {overdue_count} overdue notice(s)."
            )
        )
