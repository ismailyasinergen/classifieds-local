"""Seller purchase-flow contracts for the V342 doping catalog."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing
from promotions.doping_catalog_v342 import (
    PRICE_MATRIX_V342,
    PROMOTION_DEFINITIONS_V342,
    DurationModeV342,
    PriceGroupV342,
    PromotionCodeV342,
)
from promotions.models import ListingPromotion, PromotionPackage


class DopingPurchaseFlowV342Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="v342-purchase-owner",
            email="v342-purchase-owner@example.com",
            password="testpass123",
        )
        cls.other_user = User.objects.create_user(
            username="v342-purchase-other",
            email="v342-purchase-other@example.com",
            password="testpass123",
        )

        cls.vehicles = Category.objects.create(
            name="Vehicles",
            slug="vehicles",
        )
        cls.cars = Category.objects.create(
            name="Cars",
            slug="vehicles-cars-v342",
            parent=cls.vehicles,
        )
        cls.real_estate = Category.objects.create(
            name="Real Estate",
            slug="real-estate",
        )

        cls.vehicle_listing = Listing.objects.create(
            title="V342 vehicle promotion listing",
            description="Vehicle promotion purchase test.",
            price=Decimal("25000.00"),
            category=cls.cars,
            owner=cls.owner,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )
        cls.real_estate_listing = Listing.objects.create(
            title="V342 real estate promotion listing",
            description="Real estate promotion purchase test.",
            price=Decimal("250000.00"),
            category=cls.real_estate,
            owner=cls.owner,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def create_package(
        self,
        code=PromotionCodeV342.URGENT,
        group=PriceGroupV342.VEHICLES,
        *,
        price=None,
        is_active=True,
    ):
        definition = PROMOTION_DEFINITIONS_V342[code]

        if price is None:
            price = PRICE_MATRIX_V342[code][group]

        package_type = (
            PromotionPackage.PackageType.TOP
            if code == PromotionCodeV342.TOP_RANKING
            else PromotionPackage.PackageType.FEATURED
        )

        return PromotionPackage.objects.create(
            name=f"{definition.label} — {group.value}",
            package_type=package_type,
            duration_days=(
                7
                if definition.duration_mode
                == DurationModeV342.FIXED_WEEKS
                else 0
            ),
            price=price,
            priority=200 if code == PromotionCodeV342.TOP_RANKING else 0,
            is_active=is_active,
            catalog_code=code,
            price_group=group,
            duration_mode=definition.duration_mode,
        )

    def package_url(self, listing):
        return reverse(
            "promotions:listing_packages",
            kwargs={"pk": listing.pk},
        )

    def request_url(self, listing, package):
        return reverse(
            "promotions:listing_package_request",
            kwargs={
                "pk": listing.pk,
                "package_id": package.pk,
            },
        )

    def test_catalog_page_shows_only_matching_active_group_packages(self):
        matching = self.create_package()
        self.create_package(
            code=PromotionCodeV342.TOP_RANKING,
            is_active=False,
        )
        other_group = self.create_package(
            group=PriceGroupV342.REAL_ESTATE,
        )

        self.client.force_login(self.owner)
        response = self.client.get(
            self.package_url(self.vehicle_listing)
        )

        self.assertEqual(response.status_code, 200)
        cards = response.context["package_cards"]
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["package"], matching)
        self.assertNotContains(response, other_group.name)
        self.assertContains(response, "1999.00 TL")
        self.assertContains(response, "3798.10 TL")
        self.assertContains(response, "7436.28 TL")

    def test_fixed_week_request_stores_authoritative_snapshots(self):
        package = self.create_package()

        self.client.force_login(self.owner)
        response = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {"requested_weeks": "2"},
        )

        promotion = ListingPromotion.objects.get()

        self.assertRedirects(
            response,
            reverse(
                "promotions:payment",
                kwargs={"pk": promotion.pk},
            ),
        )
        self.assertEqual(
            promotion.promotion_code_snapshot,
            PromotionCodeV342.URGENT,
        )
        self.assertEqual(
            promotion.price_group_snapshot,
            PriceGroupV342.VEHICLES,
        )
        self.assertEqual(
            promotion.duration_mode_snapshot,
            DurationModeV342.FIXED_WEEKS,
        )
        self.assertEqual(promotion.requested_weeks, 2)
        self.assertEqual(
            promotion.unit_price_snapshot,
            Decimal("1999.00"),
        )
        self.assertEqual(
            promotion.discount_percent_snapshot,
            Decimal("0.0500"),
        )
        self.assertEqual(
            promotion.price_snapshot,
            Decimal("3798.10"),
        )

    def test_listing_lifetime_request_stores_no_week_duration(self):
        package = self.create_package(
            code=PromotionCodeV342.SMALL_PHOTO,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {},
        )

        self.assertEqual(response.status_code, 302)
        promotion = ListingPromotion.objects.get()
        self.assertEqual(
            promotion.duration_mode_snapshot,
            DurationModeV342.LISTING_LIFETIME,
        )
        self.assertIsNone(promotion.requested_weeks)
        self.assertEqual(
            promotion.price_snapshot,
            Decimal("429.00"),
        )

    def test_single_use_request_stores_no_week_duration(self):
        package = self.create_package(
            code=PromotionCodeV342.REFRESH,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {},
        )

        self.assertEqual(response.status_code, 302)
        promotion = ListingPromotion.objects.get()
        self.assertEqual(
            promotion.duration_mode_snapshot,
            DurationModeV342.SINGLE_USE,
        )
        self.assertIsNone(promotion.requested_weeks)
        self.assertEqual(
            promotion.price_snapshot,
            Decimal("979.00"),
        )

    def test_invalid_fixed_duration_creates_no_request(self):
        package = self.create_package()

        self.client.force_login(self.owner)

        for weeks in ("", "0", "3", "5", "-1", "invalid"):
            with self.subTest(weeks=weeks):
                response = self.client.post(
                    self.request_url(
                        self.vehicle_listing,
                        package,
                    ),
                    {"requested_weeks": weeks},
                )
                self.assertRedirects(
                    response,
                    self.package_url(self.vehicle_listing),
                )
                self.assertFalse(
                    ListingPromotion.objects.exists()
                )

    def test_category_group_mismatch_creates_no_request(self):
        package = self.create_package(
            group=PriceGroupV342.REAL_ESTATE,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {"requested_weeks": "1"},
        )

        self.assertRedirects(
            response,
            self.package_url(self.vehicle_listing),
        )
        self.assertFalse(ListingPromotion.objects.exists())

    def test_stale_catalog_price_fails_closed(self):
        package = self.create_package(
            price=Decimal("1.00"),
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {"requested_weeks": "1"},
        )

        self.assertRedirects(
            response,
            self.package_url(self.vehicle_listing),
        )
        self.assertFalse(ListingPromotion.objects.exists())

    def test_duplicate_pending_product_request_is_blocked(self):
        package = self.create_package()

        self.client.force_login(self.owner)

        first = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {"requested_weeks": "1"},
        )
        self.assertEqual(first.status_code, 302)

        second = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {"requested_weeks": "4"},
        )

        self.assertRedirects(
            second,
            self.package_url(self.vehicle_listing),
        )
        self.assertEqual(
            ListingPromotion.objects.count(),
            1,
        )

    def test_legacy_package_request_remains_supported(self):
        package = PromotionPackage.objects.create(
            name="Legacy Featured 7 days",
            package_type=PromotionPackage.PackageType.FEATURED,
            duration_days=7,
            price=Decimal("199.00"),
            priority=50,
        )

        self.client.force_login(self.owner)
        response = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {},
        )

        self.assertEqual(response.status_code, 302)
        promotion = ListingPromotion.objects.get()
        self.assertEqual(
            promotion.price_snapshot,
            Decimal("199.00"),
        )
        self.assertEqual(
            promotion.promotion_code_snapshot,
            "",
        )

    def test_non_owner_cannot_create_catalog_request(self):
        package = self.create_package()

        self.client.force_login(self.other_user)
        response = self.client.post(
            self.request_url(self.vehicle_listing, package),
            {"requested_weeks": "1"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ListingPromotion.objects.exists())
