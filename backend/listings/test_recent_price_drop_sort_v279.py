from datetime import timedelta
from decimal import Decimal
from urllib.parse import parse_qs

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from categories.models import Category
from listings.listing_price_drop_sort_v279 import (
    RECENT_PRICE_DROP_SORT_LABEL_V279,
    RECENT_PRICE_DROP_SORT_VALUE_V279,
    RECENT_PRICE_DROP_SORT_V279,
)
from listings.models import (
    Listing,
    ListingPriceHistory,
    SavedSearch,
)
from listings.saved_searches import SORT_LABELS_V78


class RecentPriceDropSortV279Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.seller = User.objects.create_user(
            username="v279-seller",
            password="StrongPass123!",
        )

        UserProfile.objects.get_or_create(
            user=cls.seller,
        )

        cls.category = Category.objects.create(
            name="V279 Furniture",
            slug="v279-furniture",
        )

    def create_listing(self, title):
        return Listing.objects.create(
            title=title,
            description=title,
            price=Decimal("1000.00"),
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def reduce_price(self, listing, price, changed_at):
        listing.price = Decimal(price)
        listing.save(update_fields=["price"])

        transition = (
            ListingPriceHistory.objects
            .filter(
                listing=listing,
                previous_price__isnull=False,
            )
            .order_by("-changed_at", "-pk")
            .first()
        )

        ListingPriceHistory.objects.filter(
            pk=transition.pk,
        ).update(changed_at=changed_at)

    def response_titles(self, response):
        return [
            listing.title
            for listing in response.context["listings"]
        ]

    def create_sort_fixture(self):
        now = timezone.now()

        older = self.create_listing("V279 Older Drop")
        self.reduce_price(
            older,
            "900.00",
            now - timedelta(days=2),
        )

        newer = self.create_listing("V279 Newer Drop")
        self.reduce_price(
            newer,
            "800.00",
            now - timedelta(hours=1),
        )

        self.create_listing("V279 Baseline")

        increase = self.create_listing("V279 Increase")
        increase.price = Decimal("1100.00")
        increase.save(update_fields=["price"])

        stale = self.create_listing(
            "V279 Stale Drop"
        )

        self.reduce_price(
            stale,
            "700.00",
            now,
        )

        Listing.objects.filter(
            pk=stale.pk,
        ).update(
            price=Decimal("650.00"),
        )

    def test_main_browse_orders_recent_price_drops(self):
        self.create_sort_fixture()

        response = self.client.get(
            reverse("listings:listing_list"),
            {"sort": "recent_price_drop"},
        )

        self.assertEqual(
            self.response_titles(response),
            [
                "V279 Newer Drop",
                "V279 Older Drop",
            ],
        )

    def test_category_browse_uses_recent_price_drop_sort(
        self,
    ):
        self.create_sort_fixture()

        response = self.client.get(
            self.category.get_absolute_url(),
            {
                "sort": "recent_price_drop",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self.response_titles(response),
            [
                "V279 Newer Drop",
                "V279 Older Drop",
            ],
        )

    def test_category_browse_honors_v278_drop_filter(
        self,
    ):
        dropped = self.create_listing(
            "V279 Category Drop"
        )

        self.reduce_price(
            dropped,
            "900.00",
            timezone.now(),
        )

        self.create_listing(
            "V279 Category Baseline"
        )

        response = self.client.get(
            self.category.get_absolute_url(),
            {
                "price_drops": "1",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            self.response_titles(response),
            [
                "V279 Category Drop",
            ],
        )


    def test_contract_ui_and_active_filter_chip(
        self,
    ):
        self.assertTrue(
            RECENT_PRICE_DROP_SORT_V279
        )

        self.assertEqual(
            RECENT_PRICE_DROP_SORT_VALUE_V279,
            "recent_price_drop",
        )

        self.assertEqual(
            RECENT_PRICE_DROP_SORT_LABEL_V279,
            "Recently reduced",
        )

        self.assertEqual(
            SORT_LABELS_V78["recent_price_drop"],
            "Recently reduced",
        )

        listing = self.create_listing(
            "V279 Render Drop"
        )

        self.reduce_price(
            listing,
            "900.00",
            timezone.now(),
        )

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "sort": "recent_price_drop",
            },
        )

        self.assertContains(
            response,
            'value="recent_price_drop" selected',
        )

        self.assertContains(
            response,
            'name="price_drops"',
        )

        chips = {
            chip["clear_param"]: chip
            for chip in response.context[
                "active_filter_chips"
            ]
        }

        self.assertEqual(
            chips["sort"]["value"],
            "Recently reduced",
        )


    def test_pagination_and_saved_search_preserve_sort(
        self,
    ):
        now = timezone.now()

        for index in range(13):
            listing = self.create_listing(
                f"V279 Page Drop {index:02d}"
            )

            self.reduce_price(
                listing,
                "900.00",
                now - timedelta(minutes=index),
            )

        self.client.force_login(self.seller)

        response = self.client.get(
            reverse("listings:listing_list"),
            {
                "sort": "recent_price_drop",
            },
        )

        self.assertEqual(
            response.context["page_querystring"],
            "sort=recent_price_drop",
        )

        querystring = response.context[
            "save_search_querystring"
        ]

        self.assertEqual(
            parse_qs(querystring)["sort"],
            ["recent_price_drop"],
        )

        create_response = self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "V279 recent drops",
                "querystring": querystring,
            },
        )

        self.assertEqual(
            create_response.status_code,
            302,
        )

        saved = SavedSearch.objects.get(
            user=self.seller,
            name="V279 recent drops",
        )

        self.assertEqual(
            saved.query_params["sort"],
            "recent_price_drop",
        )
