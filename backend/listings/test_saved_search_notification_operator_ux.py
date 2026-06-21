# SAVED_SEARCH_NOTIFICATION_OPERATOR_UX_V87_TESTS
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.management.commands.check_saved_search_notifications import Command
from listings.models import Listing, SavedSearch


class SavedSearchNotificationOperatorUxTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="v87-operator-buyer@classifieds.local",
            username="v87_operator_buyer",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            email="v87-operator-seller@classifieds.local",
            username="v87_operator_seller",
            password="Testpass12345",
        )
        self.vehicles = Category.objects.create(name="Vehicles", slug="vehicles")
        self.cars = Category.objects.create(name="Cars", slug="cars", parent=self.vehicles)

    def _saved_search(self, name="V87 operator Toyota"):
        return SavedSearch.objects.create(
            user=self.buyer,
            name=name,
            path=reverse("listings:listing_list"),
            query_params={
                "category": "cars",
                "q": "Toyota",
                "min_price": "900000",
                "max_price": "1000000",
                "attr_marka": "Toyota",
                "attr_yil_min": "2019",
                "attr_km_max": "50000",
            },
            querystring=(
                "attr_km_max=50000&attr_marka=Toyota&attr_yil_min=2019"
                "&category=cars&max_price=1000000&min_price=900000&q=Toyota"
            ),
            email_notifications_enabled=True,
            last_notification_checked_at=timezone.now() - timedelta(days=1),
        )

    def _listing(self, title):
        return Listing.objects.create(
            title=title,
            description="Temporary v87 operator UX test listing.",
            price=Decimal("950000.00"),
            category=self.cars,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
            attributes={
                "marka": "Toyota",
                "model": "Corolla",
                "yil": "2020",
                "km": "45000",
            },
        )

    def test_help_examples_include_operator_safe_commands_and_safety_notes(self):
        text = Command.examples

        self.assertIn("Examples:", text)
        self.assertIn("Dry-run one saved search", text)
        self.assertIn("--saved-search-id 123", text)
        self.assertIn("--stale-before-hours 24 --max-searches 100", text)
        self.assertIn("Safety notes:", text)
        self.assertIn("failed sends do not update timestamps", text)

    def test_dry_run_output_includes_operator_header(self):
        saved_search = self._saved_search()
        self._listing("V87 Toyota operator header match")

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--saved-search-id",
            str(saved_search.pk),
            "--limit-per-search",
            "1",
            "--site-base-url",
            "https://classifieds.local",
            stdout=output,
        )
        text = output.getvalue()

        self.assertIn("Mode: DRY RUN", text)
        self.assertIn("Limit per search: 1 listing(s)", text)
        self.assertIn(f"Saved search ID filter: {saved_search.pk}", text)
        self.assertIn("Site base URL: https://classifieds.local", text)
        self.assertIn("Dry-run safety: no emails will be sent", text)
        self.assertIn("Dry run: email not sent", text)

    def test_send_output_includes_failure_isolation_safety_header(self):
        saved_search = self._saved_search()
        self._listing("V87 Toyota send safety header match")

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--saved-search-id",
            str(saved_search.pk),
            "--send",
            stdout=output,
        )
        text = output.getvalue()

        self.assertIn("Mode: SEND", text)
        self.assertIn("Send safety: failures are isolated per saved search", text)

    def test_limit_per_search_rejects_invalid_values(self):
        with self.assertRaises(CommandError):
            call_command("check_saved_search_notifications", "--limit-per-search", "0")

        with self.assertRaises(CommandError):
            call_command("check_saved_search_notifications", "--limit-per-search", "-1")
