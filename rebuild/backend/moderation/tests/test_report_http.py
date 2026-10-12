from uuid import uuid4
from unittest.mock import patch

from allauth.account.models import EmailAddress
from django.test import Client, TestCase, override_settings

from accounts.tests.mfa_support import MFATestIsolationMixin, authenticate_client
from moderation.models import ContentReport, ReportDecision
from moderation.tests.case_helpers import CaseFixtures
from moderation.tests.test_reports import ReportCalls


class ReportHTTPTests(MFATestIsolationMixin, ReportCalls, CaseFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.url = f"/inceleme/bildir/ilan/{self.public.pk}/"
        self.data = dict(reason_code="other", explanation="  Deneme açıklaması  ", client_token=str(uuid4()))

    def test_case_media_uses_the_same_login_and_verification_boundary(self):
        report = self.report_listing().record
        url = f"/inceleme/bildirimler/{report.pk}/gorsel/999999/"
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.reporter)
        EmailAddress.objects.filter(user=self.reporter).update(verified=False)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("no-store", response["Cache-Control"])

    def test_login_verification_methods_and_get_no_mutation(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.reporter)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        self.assertEqual(ContentReport.objects.count(), 0)
        self.assertEqual(self.client.put(self.url).status_code, 405)
        EmailAddress.objects.filter(user=self.reporter).update(verified=False)
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(self.client.post(self.url, self.data).status_code, 403)
        self.assertEqual(ContentReport.objects.count(), 0)

    def test_valid_replay_alias_conflict_and_invalid_preserve_input(self):
        self.client.force_login(self.reporter)
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)
        report = ContentReport.objects.get()
        self.assertEqual(report.explanation, "Deneme açıklaması")
        self.assertEqual(self.client.post(self.url, self.data)["Location"], response["Location"])
        alias = self.client.post(self.url, self.data | {"client_token": str(uuid4()), "explanation": "Yeni"}, follow=True)
        self.assertContains(alias, "Bu içerik için önceki bildiriminiz gösteriliyor; yeni açıklama kaydedilmedi.")
        conflict = self.client.post(self.url, self.data | {"explanation": "Farklı"})
        self.assertEqual(conflict.status_code, 409)
        self.assertContains(conflict, self.data["client_token"], status_code=409)
        invalid = self.client.post(self.url, self.data | {"reason_code": "invalid"})
        self.assertContains(invalid, "Deneme açıklaması")
        self.assertContains(invalid, 'id="case-errors"')
        self.assertEqual(ContentReport.objects.count(), 1)

    @override_settings(PILOT_REPORTS_PER_DAY=1)
    def test_quota_positive_retry_and_unchanged_token(self):
        self.report_message()
        self.client.force_login(self.owner)
        message = self.next_message()
        response = self.client.post(f"/inceleme/bildir/mesaj/{message.pk}/", self.data)
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response["Retry-After"]), 0)
        self.assertContains(response, self.data["client_token"], status_code=429)
        self.assertContains(response, "Deneme açıklaması", status_code=429)

    def test_csrf_real_token_origin_and_missing_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.reporter)
        self.assertEqual(client.get(self.url).status_code, 200)
        token = client.cookies["csrftoken"].value
        self.assertEqual(client.post(self.url, self.data).status_code, 403)
        for origin in ("null", "https://foreign.example"):
            self.assertEqual(client.post(self.url, self.data | {"csrfmiddlewaretoken": token}, HTTP_ORIGIN=origin).status_code, 403)
        self.assertEqual(ContentReport.objects.count(), 0)
        self.assertEqual(client.post(self.url, self.data | {"csrfmiddlewaretoken": token}, HTTP_ORIGIN="http://testserver").status_code, 302)

    def test_foreign_histories_and_new_role_password_only_post(self):
        report = self.report_listing().record
        url = f"/inceleme/bildirimler/{report.pk}/"
        self.grant(self.case_reviewer, "review_reports")
        self.client.force_login(self.case_reviewer)
        self.assertEqual(self.client.post(url, {"action": "no_action", "reason": "Yeterli neden"}).status_code, 403)
        self.assertEqual(ReportDecision.objects.count(), 0)
        authenticate_client(self.client, self.case_reviewer)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(ReportDecision.objects.count(), 0)
        self.assertEqual(self.client.post(url, {"action": "no_action", "reason": "Yeterli neden"}).status_code, 302)
        self.client.logout()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(f"/inceleme/bildirimlerim/{report.pk}/").status_code, 404)
        self.assertEqual(self.client.get(f"/inceleme/bildirimlerim/{uuid4()}/").status_code, 404)

    def test_own_and_foreign_message_forms_are_denied(self):
        self.client.force_login(self.reporter)
        self.assertEqual(self.client.get(f"/inceleme/bildir/mesaj/{self.message.pk}/").status_code, 403)
        self.client.logout()
        self.client.force_login(self.case_reviewer)
        self.assertEqual(self.client.get(f"/inceleme/bildir/mesaj/{self.message.pk}/").status_code, 403)
        self.client.logout()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(f"/inceleme/bildir/mesaj/{self.message.pk}/").status_code, 200)
