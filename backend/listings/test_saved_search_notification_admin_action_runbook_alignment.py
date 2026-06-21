# SAVED_SEARCH_NOTIFICATION_ADMIN_ACTION_RUNBOOK_ALIGNMENT_V90_TESTS
from django.test import SimpleTestCase

from listings.admin import (
    disable_saved_search_email_notifications,
    enable_saved_search_email_notifications,
)


class SavedSearchNotificationAdminActionRunbookAlignmentTests(SimpleTestCase):
    def test_admin_action_descriptions_match_runbook_language(self):
        self.assertEqual(
            enable_saved_search_email_notifications.short_description,
            "Enable email notifications for selected saved searches",
        )
        self.assertEqual(
            disable_saved_search_email_notifications.short_description,
            "Disable email notifications for selected saved searches",
        )

    def test_admin_action_names_are_stable_for_runbook_alignment(self):
        self.assertEqual(
            enable_saved_search_email_notifications.__name__,
            "enable_saved_search_email_notifications",
        )
        self.assertEqual(
            disable_saved_search_email_notifications.__name__,
            "disable_saved_search_email_notifications",
        )

    def test_admin_action_functions_are_explicitly_notification_only(self):
        enable_names = enable_saved_search_email_notifications.__code__.co_names
        disable_names = disable_saved_search_email_notifications.__code__.co_names

        self.assertIn("update", enable_names)
        self.assertIn("message_user", enable_names)
        self.assertIn("update", disable_names)
        self.assertIn("message_user", disable_names)
        self.assertNotIn("send_mail", enable_names)
        self.assertNotIn("send_mail", disable_names)
        self.assertNotIn("mark_saved_search_sent", enable_names)
        self.assertNotIn("mark_saved_search_sent", disable_names)
