from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import TrustSafetyEvent, UserReport
from categories.models import Category
from listings.models import Listing, ListingReport


class ReportTrustSafetyEventTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            email="report_event_admin@classifieds.local",
            username="reporteventadmin",
            password="Testpass12345",
            is_staff=True,
            is_superuser=True,
        )
        self.seller = User.objects.create_user(
            email="report_event_seller@classifieds.local",
            username="reporteventseller",
            password="Testpass12345",
        )
        self.buyer = User.objects.create_user(
            email="report_event_buyer@classifieds.local",
            username="reporteventbuyer",
            password="Testpass12345",
        )
        self.category = Category.objects.create(name="Report Event Cars", slug="report-event-cars")
        self.listing = Listing.objects.create(
            title="Report event listing",
            description="Report event listing description",
            price=Decimal("1000.00"),
            category=self.category,
            owner=self.seller,
            location="Istanbul",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def _listing_report(self):
        return ListingReport.objects.create(
            listing=self.listing,
            reporter=self.buyer,
            reason=ListingReport.Reason.SCAM,
            details="Suspicious listing.",
        )

    def _user_report(self):
        return UserReport.objects.create(
            reported_user=self.seller,
            reporter=self.buyer,
            source_listing=self.listing,
            reasons=[UserReport.Reason.SCAM],
            details="Suspicious seller.",
        )

    def test_listing_report_review_creates_trust_safety_event(self):
        report = self._listing_report()
        self.client.login(username="reporteventadmin", password="Testpass12345")

        response = self.client.post(
            reverse("listings:report_review", args=[report.pk]),
            {"admin_note": "Reviewed report."},
        )

        self.assertEqual(response.status_code, 302)
        event = TrustSafetyEvent.objects.get(listing_report=report)
        self.assertEqual(event.event_type, TrustSafetyEvent.EventType.LISTING_REPORT_REVIEWED)
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.target_user, self.seller)
        self.assertEqual(event.listing, self.listing)
        self.assertEqual(event.metadata["report_status"], ListingReport.Status.REVIEWED)

    def test_listing_report_suspend_creates_trust_safety_event(self):
        report = self._listing_report()
        self.client.login(username="reporteventadmin", password="Testpass12345")

        response = self.client.post(
            reverse("listings:report_suspend_listing", args=[report.pk]),
            {"admin_note": "Suspend while investigating."},
        )

        self.assertEqual(response.status_code, 302)
        event = TrustSafetyEvent.objects.get(listing_report=report)
        self.assertEqual(event.event_type, TrustSafetyEvent.EventType.LISTING_SUSPENDED)
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.target_user, self.seller)
        self.assertEqual(event.listing, self.listing)

    def test_seller_report_warning_creates_trust_safety_event(self):
        report = self._user_report()
        self.client.login(username="reporteventadmin", password="Testpass12345")

        response = self.client.post(
            reverse("accounts:user_report_warn", args=[report.pk]),
            {"admin_note": "Warn seller."},
        )

        self.assertEqual(response.status_code, 302)
        event = TrustSafetyEvent.objects.get(user_report=report)
        self.assertEqual(event.event_type, TrustSafetyEvent.EventType.SELLER_WARNED)
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.target_user, self.seller)
        self.assertEqual(event.listing, self.listing)
        self.assertEqual(event.metadata["report_action_taken"], UserReport.Action.WARNED_SELLER)
