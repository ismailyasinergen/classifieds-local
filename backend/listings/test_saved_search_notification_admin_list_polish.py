# SAVED_SEARCH_NOTIFICATION_ADMIN_LIST_POLISH_V91_TESTS
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase

from listings.admin import SavedSearchAdmin
from listings.models import SavedSearch


class SavedSearchNotificationAdminListPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="v91-admin-list@classifieds.local",
            username="v91_admin_list",
            password="Testpass12345",
        )
        self.model_admin = SavedSearchAdmin(SavedSearch, AdminSite())

    def _saved_search(self, enabled):
        return SavedSearch.objects.create(
            user=self.user,
            name="V91 admin list polish",
            path="/listings/",
            query_params={"q": "Toyota"},
            querystring="q=Toyota",
            email_notifications_enabled=enabled,
        )

    def test_admin_list_display_uses_clear_notification_preference_column(self):
        self.assertIn("notification_preference", self.model_admin.list_display)
        self.assertNotIn("email_notifications_enabled", self.model_admin.list_display)
        self.assertLess(
            self.model_admin.list_display.index("notification_status"),
            self.model_admin.list_display.index("notification_preference"),
        )

    def test_notification_preference_display_metadata_is_admin_friendly(self):
        field = self.model_admin.notification_preference

        self.assertEqual(field.short_description, "Email alerts")
        self.assertEqual(field.admin_order_field, "email_notifications_enabled")
        self.assertTrue(field.boolean)

    def test_notification_preference_returns_boolean_state(self):
        enabled = self._saved_search(enabled=True)
        disabled = self._saved_search(enabled=False)

        self.assertIs(self.model_admin.notification_preference(enabled), True)
        self.assertIs(self.model_admin.notification_preference(disabled), False)

    def test_admin_list_uses_select_related_date_hierarchy_and_ordering(self):
        self.assertEqual(self.model_admin.list_select_related, ["user"])
        self.assertEqual(self.model_admin.date_hierarchy, "updated_at")
        self.assertEqual(self.model_admin.ordering, ["-updated_at", "-created_at"])

    def test_admin_search_and_filters_keep_notification_usability_fields(self):
        self.assertIn("user__email", self.model_admin.search_fields)
        self.assertIn("user__username", self.model_admin.search_fields)
        self.assertIn("querystring", self.model_admin.search_fields)
        self.assertIn("email_notifications_enabled", self.model_admin.list_filter)
        self.assertIn("last_notification_checked_at", self.model_admin.list_filter)
        self.assertIn("last_notification_sent_at", self.model_admin.list_filter)
