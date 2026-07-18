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
from listings.listing_biggest_price_drop_sort_v281 import (
    BIGGEST_PRICE_DROP_SORT_LABEL_V281,
    BIGGEST_PRICE_DROP_SORT_VALUE_V281,
    BIGGEST_PRICE_DROP_SORT_V281,
    PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281,
    PRICE_DROP_DISCOUNT_PERCENTAGE_ANNOTATION_V281,
)
from listings.models import Listing, ListingPriceHistory, SavedSearch
from listings.saved_searches import (
    SORT_LABELS_V78,
    summarize_saved_search_params,
)


class BiggestPriceDropSortV281Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller = User.objects.create_user(
            username="v281-seller",
            password="StrongPass123!",
        )
        UserProfile.objects.get_or_create(user=cls.seller)

        cls.category = Category.objects.create(
            name="V281 Furniture",
            slug="v281-furniture",
        )
        cls.other_category = Category.objects.create(
            name="V281 Other",
            slug="v281-other",
        )
        cls.now = timezone.now()

    def create_listing(
        self,
        title,
        *,
        price="1000.00",
        category=None,
        location="Berlin",
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

    @staticmethod
    def response_listings(response):
        return list(response.context["listings"])

    def response_titles(self, response):
        return [
            listing.title
            for listing in self.response_listings(response)
        ]

    def test_main_and_category_browse_support_biggest_discount(self):
        larger = self.create_listing("V281 Larger Percentage")
        self.change_price(
            larger,
            "500.00",
            self.now - timedelta(hours=2),
        )
        smaller = self.create_listing("V281 Smaller Percentage")
        self.change_price(
            smaller,
            "750.00",
            self.now - timedelta(hours=1),
        )
        other = self.create_listing(
            "V281 Other Category",
            category=self.other_category,
        )
        self.change_price(
            other,
            "100.00",
            self.now,
        )
        self.create_listing("V281 Baseline Excluded")

        params = {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        main_response = self.browse(params)
        self.assertEqual(main_response.status_code, 200)
        self.assertEqual(
            self.response_titles(main_response),
            [
                "V281 Other Category",
                "V281 Larger Percentage",
                "V281 Smaller Percentage",
            ],
        )

        category_response = self.browse(
            params,
            category=self.category,
        )
        self.assertEqual(category_response.status_code, 200)
        self.assertEqual(
            self.response_titles(category_response),
            [
                "V281 Larger Percentage",
                "V281 Smaller Percentage",
            ],
        )

    def test_percentage_precedes_absolute_discount_amount(self):
        high_percentage = self.create_listing(
            "V281 High Percentage Small Amount",
            price="100.00",
        )
        self.change_price(
            high_percentage,
            "50.00",
            self.now - timedelta(hours=2),
        )

        high_amount = self.create_listing(
            "V281 Lower Percentage Large Amount"
        )
        self.change_price(
            high_amount,
            "600.00",
            self.now - timedelta(hours=1),
        )

        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        self.assertEqual(
            self.response_titles(response),
            [
                "V281 High Percentage Small Amount",
                "V281 Lower Percentage Large Amount",
            ],
        )

    def test_equal_percentage_is_resolved_by_discount_amount(self):
        small = self.create_listing(
            "V281 Equal Percentage Small Amount",
            price="100.00",
        )
        self.change_price(
            small,
            "50.00",
            self.now,
        )

        large = self.create_listing(
            "V281 Equal Percentage Large Amount"
        )
        self.change_price(
            large,
            "500.00",
            self.now - timedelta(hours=1),
        )

        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        self.assertEqual(
            self.response_titles(response),
            [
                "V281 Equal Percentage Large Amount",
                "V281 Equal Percentage Small Amount",
            ],
        )

    def test_equal_discounts_use_time_then_primary_key(self):
        older = self.create_listing("V281 Older Equal Drop")
        self.change_price(
            older,
            "500.00",
            self.now - timedelta(hours=2),
        )
        newer = self.create_listing("V281 Newer Equal Drop")
        self.change_price(
            newer,
            "500.00",
            self.now - timedelta(hours=1),
        )
        first_tied = self.create_listing("V281 First PK Tie")
        self.change_price(first_tied, "500.00", self.now)
        second_tied = self.create_listing("V281 Second PK Tie")
        self.change_price(second_tied, "500.00", self.now)

        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        self.assertEqual(
            self.response_titles(response),
            [
                "V281 Second PK Tie",
                "V281 First PK Tie",
                "V281 Newer Equal Drop",
                "V281 Older Equal Drop",
            ],
        )

    def test_invalid_current_reduction_states_are_excluded(self):
        valid = self.create_listing("V281 Valid Current Drop")
        self.change_price(valid, "800.00", self.now)

        self.create_listing("V281 Baseline Only")

        increased = self.create_listing("V281 Latest Increase")
        self.change_price(
            increased,
            "700.00",
            self.now - timedelta(hours=2),
        )
        self.change_price(
            increased,
            "900.00",
            self.now - timedelta(hours=1),
        )

        mismatched = self.create_listing("V281 Current Mismatch")
        self.change_price(
            mismatched,
            "800.00",
            self.now - timedelta(hours=1),
        )
        Listing.objects.filter(pk=mismatched.pk).update(
            price=Decimal("750.00")
        )

        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        self.assertEqual(
            self.response_titles(response),
            ["V281 Valid Current Drop"],
        )

    def test_zero_and_missing_previous_prices_are_excluded(self):
        missing = self.create_listing("V281 Missing Previous")
        self.assertTrue(
            ListingPriceHistory.objects.filter(
                listing=missing,
                previous_price__isnull=True,
            ).exists()
        )

        zero = self.create_listing(
            "V281 Zero Previous",
            price="0.00",
        )
        Listing.objects.filter(pk=zero.pk).update(
            price=Decimal("-1.00")
        )
        ListingPriceHistory.objects.create(
            listing=zero,
            previous_price=Decimal("0.00"),
            new_price=Decimal("-1.00"),
            changed_at=self.now,
        )

        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        self.assertEqual(self.response_titles(response), [])

    def test_decimal_percentage_annotations_are_precise(self):
        repeating = self.create_listing(
            "V281 Repeating Decimal",
            price="3.00",
        )
        self.change_price(repeating, "2.00", self.now)

        rounded = self.create_listing(
            "V281 Rounded Decimal",
            price="100.00",
        )
        self.change_price(rounded, "66.67", self.now)

        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        listings = self.response_listings(response)
        self.assertEqual(
            [listing.title for listing in listings],
            [
                "V281 Repeating Decimal",
                "V281 Rounded Decimal",
            ],
        )
        self.assertEqual(
            getattr(
                listings[0],
                PRICE_DROP_DISCOUNT_AMOUNT_ANNOTATION_V281,
            ),
            Decimal("1.00"),
        )
        percentage = getattr(
            listings[0],
            PRICE_DROP_DISCOUNT_PERCENTAGE_ANNOTATION_V281,
        )
        self.assertGreater(percentage, Decimal("33.3333"))
        self.assertLess(percentage, Decimal("33.3334"))

    def test_sort_combines_with_v278_and_public_filters(self):
        eligible = self.create_listing(
            "V281 Searchable Oak Desk",
            price="1000.00",
        )
        self.change_price(eligible, "800.00", self.now)

        wrong_location = self.create_listing(
            "V281 Searchable Oak Desk Munich",
            location="Munich",
        )
        self.change_price(wrong_location, "700.00", self.now)

        other_category = self.create_listing(
            "V281 Searchable Oak Desk Other",
            category=self.other_category,
        )
        self.change_price(other_category, "600.00", self.now)
        self.create_listing(
            "V281 Searchable Oak Desk Baseline",
            price="800.00",
        )

        response = self.browse(
            {
                "q": "Oak Desk",
                "location": "Berlin",
                "min_price": "750",
                "max_price": "850",
                "category": self.category.slug,
                "price_drops": "1",
                "sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281,
            }
        )
        self.assertEqual(
            self.response_titles(response),
            ["V281 Searchable Oak Desk"],
        )

    def test_sort_combines_with_each_v280_period(self):
        fixtures = (
            ("V281 Drop 12 Hours", timedelta(hours=12)),
            ("V281 Drop 3 Days", timedelta(days=3)),
            ("V281 Drop 20 Days", timedelta(days=20)),
            ("V281 Drop 45 Days", timedelta(days=45)),
        )
        for title, age in fixtures:
            listing = self.create_listing(title)
            self.change_price(listing, "500.00", self.now - age)

        expectations = {
            "24h": ["V281 Drop 12 Hours"],
            "7d": [
                "V281 Drop 12 Hours",
                "V281 Drop 3 Days",
            ],
            "30d": [
                "V281 Drop 12 Hours",
                "V281 Drop 3 Days",
                "V281 Drop 20 Days",
            ],
        }
        for period, expected in expectations.items():
            with self.subTest(period=period):
                response = self.browse(
                    {
                        "price_drop_period": period,
                        "sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281,
                    }
                )
                self.assertEqual(
                    self.response_titles(response),
                    expected,
                )

    def test_pagination_preserves_biggest_discount_sort(self):
        for index in range(13):
            listing = self.create_listing(
                f"V281 Paginated Drop {index:02d}"
            )
            self.change_price(
                listing,
                "500.00",
                self.now - timedelta(minutes=index),
            )

        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        self.assertEqual(
            response.context["page_obj"].paginator.count,
            13,
        )
        self.assertEqual(
            response.context["page_querystring"],
            "sort=biggest_price_drop",
        )
        self.assertContains(
            response,
            "sort=biggest_price_drop&page=2",
        )

    def test_saved_search_creation_and_execution_preserve_sort(self):
        eligible = self.create_listing("V281 Saved Eligible")
        self.change_price(eligible, "500.00", self.now)
        self.create_listing("V281 Saved Baseline")

        self.client.force_login(self.seller)
        response = self.browse(
            {"sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281}
        )
        querystring = response.context["save_search_querystring"]
        self.assertEqual(
            parse_qs(querystring)["sort"],
            [BIGGEST_PRICE_DROP_SORT_VALUE_V281],
        )

        create_response = self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "V281 biggest discounts",
                "querystring": querystring,
            },
        )
        self.assertEqual(create_response.status_code, 302)

        saved = SavedSearch.objects.get(
            user=self.seller,
            name="V281 biggest discounts",
        )
        self.assertEqual(
            saved.query_params["sort"],
            BIGGEST_PRICE_DROP_SORT_VALUE_V281,
        )
        self.assertIn(
            "sort=biggest_price_drop",
            saved.get_absolute_url(),
        )
        self.assertIn(
            {
                "label": "Sort",
                "value": BIGGEST_PRICE_DROP_SORT_LABEL_V281,
                "param": "sort",
                "kind": "sort",
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
            ["V281 Saved Eligible"],
        )
        self.assertContains(
            executed,
            'value="biggest_price_drop" selected',
        )

    def test_active_chip_and_template_display_biggest_discount(self):
        listing = self.create_listing("V281 Template Drop")
        self.change_price(listing, "500.00", self.now)

        response = self.browse(
            {
                "q": "Template Drop",
                "sort": BIGGEST_PRICE_DROP_SORT_VALUE_V281,
            }
        )
        chips = {
            chip["clear_param"]: chip
            for chip in response.context["active_filter_chips"]
        }
        self.assertEqual(
            chips["sort"]["value"],
            BIGGEST_PRICE_DROP_SORT_LABEL_V281,
        )
        clear_query = parse_qs(
            urlsplit(chips["sort"]["clear_url"]).query
        )
        self.assertNotIn("sort", clear_query)
        self.assertEqual(clear_query["q"], ["Template Drop"])
        self.assertContains(
            response,
            'value="biggest_price_drop" selected',
        )
        self.assertContains(response, "Biggest discount")
        self.assertContains(response, 'name="price_drops"')
        self.assertContains(response, 'name="price_drop_period"')
        html = response.content.decode("utf-8")
        checkbox_start = html.index('id="price-drops-only-v278"')
        checkbox_end = html.index(">", checkbox_start)
        self.assertIn(
            "checked",
            html[checkbox_start:checkbox_end],
        )

    def test_recent_price_drop_sort_behavior_is_unchanged(self):
        older_larger = self.create_listing("V281 Older Larger Drop")
        self.change_price(
            older_larger,
            "100.00",
            self.now - timedelta(days=2),
        )
        newer_smaller = self.create_listing("V281 Newer Smaller Drop")
        self.change_price(
            newer_smaller,
            "900.00",
            self.now - timedelta(hours=1),
        )

        response = self.browse({"sort": "recent_price_drop"})
        self.assertEqual(
            self.response_titles(response),
            [
                "V281 Newer Smaller Drop",
                "V281 Older Larger Drop",
            ],
        )

    def test_existing_price_sorts_are_unchanged(self):
        self.create_listing("V281 Expensive", price="900.00")
        self.create_listing("V281 Cheap", price="100.00")

        low_response = self.browse({"sort": "price_low"})
        self.assertEqual(
            self.response_titles(low_response),
            ["V281 Cheap", "V281 Expensive"],
        )

        high_response = self.browse({"sort": "price_high"})
        self.assertEqual(
            self.response_titles(high_response),
            ["V281 Expensive", "V281 Cheap"],
        )

    def test_invalid_sort_retains_newest_fallback(self):
        older = self.create_listing("V281 Invalid Older")
        newer = self.create_listing("V281 Invalid Newer")
        Listing.objects.filter(pk=older.pk).update(
            created_at=self.now - timedelta(hours=2)
        )
        Listing.objects.filter(pk=newer.pk).update(
            created_at=self.now - timedelta(hours=1)
        )

        response = self.browse({"sort": "largest_discount"})
        self.assertEqual(
            self.response_titles(response),
            ["V281 Invalid Newer", "V281 Invalid Older"],
        )

    def test_contract_and_no_migration(self):
        self.assertTrue(BIGGEST_PRICE_DROP_SORT_V281)
        self.assertEqual(
            BIGGEST_PRICE_DROP_SORT_VALUE_V281,
            "biggest_price_drop",
        )
        self.assertEqual(
            BIGGEST_PRICE_DROP_SORT_LABEL_V281,
            "Biggest discount",
        )
        self.assertEqual(
            SORT_LABELS_V78[BIGGEST_PRICE_DROP_SORT_VALUE_V281],
            BIGGEST_PRICE_DROP_SORT_LABEL_V281,
        )

        migration_dir = (
            Path(settings.BASE_DIR)
            / "listings"
            / "migrations"
        )
        self.assertEqual(
            list(migration_dir.glob("*v281*")),
            [],
        )
