from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from categories.models import Category
from categories.seed_taxonomy_v183 import (
    build_category_seed_plan_v183,
    summarize_category_seed_plan_v183,
)
from categories.seed_taxonomy_v184 import (
    V184_CATEGORY_SEED_TAXONOMY_MARKER,
    CategorySeedRecordV184,
    build_category_seed_plan_v184,
    summarize_category_seed_plan_v184,
    validate_category_seed_plan_v184,
)


class CategoryExpandedSeedTaxonomyV184Tests(TestCase):
    def test_v184_keeps_v183_pilot_plan_unchanged(self):
        v183_records = build_category_seed_plan_v183()
        v183_summary = summarize_category_seed_plan_v183(v183_records)

        self.assertEqual(v183_summary["total"], 35)
        self.assertEqual(v183_summary["roots"], 5)
        self.assertEqual(v183_summary["children"], 10)
        self.assertEqual(v183_summary["grandchildren"], 20)
        self.assertEqual(v183_summary["max_depth"], 3)

    def test_v184_expanded_seed_plan_marker_and_summary_are_stable(self):
        records = build_category_seed_plan_v184()
        summary = summarize_category_seed_plan_v184(records)

        self.assertEqual(
            V184_CATEGORY_SEED_TAXONOMY_MARKER,
            "V184_CATEGORY_SEED_TAXONOMY_EXPANDED_PLAN",
        )
        self.assertEqual(summary["total"], 100)
        self.assertEqual(summary["roots"], 10)
        self.assertEqual(summary["children"], 30)
        self.assertEqual(summary["grandchildren"], 60)
        self.assertEqual(summary["max_depth"], 3)

    def test_v184_expanded_seed_plan_has_no_duplicates_or_missing_parents(self):
        records = build_category_seed_plan_v184()
        errors = validate_category_seed_plan_v184(records)

        self.assertEqual(errors, ())
        self.assertEqual(len({record.slug for record in records}), len(records))

    def test_v184_expanded_seed_plan_rejects_duplicate_slugs(self):
        records = (
            CategorySeedRecordV184("Root", "root", None, 1),
            CategorySeedRecordV184("Duplicate Root", "root", None, 1),
        )

        errors = validate_category_seed_plan_v184(records)

        self.assertIn("Duplicate category slug `root`.", errors)

    def test_v184_expanded_seed_plan_rejects_missing_parent(self):
        records = (
            CategorySeedRecordV184("Child", "child", "missing-root", 2),
        )

        errors = validate_category_seed_plan_v184(records)

        self.assertIn("Category `child` references missing parent `missing-root`.", errors)

    def test_v184_expanded_dry_run_command_creates_no_categories(self):
        output = StringIO()

        call_command("seed_marketplace_categories_expanded", stdout=output)

        text = output.getvalue()
        self.assertIn("V184_CATEGORY_SEED_COMMAND_DRY_RUN_FIRST", text)
        self.assertIn("V184_CATEGORY_SEED_TAXONOMY_EXPANDED_PLAN", text)
        self.assertIn("Expanded plan: 100 categories", text)
        self.assertIn("Dry run complete", text)
        self.assertEqual(Category.objects.count(), 0)

    def test_v184_expanded_apply_command_creates_expected_category_tree(self):
        output = StringIO()

        call_command("seed_marketplace_categories_expanded", "--apply", stdout=output)

        text = output.getvalue()
        self.assertIn("Applied expanded category seed plan", text)
        self.assertEqual(Category.objects.count(), 100)

        services = Category.objects.get(slug="services")
        home_services = Category.objects.get(slug="services-home")
        repairs = Category.objects.get(slug="services-home-repairs")

        self.assertIsNone(services.parent)
        self.assertEqual(home_services.parent, services)
        self.assertEqual(repairs.parent, home_services)

    def test_v184_expanded_apply_command_is_idempotent(self):
        first_output = StringIO()
        second_output = StringIO()

        call_command("seed_marketplace_categories_expanded", "--apply", stdout=first_output)
        first_count = Category.objects.count()

        call_command("seed_marketplace_categories_expanded", "--apply", stdout=second_output)
        second_count = Category.objects.count()

        self.assertEqual(first_count, 100)
        self.assertEqual(second_count, 100)
        self.assertIn("unchanged=100", second_output.getvalue())

    def test_v184_expanded_plan_can_extend_after_v183_pilot_apply(self):
        pilot_output = StringIO()
        expanded_output = StringIO()

        call_command("seed_marketplace_categories", "--apply", stdout=pilot_output)
        self.assertEqual(Category.objects.count(), 35)

        call_command("seed_marketplace_categories_expanded", "--apply", stdout=expanded_output)

        self.assertEqual(Category.objects.count(), 100)
        self.assertIn("Applied expanded category seed plan", expanded_output.getvalue())
