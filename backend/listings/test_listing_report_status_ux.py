from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from categories.models import Category
from listings.models import Listing, ListingReport


class ListingReportStatusUxTests(TestCase):
    password = "Testpass12345"

    def setUp(self):
        self.admin = self._create_user("report-status-admin@classifieds.local", is_staff=True, is_superuser=True)
        self.owner = self._create_user("report-status-owner@classifieds.local")
        self.reporter = self._create_user("report-status-reporter@classifieds.local")
        self.category = Category.objects.create(name="Report status QA", slug="report-status-qa")
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin)

    def _create_user(self, email, is_staff=False, is_superuser=False):
        User = get_user_model()
        username_field = User.USERNAME_FIELD
        kwargs = {username_field: email}
        if username_field != "email" and any(field.name == "email" for field in User._meta.fields):
            kwargs["email"] = email
        user = User.objects.create_user(password=self.password, **kwargs)
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save(update_fields=["is_staff", "is_superuser"])
        return user

    def _listing(self, title, status=Listing.Status.APPROVED):
        return Listing.objects.create(
            title=title,
            description="Report status QA description",
            price="100.00",
            category=self.category,
            owner=self.owner,
            location="Berlin",
            status=status,
        )

    def _report(self, listing, status=ListingReport.Status.PENDING):
        return ListingReport.objects.create(
            listing=listing,
            reporter=self.reporter,
            reason=ListingReport.Reason.SCAM,
            reasons=[ListingReport.Reason.SCAM],
            details="Report status QA details",
            status=status,
        )

    def test_report_queue_uses_clear_report_and_listing_status_labels(self):
        self._report(self._listing("Pending report active listing"))

        response = self.client.get(reverse("listings:report_queue"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report status")
        self.assertContains(response, "Listing status")
        self.assertContains(response, "Pending review")
        self.assertContains(response, "Marked reviewed")
        self.assertContains(response, "Dismissed as invalid")
        self.assertContains(response, "Listing suspended")
        self.assertContains(response, "Listing archived")

    def test_listing_status_filter_limits_listing_reports(self):
        suspended_listing = self._listing("Suspended filtered listing", status=Listing.Status.SUSPENDED)
        active_listing = self._listing("Active filtered listing", status=Listing.Status.APPROVED)
        self._report(suspended_listing)
        self._report(active_listing)

        response = self.client.get(
            reverse("listings:report_queue"),
            {"listing_status": Listing.Status.SUSPENDED},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Suspended filtered listing")
        self.assertNotContains(response, "Active filtered listing")

    def test_suspend_listing_action_marks_report_reviewed(self):
        listing = self._listing("Suspension action listing", status=Listing.Status.APPROVED)
        report = self._report(listing)

        response = self.client.post(
            reverse("listings:report_suspend_listing", args=[report.pk]),
            {
                "admin_note": "Temporary investigation.",
                "reporter_note": "We temporarily hid this listing.",
            },
        )

        self.assertEqual(response.status_code, 302)
        report.refresh_from_db()
        listing.refresh_from_db()
        self.assertEqual(report.status, ListingReport.Status.REVIEWED)
        self.assertEqual(report.action_taken, "suspended_listing")
        self.assertEqual(listing.status, Listing.Status.SUSPENDED)
