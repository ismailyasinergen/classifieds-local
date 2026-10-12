from uuid import uuid4

from django.test import TestCase
from accounts.tests.mfa_support import MFATestIsolationMixin, authenticate_client
from moderation.models import Appeal, AppealDecision
from moderation.tests.test_appeals import AppealCalls, AppealFixtures


class AppealHTTPTests(MFATestIsolationMixin, AppealCalls, AppealFixtures, TestCase):
    def test_subject_page_safe_appeal_and_foreign_uuid(self):
        self.client.force_login(self.owner)
        url = f"/inceleme/kararlarim/{self.decision.pk}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.report.explanation)
        self.assertNotContains(response, self.reporter.email)
        data = {"explanation": "<script>özel itiraz</script>", "client_token": str(uuid4())}
        response = self.client.post(url + "itiraz/", data)
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get(response["Location"]), "&lt;script&gt;özel itiraz&lt;/script&gt;")
        self.assertEqual(self.client.post(url + "itiraz/", data)["Location"], response["Location"])
        self.assertEqual(Appeal.objects.count(), 1)
        self.client.logout()
        self.client.force_login(self.reporter)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(response["Location"]).status_code, 404)

    def test_independent_mfa_reviewer_and_get_no_decision(self):
        appeal = self.appeal().record
        url = f"/inceleme/itirazlar/{appeal.pk}/"
        self.client.force_login(self.appeal_reviewer)
        self.assertEqual(self.client.post(url, {"outcome": "revoke", "reason": "Gerekçe"}).status_code, 403)
        authenticate_client(self.client, self.appeal_reviewer)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(AppealDecision.objects.count(), 0)
        self.assertEqual(self.client.post(url, {"outcome": "revoke", "reason": "Gerekçe"}).status_code, 302)
        self.assertEqual(AppealDecision.objects.count(), 1)
        self.assertEqual(self.client.post(url, {"outcome": "uphold", "reason": "Değişti"}).status_code, 409)
        self.assertEqual(self.client.delete(url).status_code, 405)
