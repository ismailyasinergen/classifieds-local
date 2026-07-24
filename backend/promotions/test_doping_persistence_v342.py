"""Database persistence contracts for the V342 promotion catalog."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from categories.models import Category
from listings.models import Listing
from promotions.doping_catalog_v342 import (
    DURATION_MODE_CHOICES_V342,
    PRICE_GROUP_CHOICES_V342,
    PROMOTION_CODE_CHOICES_V342,
    DurationModeV342,
    PriceGroupV342,
    PromotionCodeV342,
)
from promotions.models import ListingPromotion, PromotionPackage


class DopingPersistenceV342Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()

        cls.owner = User.objects.create_user(
            username="v342-doping-owner",
            email="v342-owner@example.com",
            password="testpass123",
        )
        cls.category = Category.objects.create(
            name="V342 Vehicles",
            slug="v342-vehicles",
        )
        cls.listing = Listing.objects.create(
            title="V342 promotion persistence listing",
            description="Persistence test listing.",
            price=Decimal("25000.00"),
            category=cls.category,
            owner=cls.owner,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )

    def create_package(self, **overrides):
        values = {
            "name": "V342 Urgent Vehicles",
            "package_type": PromotionPackage.PackageType.FEATURED,
            "duration_days": 7,
            "price": Decimal("1999.00"),
            "priority": 100,
            "is_active": True,
            "catalog_code": PromotionCodeV342.URGENT,
            "price_group": PriceGroupV342.VEHICLES,
            "duration_mode": DurationModeV342.FIXED_WEEKS,
        }
        values.update(overrides)
        return PromotionPackage.objects.create(**values)

    def test_package_catalog_fields_have_exact_choices(self):
        catalog_field = PromotionPackage._meta.get_field("catalog_code")
        group_field = PromotionPackage._meta.get_field("price_group")
        duration_field = PromotionPackage._meta.get_field("duration_mode")

        self.assertEqual(tuple(catalog_field.choices), PROMOTION_CODE_CHOICES_V342)
        self.assertEqual(tuple(group_field.choices), PRICE_GROUP_CHOICES_V342)
        self.assertEqual(
            tuple(duration_field.choices),
            DURATION_MODE_CHOICES_V342,
        )

        self.assertEqual(catalog_field.max_length, 40)
        self.assertEqual(group_field.max_length, 32)
        self.assertEqual(duration_field.max_length, 24)

    def test_catalog_package_persists_product_group_and_duration(self):
        package = self.create_package()

        package.refresh_from_db()

        self.assertEqual(
            package.catalog_code,
            PromotionCodeV342.URGENT,
        )
        self.assertEqual(
            package.price_group,
            PriceGroupV342.VEHICLES,
        )
        self.assertEqual(
            package.duration_mode,
            DurationModeV342.FIXED_WEEKS,
        )
        self.assertEqual(package.price, Decimal("1999.00"))

    def test_legacy_package_remains_valid_with_blank_catalog_fields(self):
        package = PromotionPackage.objects.create(
            name="Legacy Featured 7 days",
            package_type=PromotionPackage.PackageType.FEATURED,
            duration_days=7,
            price=Decimal("199.00"),
            priority=50,
        )

        package.refresh_from_db()

        self.assertEqual(package.catalog_code, "")
        self.assertEqual(package.price_group, "")
        self.assertEqual(package.duration_mode, "")

    def test_multiple_legacy_packages_may_keep_blank_catalog_identity(self):
        PromotionPackage.objects.create(
            name="Legacy Featured",
            package_type=PromotionPackage.PackageType.FEATURED,
            duration_days=7,
            price=Decimal("199.00"),
        )
        PromotionPackage.objects.create(
            name="Legacy Top",
            package_type=PromotionPackage.PackageType.TOP,
            duration_days=30,
            price=Decimal("799.00"),
        )

        self.assertEqual(
            PromotionPackage.objects.filter(catalog_code="").count(),
            2,
        )

    def test_catalog_code_and_price_group_are_unique_together(self):
        self.create_package()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_package(
                    name="Duplicate Urgent Vehicles",
                    duration_days=30,
                    price=Decimal("9999.00"),
                )

    def test_same_product_is_allowed_for_another_price_group(self):
        first = self.create_package()
        second = self.create_package(
            name="V342 Urgent Real Estate",
            price_group=PriceGroupV342.REAL_ESTATE,
        )

        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(
            PromotionPackage.objects.filter(
                catalog_code=PromotionCodeV342.URGENT,
            ).count(),
            2,
        )

    def test_purchase_snapshot_fields_persist_independently(self):
        package = self.create_package()

        promotion = ListingPromotion.objects.create(
            listing=self.listing,
            package=package,
            user=self.owner,
            price_snapshot=Decimal("3798.10"),
            promotion_code_snapshot=PromotionCodeV342.URGENT,
            price_group_snapshot=PriceGroupV342.VEHICLES,
            duration_mode_snapshot=DurationModeV342.FIXED_WEEKS,
            requested_weeks=2,
            unit_price_snapshot=Decimal("1999.00"),
            discount_percent_snapshot=Decimal("0.0500"),
            payment_reference="PROMO-V342TEST",
        )

        promotion.refresh_from_db()

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

    def test_legacy_purchase_remains_valid_without_new_snapshots(self):
        package = PromotionPackage.objects.create(
            name="Legacy Top 7 days",
            package_type=PromotionPackage.PackageType.TOP,
            duration_days=7,
            price=Decimal("299.00"),
            priority=100,
        )

        promotion = ListingPromotion.objects.create(
            listing=self.listing,
            package=package,
            user=self.owner,
            price_snapshot=Decimal("299.00"),
        )

        promotion.refresh_from_db()

        self.assertEqual(promotion.promotion_code_snapshot, "")
        self.assertEqual(promotion.price_group_snapshot, "")
        self.assertEqual(promotion.duration_mode_snapshot, "")
        self.assertIsNone(promotion.requested_weeks)
        self.assertIsNone(promotion.unit_price_snapshot)
        self.assertEqual(
            promotion.discount_percent_snapshot,
            Decimal("0.0000"),
        )

    def test_requested_weeks_constraint_rejects_invalid_value(self):
        package = self.create_package()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ListingPromotion.objects.create(
                    listing=self.listing,
                    package=package,
                    user=self.owner,
                    price_snapshot=Decimal("100.00"),
                    requested_weeks=3,
                )

    def test_requested_weeks_constraint_accepts_supported_values(self):
        package = self.create_package()

        for index, weeks in enumerate((None, 1, 2, 4), start=1):
            with self.subTest(weeks=weeks):
                promotion = ListingPromotion.objects.create(
                    listing=self.listing,
                    package=package,
                    user=self.owner,
                    price_snapshot=Decimal("100.00"),
                    requested_weeks=weeks,
                    payment_reference=f"PROMO-V342-{index}",
                )
                self.assertEqual(promotion.requested_weeks, weeks)

    def test_discount_constraint_rejects_negative_value(self):
        package = self.create_package()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ListingPromotion.objects.create(
                    listing=self.listing,
                    package=package,
                    user=self.owner,
                    price_snapshot=Decimal("100.00"),
                    discount_percent_snapshot=Decimal("-0.0001"),
                )

    def test_discount_constraint_rejects_value_above_one(self):
        package = self.create_package()

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ListingPromotion.objects.create(
                    listing=self.listing,
                    package=package,
                    user=self.owner,
                    price_snapshot=Decimal("100.00"),
                    discount_percent_snapshot=Decimal("1.0001"),
                )
