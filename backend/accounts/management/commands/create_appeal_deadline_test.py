from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationNotice


class Command(BaseCommand):
    help = "Create a fresh browser-test appeal with a 15-day extra-evidence deadline."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seller-email",
            default="appeal_deadline_seller@classifieds.local",
            help="Seller email/username for browser login.",
        )
        parser.add_argument(
            "--seller-password",
            default="Testpass12345",
            help="Seller password for browser login.",
        )
        parser.add_argument(
            "--admin-username",
            default="admin",
            help="Admin username.",
        )
        parser.add_argument(
            "--admin-email",
            default="admin@classifieds.local",
            help="Admin email.",
        )
        parser.add_argument(
            "--admin-password",
            default="Testpass12345",
            help="Admin password.",
        )
        parser.add_argument(
            "--deadline-days",
            type=int,
            default=15,
            help="Number of days until extra-evidence deadline.",
        )

    def handle(self, *args, **options):
        User = get_user_model()

        seller_email = options["seller_email"]
        seller_password = options["seller_password"]
        admin_username = options["admin_username"]
        admin_email = options["admin_email"]
        admin_password = options["admin_password"]
        deadline_days = options["deadline_days"]

        admin, _ = User.objects.get_or_create(username=admin_username)
        admin.email = admin_email
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_active = True
        admin.set_password(admin_password)
        admin.save()

        seller = (
            User.objects.filter(username=seller_email).first()
            or User.objects.filter(email=seller_email).first()
        )

        if not seller:
            seller = User.objects.create_user(
                username=seller_email,
                email=seller_email,
                password=seller_password,
            )
        else:
            username_taken = User.objects.filter(username=seller_email).exclude(pk=seller.pk).exists()
            if not username_taken:
                seller.username = seller_email
            seller.email = seller_email
            seller.is_active = True
            seller.set_password(seller_password)
            seller.save()

        field_names = {field.name for field in ModerationAppeal._meta.fields}

        appeal_data = {
            "appellant": seller,
            "status": ModerationAppeal.Status.PENDING,
        }

        if "appeal_type" in field_names:
            field = ModerationAppeal._meta.get_field("appeal_type")
            choices = list(field.choices or [])
            appeal_data["appeal_type"] = choices[0][0] if choices else "listing"

        if "message" in field_names:
            appeal_data["message"] = (
                "Browser test appeal: seller must upload extra evidence before the deadline."
            )

        appeal = ModerationAppeal.objects.create(**appeal_data)

        appeal.extra_evidence_requested_at = timezone.now()
        appeal.extra_evidence_due_at = timezone.now() + timedelta(days=deadline_days)
        appeal.extra_evidence_request_note = (
            "Please upload proof of ownership, invoice, or another document that supports this appeal."
        )
        appeal.extra_evidence_requested_by = admin
        appeal.extra_evidence_fulfilled_at = None
        appeal.extra_evidence_reminder_sent_at = None
        appeal.extra_evidence_overdue_notice_sent_at = None
        appeal.save()

        ModerationNotice.objects.create(
            recipient=seller,
            title="Extra evidence requested for your appeal",
            body=(
                "Trust & Safety needs more evidence before making a final decision. "
                "Please upload proof of ownership, invoice, or another supporting document before the deadline."
            ),
            notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        )

        ModerationNotice.objects.create(
            recipient=admin,
            title="Browser test appeal created",
            body=(
                f"Appeal #{appeal.pk} was created with a {deadline_days}-day extra-evidence deadline."
            ),
            notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        )

        self.stdout.write(self.style.SUCCESS("Created browser-test appeal."))
        self.stdout.write("")
        self.stdout.write("Admin login:")
        self.stdout.write(f"  username: {admin_username}")
        self.stdout.write(f"  email: {admin_email}")
        self.stdout.write(f"  password: {admin_password}")
        self.stdout.write("")
        self.stdout.write("Seller login:")
        self.stdout.write(f"  login field: {seller_email}")
        self.stdout.write(f"  password: {seller_password}")
        self.stdout.write("")
        self.stdout.write("Browser URLs:")
        self.stdout.write("  Admin queue: http://localhost/accounts/trust-safety/appeals/")
        self.stdout.write(f"  Admin appeal detail: http://localhost/accounts/trust-safety/appeals/{appeal.pk}/")
        self.stdout.write("  Seller appeals: http://localhost/accounts/appeals/")
        self.stdout.write(f"  Seller appeal detail: http://localhost/accounts/appeals/{appeal.pk}/")
        self.stdout.write("")
        self.stdout.write("Upload test file from your laptop:")
        self.stdout.write("  C:\\Users\\ismai\\Desktop\\classifieds_local\\test_extra_evidence.pdf")
