# SAVED_SEARCH_NOTIFICATION_SCHEDULING_ADMIN_V84_TESTS
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.admin import SavedSearchAdmin
from listings.models import Listing, SavedSearch


class SavedSearchNotificationSchedulingCommandTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="v84-scheduling-buyer@classifieds.local",
            username="v84_scheduling_buyer",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            email="v84-scheduling-seller@classifieds.local",
            username="v84_scheduling_seller",
            password="Testpass12345",
        )
        self.vehicles = Category.objects.create(name="Vehicles", slug="vehicles")
        self.cars = Category.objects.create(name="Cars", slug="cars", parent=self.vehicles)

    def _saved_search(self, name, *, brand="Toyota", checked_delta=timedelta(days=-2)):
        return SavedSearch.objects.create(
            user=self.buyer,
            name=name,
            path=reverse("listings:listing_list"),
            query_params={
                "category": "cars",
                "q": brand,
                "min_price": "900000",
                "max_price": "1000000",
                "attr_marka": brand,
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
            querystring=(
                f"attr_km_max=50000&attr_marka={brand}&attr_yil_min=2019"
                f"&category=cars&max_price=1000000&min_price=900000&q={brand}"
            ),
            email_notifications_enabled=True,
            last_notification_checked_at=timezone.now() + checked_delta,
        )

    def _listing(self, title, *, brand="Toyota"):
        return Listing.objects.create(
            title=title,
            description="Temporary v84 scheduling/admin test listing.",
            price=Decimal("950000.00"),
            category=self.cars,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes={
                "marka": brand,
                "model": "Corolla" if brand == "Toyota" else "Civic",
                "yil": "2020",
                "km": "45000",
            },
        )

    def test_stale_before_hours_processes_only_stale_saved_searches(self):
        stale_search = self._saved_search("V84 stale Toyota", checked_delta=timedelta(days=-2))
        fresh_search = self._saved_search("V84 fresh Toyota", checked_delta=timedelta(hours=-1))
        self._listing("V84 Toyota stale filter match")

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--stale-before-hours",
            "24",
            stdout=output,
        )
        text = output.getvalue()

        self.assertIn("Stale filter: checked at or before", text)
        self.assertIn("Previewed 1 enabled saved search(es)", text)
        self.assertIn(f"Saved search #{stale_search.pk}", text)
        self.assertNotIn(f"Saved search #{fresh_search.pk}", text)

    def test_stale_before_hours_reports_empty_window(self):
        self._saved_search("V84 fresh only", checked_delta=timedelta(hours=-1))
        self._listing("V84 Toyota fresh ignored")

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--stale-before-hours",
            "24",
            stdout=output,
        )

        self.assertIn(
            "No enabled saved searches found for the requested stale window",
            output.getvalue(),
        )

    def test_max_searches_limits_processed_saved_searches(self):
        first_search = self._saved_search("V84 limit first")
        second_search = self._saved_search("V84 limit second")
        self._listing("V84 Toyota max searches match")

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--max-searches",
            "1",
            stdout=output,
        )
        text = output.getvalue()

        self.assertIn("Run limit: processing at most 1 saved search(es)", text)
        self.assertIn("Previewed 1 enabled saved search(es)", text)
        self.assertIn(f"Saved search #{first_search.pk}", text)
        self.assertNotIn(f"Saved search #{second_search.pk}", text)

    def test_scheduling_filter_validation_rejects_invalid_values(self):
        with self.assertRaises(CommandError):
            call_command("check_saved_search_notifications", "--max-searches", "0")

        with self.assertRaises(CommandError):
            call_command("check_saved_search_notifications", "--stale-before-hours", "-1")


class SavedSearchAdminPolishTests(SavedSearchNotificationSchedulingCommandTests):
    def _admin(self):
        return SavedSearchAdmin(SavedSearch, AdminSite())

    def test_admin_notification_status_labels_common_states(self):
        saved_search = self._saved_search("V84 admin status", checked_delta=timedelta(days=-2))
        model_admin = self._admin()

        self.assertEqual(model_admin.user_email(saved_search), self.buyer.email)
        self.assertIn("Checked", model_admin.notification_status(saved_search))

        saved_search.last_notification_sent_at = timezone.now()
        self.assertIn("Last sent", model_admin.notification_status(saved_search))

        saved_search.email_notifications_enabled = False
        self.assertEqual(model_admin.notification_status(saved_search), "Disabled")

        saved_search.email_notifications_enabled = True
        self.buyer.email = ""
        self.buyer.save(update_fields=["email"])
        saved_search.refresh_from_db()
        self.assertEqual(model_admin.user_email(saved_search), "(no email)")
        self.assertEqual(model_admin.notification_status(saved_search), "Enabled, no recipient")

    def test_admin_query_preview_truncates_long_querystrings(self):
        saved_search = self._saved_search("V84 admin query preview")
        saved_search.querystring = "x=" + ("a" * 140)
        model_admin = self._admin()

        preview = model_admin.query_preview(saved_search)

        self.assertTrue(preview.endswith("..."))
        self.assertLessEqual(len(preview), 120)
