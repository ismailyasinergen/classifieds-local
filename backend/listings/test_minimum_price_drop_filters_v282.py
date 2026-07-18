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
from listings.listing_price_drop_threshold_filter_v282 import (
    MINIMUM_PRICE_DROP_FILTERS_V282,
    MIN_PRICE_DROP_AMOUNT_LABEL_V282,
    MIN_PRICE_DROP_AMOUNT_PARAM_V282,
    MIN_PRICE_DROP_PERCENT_LABEL_V282,
    MIN_PRICE_DROP_PERCENT_PARAM_V282,
    normalize_min_price_drop_amount_v282,
    normalize_min_price_drop_percent_v282,
)
from listings.models import Listing, ListingPriceHistory, SavedSearch
from listings.saved_searches import (
    SAVED_SEARCH_ALLOWED_KEYS,
    summarize_saved_search_params,
)


class MinimumPriceDropFiltersV282Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.seller = User.objects.create_user(
            username="v282-seller",
            password="StrongPass123!",
        )
        UserProfile.objects.get_or_create(user=cls.seller)

        cls.category = Category.objects.create(
            name="V282 Furniture",
            slug="v282-furniture",
        )
        cls.other_category = Category.objects.create(
            name="V282 Other",
            slug="v282-other",
        )
        cls.attribute_category = Category.objects.create(
            name="V282 Cars",
            slug="cars",
        )
        cls.now = timezone.now()

    def create_listing(
        self,
        title,
        *,
        price="1000.00",
        category=None,
        location="Berlin",
        attributes=None,
    ):
        return Listing.objects.create(
            title=title,
            description=f"Searchable {title}",
            price=Decimal(price),
            category=category or self.category,
            owner=self.seller,
            location=location,
            attributes=attributes or {},
            status=Listing.Status.APPROVED,
            expires_at=self.now + timedelta(days=60),
        )

    def change_price(self, listing, price, changed_at=None):
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
        ).update(changed_at=changed_at or self.now)

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
    def response_titles(response):
        return [
            listing.title
            for listing in response.context["listings"]
        ]

    def test_amount_filter_supports_main_category_and_inclusive_decimals(self):
        exact = self.create_listing("V282 Amount Exact")
        self.change_price(exact, "900.00")

        below = self.create_listing("V282 Amount Below")
        self.change_price(below, "900.01")

        decimal_exact = self.create_listing(
            "V282 Decimal Amount Exact",
            price="100.00",
        )
        self.change_price(decimal_exact, "74.50")

        params = {MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100.00"}
        main_response = self.browse(params)
        category_response = self.browse(
            params,
            category=self.category,
        )
        for response in (main_response, category_response):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                self.response_titles(response),
                ["V282 Amount Exact"],
            )

        decimal_response = self.browse(
            {MIN_PRICE_DROP_AMOUNT_PARAM_V282: "25.50"}
        )
        self.assertCountEqual(
            self.response_titles(decimal_response),
            [
                "V282 Amount Exact",
                "V282 Amount Below",
                "V282 Decimal Amount Exact",
            ],
        )

    def test_percent_filter_supports_main_category_and_precise_boundaries(self):
        exact = self.create_listing("V282 Percent Exact")
        self.change_price(exact, "800.00")

        below = self.create_listing("V282 Percent Below")
        self.change_price(below, "800.01")

        repeating = self.create_listing(
            "V282 Repeating Percentage",
            price="3.00",
        )
        self.change_price(repeating, "2.00")

        params = {MIN_PRICE_DROP_PERCENT_PARAM_V282: "20"}
        main_response = self.browse(params)
        category_response = self.browse(
            params,
            category=self.category,
        )
        for response in (main_response, category_response):
            self.assertCountEqual(
                self.response_titles(response),
                [
                    "V282 Percent Exact",
                    "V282 Repeating Percentage",
                ],
            )

        precise_response = self.browse(
            {MIN_PRICE_DROP_PERCENT_PARAM_V282: "33.3333"}
        )
        self.assertEqual(
            self.response_titles(precise_response),
            ["V282 Repeating Percentage"],
        )
        above_response = self.browse(
            {MIN_PRICE_DROP_PERCENT_PARAM_V282: "33.3334"}
        )
        self.assertEqual(self.response_titles(above_response), [])

    def test_amount_and_percent_thresholds_use_and_semantics(self):
        both = self.create_listing("V282 Meets Both")
        self.change_price(both, "700.00")

        amount_only = self.create_listing(
            "V282 Meets Amount Only",
            price="2000.00",
        )
        self.change_price(amount_only, "1800.00")

        percent_only = self.create_listing(
            "V282 Meets Percent Only",
            price="100.00",
        )
        self.change_price(percent_only, "70.00")

        response = self.browse(
            {
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "20",
            }
        )
        self.assertEqual(
            self.response_titles(response),
            ["V282 Meets Both"],
        )

    def test_invalid_current_reduction_states_are_excluded(self):
        valid = self.create_listing("V282 Valid Drop")
        self.change_price(valid, "800.00")

        self.create_listing("V282 Baseline Only")
        missing_previous = self.create_listing("V282 Missing Previous")
        self.assertTrue(
            ListingPriceHistory.objects.filter(
                listing=missing_previous,
                previous_price__isnull=True,
            ).exists()
        )

        zero = self.create_listing("V282 Zero Previous", price="0.00")
        Listing.objects.filter(pk=zero.pk).update(
            price=Decimal("-1.00")
        )
        ListingPriceHistory.objects.create(
            listing=zero,
            previous_price=Decimal("0.00"),
            new_price=Decimal("-1.00"),
            changed_at=self.now,
        )

        increased = self.create_listing("V282 Latest Increase")
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

        mismatched = self.create_listing("V282 Current Mismatch")
        self.change_price(mismatched, "800.00")
        Listing.objects.filter(pk=mismatched.pk).update(
            price=Decimal("750.00")
        )

        response = self.browse(
            {MIN_PRICE_DROP_AMOUNT_PARAM_V282: "1"}
        )
        self.assertEqual(
            self.response_titles(response),
            ["V282 Valid Drop"],
        )

    def test_missing_and_empty_parameters_do_not_activate_filtering(self):
        dropped = self.create_listing("V282 Missing Drop")
        self.change_price(dropped, "900.00")
        self.create_listing("V282 Missing Baseline")

        for params in (
            {},
            {
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "   ",
            },
        ):
            with self.subTest(params=params):
                response = self.browse(params)
                self.assertCountEqual(
                    self.response_titles(response),
                    ["V282 Missing Drop", "V282 Missing Baseline"],
                )
                self.assertEqual(
                    response.context["search_min_price_drop_amount"],
                    "",
                )
                self.assertEqual(
                    response.context["search_min_price_drop_percent"],
                    "",
                )

    def test_invalid_decimal_inputs_are_ignored_without_chips_or_storage(self):
        dropped = self.create_listing(
            "V282 Invalid Drop",
            price="1000.00",
        )
        self.change_price(dropped, "900.00")
        self.create_listing("V282 Invalid Baseline", price="500.00")

        invalid_values = {
            MIN_PRICE_DROP_AMOUNT_PARAM_V282: (
                "0",
                "-1",
                "amount",
                "10amount",
                "1,5",
                "NaN",
                "Infinity",
                "-Infinity",
                "999999999999.99",
                "1.001",
            ),
            MIN_PRICE_DROP_PERCENT_PARAM_V282: (
                "0",
                "-1",
                "percent",
                "10percent",
                "1,5",
                "NaN",
                "Infinity",
                "-Infinity",
                "999999999999999.00",
                "0.00000000001",
            ),
        }

        for param, values in invalid_values.items():
            for value in values:
                with self.subTest(param=param, value=value):
                    response = self.browse({param: value})
                    self.assertCountEqual(
                        self.response_titles(response),
                        ["V282 Invalid Drop", "V282 Invalid Baseline"],
                    )
                    self.assertFalse(
                        any(
                            chip["clear_param"] == param
                            for chip in response.context[
                                "active_filter_chips"
                            ]
                        )
                    )
                    self.assertNotIn(
                        param,
                        parse_qs(
                            response.context["save_search_querystring"]
                        ),
                    )

        sorted_response = self.browse(
            {
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "NaN",
                "sort": "price_low",
            }
        )
        self.assertEqual(
            self.response_titles(sorted_response),
            ["V282 Invalid Baseline", "V282 Invalid Drop"],
        )

    def test_one_valid_and_one_invalid_threshold_applies_only_valid_value(self):
        amount_match = self.create_listing("V282 Amount Match")
        self.change_price(amount_match, "850.00")
        percent_match = self.create_listing(
            "V282 Percent Match",
            price="100.00",
        )
        self.change_price(percent_match, "50.00")

        amount_response = self.browse(
            {
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "NaN",
            }
        )
        self.assertEqual(
            self.response_titles(amount_response),
            ["V282 Amount Match"],
        )

        percent_response = self.browse(
            {
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "invalid",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "20",
            }
        )
        self.assertEqual(
            self.response_titles(percent_response),
            ["V282 Percent Match"],
        )

    def test_thresholds_combine_with_v278_price_drop_filter(self):
        eligible = self.create_listing("V282 V278 Eligible")
        self.change_price(eligible, "800.00")
        too_small = self.create_listing("V282 V278 Too Small")
        self.change_price(too_small, "950.00")
        self.create_listing("V282 V278 Baseline")

        response = self.browse(
            {
                "price_drops": "1",
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100",
            }
        )
        self.assertEqual(
            self.response_titles(response),
            ["V282 V278 Eligible"],
        )

    def test_thresholds_combine_with_each_v280_period(self):
        fixtures = (
            ("V282 Drop 12 Hours", timedelta(hours=12)),
            ("V282 Drop 3 Days", timedelta(days=3)),
            ("V282 Drop 20 Days", timedelta(days=20)),
            ("V282 Drop 45 Days", timedelta(days=45)),
        )
        for title, age in fixtures:
            listing = self.create_listing(title)
            self.change_price(listing, "800.00", self.now - age)

        expectations = {
            "24h": ["V282 Drop 12 Hours"],
            "7d": ["V282 Drop 12 Hours", "V282 Drop 3 Days"],
            "30d": [
                "V282 Drop 12 Hours",
                "V282 Drop 3 Days",
                "V282 Drop 20 Days",
            ],
        }
        for period, expected in expectations.items():
            with self.subTest(period=period):
                response = self.browse(
                    {
                        "price_drop_period": period,
                        MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100",
                    }
                )
                self.assertCountEqual(
                    self.response_titles(response),
                    expected,
                )

    def test_recent_sort_order_is_preserved_after_threshold_filtering(self):
        older_larger = self.create_listing("V282 Recent Older")
        self.change_price(
            older_larger,
            "500.00",
            self.now - timedelta(days=2),
        )
        newer_smaller = self.create_listing("V282 Recent Newer")
        self.change_price(
            newer_smaller,
            "850.00",
            self.now - timedelta(hours=1),
        )
        excluded = self.create_listing("V282 Recent Excluded")
        self.change_price(excluded, "950.00", self.now)

        response = self.browse(
            {
                "sort": "recent_price_drop",
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100",
            }
        )
        self.assertEqual(
            self.response_titles(response),
            ["V282 Recent Newer", "V282 Recent Older"],
        )

    def test_biggest_discount_order_is_preserved_after_threshold_filtering(self):
        high_percent = self.create_listing(
            "V282 High Percent",
            price="100.00",
        )
        self.change_price(high_percent, "50.00")
        high_amount = self.create_listing("V282 High Amount")
        self.change_price(high_amount, "600.00")
        excluded = self.create_listing("V282 Biggest Excluded")
        self.change_price(excluded, "990.00")

        response = self.browse(
            {
                "sort": "biggest_price_drop",
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "25",
            }
        )
        self.assertEqual(
            self.response_titles(response),
            ["V282 High Percent", "V282 High Amount"],
        )

    def test_regular_price_and_newest_sorts_are_preserved(self):
        cheap = self.create_listing("V282 Cheap", price="300.00")
        self.change_price(cheap, "100.00")
        expensive = self.create_listing("V282 Expensive")
        self.change_price(expensive, "700.00")
        Listing.objects.filter(pk=cheap.pk).update(
            created_at=self.now - timedelta(hours=2)
        )
        Listing.objects.filter(pk=expensive.pk).update(
            created_at=self.now - timedelta(hours=1)
        )

        params = {MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100"}
        low_response = self.browse({**params, "sort": "price_low"})
        high_response = self.browse({**params, "sort": "price_high"})
        newest_response = self.browse({**params, "sort": "newest"})

        self.assertEqual(
            self.response_titles(low_response),
            ["V282 Cheap", "V282 Expensive"],
        )
        self.assertEqual(
            self.response_titles(high_response),
            ["V282 Expensive", "V282 Cheap"],
        )
        self.assertEqual(
            self.response_titles(newest_response),
            ["V282 Expensive", "V282 Cheap"],
        )

    def test_thresholds_combine_with_public_and_attribute_filters(self):
        eligible = self.create_listing(
            "V282 Searchable Volvo Wagon",
            category=self.attribute_category,
            location="Berlin",
            attributes={"marka": "Volvo"},
        )
        self.change_price(eligible, "800.00")

        wrong_attribute = self.create_listing(
            "V282 Searchable Volvo Wagon Other",
            category=self.attribute_category,
            location="Berlin",
            attributes={"marka": "Saab"},
        )
        self.change_price(wrong_attribute, "700.00")

        response = self.browse(
            {
                "q": "Volvo Wagon",
                "location": "Berlin",
                "category": self.attribute_category.slug,
                "min_price": "750",
                "max_price": "850",
                "attr_marka": "Volvo",
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "10",
            }
        )
        self.assertEqual(
            self.response_titles(response),
            ["V282 Searchable Volvo Wagon"],
        )

    def test_pagination_preserves_each_and_both_thresholds(self):
        for index in range(13):
            listing = self.create_listing(
                f"V282 Paginated Drop {index:02d}"
            )
            self.change_price(
                listing,
                "800.00",
                self.now - timedelta(minutes=index),
            )

        param_sets = (
            {MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100.00"},
            {MIN_PRICE_DROP_PERCENT_PARAM_V282: "10.5"},
            {
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100.00",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "10.5",
            },
        )
        for params in param_sets:
            with self.subTest(params=params):
                response = self.browse(params)
                self.assertEqual(
                    response.context["page_obj"].paginator.count,
                    13,
                )
                preserved = parse_qs(
                    response.context["page_querystring"]
                )
                for key, value in params.items():
                    self.assertEqual(preserved[key], [value])
                    self.assertContains(
                        response,
                        f"{key}={value}",
                    )

    def test_saved_search_creation_summary_and_execution_preserve_thresholds(self):
        eligible = self.create_listing("V282 Saved Eligible")
        self.change_price(eligible, "700.00")
        amount_only = self.create_listing("V282 Saved Amount Only")
        self.change_price(amount_only, "850.00")

        self.client.force_login(self.seller)
        params = {
            MIN_PRICE_DROP_AMOUNT_PARAM_V282: "200.00",
            MIN_PRICE_DROP_PERCENT_PARAM_V282: "20.5000",
        }
        response = self.browse(params)
        querystring = response.context["save_search_querystring"]
        parsed = parse_qs(querystring)
        self.assertEqual(
            parsed[MIN_PRICE_DROP_AMOUNT_PARAM_V282],
            ["200.00"],
        )
        self.assertEqual(
            parsed[MIN_PRICE_DROP_PERCENT_PARAM_V282],
            ["20.5000"],
        )

        create_response = self.client.post(
            reverse("listings:saved_search_create"),
            {
                "name": "V282 minimum drops",
                "querystring": querystring,
            },
        )
        self.assertEqual(create_response.status_code, 302)

        saved = SavedSearch.objects.get(
            user=self.seller,
            name="V282 minimum drops",
        )
        self.assertEqual(
            saved.query_params[MIN_PRICE_DROP_AMOUNT_PARAM_V282],
            "200.00",
        )
        self.assertEqual(
            saved.query_params[MIN_PRICE_DROP_PERCENT_PARAM_V282],
            "20.5000",
        )
        summaries = summarize_saved_search_params(saved.query_params)
        self.assertIn(
            {
                "label": MIN_PRICE_DROP_AMOUNT_LABEL_V282,
                "value": "200 TL",
                "param": MIN_PRICE_DROP_AMOUNT_PARAM_V282,
                "kind": "min_price_drop_amount",
            },
            summaries,
        )
        self.assertIn(
            {
                "label": MIN_PRICE_DROP_PERCENT_LABEL_V282,
                "value": "20.5%",
                "param": MIN_PRICE_DROP_PERCENT_PARAM_V282,
                "kind": "min_price_drop_percent",
            },
            summaries,
        )

        with patch(
            "listings.listing_price_drop_period_filter_v280.timezone.now",
            return_value=self.now,
        ):
            executed = self.client.get(saved.get_absolute_url())
        self.assertEqual(
            self.response_titles(executed),
            ["V282 Saved Eligible"],
        )

    def test_active_chips_format_and_clear_only_their_own_threshold(self):
        listing = self.create_listing("V282 Chip Listing")
        self.change_price(listing, "700.00")
        response = self.browse(
            {
                "q": "Chip Listing",
                "sort": "biggest_price_drop",
                "price_drop_period": "30d",
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100.00",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "20.5000",
            }
        )
        chips = {
            chip["clear_param"]: chip
            for chip in response.context["active_filter_chips"]
        }
        self.assertEqual(
            chips[MIN_PRICE_DROP_AMOUNT_PARAM_V282]["label"],
            MIN_PRICE_DROP_AMOUNT_LABEL_V282,
        )
        self.assertEqual(
            chips[MIN_PRICE_DROP_AMOUNT_PARAM_V282]["value"],
            "100 TL",
        )
        self.assertEqual(
            chips[MIN_PRICE_DROP_PERCENT_PARAM_V282]["label"],
            MIN_PRICE_DROP_PERCENT_LABEL_V282,
        )
        self.assertEqual(
            chips[MIN_PRICE_DROP_PERCENT_PARAM_V282]["value"],
            "20.5%",
        )

        amount_clear = parse_qs(
            urlsplit(
                chips[MIN_PRICE_DROP_AMOUNT_PARAM_V282]["clear_url"]
            ).query
        )
        self.assertNotIn(MIN_PRICE_DROP_AMOUNT_PARAM_V282, amount_clear)
        self.assertEqual(
            amount_clear[MIN_PRICE_DROP_PERCENT_PARAM_V282],
            ["20.5000"],
        )

        percent_clear = parse_qs(
            urlsplit(
                chips[MIN_PRICE_DROP_PERCENT_PARAM_V282]["clear_url"]
            ).query
        )
        self.assertNotIn(MIN_PRICE_DROP_PERCENT_PARAM_V282, percent_clear)
        self.assertEqual(
            percent_clear[MIN_PRICE_DROP_AMOUNT_PARAM_V282],
            ["100.00"],
        )
        for clear_query in (amount_clear, percent_clear):
            self.assertEqual(clear_query["q"], ["Chip Listing"])
            self.assertEqual(clear_query["sort"], ["biggest_price_drop"])
            self.assertEqual(clear_query["price_drop_period"], ["30d"])

    def test_template_controls_restore_valid_values(self):
        listing = self.create_listing("V282 Template Listing")
        self.change_price(listing, "700.00")
        response = self.browse(
            {
                MIN_PRICE_DROP_AMOUNT_PARAM_V282: "100.00",
                MIN_PRICE_DROP_PERCENT_PARAM_V282: "20.5000",
            }
        )
        self.assertContains(response, 'name="min_price_drop_amount"')
        self.assertContains(response, 'name="min_price_drop_percent"')
        self.assertContains(response, 'inputmode="decimal"', count=2)
        self.assertContains(response, 'value="100.00"')
        self.assertContains(response, 'value="20.5000"')
        self.assertContains(response, 'name="price_drops"')
        self.assertContains(response, 'name="price_drop_period"')
        self.assertContains(response, 'value="recent_price_drop"')
        self.assertContains(response, 'value="biggest_price_drop"')

    def test_v278_v279_v280_and_v281_behaviors_remain_unchanged(self):
        older_larger = self.create_listing("V282 Legacy Older")
        self.change_price(
            older_larger,
            "500.00",
            self.now - timedelta(days=2),
        )
        newer_smaller = self.create_listing("V282 Legacy Newer")
        self.change_price(
            newer_smaller,
            "900.00",
            self.now - timedelta(hours=1),
        )
        self.create_listing("V282 Legacy Baseline")

        v278_response = self.browse({"price_drops": "1"})
        self.assertCountEqual(
            self.response_titles(v278_response),
            ["V282 Legacy Older", "V282 Legacy Newer"],
        )

        v279_response = self.browse({"sort": "recent_price_drop"})
        self.assertEqual(
            self.response_titles(v279_response),
            ["V282 Legacy Newer", "V282 Legacy Older"],
        )

        v280_response = self.browse({"price_drop_period": "24h"})
        self.assertEqual(
            self.response_titles(v280_response),
            ["V282 Legacy Newer"],
        )

        v281_response = self.browse({"sort": "biggest_price_drop"})
        self.assertEqual(
            self.response_titles(v281_response),
            ["V282 Legacy Older", "V282 Legacy Newer"],
        )

    def test_contract_validation_saved_search_allowlist_and_no_migration(self):
        self.assertTrue(MINIMUM_PRICE_DROP_FILTERS_V282)
        self.assertEqual(
            normalize_min_price_drop_amount_v282(" 25.50 "),
            "25.50",
        )
        self.assertEqual(
            normalize_min_price_drop_percent_v282(" 33.3333 "),
            "33.3333",
        )
        self.assertIn(
            MIN_PRICE_DROP_AMOUNT_PARAM_V282,
            SAVED_SEARCH_ALLOWED_KEYS,
        )
        self.assertIn(
            MIN_PRICE_DROP_PERCENT_PARAM_V282,
            SAVED_SEARCH_ALLOWED_KEYS,
        )

        migration_dir = (
            Path(settings.BASE_DIR)
            / "listings"
            / "migrations"
        )
        self.assertEqual(list(migration_dir.glob("*v282*")), [])
