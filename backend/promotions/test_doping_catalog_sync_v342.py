"""Database synchronization contracts for the V342 doping catalog."""

from __future__ import annotations

from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from promotions.doping_catalog_sync_v342 import (
    DOPING_CATALOG_SYNC_V342,
    build_catalog_package_specs_v342,
    sync_doping_catalog_v342,
)
from promotions.doping_catalog_v342 import (
    PRICE_MATRIX_V342,
    DurationModeV342,
    PriceGroupV342,
    PromotionCodeV342,
)
from promotions.models import PromotionPackage


class DopingCatalogSyncV342Tests(TestCase):
    def test_catalog_spec_count_matches_available_price_cells(self):
        specs = build_catalog_package_specs_v342()

        available_cells = sum(
            1
            for row in PRICE_MATRIX_V342.values()
            for price in row.values()
            if price is not None
        )

        self.assertTrue(DOPING_CATALOG_SYNC_V342)
        self.assertEqual(available_cells, 67)
        self.assertEqual(len(specs), 67)
        self.assertEqual(
            len(
                {
                    (
                        spec.catalog_code,
                        spec.price_group,
                    )
                    for spec in specs
                }
            ),
            67,
        )

    def test_catalog_specs_preserve_reference_prices(self):
        specs = {
            (
                spec.catalog_code,
                spec.price_group,
            ): spec
            for spec in build_catalog_package_specs_v342()
        }

        self.assertEqual(
            specs[
                (
                    PromotionCodeV342.HOMEPAGE_SHOWCASE,
                    PriceGroupV342.REAL_ESTATE,
                )
            ].price,
            Decimal("8399"),
        )
        self.assertEqual(
            specs[
                (
                    PromotionCodeV342.SMALL_PHOTO,
                    PriceGroupV342.VEHICLE_PARTS,
                )
            ].price,
            Decimal("65"),
        )
        self.assertEqual(
            specs[
                (
                    PromotionCodeV342.REFRESH,
                    PriceGroupV342.HELPERS,
                )
            ].price,
            Decimal("79"),
        )

    def test_unavailable_combinations_are_not_generated(self):
        keys = {
            (
                spec.catalog_code,
                spec.price_group,
            )
            for spec in build_catalog_package_specs_v342()
        }

        self.assertNotIn(
            (
                PromotionCodeV342.HOMEPAGE_SHOWCASE,
                PriceGroupV342.JOBS,
            ),
            keys,
        )
        self.assertNotIn(
            (
                PromotionCodeV342.CATEGORY_SHOWCASE,
                PriceGroupV342.HELPERS,
            ),
            keys,
        )
        self.assertNotIn(
            (
                PromotionCodeV342.COLORFUL_TITLE,
                PriceGroupV342.REAL_ESTATE,
            ),
            keys,
        )

    def test_specs_use_expected_duration_contracts(self):
        specs = build_catalog_package_specs_v342()

        for spec in specs:
            definition_mode = spec.duration_mode

            if spec.catalog_code in {
                PromotionCodeV342.SMALL_PHOTO,
                PromotionCodeV342.COLORFUL_TITLE,
            }:
                self.assertEqual(
                    definition_mode,
                    DurationModeV342.LISTING_LIFETIME,
                )
                self.assertEqual(spec.duration_days, 0)
            elif spec.catalog_code == PromotionCodeV342.REFRESH:
                self.assertEqual(
                    definition_mode,
                    DurationModeV342.SINGLE_USE,
                )
                self.assertEqual(spec.duration_days, 0)
            else:
                self.assertEqual(
                    definition_mode,
                    DurationModeV342.FIXED_WEEKS,
                )
                self.assertEqual(spec.duration_days, 7)

    def test_sync_creates_all_67_catalog_packages(self):
        result = sync_doping_catalog_v342()

        self.assertEqual(
            result,
            {
                "created": 67,
                "updated": 0,
                "unchanged": 0,
                "deactivated": 0,
                "total": 67,
            },
        )
        self.assertEqual(
            PromotionPackage.objects.exclude(catalog_code="").count(),
            67,
        )

    def test_sync_is_idempotent(self):
        first = sync_doping_catalog_v342()
        second = sync_doping_catalog_v342()

        self.assertEqual(first["created"], 67)
        self.assertEqual(
            second,
            {
                "created": 0,
                "updated": 0,
                "unchanged": 67,
                "deactivated": 0,
                "total": 67,
            },
        )
        self.assertEqual(
            PromotionPackage.objects.exclude(catalog_code="").count(),
            67,
        )

    def test_sync_repairs_modified_catalog_package(self):
        sync_doping_catalog_v342()

        package = PromotionPackage.objects.get(
            catalog_code=PromotionCodeV342.URGENT,
            price_group=PriceGroupV342.VEHICLES,
        )
        package.name = "Incorrect package name"
        package.price = Decimal("1.00")
        package.is_active = False
        package.save(
            update_fields=[
                "name",
                "price",
                "is_active",
            ]
        )

        result = sync_doping_catalog_v342()
        package.refresh_from_db()

        self.assertEqual(result["updated"], 1)
        self.assertEqual(package.name, "Urgent — Vehicles")
        self.assertEqual(package.price, Decimal("1999.00"))
        self.assertTrue(package.is_active)

    def test_sync_deactivates_unavailable_catalog_combination(self):
        PromotionPackage.objects.create(
            name="Unavailable Homepage Jobs",
            package_type=PromotionPackage.PackageType.FEATURED,
            duration_days=7,
            price=Decimal("10.00"),
            catalog_code=PromotionCodeV342.HOMEPAGE_SHOWCASE,
            price_group=PriceGroupV342.JOBS,
            duration_mode=DurationModeV342.FIXED_WEEKS,
            is_active=True,
        )

        result = sync_doping_catalog_v342()

        stale = PromotionPackage.objects.get(
            catalog_code=PromotionCodeV342.HOMEPAGE_SHOWCASE,
            price_group=PriceGroupV342.JOBS,
        )

        self.assertEqual(result["created"], 67)
        self.assertEqual(result["deactivated"], 1)
        self.assertFalse(stale.is_active)

    def test_sync_preserves_legacy_blank_catalog_packages(self):
        legacy = PromotionPackage.objects.create(
            name="Legacy Featured Package",
            package_type=PromotionPackage.PackageType.FEATURED,
            duration_days=7,
            price=Decimal("199.00"),
            is_active=True,
        )

        sync_doping_catalog_v342()
        legacy.refresh_from_db()

        self.assertEqual(legacy.catalog_code, "")
        self.assertTrue(legacy.is_active)

    def test_management_command_reports_deterministic_counts(self):
        output = StringIO()

        call_command(
            "sync_doping_catalog_v342",
            stdout=output,
        )

        self.assertIn(
            "created=67 updated=0 unchanged=0 "
            "deactivated=0 total=67",
            output.getvalue(),
        )

        output = StringIO()

        call_command(
            "sync_doping_catalog_v342",
            stdout=output,
        )

        self.assertIn(
            "created=0 updated=0 unchanged=67 "
            "deactivated=0 total=67",
            output.getvalue(),
        )
