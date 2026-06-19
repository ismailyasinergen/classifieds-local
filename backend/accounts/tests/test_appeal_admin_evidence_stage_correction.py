from datetime import timedelta
import hashlib

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationAppealAttachment


@override_settings(ALLOWED_HOSTS=["localhost", "testserver", "127.0.0.1"])
class AppealAdminEvidenceStageCorrectionTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="stage_correct_admin",
            email="stage_correct_admin@classifieds.local",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )

        self.seller = User.objects.create_user(
            username="stage_correct_seller@classifieds.local",
            email="stage_correct_seller@classifieds.local",
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
            data["message"] = "Evidence stage correction test."

        appeal = ModerationAppeal.objects.create(**data)
        appeal.extra_evidence_requested_at = timezone.now()
        appeal.extra_evidence_due_at = timezone.now() + timedelta(days=15)
        appeal.extra_evidence_request_note = "Upload extra proof."
        appeal.extra_evidence_requested_by = self.admin
        appeal.save()

        return appeal

    def _file_field_name(self):
        for field in ModerationAppealAttachment._meta.fields:
            if field.get_internal_type() == "FileField":
                return field.name
        return "file"

    def _create_attachment(self, appeal):
        field_names = {field.name for field in ModerationAppealAttachment._meta.fields}
        file_field_name = self._file_field_name()
        content = b"%PDF-1.4\nstage correction upload\n%%EOF\n"

        data = {
            "appeal": appeal,
            file_field_name: SimpleUploadedFile(
                "wrongly_labeled_evidence.pdf",
                content,
                content_type="application/pdf",
            ),
        }

        if "original_name" in field_names:
            data["original_name"] = "wrongly_labeled_evidence.pdf"

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
            data["evidence_stage"] = "initial"

        return ModerationAppealAttachment.objects.create(**data)

    def test_admin_can_correct_evidence_stage(self):
        appeal = self._create_appeal()
        attachment = self._create_attachment(appeal)

        self.assertEqual(attachment.evidence_stage, "initial")

        self.assertTrue(
            self.client.login(
                username="stage_correct_admin",
                password="Testpass12345",
            )
        )

        response = self.client.post(
            reverse("accounts:moderation_appeal_attachment_update_stage", args=[attachment.pk]),
            {"evidence_stage": "extra"},
            HTTP_HOST="localhost",
            follow=True,
        )

        self.assertEqual(response.status_code, 200)

        attachment.refresh_from_db()
        self.assertEqual(attachment.evidence_stage, "extra")

        html = response.content.decode("utf-8", errors="replace")
        self.assertIn("ADMIN_EVIDENCE_STAGE_CORRECTION_FORM_V1", html)
        self.assertIn("Extra evidence", html)

    def test_seller_cannot_correct_evidence_stage(self):
        appeal = self._create_appeal()
        attachment = self._create_attachment(appeal)

        self.assertTrue(
            self.client.login(
                username="stage_correct_seller@classifieds.local",
                password="Testpass12345",
            )
        )

        response = self.client.post(
            reverse("accounts:moderation_appeal_attachment_update_stage", args=[attachment.pk]),
            {"evidence_stage": "extra"},
            HTTP_HOST="localhost",
        )

        self.assertIn(response.status_code, [302, 403])
        attachment.refresh_from_db()
        self.assertEqual(attachment.evidence_stage, "initial")
