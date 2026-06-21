# SAVED_SEARCH_NOTIFICATION_ADMIN_ACTIONS_V89_TESTS
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from listings.admin import (
    SavedSearchAdmin,
    disable_saved_search_email_notifications,
    enable_saved_search_email_notifications,
)
from listings.models import SavedSearch


class SavedSearchNotificationAdminActionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="v89-admin-actions@classifieds.local",
            username="v89_admin_actions",
            password="Testpass12345",
        )
        self.request = RequestFactory().post("/admin/listings/savedsearch/")
        self.model_admin = SavedSearchAdmin(SavedSearch, AdminSite())
        self.messages = []
        self.model_admin.message_user = lambda request, message, *args, **kwargs: self.messages.append(str(message))

    def _saved_search(self, name, enabled=False):
        return SavedSearch.objects.create(
            user=self.user,
            name=name,
            path="/listings/",
            query_params={"q": name},
            querystring=f"q={name}",
            email_notifications_enabled=enabled,
        )

    def test_admin_exposes_notification_bulk_actions(self):
        self.assertIn(enable_saved_search_email_notifications, self.model_admin.actions)
        self.assertIn(disable_saved_search_email_notifications, self.model_admin.actions)

    def test_enable_saved_search_email_notifications_action_updates_queryset(self):
        disabled_one = self._saved_search("disabled-one", enabled=False)
        disabled_two = self._saved_search("disabled-two", enabled=False)
        already_enabled = self._saved_search("already-enabled", enabled=True)
        queryset = SavedSearch.objects.filter(pk__in=[disabled_one.pk, disabled_two.pk, already_enabled.pk])

        enable_saved_search_email_notifications(self.model_admin, self.request, queryset)

        disabled_one.refresh_from_db()
        disabled_two.refresh_from_db()
        already_enabled.refresh_from_db()
        self.assertTrue(disabled_one.email_notifications_enabled)
        self.assertTrue(disabled_two.email_notifications_enabled)
        self.assertTrue(already_enabled.email_notifications_enabled)
        self.assertIn("Enabled email notifications for 3 saved search(es).", self.messages)

    def test_disable_saved_search_email_notifications_action_updates_queryset(self):
        enabled_one = self._saved_search("enabled-one", enabled=True)
        enabled_two = self._saved_search("enabled-two", enabled=True)
        already_disabled = self._saved_search("already-disabled", enabled=False)
        queryset = SavedSearch.objects.filter(pk__in=[enabled_one.pk, enabled_two.pk, already_disabled.pk])

        disable_saved_search_email_notifications(self.model_admin, self.request, queryset)

        enabled_one.refresh_from_db()
        enabled_two.refresh_from_db()
        already_disabled.refresh_from_db()
        self.assertFalse(enabled_one.email_notifications_enabled)
        self.assertFalse(enabled_two.email_notifications_enabled)
        self.assertFalse(already_disabled.email_notifications_enabled)
        self.assertIn("Disabled email notifications for 3 saved search(es).", self.messages)

    def test_notification_status_reflects_bulk_action_changes(self):
        saved_search = self._saved_search("status-change", enabled=False)

        enable_saved_search_email_notifications(
            self.model_admin,
            self.request,
            SavedSearch.objects.filter(pk=saved_search.pk),
        )
        saved_search.refresh_from_db()
        self.assertEqual(self.model_admin.notification_status(saved_search), "Enabled, never checked")

        disable_saved_search_email_notifications(
            self.model_admin,
            self.request,
            SavedSearch.objects.filter(pk=saved_search.pk),
        )
        saved_search.refresh_from_db()
        self.assertEqual(self.model_admin.notification_status(saved_search), "Disabled")
