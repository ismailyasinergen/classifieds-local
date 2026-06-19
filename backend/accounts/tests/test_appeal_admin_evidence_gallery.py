from datetime import timedelta
import hashlib

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationAppealAttachment


@override_settings(ALLOWED_HOSTS=["localhost", "testserver", "127.0.0.1"])
class AppealAdminEvidenceGalleryTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="admin_gallery",
            email="admin_gallery@classifieds.local",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )

        self.seller = User.objects.create_user(
            username="gallery_seller@classifieds.local",
            email="gallery_seller@classifieds.local",
            password="Testpass12345",
        )

    def _first_choice_value(self, model, field_name, fallback):
        try:
            field = model._meta.get_field(field_name)
        except Exception:
            return fallback

        choices = list(field.choices or [])
        return choices[0][0] if choices else fallback

    def _create_appeal(self):
        data = {
            "appellant": self.seller,
            "status": ModerationAppeal.Status.PENDING,
        }

        field_names = {field.name for field in ModerationAppeal._meta.fields}

        if "appeal_type" in field_names:
            data["appeal_type"] = self._first_choice_value(ModerationAppeal, "appeal_type", "listing")

        if "message" in field_names:
            data["message"] = "Admin evidence gallery test."

        appeal = ModerationAppeal.objects.create(**data)
        appeal.extra_evidence_requested_at = timezone.now()
        appeal.extra_evidence_due_at = timezone.now() + timedelta(days=15)
        appeal.extra_evidence_request_note = "Upload more supporting files."
        appeal.extra_evidence_requested_by = self.admin
        appeal.save()

        return appeal

    def _file_field_name(self):
        for field in ModerationAppealAttachment._meta.fields:
            if field.get_internal_type() == "FileField":
                return field.name
        return "file"

    def _create_attachment(self, appeal, filename, content, timestamp):
        field_names = {field.name for field in ModerationAppealAttachment._meta.fields}
        file_field_name = self._file_field_name()

        data = {
            "appeal": appeal,
            file_field_name: SimpleUploadedFile(
                filename,
                content,
                content_type="application/pdf",
            ),
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
            data["uploaded_by"] = self.seller

        if "evidence_stage" in field_names:
            data["evidence_stage"] = "extra" if filename.startswith("extra_") else "initial"

        attachment = ModerationAppealAttachment.objects.create(**data)

        timestamp_updates = {}
        for timestamp_field in ("created_at", "uploaded_at"):
            if hasattr(attachment, timestamp_field):
                timestamp_updates[timestamp_field] = timestamp

        if timestamp_updates:
            ModerationAppealAttachment.objects.filter(pk=attachment.pk).update(**timestamp_updates)
            attachment.refresh_from_db()

        return attachment

    def test_admin_evidence_gallery_shows_initial_and_extra_labels(self):
        appeal = self._create_appeal()

        initial_attachment = self._create_attachment(
            appeal,
            "initial_admin_gallery_evidence.pdf",
            b"%PDF-1.4 initial admin evidence %%EOF",
            appeal.extra_evidence_requested_at - timedelta(hours=1),
        )

        extra_attachment = self._create_attachment(
            appeal,
            "extra_admin_gallery_evidence.pdf",
            b"%PDF-1.4 extra admin evidence %%EOF",
            appeal.extra_evidence_requested_at + timedelta(hours=1),
        )

        self.assertTrue(
            self.client.login(
                username="admin_gallery",
                password="Testpass12345",
            )
        )

        response = self.client.get(
            reverse("accounts:moderation_appeal_admin_detail", args=[appeal.pk]),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8", errors="replace")

        expected_tokens = [
            "ADMIN_EVIDENCE_GALLERY_STAGE_LABELS_V1",
            "admin-evidence-gallery",
            "Initial appeal evidence",
            "Extra evidence",
            "initial_admin_gallery_evidence.pdf",
            "extra_admin_gallery_evidence.pdf",
            "Open / download",
        ]

        for token in expected_tokens:
            self.assertIn(token, html)

        initial_download = self.client.get(
            f"/accounts/appeals/attachments/{initial_attachment.pk}/download/",
            HTTP_HOST="localhost",
        )
        self.assertEqual(initial_download.status_code, 200)

        extra_download = self.client.get(
            f"/accounts/appeals/attachments/{extra_attachment.pk}/download/",
            HTTP_HOST="localhost",
        )
        self.assertEqual(extra_download.status_code, 200)
