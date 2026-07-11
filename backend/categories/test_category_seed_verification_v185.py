from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from categories.category_seed_verification_v185 import (
    V185_CATEGORY_SEED_VERIFICATION_MARKER,
    V185_EXPECTED_TOTAL_CATEGORIES,
    build_category_seed_verification_report_v185,
)
from categories.models import Category


class CategorySeedVerificationV185Tests(TestCase):
    def test_v185_empty_database_report_is_non_destructive(self):
        report = build_category_seed_verification_report_v185()

        self.assertEqual(report.marker, V185_CATEGORY_SEED_VERIFICATION_MARKER)
        self.assertEqual(report.planned_count, V185_EXPECTED_TOTAL_CATEGORIES)
        self.assertEqual(report.existing_planned_count, 0)
        self.assertEqual(report.missing_count, V185_EXPECTED_TOTAL_CATEGORIES)
        self.assertFalse(report.verified)
        self.assertEqual(Category.objects.count(), 0)

    def test_v185_verify_command_without_require_applied_reports_empty_database(self):
        output = StringIO()

        call_command("verify_marketplace_category_seed", stdout=output)

        text = output.getvalue()
        self.assertIn("V185_CATEGORY_VERIFY_COMMAND", text)
        self.assertIn("V185_CATEGORY_SEED_APPLY_ADMIN_VERIFICATION", text)
        self.assertIn("Missing planned categories: 100", text)
        self.assertIn("Verified: False", text)
        self.assertEqual(Category.objects.count(), 0)

    def test_v185_verify_command_with_require_applied_fails_before_seed_apply(self):
        output = StringIO()

        with self.assertRaises(CommandError):
            call_command("verify_marketplace_category_seed", "--require-applied", stdout=output)

        self.assertIn("Verified: False", output.getvalue())

    def test_v185_verify_command_passes_after_expanded_seed_apply(self):
        seed_output = StringIO()
        verify_output = StringIO()

        call_command("seed_marketplace_categories_expanded", "--apply", stdout=seed_output)
        call_command("verify_marketplace_category_seed", "--require-applied", stdout=verify_output)

        text = verify_output.getvalue()
        self.assertIn("Verified: True", text)
        self.assertIn("Category seed verification passed.", text)
        self.assertEqual(Category.objects.count(), 100)

    def test_v185_expanded_seed_apply_remains_idempotent_before_verification(self):
        first_output = StringIO()
        second_output = StringIO()
        verify_output = StringIO()

        call_command("seed_marketplace_categories_expanded", "--apply", stdout=first_output)
        call_command("seed_marketplace_categories_expanded", "--apply", stdout=second_output)
        call_command("verify_marketplace_category_seed", "--require-applied", stdout=verify_output)

        self.assertEqual(Category.objects.count(), 100)
        self.assertIn("unchanged=100", second_output.getvalue())
        self.assertIn("Verified: True", verify_output.getvalue())
