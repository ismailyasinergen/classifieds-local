from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import ModerationNotice


class ModerationNoticeRedirectSecurityR003Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="r003-notice-user",
            password="StrongPass123!",
        )
        self.notice = ModerationNotice.objects.create(
            recipient=self.user,
            title="R003 notice",
            body="Redirect safety regression fixture.",
        )
        self.client.force_login(self.user)
        self.url = reverse(
            "accounts:moderation_notice_mark_read",
            kwargs={"pk": self.notice.pk},
        )

    def test_external_next_target_falls_back_to_notice_list(self):
        response = self.client.post(
            self.url,
            {"next": "https://attacker.example/phishing"},
        )

        self.assertRedirects(
            response,
            reverse("accounts:moderation_notices"),
            fetch_redirect_response=False,
        )
        self.notice.refresh_from_db()
        self.assertTrue(self.notice.is_read)

    def test_same_origin_relative_next_target_is_preserved(self):
        response = self.client.post(
            self.url,
            {"next": "/accounts/notices/?read=unread"},
        )

        self.assertRedirects(
            response,
            "/accounts/notices/?read=unread",
            fetch_redirect_response=False,
        )
