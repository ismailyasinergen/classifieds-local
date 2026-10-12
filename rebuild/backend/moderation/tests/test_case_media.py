from tempfile import TemporaryDirectory

from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings

from media.models import MediaAsset, RevisionImage
from media.views import _authorized_asset
from moderation.models import CaseAuditEvent
from moderation.tests.case_helpers import CaseFixtures
from moderation.tests.test_appeals import AppealCalls
from moderation.tests.test_case_access import boundary


class CaseMediaTests(AppealCalls, CaseFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(PRIVATE_MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.grant(self.case_reviewer, "review_reports")
        self.grant(self.appeal_reviewer, "review_appeals")
        self.asset = MediaAsset.objects.create(owner=self.owner, original="originals/unused.bin",
            source_mime="image/jpeg", source_bytes=7, width=1, height=1, state="ready")
        self.asset.derivative.save("cases/preview.jpg", ContentFile(b"preview"), save=True)
        RevisionImage.objects.create(revision=self.public, asset=self.asset, position=0)
        self.report = self.report_listing().record

    def request(self, actor):
        request = RequestFactory().get("/inceleme/bildirimler/gorsel/")
        request.user = actor
        return request

    def test_authorized_case_streams_only_derivative_and_audits_metadata(self):
        media = boundary(self, "case_media")
        response = media.case_media(self.request(self.case_reviewer), self.report.pk, self.asset.pk)
        try:
            self.assertEqual(b"".join(response.streaming_content), b"preview")
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response["Referrer-Policy"], "same-origin")
        finally:
            response.file_to_stream.close()
        self.assertEqual(CaseAuditEvent.objects.filter(action="evidence_media_viewed").count(), 1)
        with self.assertRaises(PermissionDenied):
            _authorized_asset(self.request(self.case_reviewer), self.asset.pk)

    def test_reporter_owner_foreign_asset_and_missing_derivative_denied(self):
        media = boundary(self, "case_media")
        for actor in (self.reporter, self.owner, self.reviewer):
            with self.assertRaises(PermissionDenied):
                media.case_media(self.request(actor), self.report.pk, self.asset.pk)
        with self.assertRaises(Http404):
            media.case_media(self.request(self.case_reviewer), self.report.pk, self.asset.pk + 999)
        self.asset.derivative.delete(save=False)
        with self.assertRaises(Http404):
            media.case_media(self.request(self.case_reviewer), self.report.pk, self.asset.pk)
        self.assertEqual(CaseAuditEvent.objects.filter(action="evidence_media_viewed").count(), 0)

    def test_nonready_or_unlinked_asset_denied_even_if_snapshot_mentions_it(self):
        media = boundary(self, "case_media")
        self.asset.state = "pending"
        self.asset.save()
        with self.assertRaises(Http404):
            media.case_media(self.request(self.case_reviewer), self.report.pk, self.asset.pk)
        self.asset.state = "ready"
        self.asset.save()
        RevisionImage.objects.filter(revision=self.public, asset=self.asset).delete()
        with self.assertRaises(Http404):
            media.case_media(self.request(self.case_reviewer), self.report.pk, self.asset.pk)

    def test_appeal_reviewer_uses_exact_appeal_relation(self):
        media = boundary(self, "case_media")
        self.decision = self.decide(self.report, action="hide_listing", expected_public_revision_id=self.public.pk)
        appeal = self.appeal().record
        response = media.appeal_case_media(self.request(self.appeal_reviewer), appeal.pk, self.asset.pk)
        response.file_to_stream.close()
        with self.assertRaises(PermissionDenied):
            media.case_media(self.request(self.appeal_reviewer), self.report.pk, self.asset.pk)
