# SAVED_SEARCH_NOTIFICATION_ADMIN_CHANGELIST_SMOKE_V92_TESTS
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from listings.models import SavedSearch


class SavedSearchNotificationAdminChangelistSmokeTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            email="v92-admin@classifieds.local",
            username="v92_admin",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.owner = User.objects.create_user(
            email="v92-owner@classifieds.local",
            username="v92_owner",
            password="Testpass12345",
        )
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin_user)
        self.changelist_url = reverse("admin:listings_savedsearch_changelist")

    def _saved_search(self, name, enabled=False):
        return SavedSearch.objects.create(
            user=self.owner,
            name=name,
            path="/listings/",
            query_params={"q": name},
            querystring=f"q={name}",
            email_notifications_enabled=enabled,
        )

    def test_admin_changelist_renders_email_alerts_column_and_actions(self):
        self._saved_search("V92 enabled changelist smoke", enabled=True)
        self._saved_search("V92 disabled changelist smoke", enabled=False)

        response = self.client.get(self.changelist_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Email alerts")
        self.assertContains(response, "Notification status")
        self.assertContains(response, "Enable email notifications for selected saved searches")
        self.assertContains(response, "Disable email notifications for selected saved searches")
        self.assertContains(response, "V92 enabled changelist smoke")
        self.assertContains(response, "V92 disabled changelist smoke")
        self.assertContains(response, "Enabled, never checked")
        self.assertContains(response, "Disabled")

    def test_admin_changelist_search_finds_saved_search_by_owner_email(self):
        self._saved_search("V92 owner email searchable", enabled=True)

        response = self.client.get(self.changelist_url, {"q": "v92-owner@classifieds.local"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V92 owner email searchable")
        self.assertContains(response, "v92-owner@classifieds.local")

    def test_admin_changelist_enable_action_updates_selected_saved_searches(self):
        first = self._saved_search("V92 enable first", enabled=False)
        second = self._saved_search("V92 enable second", enabled=False)

        response = self.client.post(
            self.changelist_url,
            {
                "action": "enable_saved_search_email_notifications",
                "_selected_action": [str(first.pk), str(second.pk)],
                "index": "0",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertTrue(first.email_notifications_enabled)
        self.assertTrue(second.email_notifications_enabled)
        self.assertContains(response, "Enabled email notifications for 2 saved search(es).")

    def test_admin_changelist_disable_action_updates_selected_saved_searches(self):
        first = self._saved_search("V92 disable first", enabled=True)
        second = self._saved_search("V92 disable second", enabled=True)

        response = self.client.post(
            self.changelist_url,
            {
                "action": "disable_saved_search_email_notifications",
                "_selected_action": [str(first.pk), str(second.pk)],
                "index": "0",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.email_notifications_enabled)
        self.assertFalse(second.email_notifications_enabled)
        self.assertContains(response, "Disabled email notifications for 2 saved search(es).")
