"""Focused contracts for the V342 promotion catalog and pricing rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from django.test import SimpleTestCase

from promotions.doping_catalog_v342 import (
    DOPING_CATALOG_V342,
    EXCLUDED_ROOT_SLUGS_V342,
    PRICE_MATRIX_V342,
    PROMOTION_DEFINITIONS_V342,
    ROOT_PRICE_GROUPS_V342,
    WEEK_DISCOUNTS_V342,
    DurationModeV342,
    PriceGroupV342,
    PromotionCodeV342,
    promotion_end_at_v342,
    quote_promotion_v342,
    resolve_price_group_v342,
)


@dataclass
class CategoryStubV342:
    slug: str
    parent: "CategoryStubV342 | None" = None
    pk: int | None = None


class DopingCatalogV342Tests(SimpleTestCase):
    def test_catalog_marker_and_complete_dimensions(self):
        self.assertTrue(DOPING_CATALOG_V342)
        self.assertEqual(len(PromotionCodeV342), 8)
        self.assertEqual(len(PriceGroupV342), 9)
        self.assertEqual(len(PROMOTION_DEFINITIONS_V342), 8)
        self.assertEqual(len(PRICE_MATRIX_V342), 8)

        for code in PromotionCodeV342:
            self.assertIn(code, PROMOTION_DEFINITIONS_V342)
            self.assertIn(code, PRICE_MATRIX_V342)
            self.assertEqual(set(PRICE_MATRIX_V342[code]), set(PriceGroupV342))

        self.assertEqual(
            sum(len(row) for row in PRICE_MATRIX_V342.values()),
            72,
        )

    def test_exact_price_matrix_matches_supplied_reference(self):
        expected = {
            PromotionCodeV342.SMALL_PHOTO: (
                "429", "429", "65", "89", "109", "75", "75", "75", "75"
            ),
            PromotionCodeV342.URGENT: (
                "1999", "1999", "89", "89", "409", "99", "99", "99", "99"
            ),
            PromotionCodeV342.HOMEPAGE_SHOWCASE: (
                "8399", "8399", "4699", "8799", "5099",
                "3199", None, "2859", "1949"
            ),
            PromotionCodeV342.CATEGORY_SHOWCASE: (
                "2549", "2549", "219", "229", "999",
                None, None, "219", None
            ),
            PromotionCodeV342.TOP_RANKING: (
                "7299", "7299", "649", "1149", "1429",
                "309", "309", "509", "309"
            ),
            PromotionCodeV342.DETAILED_SEARCH_SHOWCASE: (
                "989", "989", "89", "89", "409", "89", "89", "89", "89"
            ),
            PromotionCodeV342.COLORFUL_TITLE: (
                None, "679", "109", "89", "109", "75", "75", "75", "75"
            ),
            PromotionCodeV342.REFRESH: (
                "979", "979", "120", "99", "109", "89", "79", "79", "79"
            ),
        }

        groups = tuple(PriceGroupV342)

        for code, values in expected.items():
            expected_row = {
                group: Decimal(value) if value is not None else None
                for group, value in zip(groups, values, strict=True)
            }
            self.assertEqual(PRICE_MATRIX_V342[code], expected_row)

    def test_duration_modes_match_product_contract(self):
        fixed_week_codes = {
            PromotionCodeV342.URGENT,
            PromotionCodeV342.HOMEPAGE_SHOWCASE,
            PromotionCodeV342.CATEGORY_SHOWCASE,
            PromotionCodeV342.TOP_RANKING,
            PromotionCodeV342.DETAILED_SEARCH_SHOWCASE,
        }
        lifetime_codes = {
            PromotionCodeV342.SMALL_PHOTO,
            PromotionCodeV342.COLORFUL_TITLE,
        }

        for code in fixed_week_codes:
            definition = PROMOTION_DEFINITIONS_V342[code]
            self.assertEqual(
                definition.duration_mode,
                DurationModeV342.FIXED_WEEKS,
            )
            self.assertEqual(definition.allowed_weeks, (1, 2, 4))

        for code in lifetime_codes:
            definition = PROMOTION_DEFINITIONS_V342[code]
            self.assertEqual(
                definition.duration_mode,
                DurationModeV342.LISTING_LIFETIME,
            )
            self.assertEqual(definition.allowed_weeks, ())

        refresh = PROMOTION_DEFINITIONS_V342[PromotionCodeV342.REFRESH]
        self.assertEqual(refresh.duration_mode, DurationModeV342.SINGLE_USE)
        self.assertEqual(refresh.allowed_weeks, ())

    def test_week_discount_contract(self):
        self.assertEqual(
            WEEK_DISCOUNTS_V342,
            {
                1: Decimal("0.00"),
                2: Decimal("0.05"),
                4: Decimal("0.07"),
            },
        )

    def test_one_week_quote_has_no_discount(self):
        quote = quote_promotion_v342(
            PromotionCodeV342.URGENT,
            PriceGroupV342.MARKETPLACE,
            requested_weeks=1,
        )

        self.assertEqual(quote.unit_price, Decimal("89.00"))
        self.assertEqual(quote.subtotal, Decimal("89.00"))
        self.assertEqual(quote.discount_percent, Decimal("0.00"))
        self.assertEqual(quote.total_price, Decimal("89.00"))
        self.assertEqual(quote.duration_days, 7)

    def test_two_week_quote_applies_five_percent_discount(self):
        quote = quote_promotion_v342(
            PromotionCodeV342.TOP_RANKING,
            PriceGroupV342.REAL_ESTATE,
            requested_weeks=2,
        )

        self.assertEqual(quote.unit_price, Decimal("7299.00"))
        self.assertEqual(quote.subtotal, Decimal("14598.00"))
        self.assertEqual(quote.discount_percent, Decimal("0.05"))
        self.assertEqual(quote.total_price, Decimal("13868.10"))
        self.assertEqual(quote.duration_days, 14)

    def test_four_week_quote_applies_seven_percent_discount(self):
        quote = quote_promotion_v342(
            PromotionCodeV342.URGENT,
            PriceGroupV342.VEHICLES,
            requested_weeks=4,
        )

        self.assertEqual(quote.unit_price, Decimal("1999.00"))
        self.assertEqual(quote.subtotal, Decimal("7996.00"))
        self.assertEqual(quote.discount_percent, Decimal("0.07"))
        self.assertEqual(quote.total_price, Decimal("7436.28"))
        self.assertEqual(quote.duration_days, 28)

    def test_listing_lifetime_quote_has_no_week_duration(self):
        quote = quote_promotion_v342(
            PromotionCodeV342.SMALL_PHOTO,
            PriceGroupV342.MARKETPLACE,
        )

        self.assertEqual(
            quote.duration_mode,
            DurationModeV342.LISTING_LIFETIME,
        )
        self.assertIsNone(quote.requested_weeks)
        self.assertEqual(quote.total_price, Decimal("89.00"))
        self.assertIsNone(quote.duration_days)

    def test_single_use_quote_has_no_week_duration(self):
        quote = quote_promotion_v342(
            PromotionCodeV342.REFRESH,
            PriceGroupV342.PETS,
        )

        self.assertEqual(
            quote.duration_mode,
            DurationModeV342.SINGLE_USE,
        )
        self.assertEqual(quote.total_price, Decimal("79.00"))
        self.assertIsNone(quote.duration_days)

    def test_unavailable_product_group_combinations_fail_closed(self):
        unavailable = (
            (
                PromotionCodeV342.HOMEPAGE_SHOWCASE,
                PriceGroupV342.JOBS,
            ),
            (
                PromotionCodeV342.CATEGORY_SHOWCASE,
                PriceGroupV342.LESSONS,
            ),
            (
                PromotionCodeV342.CATEGORY_SHOWCASE,
                PriceGroupV342.JOBS,
            ),
            (
                PromotionCodeV342.CATEGORY_SHOWCASE,
                PriceGroupV342.HELPERS,
            ),
            (
                PromotionCodeV342.COLORFUL_TITLE,
                PriceGroupV342.REAL_ESTATE,
            ),
        )

        for code, group in unavailable:
            with self.subTest(code=code, group=group):
                with self.assertRaisesMessage(
                    ValueError,
                    "Promotion is unavailable for this price group.",
                ):
                    quote_promotion_v342(code, group, requested_weeks=None)

    def test_invalid_fixed_duration_fails_closed(self):
        for weeks in (None, 0, 3, 5, -1):
            with self.subTest(weeks=weeks):
                with self.assertRaisesMessage(
                    ValueError,
                    "Duration must be 1, 2, or 4 weeks.",
                ):
                    quote_promotion_v342(
                        PromotionCodeV342.URGENT,
                        PriceGroupV342.VEHICLES,
                        requested_weeks=weeks,
                    )

    def test_lifetime_and_single_use_products_reject_week_input(self):
        for code in (
            PromotionCodeV342.SMALL_PHOTO,
            PromotionCodeV342.COLORFUL_TITLE,
            PromotionCodeV342.REFRESH,
        ):
            with self.subTest(code=code):
                with self.assertRaisesMessage(
                    ValueError,
                    "This promotion does not accept a week duration.",
                ):
                    quote_promotion_v342(
                        code,
                        PriceGroupV342.VEHICLES,
                        requested_weeks=1,
                    )

    def test_root_category_price_group_mapping(self):
        expected = {
            "real-estate": PriceGroupV342.REAL_ESTATE,
            "vehicles": PriceGroupV342.VEHICLES,
            "electronics": PriceGroupV342.MARKETPLACE,
            "fashion": PriceGroupV342.MARKETPLACE,
            "home-garden": PriceGroupV342.MARKETPLACE,
            "baby-kids": PriceGroupV342.MARKETPLACE,
            "sports-hobbies": PriceGroupV342.MARKETPLACE,
            "jobs": PriceGroupV342.JOBS,
            "pets": PriceGroupV342.PETS,
            "services": PriceGroupV342.MARKETPLACE,
        }

        for slug, group in expected.items():
            with self.subTest(slug=slug):
                category = CategoryStubV342(slug=slug, pk=1)
                self.assertEqual(resolve_price_group_v342(category), group)

        self.assertGreaterEqual(
            set(ROOT_PRICE_GROUPS_V342),
            set(expected),
        )

    def test_descendants_inherit_root_price_group(self):
        root = CategoryStubV342("home-garden", pk=1)
        child = CategoryStubV342("home-garden-furniture", root, 2)
        grandchild = CategoryStubV342(
            "home-garden-living-room",
            child,
            3,
        )

        self.assertEqual(
            resolve_price_group_v342(grandchild),
            PriceGroupV342.MARKETPLACE,
        )

    def test_lessons_and_helpers_use_specific_subtree_overrides(self):
        services = CategoryStubV342("services", pk=1)
        lessons = CategoryStubV342(
            "services-lessons-training",
            services,
            2,
        )
        language = CategoryStubV342(
            "services-language-lessons",
            lessons,
            3,
        )

        jobs = CategoryStubV342("jobs", pk=10)
        helpers = CategoryStubV342("jobs-service", jobs, 11)
        cleaning = CategoryStubV342("jobs-cleaning", helpers, 12)

        self.assertEqual(
            resolve_price_group_v342(language),
            PriceGroupV342.LESSONS,
        )
        self.assertEqual(
            resolve_price_group_v342(cleaning),
            PriceGroupV342.HELPERS,
        )

    def test_test_only_and_unknown_roots_are_not_sellable(self):
        for slug in EXCLUDED_ROOT_SLUGS_V342:
            with self.subTest(slug=slug):
                self.assertIsNone(
                    resolve_price_group_v342(
                        CategoryStubV342(slug=slug, pk=1)
                    )
                )

        self.assertIsNone(
            resolve_price_group_v342(
                CategoryStubV342(slug="unknown-root", pk=2)
            )
        )
        self.assertIsNone(resolve_price_group_v342(None))

    def test_category_cycle_fails_closed(self):
        first = CategoryStubV342("vehicles", pk=1)
        second = CategoryStubV342("vehicles-cars", first, 2)
        first.parent = second

        self.assertIsNone(resolve_price_group_v342(second))

    def test_fixed_week_end_date(self):
        starts_at = datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc)

        self.assertEqual(
            promotion_end_at_v342(
                starts_at=starts_at,
                duration_mode=DurationModeV342.FIXED_WEEKS,
                requested_weeks=2,
                listing_expires_at=None,
            ),
            starts_at + timedelta(days=14),
        )

    def test_listing_lifetime_end_date_uses_listing_expiry(self):
        starts_at = datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc)
        listing_expiry = starts_at + timedelta(days=30)

        self.assertEqual(
            promotion_end_at_v342(
                starts_at=starts_at,
                duration_mode=DurationModeV342.LISTING_LIFETIME,
                requested_weeks=None,
                listing_expires_at=listing_expiry,
            ),
            listing_expiry,
        )

        self.assertIsNone(
            promotion_end_at_v342(
                starts_at=starts_at,
                duration_mode=DurationModeV342.LISTING_LIFETIME,
                requested_weeks=None,
                listing_expires_at=None,
            )
        )

    def test_single_use_end_date_is_activation_time(self):
        starts_at = datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc)

        self.assertEqual(
            promotion_end_at_v342(
                starts_at=starts_at,
                duration_mode=DurationModeV342.SINGLE_USE,
                requested_weeks=None,
                listing_expires_at=None,
            ),
            starts_at,
        )
