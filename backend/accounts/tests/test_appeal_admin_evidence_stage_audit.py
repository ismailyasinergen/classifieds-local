from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import ModerationAppeal, ModerationAppealAttachment, TrustSafetyEvent


class AppealAdminEvidenceStageAuditTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@classifieds.local",
            password="Testpass12345",
        )

        self.seller = User.objects.create_user(
            username="appeal_audit_seller@classifieds.local",
            email="appeal_audit_seller@classifieds.local",
            password="Testpass12345",
        )

    def _create_appeal(self):
        fields = {field.name for field in ModerationAppeal._meta.fields}
        data = {
            "appellant": self.seller,
            "status": ModerationAppeal.Status.PENDING,
        }

        if "appeal_type" in fields:
            field = ModerationAppeal._meta.get_field("appeal_type")
            choices = list(field.choices or [])
            data["appeal_type"] = choices[0][0] if choices else "listing"

        if "message" in fields:
            data["message"] = "Audit test appeal."

        return ModerationAppeal.objects.create(**data)

    def _create_attachment(self, appeal):
        fields = {field.name for field in ModerationAppealAttachment._meta.fields}

        file_field_name = "file"
        for field in ModerationAppealAttachment._meta.fields:
            if field.get_internal_type() == "FileField":
                file_field_name = field.name
                break

        data = {
            "appeal": appeal,
            file_field_name: ContentFile(b"%PDF-1.4\\nAudit evidence.\\n%%EOF\\n", name="audit_evidence.pdf"),
        }

        if "original_name" in fields:
            data["original_name"] = "audit_evidence.pdf"
        if "content_type" in fields:
            data["content_type"] = "application/pdf"
        if "size" in fields:
            data["size"] = 32
        if "file_size" in fields:
            data["file_size"] = 32
        if "uploaded_by" in fields:
            data["uploaded_by"] = self.seller
        if "evidence_stage" in fields:
            data["evidence_stage"] = "initial"

        return ModerationAppealAttachment.objects.create(**data)

    def test_admin_stage_correction_creates_trust_safety_event(self):
        appeal = self._create_appeal()
        attachment = self._create_attachment(appeal)

        before_count = TrustSafetyEvent.objects.count()

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("accounts:moderation_appeal_attachment_update_stage", args=[attachment.pk]),
            {"evidence_stage": "extra"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TrustSafetyEvent.objects.count(), before_count + 1)

        event = TrustSafetyEvent.objects.order_by("-id").first()
        event_text = " ".join(
            str(value)
            for value in [
                getattr(event, "event_type", ""),
                getattr(event, "action", ""),
                getattr(event, "details", ""),
                getattr(event, "note", ""),
                getattr(event, "metadata", ""),
            ]
        )

        self.assertIn("appeal", event_text.lower())
        self.assertIn("extra", event_text.lower())
