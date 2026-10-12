from unittest.mock import patch

from django.core.paginator import Page, Paginator
from django.db.models import Model, QuerySet
from django.shortcuts import render
from django.test import TestCase

from accounts.tests.mfa_support import MFATestIsolationMixin, authenticate_client
from moderation.case_evidence import read_case_evidence
from moderation.tests.test_appeals import AppealCalls, AppealFixtures


class ReviewRegressionTests(MFATestIsolationMixin, AppealCalls, AppealFixtures, TestCase):
    def assertContains(self, response, text, status_code=200):
        self.assertEqual(response.status_code, status_code)
        self.assertTrue(text in response.content.decode(), "Expected safe UI text is absent")

    def test_history_context_cannot_reach_raw_records_through_pagination(self):
        self.appeal()

        def safe(value):
            self.assertNotIsInstance(value, (Model, QuerySet, Page, Paginator))
            if isinstance(value, dict):
                for item in value.values():
                    safe(item)
            elif isinstance(value, (tuple, list)):
                for item in value:
                    safe(item)

        for actor, route in ((self.owner, "kararlarim"), (self.reporter, "bildirimlerim"),
                             (self.case_reviewer, "bildirimler"), (self.appeal_reviewer, "itirazlar")):
            self.client.logout()
            if actor in (self.case_reviewer, self.appeal_reviewer):
                authenticate_client(self.client, actor)
            else:
                self.client.force_login(actor)
            with patch("moderation.case_http.render", wraps=render) as rendering:
                response = self.client.get(f"/inceleme/{route}/")
            self.assertEqual(response.status_code, 200)
            context = rendering.call_args.args[2]
            safe(context)
            if route == "kararlarim":
                self.assertNotIn(self.report.explanation, str(context))
                self.assertNotIn(self.reporter.email, str(context))

    def test_reviewer_sees_snapshot_separate_from_current_listing_state(self):
        current = read_case_evidence(actor=self.case_reviewer, report_id=self.report.pk)
        self.assertEqual(current.get("current_target"), {
            "public_revision_id": self.public.pk, "lifecycle": "live", "visible": False,
            "reported_revision_is_current": True,
        })
        newer = self.submit(self.edit(self.public, title="Yeni sürüm"))
        self.approve(newer, expected=self.public.pk)
        authenticate_client(self.client, self.case_reviewer)
        response = self.client.get(f"/inceleme/bildirimler/{self.report.pk}/")
        self.assertContains(response, "Bildirilen sürüm artık güncel değil")
        self.assertEqual(response.context["case"]["evidence"]["revision_id"], self.public.pk)
        self.assertEqual(response.context["case"]["current_target"]["public_revision_id"], newer.pk)

    def test_conflicting_report_post_keeps_error_and_submitted_reason_visible(self):
        authenticate_client(self.client, self.case_reviewer)
        response = self.client.post(f"/inceleme/bildirimler/{self.report.pk}/", {
            "action": "no_action", "reason": "Farklı karar gerekçesi",
        })
        self.assertContains(response, 'id="case-errors"', status_code=409)
        self.assertContains(response, "Farklı karar gerekçesi", status_code=409)
        self.assertContains(response, self.decision.reason, status_code=409)

    def test_conflicting_appeal_post_keeps_error_and_submitted_reason_visible(self):
        appeal = self.appeal().record
        self.resolve(appeal)
        authenticate_client(self.client, self.appeal_reviewer)
        response = self.client.post(f"/inceleme/itirazlar/{appeal.pk}/", {
            "outcome": "uphold", "reason": "Farklı itiraz gerekçesi",
        })
        self.assertContains(response, 'id="case-errors"', status_code=409)
        self.assertContains(response, "Farklı itiraz gerekçesi", status_code=409)

    def test_submission_forms_warn_against_sensitive_input(self):
        self.client.force_login(self.owner)
        for route in (f"/inceleme/bildir/mesaj/{self.message.pk}/",
                      f"/inceleme/kararlarim/{self.decision.pk}/itiraz/"):
            response = self.client.get(route)
            self.assertContains(response, "Kişisel belge, parola veya doğrulama kodu paylaşmayın.")
