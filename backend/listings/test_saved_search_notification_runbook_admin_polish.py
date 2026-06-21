# SAVED_SEARCH_NOTIFICATION_RUNBOOK_ADMIN_POLISH_V86_TESTS
from datetime import timedelta
from pathlib import Path

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.admin import SavedSearchAdmin
from listings.models import SavedSearch


class SavedSearchNotificationRunbookAdminPolishTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="v86-admin-polish@classifieds.local",
            username="v86_admin_polish",
            password="Testpass12345",
        )
        self.category = Category.objects.create(name="Cars", slug="cars")
        self.saved_search = SavedSearch.objects.create(
            user=self.user,
            name="V86 admin guidance search",
            path=reverse("listings:listing_list"),
            query_params={"category": "cars", "q": "Toyota"},
            querystring="category=cars&q=Toyota",
            email_notifications_enabled=True,
            last_notification_checked_at=timezone.now() - timedelta(days=1),
        )

    def test_admin_notification_run_guidance_mentions_manual_dry_run_and_failure_isolation(self):
        model_admin = SavedSearchAdmin(SavedSearch, AdminSite())

        html = str(model_admin.notification_run_guidance(self.saved_search))

        self.assertIn("Notifications are operator-triggered", html)
        self.assertIn("--send", html)
        self.assertIn("dry-run", html)
        self.assertIn("Send failures are isolated", html)
        self.assertIn("SAVED_SEARCH_NOTIFICATIONS.md", html)

    def test_admin_readonly_fields_include_notification_run_guidance(self):
        model_admin = SavedSearchAdmin(SavedSearch, AdminSite())

        self.assertIn("notification_run_guidance", model_admin.readonly_fields)
        self.assertLess(
            model_admin.readonly_fields.index("notification_run_guidance"),
            model_admin.readonly_fields.index("notification_status"),
        )

    def test_notification_run_guidance_mentions_timestamp_safety_and_runbook(self):
        model_admin = SavedSearchAdmin(SavedSearch, AdminSite())

        html = str(model_admin.notification_run_guidance(self.saved_search))

        self.assertIn("failed sends do not update timestamps", html)
        self.assertIn("runbook", html)
        self.assertIn("SAVED_SEARCH_NOTIFICATIONS.md", html)
