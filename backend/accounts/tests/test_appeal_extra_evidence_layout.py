from datetime import timedelta
import hashlib

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationAppealAttachment


@override_settings(ALLOWED_HOSTS=["localhost", "testserver", "127.0.0.1"])
class AppealExtraEvidenceLayoutTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="layout_admin",
            email="layout_admin@classifieds.local",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )

        self.seller = User.objects.create_user(
            username="layout_seller@classifieds.local",
            email="layout_seller@classifieds.local",
            password="Testpass12345",
        )

    def _first_choice_value(self, field_name, fallback):
        try:
            field = ModerationAppeal._meta.get_field(field_name)
        except Exception:
            return fallback

        choices = list(field.choices or [])
        return choices[0][0] if choices else fallback

    def _create_pending_appeal_with_deadline(self):
        data = {
            "appellant": self.seller,
            "status": ModerationAppeal.Status.PENDING,
        }

        field_names = {field.name for field in ModerationAppeal._meta.fields}

        if "appeal_type" in field_names:
            data["appeal_type"] = self._first_choice_value("appeal_type", "listing")

        if "message" in field_names:
            data["message"] = "Layout test: upload extra evidence before deadline."

        appeal = ModerationAppeal.objects.create(**data)
        appeal.extra_evidence_requested_at = timezone.now()
        appeal.extra_evidence_due_at = timezone.now() + timedelta(days=15)
        appeal.extra_evidence_request_note = (
            "Please upload proof of ownership, invoice, or another supporting document."
        )
        appeal.extra_evidence_requested_by = self.admin
        appeal.extra_evidence_fulfilled_at = None
        appeal.save()

        return appeal

    def _attachment_file_field_name(self):
        for field in ModerationAppealAttachment._meta.fields:
            if field.get_internal_type() == "FileField":
                return field.name
        return "file"

    def _create_attachment(self, appeal, filename, content, created_at=None):
        field_names = {field.name for field in ModerationAppealAttachment._meta.fields}
        file_field_name = self._attachment_file_field_name()

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
            data["evidence_stage"] = "extra" if filename.startswith("extra_") or filename.startswith("test_extra_") else "initial"

        attachment = ModerationAppealAttachment.objects.create(**data)

        if created_at:
            timestamp_updates = {}

            for timestamp_field in ("created_at", "uploaded_at"):
                if hasattr(attachment, timestamp_field):
                    timestamp_updates[timestamp_field] = created_at

            if timestamp_updates:
                ModerationAppealAttachment.objects.filter(pk=attachment.pk).update(**timestamp_updates)
                attachment.refresh_from_db()

        return attachment

    def test_seller_extra_evidence_page_has_upload_design_rules(self):
        appeal = self._create_pending_appeal_with_deadline()

        self.assertTrue(
            self.client.login(
                username="layout_seller@classifieds.local",
                password="Testpass12345",
            )
        )

        response = self.client.get(
            reverse("accounts:moderation_appeal_detail", args=[appeal.pk]),
            HTTP_HOST="localhost",
        )

        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8", errors="replace")

        expected_tokens = [
            "Extra evidence requested",
            "js-countdown",
            "Countdown",
            "appeal-upload-box",
            "Drop files here or click to choose",
            "multiple",
            "extra-evidence-input",
            "appeal-file-preview",
            "Hide preview",
            "Show preview",
            "Remove before submit",
            "selectedFiles.splice",
            "JPG",
            "PNG",
            "WEBP",
            "PDF",
            "MP4",
            "15 total evidence files",
            "200 MB",
            "duplicate selected file",
            "invalid type",
            "Upload extra evidence",
            "EXTRA_EVIDENCE_UPLOAD_LAYOUT_FIX_V1",
            "EXTRA_EVIDENCE_EXISTING_GALLERY_V1",
            "EVIDENCE_STAGE_BADGES_V1",
        ]

        for token in expected_tokens:
            self.assertIn(token, html)

    def test_initial_and_extra_evidence_are_labeled_visible_and_not_deletable(self):
        appeal = self._create_pending_appeal_with_deadline()

        initial_time = appeal.extra_evidence_requested_at - timedelta(hours=1)
        extra_time = appeal.extra_evidence_requested_at + timedelta(hours=1)

        initial_attachment = self._create_attachment(
            appeal,
            "initial_original_evidence.pdf",
            b"%PDF-1.4\ninitial evidence before extra request\n%%EOF\n",
            created_at=initial_time,
        )

        self._create_attachment(
            appeal,
            "extra_followup_evidence.pdf",
            b"%PDF-1.4\nextra evidence after request\n%%EOF\n",
            created_at=extra_time,
        )

        self.assertTrue(
            self.client.login(
                username="layout_seller@classifieds.local",
                password="Testpass12345",
            )
        )

        response = self.client.get(
            reverse("accounts:moderation_appeal_detail", args=[appeal.pk]),
            HTTP_HOST="localhost",
        )

        html = response.content.decode("utf-8", errors="replace")

        self.assertEqual(response.status_code, 200)
        self.assertIn("existing-evidence-gallery", html)
        self.assertIn("existing-evidence-stage", html)
        self.assertIn("Initial appeal evidence", html)
        self.assertIn("Extra evidence", html)
        self.assertIn("initial_original_evidence.pdf", html)
        self.assertIn("extra_followup_evidence.pdf", html)
        self.assertIn("Submitted evidence is locked", html)
        self.assertIn("Seller cannot delete this file", html)
        self.assertNotIn("Delete evidence", html)
        self.assertNotIn("delete/", html)
        self.assertNotIn(f"/accounts/appeals/attachments/{initial_attachment.pk}/delete/", html)

    def test_seller_can_upload_more_than_once_before_deadline_and_limits_but_no_delete_after_submit(self):
        appeal = self._create_pending_appeal_with_deadline()

        self.assertTrue(
            self.client.login(
                username="layout_seller@classifieds.local",
                password="Testpass12345",
            )
        )

        first_pdf = SimpleUploadedFile(
            "test_extra_evidence_first.pdf",
            b"%PDF-1.4\nfirst evidence\n%%EOF\n",
            content_type="application/pdf",
        )

        first_response = self.client.post(
            reverse("accounts:moderation_appeal_add_extra_evidence", args=[appeal.pk]),
            {"attachments": [first_pdf]},
            HTTP_HOST="localhost",
            follow=False,
        )

        self.assertEqual(first_response.status_code, 302)

        appeal.refresh_from_db()
        self.assertIsNotNone(appeal.extra_evidence_fulfilled_at)
        self.assertEqual(ModerationAppealAttachment.objects.filter(appeal=appeal).count(), 1)

        second_pdf = SimpleUploadedFile(
            "test_extra_evidence_second.pdf",
            b"%PDF-1.4\nsecond evidence\n%%EOF\n",
            content_type="application/pdf",
        )

        second_response = self.client.post(
            reverse("accounts:moderation_appeal_add_extra_evidence", args=[appeal.pk]),
            {"attachments": [second_pdf]},
            HTTP_HOST="localhost",
            follow=False,
        )

        self.assertEqual(second_response.status_code, 302)

        appeal.refresh_from_db()
        self.assertEqual(ModerationAppealAttachment.objects.filter(appeal=appeal).count(), 2)

        seller_response = self.client.get(
            reverse("accounts:moderation_appeal_detail", args=[appeal.pk]),
            HTTP_HOST="localhost",
        )

        seller_html = seller_response.content.decode("utf-8", errors="replace")

        self.assertIn("test_extra_evidence_first.pdf", seller_html)
        self.assertIn("test_extra_evidence_second.pdf", seller_html)
        self.assertIn("existing-evidence-gallery", seller_html)
        self.assertIn("Extra evidence", seller_html)
        self.assertIn("Submitted evidence is locked", seller_html)
        self.assertIn("Seller cannot delete this file", seller_html)
        self.assertIn("Upload extra evidence", seller_html)
        self.assertNotIn("Delete evidence", seller_html)
        self.assertNotIn("delete/", seller_html)
        self.assertNotIn("delete/", seller_html)

        self.client.logout()

        self.assertTrue(
            self.client.login(
                username="layout_admin",
                password="Testpass12345",
            )
        )

        admin_response = self.client.get(
            reverse("accounts:moderation_appeal_admin_detail", args=[appeal.pk]),
            HTTP_HOST="localhost",
        )

        self.assertEqual(admin_response.status_code, 200)

        admin_html = admin_response.content.decode("utf-8", errors="replace")

        self.assertTrue(
            "Ready for final decision" in admin_html
            or "Approve final decision" in admin_html
        )
