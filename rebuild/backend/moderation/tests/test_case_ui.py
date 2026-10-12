from django.test import TestCase
from django.urls import reverse
from moderation.tests.case_helpers import CaseFixtures
from moderation.tests.test_reports import ReportCalls


class CaseUITests(ReportCalls, CaseFixtures, TestCase):
    def test_pagination_preserves_query_and_escapes_report_text(self):
        self.client.force_login(self.owner)
        self.report_message(explanation="<script>canary</script>")
        for _ in range(12):
            self.report_message(message_id=self.next_message().pk)
        response = self.client.get("/inceleme/bildirimlerim/?filter=all")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["items"]), 12)
        self.assertContains(response, "filter=all&amp;page=2")
        second = self.client.get("/inceleme/bildirimlerim/?filter=all&page=2")
        self.assertEqual(len(second.context["items"]), 1)
        self.assertNotContains(second, "<script>canary</script>")

    def test_received_only_message_report_link_and_focus_poll_guard(self):
        url = reverse("conversations:history", args=[self.conversation.pk])
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertContains(response, f"/inceleme/bildir/mesaj/{self.message.pk}/")
        self.assertContains(response, "!this.contains(document.activeElement)")
        self.client.logout()
        self.client.force_login(self.reporter)
        self.assertNotContains(self.client.get(url), f"/inceleme/bildir/mesaj/{self.message.pk}/")

    def test_report_form_labels_hidden_token_and_listing_link(self):
        self.client.force_login(self.reporter)
        url = f"/inceleme/bildir/ilan/{self.public.pk}/"
        response = self.client.get(url)
        self.assertContains(response, 'for="id_explanation"')
        self.assertContains(response, 'name="client_token"')
        self.assertContains(response, "Bildirim gönder")
        self.assertContains(self.client.get(reverse("listings:detail", args=[self.listing.pk])), url)
