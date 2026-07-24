"""Activation lifecycle contracts for V342 promotion products."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import Listing
from promotions.doping_catalog_v342 import (
    DurationModeV342,
    PriceGroupV342,
    PromotionCodeV342,
)
from promotions.models import (
    ListingPromotion,
    PromotionPackage,
)


class DopingActivationV342Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="v342-activation-owner",
            email="v342-activation-owner@example.com",
            password="testpass123",
        )
        cls.staff = User.objects.create_user(
            username="v342-activation-staff",
            email="v342-activation-staff@example.com",
            password="testpass123",
            is_staff=True,
        )

        cls.vehicles = Category.objects.create(
            name="V342 Activation Vehicles",
            slug="v342-activation-vehicles",
        )

    def create_listing(self):
        return Listing.objects.create(
            title="V342 activation listing",
            description="Activation lifecycle test.",
            price=Decimal("25000.00"),
            category=self.vehicles,
            owner=self.owner,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=(
                timezone.now()
                + timedelta(days=30)
            ),
        )

    def create_catalog_package(
        self,
        code,
        mode,
        *,
        priority=0,
    ):
        package_type = (
            PromotionPackage.PackageType.TOP
            if code == PromotionCodeV342.TOP_RANKING
            else PromotionPackage.PackageType.FEATURED
        )

        return PromotionPackage.objects.create(
            name=f"V342 {code.value}",
            package_type=package_type,
            duration_days=(
                7
                if mode == DurationModeV342.FIXED_WEEKS
                else 0
            ),
            price=Decimal("100.00"),
            priority=priority,
            catalog_code=code,
            price_group=PriceGroupV342.VEHICLES,
            duration_mode=mode,
        )

    def create_catalog_promotion(
        self,
        listing,
        code,
        mode,
        *,
        requested_weeks=None,
        priority=0,
    ):
        package = self.create_catalog_package(
            code,
            mode,
            priority=priority,
        )

        return ListingPromotion.objects.create(
            listing=listing,
            package=package,
            user=self.owner,
            payment_status=(
                ListingPromotion.PaymentStatus.PAID
            ),
            price_snapshot=Decimal("100.00"),
            promotion_code_snapshot=code,
            price_group_snapshot=(
                PriceGroupV342.VEHICLES
            ),
            duration_mode_snapshot=mode,
            requested_weeks=requested_weeks,
            unit_price_snapshot=Decimal("100.00"),
        )

    def test_fixed_week_urgent_activates_without_featured_side_effect(self):
        listing = self.create_listing()
        promotion = self.create_catalog_promotion(
            listing,
            PromotionCodeV342.URGENT,
            DurationModeV342.FIXED_WEEKS,
            requested_weeks=2,
        )

        promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertEqual(
            promotion.status,
            ListingPromotion.Status.ACTIVE,
        )
        self.assertIsNotNone(promotion.starts_at)
        self.assertEqual(
            promotion.ends_at,
            promotion.starts_at + timedelta(days=14),
        )
        self.assertFalse(listing.is_featured)
        self.assertEqual(listing.featured_priority, 0)
        self.assertIsNone(listing.featured_until)
        self.assertEqual(listing.top_listing_priority, 0)
        self.assertIsNone(listing.top_listing_until)

    def test_homepage_showcase_applies_featured_fields(self):
        listing = self.create_listing()
        promotion = self.create_catalog_promotion(
            listing,
            PromotionCodeV342.HOMEPAGE_SHOWCASE,
            DurationModeV342.FIXED_WEEKS,
            requested_weeks=4,
            priority=125,
        )

        promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertTrue(listing.is_featured)
        self.assertEqual(
            listing.featured_priority,
            125,
        )
        self.assertEqual(
            listing.featured_until,
            promotion.ends_at,
        )
        self.assertEqual(
            promotion.ends_at,
            promotion.starts_at + timedelta(days=28),
        )

    def test_top_ranking_applies_top_listing_fields(self):
        listing = self.create_listing()
        promotion = self.create_catalog_promotion(
            listing,
            PromotionCodeV342.TOP_RANKING,
            DurationModeV342.FIXED_WEEKS,
            requested_weeks=1,
            priority=200,
        )

        promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertEqual(
            listing.top_listing_priority,
            200,
        )
        self.assertEqual(
            listing.top_listing_until,
            promotion.ends_at,
        )
        self.assertFalse(listing.is_featured)

    def test_listing_lifetime_product_uses_listing_expiry(self):
        listing = self.create_listing()
        promotion = self.create_catalog_promotion(
            listing,
            PromotionCodeV342.SMALL_PHOTO,
            DurationModeV342.LISTING_LIFETIME,
        )

        expected_expiry = listing.expires_at
        promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertEqual(
            promotion.ends_at,
            expected_expiry,
        )
        self.assertFalse(listing.is_featured)
        self.assertEqual(
            listing.top_listing_priority,
            0,
        )

    def test_single_use_product_records_activation_instant(self):
        listing = self.create_listing()
        promotion = self.create_catalog_promotion(
            listing,
            PromotionCodeV342.REFRESH,
            DurationModeV342.SINGLE_USE,
        )

        promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertEqual(
            promotion.status,
            ListingPromotion.Status.ACTIVE,
        )
        self.assertEqual(
            promotion.ends_at,
            promotion.starts_at,
        )
        self.assertFalse(listing.is_featured)
        self.assertEqual(
            listing.top_listing_priority,
            0,
        )

    def test_invalid_fixed_week_snapshot_fails_before_activation(self):
        listing = self.create_listing()
        promotion = self.create_catalog_promotion(
            listing,
            PromotionCodeV342.URGENT,
            DurationModeV342.FIXED_WEEKS,
            requested_weeks=None,
        )

        with self.assertRaises(ValidationError):
            promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertEqual(
            promotion.status,
            ListingPromotion.Status.PENDING,
        )
        self.assertIsNone(promotion.starts_at)
        self.assertIsNone(promotion.ends_at)
        self.assertFalse(listing.is_featured)

    def test_legacy_featured_activation_remains_supported(self):
        listing = self.create_listing()
        package = PromotionPackage.objects.create(
            name="Legacy Featured V342",
            package_type=(
                PromotionPackage.PackageType.FEATURED
            ),
            duration_days=7,
            price=Decimal("199.00"),
            priority=50,
        )
        promotion = ListingPromotion.objects.create(
            listing=listing,
            package=package,
            user=self.owner,
            price_snapshot=Decimal("199.00"),
        )

        promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertTrue(listing.is_featured)
        self.assertEqual(listing.featured_priority, 50)
        self.assertEqual(
            listing.featured_until,
            promotion.ends_at,
        )

    def test_legacy_top_activation_remains_supported(self):
        listing = self.create_listing()
        package = PromotionPackage.objects.create(
            name="Legacy Top V342",
            package_type=PromotionPackage.PackageType.TOP,
            duration_days=30,
            price=Decimal("799.00"),
            priority=150,
        )
        promotion = ListingPromotion.objects.create(
            listing=listing,
            package=package,
            user=self.owner,
            price_snapshot=Decimal("799.00"),
        )

        promotion.activate()

        promotion.refresh_from_db()
        listing.refresh_from_db()

        self.assertEqual(
            listing.top_listing_priority,
            150,
        )
        self.assertEqual(
            listing.top_listing_until,
            promotion.ends_at,
        )

    def test_admin_approval_handles_invalid_snapshot_without_server_error(self):
        listing = self.create_listing()
        promotion = self.create_catalog_promotion(
            listing,
            PromotionCodeV342.URGENT,
            DurationModeV342.FIXED_WEEKS,
            requested_weeks=None,
        )

        self.client.force_login(self.staff)
        response = self.client.post(
            reverse(
                "promotions:approve",
                kwargs={"pk": promotion.pk},
            )
        )

        self.assertRedirects(
            response,
            reverse("promotions:admin_queue"),
        )

        promotion.refresh_from_db()

        self.assertEqual(
            promotion.status,
            ListingPromotion.Status.PENDING,
        )
        self.assertIsNone(promotion.starts_at)
        self.assertIsNone(promotion.ends_at)
