from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchSellerStoreEmailAlertGuardrailTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="saved_search_store_alert_guardrail_v124",
            email="saved-search-store-alert-guardrail-v124@classifieds.local",
            password="StrongPass123!",
        )
        self.saved_search_list_url = reverse("listings:saved_search_list")
        self.listing_browse_url = reverse("listings:listing_list")
        self.store_directory_url = reverse("accounts:seller_store_directory")

    def create_listing_search(self, **overrides):
        defaults = {
            "user": self.user,
            "name": "Desk listings",
            "path": self.listing_browse_url,
            "query_params": {"q": "Desk"},
            "querystring": "q=Desk",
        }
        defaults.update(overrides)
        return SavedSearch.objects.create(**defaults)

    def create_store_search(self, **overrides):
        defaults = {
            "user": self.user,
            "name": "Berlin seller stores",
            "path": self.store_directory_url,
            "query_params": {"location": "Berlin", "verified_only": "1"},
            "querystring": "location=Berlin&verified_only=1",
        }
        defaults.update(overrides)
        return SavedSearch.objects.create(**defaults)

    def test_seller_store_saved_search_hides_listing_email_alert_controls(self):
        store_search = self.create_store_search()
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SELLER_STORE_SAVED_SEARCH_EMAIL_ALERT_GUARDRAILS_V124")
        self.assertContains(response, "Seller stores")
        self.assertContains(
            response,
            "Email alerts are available for listing searches only.",
        )
        self.assertNotContains(
            response,
            reverse("listings:saved_search_notifications_toggle", args=[store_search.pk]),
        )
        self.assertNotContains(response, "Email me when new listings match")
        self.assertNotContains(response, "Disable email alerts")

    def test_listing_saved_search_keeps_email_alert_controls(self):
        listing_search = self.create_listing_search()
        self.client.force_login(self.user)

        response = self.client.get(self.saved_search_list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Listings")
        self.assertContains(
            response,
            reverse("listings:saved_search_notifications_toggle", args=[listing_search.pk]),
        )
        self.assertContains(response, "Email me when new listings match")

        toggle_response = self.client.post(
            reverse("listings:saved_search_notifications_toggle", args=[listing_search.pk]),
            {
                "enabled": "on",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(toggle_response.status_code, 302)
        listing_search.refresh_from_db()
        self.assertTrue(listing_search.email_notifications_enabled)

        response = self.client.get(self.saved_search_list_url)
        self.assertContains(response, "Disable email alerts")

    def test_toggle_endpoint_refuses_seller_store_saved_search_alerts(self):
        store_search = self.create_store_search()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("listings:saved_search_notifications_toggle", args=[store_search.pk]),
            {
                "enabled": "on",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], self.saved_search_list_url)
        store_search.refresh_from_db()
        self.assertFalse(store_search.email_notifications_enabled)

    def test_toggle_endpoint_turns_off_legacy_seller_store_alert_flag(self):
        store_search = self.create_store_search(email_notifications_enabled=True)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("listings:saved_search_notifications_toggle", args=[store_search.pk]),
            {
                "enabled": "on",
                "next": self.saved_search_list_url,
            },
        )

        self.assertEqual(response.status_code, 302)
        store_search.refresh_from_db()
        self.assertFalse(store_search.email_notifications_enabled)
