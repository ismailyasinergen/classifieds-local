from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing, SavedSearch
from listings.saved_search_notifications import (
    build_saved_search_match_preview,
    get_saved_search_matching_queryset,
)


class SavedSearchNotificationMatcherTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.buyer = User.objects.create_user(
            email="saved-search-matcher-buyer-v81@classifieds.local",
            username="saved_search_matcher_buyer_v81",
            password="Testpass12345",
        )
        self.seller = User.objects.create_user(
            email="saved-search-matcher-seller-v81@classifieds.local",
            username="saved_search_matcher_seller_v81",
            password="Testpass12345",
        )
        self.vehicles = Category.objects.create(name="Vehicles", slug="vehicles")
        self.cars = Category.objects.create(name="Cars", slug="cars", parent=self.vehicles)

    def _listing(
        self,
        title,
        *,
        brand="Toyota",
        year="2020",
        km="45000",
        price="950000.00",
        status=Listing.Status.APPROVED,
        created_delta=timedelta(minutes=0),
        expires_delta=timedelta(days=30),
    ):
        listing = Listing.objects.create(
            title=title,
            description="Temporary v81 matcher listing.",
            price=Decimal(price),
            category=self.cars,
            owner=self.seller,
            location="Istanbul / Kadikoy",
            status=status,
            expires_at=timezone.now() + expires_delta,
            attributes={
                "marka": brand,
                "model": "Corolla" if brand == "Toyota" else "Civic",
                "yil": year,
                "km": km,
            },
        )
        Listing.objects.filter(pk=listing.pk).update(created_at=timezone.now() + created_delta)
        listing.refresh_from_db()
        return listing

    def _saved_search(self, *, checked_delta=timedelta(days=-1), enabled=True):
        return SavedSearch.objects.create(
            user=self.buyer,
            name="V81 Toyota matcher",
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
            email_notifications_enabled=enabled,
            last_notification_checked_at=timezone.now() + checked_delta,
        )

    def test_saved_search_matcher_finds_only_new_approved_matching_listings(self):
        saved_search = self._saved_search()

        match = self._listing("V81 Toyota Corolla match")
        self._listing("V81 Honda Civic wrong brand", brand="Honda")
        self._listing("V81 Toyota too old", created_delta=timedelta(days=-2))
        self._listing("V81 Toyota pending", status=Listing.Status.PENDING)
        self._listing("V81 Toyota expired", expires_delta=timedelta(days=-1))
        self._listing("V81 Toyota too expensive", price="1200000.00")
        self._listing("V81 Toyota too much km", km="80000")

        matches = list(get_saved_search_matching_queryset(saved_search))

        self.assertEqual(matches, [match])

    def test_match_preview_reports_count_and_limited_listing_list(self):
        saved_search = self._saved_search()
        self._listing("V81 Toyota match one")
        self._listing("V81 Toyota match two")

        preview = build_saved_search_match_preview(saved_search, limit=1)

        self.assertEqual(preview.match_count, 2)
        self.assertEqual(len(preview.listings), 1)
        self.assertEqual(preview.saved_search, saved_search)

    def test_management_command_previews_without_sending_or_marking_checked_by_default(self):
        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at
        self._listing("V81 Toyota command match")

        output = StringIO()
        call_command("check_saved_search_notifications", stdout=output)

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("V81 Toyota command match", text)
        self.assertIn("1 new matching approved listing", text)
        self.assertIn("No emails were sent", text)
        self.assertEqual(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_management_command_can_mark_search_checked(self):
        saved_search = self._saved_search()
        original_checked_at = saved_search.last_notification_checked_at
        self._listing("V81 Toyota mark checked match")

        output = StringIO()
        call_command(
            "check_saved_search_notifications",
            "--saved-search-id",
            str(saved_search.pk),
            "--mark-checked",
            stdout=output,
        )

        saved_search.refresh_from_db()
        text = output.getvalue()

        self.assertIn("Marked checked", text)
        self.assertGreater(saved_search.last_notification_checked_at, original_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_management_command_ignores_disabled_saved_searches(self):
        self._saved_search(enabled=False)
        self._listing("V81 Toyota disabled should not show")

        output = StringIO()
        call_command("check_saved_search_notifications", stdout=output)

        self.assertIn("No enabled saved searches found", output.getvalue())
        self.assertNotIn("V81 Toyota disabled should not show", output.getvalue())
