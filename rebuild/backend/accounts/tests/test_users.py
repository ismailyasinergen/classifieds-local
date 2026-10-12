from django.core import mail
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from accounts.models import User


class UserTests(TestCase):
    def test_create_normalizes_whole_email(self):
        user = User.objects.create_user("  Person@EXAMPLE.COM  ", "StrongExamplePass471!")
        user.refresh_from_db()
        self.assertEqual(user.email, "person@example.com")
        self.assertTrue(user.check_password("StrongExamplePass471!"))

    def test_invalid_or_blank_email_rejected(self):
        for email in ("", "   ", "broken-address", None):
            with self.subTest(email=email), self.assertRaises(ValidationError):
                User.objects.create_user(email, "StrongExamplePass471!")

    def test_direct_save_normalizes_email(self):
        user = User(email="  PERSON@Example.com ")
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.email, "person@example.com")

    def test_case_insensitive_database_constraint(self):
        User.objects.create_user("person@example.com")
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="PERSON@EXAMPLE.COM")])

    def test_database_rejects_blank_email(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.bulk_create([User(email="")])

    def test_superuser_requires_both_privileges(self):
        for flag in ("is_staff", "is_superuser"):
            with self.subTest(flag=flag), self.assertRaises(ValueError):
                User.objects.create_superuser("admin@example.com", **{flag: False})

    def test_root_does_not_expose_account_email(self):
        user = User.objects.create_user("private@example.com")
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, user.email)

    def test_allauth_login_and_signup_routes(self):
        self.assertEqual(self.client.get("/accounts/login/").status_code, 200)
        self.assertEqual(self.client.get("/accounts/signup/").status_code, 200)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_allauth_signup_requires_email_verification(self):
        response = self.client.post("/accounts/signup/", {
            "email": "New@Example.COM", "password1": "StrongExamplePass471!",
            "password2": "StrongExamplePass471!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("confirm-email", response.url)
        self.assertEqual(User.objects.get().email, "new@example.com")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(len(mail.outbox), 1)

    def test_unverified_user_cannot_login(self):
        User.objects.create_user("new@example.com", "StrongExamplePass471!")
        response = self.client.post("/accounts/login/", {
            "login": "new@example.com", "password": "StrongExamplePass471!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn("confirm-email", response.url)
        self.assertNotIn("_auth_user_id", self.client.session)
