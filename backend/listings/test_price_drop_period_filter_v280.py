from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserProfile
from categories.models import Category
from listings.listing_price_drop_period_filter_v280 import (
    PRICE_DROP_PERIOD_FILTER_V280,
    PRICE_DROP_PERIOD_LABELS_V280,
    PRICE_DROP_PERIOD_PARAM_V280,
    PRICE_DROP_PERIODS_V280,
)
from listings.models import Listing, ListingPriceHistory, SavedSearch
from listings.saved_searches import (
    SAVED_SEARCH_ALLOWED_KEYS,
    summarize_saved_search_params,
)


class PriceDropPeriodFilterV280Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller = User.objects.create_user(
            username="v280-seller",
            password="StrongPass123!",
        )
        UserProfile.objects.get_or_create(user=cls.seller)

        cls.category = Category.objects.create(
            name="V280 Furniture",
            slug="v280-furniture",
        )
        cls.other_category = Category.objects.create(
            name="V280 Other",
            slug="v280-other",
        )
        cls.now = timezone.now()

    def create_listing(
        self,
        title,
        *,
        category=None,
        location="Berlin",
        price="1000.00",
    ):
        return Listing.objects.create(
            title=title,
            description=f"Searchable {title}",
            price=Decimal(price),
            category=category or self.category,
            owner=self.seller,
            location=location,
            status=Listing.Status.APPROVED,
            expires_at=self.now + timedelta(days=60),
        )

    def change_price(self, listing, price, changed_at):
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

    def browse(self, params=None, *, category=None):
        url = (
            category.get_absolute_url()
            if category is not None
            else reverse("listings:listing_list")
        )
        with patch(
            "listings.listing_price_drop_period_filter_v280.timezone.now",
            return_value=self.now,
        ):
            return self.client.get(url, params or {})

    def response_titles(self, response):
        return [
            listing.title
            for listing in response.context["listings"]
        ]

    def test_each_supported_period_filters_main_browse(self):
        fixtures = (
            ("V280 Drop 12 Hours", timedelta(hours=12)),
            ("V280 Drop 3 Days", timedelta(days=3)),
            ("V280 Drop 20 Days", timedelta(days=20)),
            ("V280 Drop 45 Days", timedelta(days=45)),
        )
        for title, age in fixtures:
            listing = self.create_listing(title)
            self.change_price(
                listing,
                "900.00",
                self.now - age,
            )

        expectations = {
            "24h": ["V280 Drop 12 Hours"],
            "7d": [
                "V280 Drop 12 Hours",
                "V280 Drop 3 Days",
            ],
            "30d": [
                "V280 Drop 12 Hours",
                "V280 Drop 3 Days",
                "V280 Drop 20 Days",
            ],
        }

        for period, expected_titles in expectations.items():
            with self.subTest(period=period):
                response = self.browse(
                    {"price_drop_period": period}
                )
                self.assertEqual(response.status_code, 200)
                self.assertCountEqual(
                    self.response_titles(response),
                    expected_titles,
                )

    def test_exact_period_boundary_is_inclusive(self):
        boundary = self.create_listing("V280 Exact Boundary")
        self.change_price(
            boundary,
            "900.00",
            self.now - timedelta(hours=24),
        )

        too_old = self.create_listing("V280 Beyond Boundary")
        self.change_price(
            too_old,
            "900.00",
            self.now
            - timedelta(hours=24, microseconds=1),
        )

        response = self.browse(
            {"price_drop_period": "24h"}
        )
        self.assertEqual(
            self.response_titles(response),
            ["V280 Exact Boundary"],
        )

    def test_invalid_period_is_ignored_safely(self):
        old_drop = self.create_listing("V280 Invalid Old Drop")
        self.change_price(
            old_drop,
            "900.00",
            self.now - timedelta(days=45),
        )
        self.create_listing("V280 Invalid Baseline")

        response = self.browse(
            {"price_drop_period": "weekly"}
        )

        self.assertCountEqual(
            self.response_titles(response),
            [
                "V280 Invalid Old Drop",
                "V280 Invalid Baseline",
            ],
        )
        self.assertEqual(
            response.context["search_price_drop_period"],
            "",
        )
        self.assertEqual(
            response.context["save_search_querystring"],
            "",
        )
        self.assertFalse(
            any(
                chip["clear_param"]
                == PRICE_DROP_PERIOD_PARAM_V280
                for chip in response.context[
                    "active_filter_chips"
                ]
            )
        )

    def test_missing_period_does_not_filter_browse(self):
        old_drop = self.create_listing("V280 Missing Old Drop")
        self.change_price(
            old_drop,
            "900.00",
            self.now - timedelta(days=45),
        )
        self.create_listing("V280 Missing Baseline")

        response = self.browse()

        self.assertCountEqual(
            self.response_titles(response),
            [
                "V280 Missing Old Drop",
                "V280 Missing Baseline",
            ],
        )
        self.assertEqual(
            response.context["search_price_drop_period"],
            "",
        )
        self.assertFalse(
            any(
                chip["clear_param"]
                == PRICE_DROP_PERIOD_PARAM_V280
                for chip in response.context[
                    "active_filter_chips"
                ]
            )
        )

    def test_stale_drop_and_latest_increase_do_not_qualify(self):
        current = self.create_listing("V280 Current Drop")
        self.change_price(
            current,
            "900.00",
            self.now - timedelta(hours=1),
        )

        stale = self.create_listing("V280 Stale Drop")
        self.change_price(
            stale,
            "850.00",
            self.now - timedelta(hours=1),
        )
        Listing.objects.filter(pk=stale.pk).update(
            price=Decimal("825.00")
        )

        increased = self.create_listing("V280 Latest Increase")
        self.change_price(
            increased,
            "800.00",
            self.now - timedelta(hours=2),
        )
        self.change_price(
            increased,
            "900.00",
            self.now - timedelta(hours=1),
        )

        response = self.browse(
            {"price_drop_period": "24h"}
        )
        self.assertEqual(
            self.response_titles(response),
            ["V280 Current Drop"],
        )

    def test_main_browse_combines_all_public_filters(self):
        older = self.create_listing(
            "V280 Oak Chair Older",
            price="1000.00",
        )
        self.change_price(
            older,
            "850.00",
            self.now - timedelta(hours=6),
        )

        newer = self.create_listing(
            "V280 Oak Chair Newer",
            price="1000.00",
        )
        self.change_price(
            newer,
            "900.00",
            self.now - timedelta(hours=1),
        )

        wrong_location = self.create_listing(
            "V280 Oak Chair Munich",
            location="Munich",
        )
        self.change_price(
            wrong_location,
            "875.00",
            self.now - timedelta(hours=1),
        )
        self.create_listing("V280 Oak Chair Baseline")

        response = self.browse(
            {
                "q": "Oak Chair",
                "location": "Berlin",
                "min_price": "800",
                "max_price": "920",
                "category": self.category.slug,
                "price_drops": "1",
                "price_drop_period": "24h",
                "sort": "recent_price_drop",
            }
        )

        self.assertEqual(
            self.response_titles(response),
            [
                "V280 Oak Chair Newer",
                "V280 Oak Chair Older",
            ],
        )

    def test_category_browse_combines_v278_v279_and_period(self):
        older = self.create_listing("V280 Category Desk Older")
        self.change_price(
            older,
            "850.00",
            self.now - timedelta(days=2),
        )
        newer = self.create_listing("V280 Category Desk Newer")
        self.change_price(
            newer,
            "900.00",
            self.now - timedelta(hours=2),
        )
        other = self.create_listing(
            "V280 Category Desk Other",
            category=self.other_category,
        )
        self.change_price(
            other,
            "875.00",
            self.now - timedelta(hours=1),
        )

        response = self.browse(
            {
                "q": "Category Desk",
                "location": "Berlin",
                "min_price": "800",
                "max_price": "920",
                "price_drops": "1",
                "price_drop_period": "7d",
                "sort": "recent_price_drop",
            },
            category=self.category,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.response_titles(response),
            [
                "V280 Category Desk Newer",
                "V280 Category Desk Older",
            ],
        )
        self.assertContains(
            response,
            '<option value="7d" selected>',
        )

    def test_recent_sort_uses_stable_pk_tiebreaker(self):
        first = self.create_listing("V280 Same Time First")
        self.change_price(
            first,
            "900.00",
            self.now - timedelta(hours=1),
        )
        second = self.create_listing("V280 Same Time Second")
        self.change_price(
            second,
            "900.00",
            self.now - timedelta(hours=1),
        )

        response = self.browse(
            {
                "price_drop_period": "24h",
                "sort": "recent_price_drop",
            }
        )
        self.assertEqual(
            self.response_titles(response),
            [
                "V280 Same Time Second",
                "V280 Same Time First",
            ],
        )

    def test_pagination_preserves_period(self):
        for index in range(13):
            listing = self.create_listing(
                f"V280 Paginated Drop {index:02d}"
            )
            self.change_price(
                listing,
                "900.00",
                self.now - timedelta(hours=index),
            )

        response = self.browse(
            {"price_drop_period": "7d"}
        )

        self.assertEqual(
            response.context["page_obj"].paginator.count,
            13,
        )
        self.assertEqual(
            response.context["page_querystring"],
            "price_drop_period=7d",
        )
        self.assertContains(
            response,
            "price_drop_period=7d&page=2",
        )

    def test_saved_search_creation_and_execution_preserve_period(self):
        eligible = self.create_listing("V280 Saved Eligible")
        self.change_price(
            eligible,
            "900.00",
            self.now - timedelta(days=2),
        )
        old = self.create_listing("V280 Saved Old")
        self.change_price(
            old,
            "900.00",
            self.now - timedelta(days=10),
        )

        self.client.force_login(self.seller)
        response = self.browse(
            {"price_drop_period": "7d"}
        )
        querystring = response.context[
            "save_search_querystring"
        ]
        self.assertEqual(
            parse_qs(querystring)["price_drop_period"],
            ["7d"],
        )

        create_response = self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "V280 recent reductions",
                "querystring": querystring,
            },
        )
        self.assertEqual(create_response.status_code, 302)

        saved = SavedSearch.objects.get(
            user=self.seller,
            name="V280 recent reductions",
        )
        self.assertEqual(
            saved.query_params["price_drop_period"],
            "7d",
        )
        self.assertIn(
            "price_drop_period=7d",
            saved.get_absolute_url(),
        )
        self.assertIn(
            {
                "label": "Price drop period",
                "value": "Last 7 days",
                "param": "price_drop_period",
                "kind": "price_drop_period",
            },
            summarize_saved_search_params(saved.query_params),
        )

        with patch(
            "listings.listing_price_drop_period_filter_v280.timezone.now",
            return_value=self.now,
        ):
            executed = self.client.get(saved.get_absolute_url())
        self.assertEqual(
            self.response_titles(executed),
            ["V280 Saved Eligible"],
        )

    def test_active_chip_labels_and_template_control(self):
        listing = self.create_listing("V280 Chip Listing")
        self.change_price(
            listing,
            "900.00",
            self.now - timedelta(hours=1),
        )

        expectations = {
            "24h": "Last 24 hours",
            "7d": "Last 7 days",
            "30d": "Last 30 days",
        }

        for period, label in expectations.items():
            with self.subTest(period=period):
                response = self.browse(
                    {
                        "q": "Chip Listing",
                        "price_drop_period": period,
                    }
                )
                chips = {
                    chip["clear_param"]: chip
                    for chip in response.context[
                        "active_filter_chips"
                    ]
                }
                chip = chips[PRICE_DROP_PERIOD_PARAM_V280]
                self.assertEqual(
                    chip["label"],
                    "Price drop period",
                )
                self.assertEqual(chip["value"], label)

                clear_query = parse_qs(
                    urlsplit(chip["clear_url"]).query
                )
                self.assertNotIn(
                    "price_drop_period",
                    clear_query,
                )
                self.assertEqual(
                    clear_query["q"],
                    ["Chip Listing"],
                )
                self.assertContains(
                    response,
                    f'<option value="{period}" selected>',
                )

        self.assertContains(
            response,
            'name="price_drop_period"',
        )
        self.assertContains(response, "Any time")
        self.assertContains(response, "Last 24 hours")
        self.assertContains(response, "Last 7 days")
        self.assertContains(response, "Last 30 days")

    def test_contract_and_no_migration(self):
        self.assertTrue(PRICE_DROP_PERIOD_FILTER_V280)
        self.assertEqual(
            PRICE_DROP_PERIOD_PARAM_V280,
            "price_drop_period",
        )
        self.assertEqual(
            set(PRICE_DROP_PERIODS_V280),
            {"24h", "7d", "30d"},
        )
        self.assertEqual(
            PRICE_DROP_PERIOD_LABELS_V280["24h"],
            "Last 24 hours",
        )
        self.assertIn(
            PRICE_DROP_PERIOD_PARAM_V280,
            SAVED_SEARCH_ALLOWED_KEYS,
        )

        migration_dir = (
            Path(settings.BASE_DIR)
            / "listings"
            / "migrations"
        )
        self.assertEqual(
            list(migration_dir.glob("*v280*")),
            [],
        )
