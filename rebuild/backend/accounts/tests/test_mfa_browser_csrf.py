"""Browser-compatible privacy policy must not disable same-origin CSRF proof."""
from allauth.account.models import EmailAddress
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import User


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class MFAReferrerCSRFTests(TestCase):
    def setUp(self):
        self.password = "Synthetic-browser-csrf-password-72"
        self.user = User.objects.create_user(email="mfa-csrf@example.invalid", password=self.password)
        EmailAddress.objects.create(user=self.user, email=self.user.email, primary=True, verified=True)
        self.host = "localhost:8089"
        self.origin = "http://localhost:8089"

    def prepared_client(self):
        client = Client(enforce_csrf_checks=True, HTTP_HOST=self.host)
        response = client.get(reverse("account_login"))
        self.assertEqual(response.status_code, 200)
        token = client.cookies[settings.CSRF_COOKIE_NAME].value
        return client, token, response

    def test_account_form_referrer_policy_preserves_same_origin_and_blocks_cross_origin(self):
        client, token, response = self.prepared_client()
        self.assertEqual(response["Referrer-Policy"], "same-origin")
        login = client.post(reverse("account_login"), {
            "login": self.user.email, "password": self.password, "csrfmiddlewaretoken": token,
        }, HTTP_ORIGIN=self.origin)
        self.assertEqual(login.status_code, 302)
        for route in ("accounts:security", "mfa_activate_totp", "account_logout"):
            with self.subTest(route=route):
                response = client.get(reverse(route))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Referrer-Policy"], "same-origin")
                self.assertIn("private", response["Cache-Control"])
                self.assertIn("no-store", response["Cache-Control"])
                self.assertEqual(response["X-Content-Type-Options"], "nosniff")

    def test_real_csrf_allows_valid_same_origin_password_form(self):
        client, token, _ = self.prepared_client()
        response = client.post(reverse("account_login"), {
            "login": self.user.email, "password": self.password, "csrfmiddlewaretoken": token,
        }, HTTP_ORIGIN=self.origin)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(client.session["_auth_user_id"]), self.user.pk)

    def test_null_foreign_or_missing_csrf_token_cannot_authenticate(self):
        for origin, include_token in (("null", True), ("https://foreign.example.invalid", True), (self.origin, False)):
            with self.subTest(origin_class="same" if origin == self.origin else "untrusted", token_present=include_token):
                client, token, _ = self.prepared_client()
                data = {"login": self.user.email, "password": self.password}
                if include_token:
                    data["csrfmiddlewaretoken"] = token
                response = client.post(reverse("account_login"), data, HTTP_ORIGIN=origin)
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("_auth_user_id", client.session)
