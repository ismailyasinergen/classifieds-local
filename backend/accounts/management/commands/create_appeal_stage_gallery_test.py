from datetime import timedelta
import hashlib
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationAppealAttachment


class Command(BaseCommand):
    help = "Create a browser-test appeal with initial and extra evidence labels."

    def add_arguments(self, parser):
        parser.add_argument("--seller-email", default="appeal_stage_seller@classifieds.local")
        parser.add_argument("--seller-password", default="Testpass12345")
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--admin-email", default="admin@classifieds.local")
        parser.add_argument("--admin-password", default="Testpass12345")

    def _first_choice_value(self, model, field_name, fallback):
        try:
            field = model._meta.get_field(field_name)
        except Exception:
            return fallback

        choices = list(field.choices or [])
        return choices[0][0] if choices else fallback

    def _file_field_name(self):
        for field in ModerationAppealAttachment._meta.fields:
            if field.get_internal_type() == "FileField":
                return field.name
        return "file"

    def _create_user(self, username, email, password, *, is_staff=False, is_superuser=False):
        User = get_user_model()
        user, _ = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.is_active = True
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()
        return user

    def _create_attachment(self, appeal, user, filename, content, stage):
        field_names = {field.name for field in ModerationAppealAttachment._meta.fields}
        file_field_name = self._file_field_name()

        data = {
            "appeal": appeal,
            file_field_name: ContentFile(content, name=filename),
        }

        if "original_name" in field_names:
            data["original_name"] = filename

        if "content_type" in field_names:
            data["content_type"] = "application/pdf"

        if "size" in field_names:
            data["size"] = len(content)

        if "file_size" in field_names:
            data["file_size"] = len(content)

        if "sha256" in field_names:
            data["sha256"] = hashlib.sha256(content).hexdigest()

        if "uploaded_by" in field_names:
            data["uploaded_by"] = user

        if "evidence_stage" in field_names:
            data["evidence_stage"] = stage

        return ModerationAppealAttachment.objects.create(**data)

    def handle(self, *args, **options):
        seller_email = options["seller_email"]
        seller_password = options["seller_password"]
        admin_username = options["admin_username"]
        admin_email = options["admin_email"]
        admin_password = options["admin_password"]

        seller = self._create_user(
            seller_email,
            seller_email,
            seller_password,
            is_staff=False,
            is_superuser=False,
        )

        admin = self._create_user(
            admin_username,
            admin_email,
            admin_password,
            is_staff=True,
            is_superuser=True,
        )

        # Clean this browser-test seller so the latest test is easy to find.
        ModerationAppeal.objects.filter(appellant=seller).delete()

        field_names = {field.name for field in ModerationAppeal._meta.fields}
        appeal_data = {
            "appellant": seller,
            "status": ModerationAppeal.Status.PENDING,
        }

        if "appeal_type" in field_names:
            appeal_data["appeal_type"] = self._first_choice_value(
                ModerationAppeal,
                "appeal_type",
                "listing",
            )

        if "message" in field_names:
            appeal_data["message"] = (
                "Browser test appeal with one initial evidence file "
                "and one requested extra evidence file."
            )

        appeal = ModerationAppeal.objects.create(**appeal_data)

        now = timezone.now()
        appeal.extra_evidence_requested_at = now
        appeal.extra_evidence_due_at = now + timedelta(days=15)
        appeal.extra_evidence_request_note = "Please upload extra supporting evidence before the deadline."
        appeal.extra_evidence_requested_by = admin
        appeal.extra_evidence_fulfilled_at = now + timedelta(minutes=5)
        appeal.save()

        self._create_attachment(
            appeal,
            seller,
            "INITIAL_original_appeal_evidence.pdf",
            b"%PDF-1.4\nInitial appeal evidence browser test.\n%%EOF\n",
            "initial",
        )

        self._create_attachment(
            appeal,
            seller,
            "EXTRA_requested_followup_evidence.pdf",
            b"%PDF-1.4\nExtra requested evidence browser test.\n%%EOF\n",
            "extra",
        )

        Path("/app/test_extra_evidence_browser_upload.pdf").write_bytes(
            b"%PDF-1.4\nAdditional browser upload test file.\n%%EOF\n"
        )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("CREATED BROWSER TEST APPEAL"))
        self.stdout.write("=" * 34)
        self.stdout.write(f"Seller login/email: {seller_email}")
        self.stdout.write(f"Seller password: {seller_password}")
        self.stdout.write(f"Seller appeal URL: http://localhost/accounts/appeals/{appeal.pk}/")
        self.stdout.write("")
        self.stdout.write(f"Admin username: {admin_username}")
        self.stdout.write(f"Admin password: {admin_password}")
        self.stdout.write(f"Admin appeal URL: http://localhost/accounts/trust-safety/appeals/{appeal.pk}/")
        self.stdout.write("")
        self.stdout.write("Expected labels:")
        for attachment in ModerationAppealAttachment.objects.filter(appeal=appeal).order_by("id"):
            self.stdout.write(f"{attachment.evidence_stage.upper():7} -> {attachment.original_name}")
