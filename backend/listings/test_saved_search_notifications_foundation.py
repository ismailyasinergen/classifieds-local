from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from listings.models import SavedSearch


class SavedSearchNotificationsFoundationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="saved-search-alert-buyer-v80@classifieds.local",
            username="saved_search_alert_buyer_v80",
            password="Testpass12345",
        )
        self.other_user = User.objects.create_user(
            email="saved-search-alert-other-v80@classifieds.local",
            username="saved_search_alert_other_v80",
            password="Testpass12345",
        )
        self.vehicles, _ = Category.objects.get_or_create(
            slug="vehicles",
            defaults={"name": "Vehicles"},
        )
        self.cars, _ = Category.objects.get_or_create(
            slug="cars",
            defaults={"name": "Cars", "parent": self.vehicles},
        )

    def _saved_search(self, user=None, name="V80 Toyota alerts", enabled=False):
        return SavedSearch.objects.create(
            user=user or self.buyer,
            name=name,
            path=reverse("listings:listing_list"),
            query_params={"category": "cars", "q": "Toyota", "attr_marka": "Toyota"},
            querystring="attr_marka=Toyota&category=cars&q=Toyota",
            email_notifications_enabled=enabled,
        )

    def test_saved_search_notification_fields_default_to_off(self):
        saved_search = self._saved_search()

        self.assertFalse(saved_search.email_notifications_enabled)
        self.assertIsNone(saved_search.last_notification_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)
        self.assertEqual(saved_search.email_notification_status_label, "Email alerts off")

    def test_saved_search_list_shows_email_alert_controls(self):
        self.client.force_login(self.buyer)
        self._saved_search(enabled=False)
        self._saved_search(name="V80 Honda enabled alerts", enabled=True)

        response = self.client.get(reverse("listings:saved_search_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80")
        self.assertContains(response, "Email me when new listings match")
        self.assertContains(response, "Disable email alerts")
        self.assertContains(response, "Email alerts off")
        self.assertContains(response, "Email alerts on")
        self.assertContains(response, "Last checked: not yet")
        self.assertContains(response, "Last email: none yet")
        self.assertContains(response, "1 email alert on")

    def test_owner_can_enable_and_disable_email_alerts(self):
        self.client.force_login(self.buyer)
        saved_search = self._saved_search(enabled=False)
        url = reverse("listings:saved_search_notifications_toggle", args=[saved_search.pk])

        enable_response = self.client.post(
            url,
            {
                "enabled": "on",
                "next": reverse("listings:saved_search_list"),
            },
        )

        self.assertRedirects(enable_response, reverse("listings:saved_search_list"))
        saved_search.refresh_from_db()
        self.assertTrue(saved_search.email_notifications_enabled)

        disable_response = self.client.post(
            url,
            {
                "enabled": "off",
                "next": reverse("listings:saved_search_list"),
            },
        )

        self.assertRedirects(disable_response, reverse("listings:saved_search_list"))
        saved_search.refresh_from_db()
        self.assertFalse(saved_search.email_notifications_enabled)

    def test_notification_toggle_is_owner_scoped(self):
        saved_search = self._saved_search(user=self.other_user, enabled=False)

        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("listings:saved_search_notifications_toggle", args=[saved_search.pk]),
            {"enabled": "on"},
        )

        self.assertEqual(response.status_code, 404)
        saved_search.refresh_from_db()
        self.assertFalse(saved_search.email_notifications_enabled)

    def test_notification_toggle_rejects_unsafe_next_url(self):
        self.client.force_login(self.buyer)
        saved_search = self._saved_search(enabled=False)
        url = reverse("listings:saved_search_notifications_toggle", args=[saved_search.pk])

        response = self.client.post(
            url,
            {
                "enabled": "on",
                "next": "https://evil.example/phishing",
            },
        )

        self.assertRedirects(response, reverse("listings:saved_search_list"))
        saved_search.refresh_from_db()
        self.assertTrue(saved_search.email_notifications_enabled)
