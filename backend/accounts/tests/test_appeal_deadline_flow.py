from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice


class AppealDeadlineFlowTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_user(
            username="deadline_admin",
            email="deadline_admin@classifieds.local",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )

        self.seller = User.objects.create_user(
            username="deadline_seller",
            email="deadline_seller@classifieds.local",
            password="Testpass12345",
        )

    def _first_choice_value(self, field_name, fallback):
        try:
            field = ModerationAppeal._meta.get_field(field_name)
        except Exception:
            return fallback

        choices = list(field.choices or [])
        if choices:
            return choices[0][0]

        return fallback

    def _create_appeal(self, **extra):
        data = {
            "appellant": self.seller,
            "status": ModerationAppeal.Status.PENDING,
        }

        field_names = {field.name for field in ModerationAppeal._meta.fields}

        if "appeal_type" in field_names:
            data["appeal_type"] = self._first_choice_value("appeal_type", "listing")

        if "message" in field_names:
            data["message"] = "Please review this moderation decision."

        data.update(extra)

        return ModerationAppeal.objects.create(**data)

    def test_admin_cannot_make_final_decision_before_active_deadline(self):
        appeal = self._create_appeal(
            extra_evidence_requested_at=timezone.now(),
            extra_evidence_due_at=timezone.now() + timedelta(days=3),
            extra_evidence_request_note="Upload invoice before deadline.",
        )

        self.assertTrue(self.client.login(username="deadline_admin", password="Testpass12345"))

        response = self.client.post(
            reverse("accounts:moderation_appeal_decide", args=[appeal.pk, "reject"]),
            {
                "evidence_reviewed": "yes",
                "decision_note": "Rejecting before deadline should be blocked.",
            },
        )

        self.assertEqual(response.status_code, 302)

        appeal.refresh_from_db()
        self.assertEqual(appeal.status, ModerationAppeal.Status.PENDING)

    def test_admin_can_make_final_decision_after_deadline_passes(self):
        appeal = self._create_appeal(
            extra_evidence_requested_at=timezone.now() - timedelta(days=20),
            extra_evidence_due_at=timezone.now() - timedelta(days=1),
            extra_evidence_request_note="Upload invoice before deadline.",
        )

        self.assertTrue(self.client.login(username="deadline_admin", password="Testpass12345"))

        response = self.client.post(
            reverse("accounts:moderation_appeal_decide", args=[appeal.pk, "reject"]),
            {
                "evidence_reviewed": "yes",
                "decision_note": "Deadline passed and no extra evidence was uploaded.",
                "admin_note": "Automated test decision.",
            },
        )

        self.assertEqual(response.status_code, 302)

        appeal.refresh_from_db()
        self.assertEqual(appeal.status, ModerationAppeal.Status.REJECTED)
        self.assertIsNotNone(appeal.reviewed_at)

    def test_seller_cannot_upload_extra_evidence_after_deadline(self):
        appeal = self._create_appeal(
            extra_evidence_requested_at=timezone.now() - timedelta(days=20),
            extra_evidence_due_at=timezone.now() - timedelta(days=1),
            extra_evidence_request_note="Upload invoice before deadline.",
        )

        self.assertTrue(self.client.login(username="deadline_seller", password="Testpass12345"))

        uploaded = SimpleUploadedFile(
            "invoice.pdf",
            b"%PDF-1.4 test file",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("accounts:moderation_appeal_add_extra_evidence", args=[appeal.pk]),
            {"attachments": [uploaded]},
        )

        self.assertEqual(response.status_code, 302)

        appeal.refresh_from_db()
        self.assertIsNone(appeal.extra_evidence_fulfilled_at)
        self.assertEqual(ModerationAppealAttachment.objects.filter(appeal=appeal).count(), 0)

    def test_15_day_reminder_sends_once(self):
        appeal = self._create_appeal(
            extra_evidence_requested_at=timezone.now(),
            extra_evidence_due_at=timezone.now() + timedelta(days=14),
            extra_evidence_request_note="Upload invoice before deadline.",
        )

        out = StringIO()
        call_command("send_appeal_evidence_deadline_reminders", stdout=out)

        appeal.refresh_from_db()
        self.assertIsNotNone(appeal.extra_evidence_reminder_sent_at)

        first_notice_count = ModerationNotice.objects.count()

        out = StringIO()
        call_command("send_appeal_evidence_deadline_reminders", stdout=out)

        self.assertEqual(ModerationNotice.objects.count(), first_notice_count)

    def test_no_reminder_when_deadline_is_more_than_15_days_away(self):
        appeal = self._create_appeal(
            extra_evidence_requested_at=timezone.now(),
            extra_evidence_due_at=timezone.now() + timedelta(days=16),
            extra_evidence_request_note="Upload invoice before deadline.",
        )

        out = StringIO()
        call_command("send_appeal_evidence_deadline_reminders", stdout=out)

        appeal.refresh_from_db()
        self.assertIsNone(appeal.extra_evidence_reminder_sent_at)
        self.assertEqual(ModerationNotice.objects.count(), 0)

    def test_overdue_notice_sends_once(self):
        appeal = self._create_appeal(
            extra_evidence_requested_at=timezone.now() - timedelta(days=20),
            extra_evidence_due_at=timezone.now() - timedelta(days=1),
            extra_evidence_request_note="Upload invoice before deadline.",
        )

        out = StringIO()
        call_command("send_appeal_evidence_deadline_reminders", stdout=out)

        appeal.refresh_from_db()
        self.assertIsNotNone(appeal.extra_evidence_overdue_notice_sent_at)

        first_notice_count = ModerationNotice.objects.count()

        out = StringIO()
        call_command("send_appeal_evidence_deadline_reminders", stdout=out)

        self.assertEqual(ModerationNotice.objects.count(), first_notice_count)
