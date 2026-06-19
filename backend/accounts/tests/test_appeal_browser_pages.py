from datetime import timedelta
import hashlib

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationAppealAttachment


class AppealBrowserPageSmokeTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.seller = User.objects.create_user(
            username="appeal_browser_seller@classifieds.local",
            email="appeal_browser_seller@classifieds.local",
            password="Testpass12345",
        )

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@classifieds.local",
            password="Testpass12345",
        )

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

    def _create_appeal(self):
        field_names = {field.name for field in ModerationAppeal._meta.fields}

        data = {
            "appellant": self.seller,
            "status": ModerationAppeal.Status.PENDING,
        }

        if "appeal_type" in field_names:
            data["appeal_type"] = self._first_choice_value(
                ModerationAppeal,
                "appeal_type",
                "listing",
            )

        if "message" in field_names:
            data["message"] = "Browser smoke test appeal."

        appeal = ModerationAppeal.objects.create(**data)

        now = timezone.now()
        appeal.extra_evidence_requested_at = now
        appeal.extra_evidence_due_at = now + timedelta(days=15)
        appeal.extra_evidence_request_note = "Please upload extra supporting evidence."
        appeal.extra_evidence_requested_by = self.admin
        appeal.extra_evidence_fulfilled_at = now
        appeal.save()

        self._create_attachment(
            appeal,
            "INITIAL_original_appeal_evidence.pdf",
            b"%PDF-1.4\nInitial evidence.\n%%EOF\n",
            "initial",
        )

        self._create_attachment(
            appeal,
            "EXTRA_requested_followup_evidence.pdf",
            b"%PDF-1.4\nExtra evidence.\n%%EOF\n",
            "extra",
        )

        return appeal

    def _create_attachment(self, appeal, filename, content, stage):
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
            data["uploaded_by"] = self.seller

        if "evidence_stage" in field_names:
            data["evidence_stage"] = stage

        return ModerationAppealAttachment.objects.create(**data)

    def test_seller_appeal_pages_render_and_upload_extra_evidence(self):
        appeal = self._create_appeal()
        self.client.force_login(self.seller)

        list_response = self.client.get(reverse("accounts:my_moderation_appeals"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "My Appeals")

        detail_response = self.client.get(
            reverse("accounts:moderation_appeal_detail", args=[appeal.pk])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Initial appeal evidence")
        self.assertContains(detail_response, "Extra evidence")
        self.assertContains(detail_response, "EXTRA_EVIDENCE_EXISTING_GALLERY_V1")
        self.assertNotContains(detail_response, "Delete")

        upload_response = self.client.post(
            reverse("accounts:moderation_appeal_add_extra_evidence", args=[appeal.pk]),
            {
                "attachments": ContentFile(
                    b"%PDF-1.4\nSecond extra evidence.\n%%EOF\n",
                    name="second_extra_evidence.pdf",
                )
            },
        )
        self.assertEqual(upload_response.status_code, 302)

        uploaded = (
            ModerationAppealAttachment.objects
            .filter(appeal=appeal, original_name="second_extra_evidence.pdf")
            .first()
        )
        self.assertIsNotNone(uploaded)
        self.assertEqual(uploaded.evidence_stage, "extra")

    def test_admin_appeal_page_renders_correction_form(self):
        appeal = self._create_appeal()
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("accounts:moderation_appeal_admin_detail", args=[appeal.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ADMIN_EVIDENCE_STAGE_CORRECTION_FORM_V1")
        self.assertContains(response, "Correct evidence label")
        self.assertContains(response, "Save label")
