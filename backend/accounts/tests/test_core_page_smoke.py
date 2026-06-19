from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CorePageSmokeTests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@classifieds.local",
            password="Testpass12345",
        )

        self.seller = User.objects.create_user(
            username="demo_seller@classifieds.local",
            email="demo_seller@classifieds.local",
            password="demo12345",
        )

        self.buyer = User.objects.create_user(
            username="buyer1@classifieds.local",
            email="buyer1@classifieds.local",
            password="Testpass12345",
        )

    def assert_page_ok(self, url_name, user=None, args=None):
        if user is not None:
            self.client.force_login(user)

        response = self.client.get(reverse(url_name, args=args or []))
        self.assertIn(
            response.status_code,
            {200, 302},
            msg=f"{url_name} returned {response.status_code}",
        )

        self.client.logout()

    def test_public_pages_render(self):
        self.assert_page_ok("pages:home")
        self.assert_page_ok("accounts:login")
        self.assert_page_ok("accounts:register")

    def test_buyer_account_pages_render(self):
        self.assert_page_ok("accounts:dashboard", self.buyer)
        self.assert_page_ok("accounts:profile", self.buyer)
        self.assert_page_ok("accounts:saved_listings", self.buyer)
        self.assert_page_ok("accounts:moderation_notices", self.buyer)
        self.assert_page_ok("accounts:my_moderation_appeals", self.buyer)

    def test_seller_pages_render(self):
        self.assert_page_ok("accounts:dashboard", self.seller)
        self.assert_page_ok("accounts:my_listings", self.seller)
        self.assert_page_ok("accounts:verification_request", self.seller)

    def test_admin_trust_safety_pages_render(self):
        self.assert_page_ok("accounts:trust_safety_dashboard", self.admin)
        self.assert_page_ok("accounts:trust_safety_action_log", self.admin)
        self.assert_page_ok("accounts:trust_safety_event_log", self.admin)
        self.assert_page_ok("accounts:moderation_appeal_queue", self.admin)
        # Seller-report admin queue currently uses the legacy route name
        # "user_report_queue" in accounts/urls.py.
        self.assert_page_ok("accounts:user_report_queue", self.admin)
