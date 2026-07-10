from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from categories.models import Category
from categories.seed_taxonomy_v183 import (
    V183_CATEGORY_SEED_TAXONOMY_MARKER,
    CategorySeedRecordV183,
    build_category_seed_plan_v183,
    summarize_category_seed_plan_v183,
    validate_category_seed_plan_v183,
)


class CategorySeedTaxonomyV183Tests(TestCase):
    def test_v183_seed_plan_marker_and_summary_are_stable(self):
        records = build_category_seed_plan_v183()
        summary = summarize_category_seed_plan_v183(records)

        self.assertEqual(V183_CATEGORY_SEED_TAXONOMY_MARKER, "V183_CATEGORY_SEED_TAXONOMY_PLAN")
        self.assertEqual(summary["total"], 35)
        self.assertEqual(summary["roots"], 5)
        self.assertEqual(summary["children"], 10)
        self.assertEqual(summary["grandchildren"], 20)
        self.assertEqual(summary["max_depth"], 3)

    def test_v183_seed_plan_has_no_duplicates_or_missing_parents(self):
        records = build_category_seed_plan_v183()
        errors = validate_category_seed_plan_v183(records)

        self.assertEqual(errors, ())
        self.assertEqual(len({record.slug for record in records}), len(records))

    def test_v183_seed_plan_rejects_duplicate_slugs(self):
        records = (
            CategorySeedRecordV183("Root", "root", None, 1),
            CategorySeedRecordV183("Duplicate Root", "root", None, 1),
        )

        errors = validate_category_seed_plan_v183(records)

        self.assertIn("Duplicate category slug `root`.", errors)

    def test_v183_seed_plan_rejects_depth_above_three(self):
        records = (
            CategorySeedRecordV183("Root", "root", None, 1),
            CategorySeedRecordV183("Child", "child", "root", 4),
        )

        errors = validate_category_seed_plan_v183(records)

        self.assertIn("Category `child` depth `4` exceeds allowed depth.", errors)

    def test_v183_dry_run_command_creates_no_categories(self):
        output = StringIO()

        call_command("seed_marketplace_categories", stdout=output)

        text = output.getvalue()
        self.assertIn("V183_CATEGORY_SEED_COMMAND_DRY_RUN_FIRST", text)
        self.assertIn("V183_CATEGORY_SEED_TAXONOMY_PLAN", text)
        self.assertIn("Dry run complete", text)
        self.assertEqual(Category.objects.count(), 0)

    def test_v183_apply_command_creates_expected_category_tree(self):
        output = StringIO()

        call_command("seed_marketplace_categories", "--apply", stdout=output)

        text = output.getvalue()
        self.assertIn("Applied category seed plan", text)
        self.assertEqual(Category.objects.count(), 35)

        vehicles = Category.objects.get(slug="vehicles")
        cars = Category.objects.get(slug="vehicles-cars")
        sedans = Category.objects.get(slug="vehicles-cars-sedans")

        self.assertIsNone(vehicles.parent)
        self.assertEqual(cars.parent, vehicles)
        self.assertEqual(sedans.parent, cars)

    def test_v183_apply_command_is_idempotent(self):
        first_output = StringIO()
        second_output = StringIO()

        call_command("seed_marketplace_categories", "--apply", stdout=first_output)
        first_count = Category.objects.count()

        call_command("seed_marketplace_categories", "--apply", stdout=second_output)
        second_count = Category.objects.count()

        self.assertEqual(first_count, 35)
        self.assertEqual(second_count, 35)
        self.assertIn("unchanged=35", second_output.getvalue())
