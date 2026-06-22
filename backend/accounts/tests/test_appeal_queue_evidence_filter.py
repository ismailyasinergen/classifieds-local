# APPEAL_QUEUE_EVIDENCE_FILTER_V95_TESTS
import zipfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import ModerationAppeal, ModerationAppealAttachment


class ModerationAppealQueueEvidenceFilterTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="v95-appeal-evidence-admin@classifieds.local",
            username="v95_appeal_evidence_admin",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.appellant = User.objects.create_user(
            email="v95-appeal-evidence-user@classifieds.local",
            username="v95_appeal_evidence_user",
            password="Testpass12345",
        )
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin)
        self.queue_url = reverse("accounts:moderation_appeal_queue")
        self.export_url = reverse("accounts:moderation_appeal_export_csv")
        self.bulk_zip_url = reverse("accounts:moderation_appeal_bulk_evidence_zip")

    def _appeal(self, message):
        return ModerationAppeal.objects.create(
            appellant=self.appellant,
            message=message,
            status=ModerationAppeal.Status.PENDING,
        )

    def _attach(self, appeal, name):
        attachment = ModerationAppealAttachment(
            appeal=appeal,
            original_name=name,
            content_type="application/pdf",
            size=21,
        )
        attachment.file.save(name, ContentFile(b"%PDF-1.4 v95 evidence"), save=True)
        return attachment

    def test_queue_has_evidence_filter_shows_only_appeals_with_files(self):
        with_evidence = self._appeal("v95 appeal with evidence")
        self._attach(with_evidence, "v95-has-evidence.pdf")
        self._appeal("v95 appeal without evidence")

        response = self.client.get(self.queue_url, {"evidence": "has_evidence"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v95 appeal with evidence")
        self.assertContains(response, "1 file(s)")
        self.assertNotContains(response, "v95 appeal without evidence")
        self.assertEqual(response.context["paginator"].count, 1)
        self.assertEqual(response.context["selected_evidence"], "has_evidence")

    def test_queue_no_evidence_filter_shows_only_appeals_without_files(self):
        with_evidence = self._appeal("v95 appeal with evidence hidden from no evidence")
        self._attach(with_evidence, "v95-hidden-evidence.pdf")
        self._appeal("v95 appeal without evidence visible")

        response = self.client.get(self.queue_url, {"evidence": "no_evidence"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "v95 appeal without evidence visible")
        self.assertContains(response, "0 file(s)")
        self.assertNotContains(response, "v95 appeal with evidence hidden from no evidence")
        self.assertEqual(response.context["paginator"].count, 1)
        self.assertEqual(response.context["selected_evidence"], "no_evidence")

    def test_csv_export_reuses_has_evidence_filter(self):
        with_evidence = self._appeal("v95 export appeal with evidence")
        self._attach(with_evidence, "v95-export-evidence.pdf")
        self._appeal("v95 export appeal without evidence")

        response = self.client.get(self.export_url, {"evidence": "has_evidence"})

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("appeal_id,status,appeal_type,created_at", body)
        self.assertIn("v95 export appeal with evidence", body)
        self.assertIn("v95-export-evidence.pdf", body)
        self.assertNotIn("v95 export appeal without evidence", body)

    def test_bulk_evidence_zip_reuses_no_evidence_filter(self):
        with_evidence = self._appeal("v95 zip appeal with evidence hidden")
        self._attach(with_evidence, "v95-hidden-from-no-evidence-zip.pdf")
        no_evidence = self._appeal("v95 zip appeal without evidence visible")

        response = self.client.get(self.bulk_zip_url, {"evidence": "no_evidence"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")

        archive = zipfile.ZipFile(BytesIO(response.content))
        names = archive.namelist()
        summary_name = next(name for name in names if name.endswith(".csv"))
        summary = archive.read(summary_name).decode("utf-8")

        self.assertIn(f"appeal_{no_evidence.pk:04d}/NO_EVIDENCE_FILES.txt", names)
        self.assertIn(f"{no_evidence.pk},Pending", summary)
        self.assertNotIn(f"{with_evidence.pk},Pending", summary)
        self.assertFalse(
            any("v95-hidden-from-no-evidence-zip.pdf" in name for name in names)
        )
