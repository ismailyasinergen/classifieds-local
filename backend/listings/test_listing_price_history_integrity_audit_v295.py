import json
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from categories.models import Category

from .listing_price_history_integrity_audit_v295 import (
    BROKEN_TRANSITION_CHAIN_V295,
    CURRENT_PRICE_MISMATCH_V295,
    FUTURE_TIMESTAMP_V295,
    INVALID_GUARDRAIL_STATUS_V295,
    INVALID_REASON_V295,
    INVALID_RESTRICTION_DIRECTION_V295,
    INVALID_RESTRICTION_REFERENCE_V295,
    MISSING_BASELINE_V295,
    NOOP_TRANSITION_V295,
    PRICE_HISTORY_INTEGRITY_AUDIT_V295,
    RESTRICTED_WITHOUT_REFERENCE_V295,
    audit_listing_price_history_integrity_v295,
)
from .listing_price_integrity_v293 import (
    DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
)
from .models import Listing, ListingPriceHistory


User = get_user_model()


class ListingPriceHistoryIntegrityAuditV295Tests(TestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            username="price-audit-seller-v295",
            email="private-price-audit-v295@example.test",
            password="test-pass-v295",
        )
        self.category = Category.objects.create(
            name="Price audit v295",
            slug="price-audit-v295",
        )

    def _listing(self, title="Price audit listing", price="100.00"):
        return Listing.objects.create(
            owner=self.seller,
            category=self.category,
            title=title,
            description="Read-only price-history audit fixture.",
            price=Decimal(price),
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=timezone.now() + timedelta(days=30),
        )

    @staticmethod
    def _codes(report):
        return [finding.code for finding in report.displayed_findings]

    def test_clean_price_history_passes_with_deterministic_summary(self):
        self.assertTrue(PRICE_HISTORY_INTEGRITY_AUDIT_V295)
        listing = self._listing()
        listing.price = Decimal("80.00")
        listing.save(update_fields=["price"])

        report = audit_listing_price_history_integrity_v295()

        self.assertTrue(report.is_clean)
        self.assertEqual(report.listing_count, 1)
        self.assertEqual(report.transition_count, 2)
        self.assertEqual(report.finding_count, 0)
        self.assertEqual(report.as_dict()["findings"], [])

    def test_missing_baseline_is_reported_without_repair(self):
        listing = self._listing()
        listing.price_history.filter(previous_price__isnull=True).delete()

        report = audit_listing_price_history_integrity_v295()

        self.assertIn(MISSING_BASELINE_V295, self._codes(report))
        self.assertFalse(listing.price_history.exists())

    def test_broken_chain_and_noop_transition_are_reported(self):
        listing = self._listing()
        transition = ListingPriceHistory.objects.create(
            listing=listing,
            previous_price=Decimal("90.00"),
            new_price=Decimal("90.00"),
        )

        report = audit_listing_price_history_integrity_v295()
        findings = {
            (finding.code, finding.transition_id)
            for finding in report.displayed_findings
        }

        self.assertIn((BROKEN_TRANSITION_CHAIN_V295, transition.pk), findings)
        self.assertIn((NOOP_TRANSITION_V295, transition.pk), findings)

    def test_current_price_mismatch_and_future_timestamp_are_reported(self):
        listing = self._listing()
        baseline = listing.price_history.get(previous_price__isnull=True)
        Listing.objects.filter(pk=listing.pk).update(price=Decimal("120.00"))
        ListingPriceHistory.objects.filter(pk=baseline.pk).update(
            changed_at=timezone.now() + timedelta(days=1)
        )

        report = audit_listing_price_history_integrity_v295()
        codes = self._codes(report)

        self.assertIn(CURRENT_PRICE_MISMATCH_V295, codes)
        self.assertIn(FUTURE_TIMESTAMP_V295, codes)

    def test_invalid_reason_and_guardrail_status_are_reported(self):
        listing = self._listing()
        baseline = listing.price_history.get(previous_price__isnull=True)
        ListingPriceHistory.objects.filter(pk=baseline.pk).update(
            reason="unknown_reason",
            discount_guardrail_status="unknown_guardrail",
        )

        report = audit_listing_price_history_integrity_v295()
        codes = self._codes(report)

        self.assertIn(INVALID_REASON_V295, codes)
        self.assertIn(INVALID_GUARDRAIL_STATUS_V295, codes)

    def test_malformed_restricted_evidence_is_reported(self):
        listing = self._listing("Missing guardrail reference")
        invalid_direction = ListingPriceHistory.objects.create(
            listing=listing,
            previous_price=Decimal("100.00"),
            new_price=Decimal("150.00"),
            discount_guardrail_status=(
                DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293
            ),
        )
        second = self._listing("Invalid guardrail reference")
        invalid_reference = ListingPriceHistory.objects.create(
            listing=second,
            previous_price=Decimal("100.00"),
            new_price=Decimal("80.00"),
            discount_guardrail_status=(
                DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293
            ),
            discount_reference_price=Decimal("90.00"),
        )

        report = audit_listing_price_history_integrity_v295()
        findings = {
            (finding.code, finding.transition_id)
            for finding in report.displayed_findings
        }

        self.assertIn(
            (RESTRICTED_WITHOUT_REFERENCE_V295, invalid_direction.pk),
            findings,
        )
        self.assertIn(
            (INVALID_RESTRICTION_DIRECTION_V295, invalid_direction.pk),
            findings,
        )
        self.assertIn(
            (INVALID_RESTRICTION_REFERENCE_V295, invalid_reference.pk),
            findings,
        )

    def test_finding_output_is_bounded_while_total_counts_remain_complete(self):
        listing = self._listing()
        baseline = listing.price_history.get(previous_price__isnull=True)
        ListingPriceHistory.objects.filter(pk=baseline.pk).update(
            reason="unknown_reason",
            changed_at=timezone.now() + timedelta(days=1),
        )

        report = audit_listing_price_history_integrity_v295(max_findings=1)

        self.assertGreater(report.finding_count, 1)
        self.assertEqual(len(report.displayed_findings), 1)
        self.assertTrue(report.is_truncated)

    def test_command_supports_sanitized_json_and_fail_on_findings(self):
        listing = self._listing("Private audit title")
        listing.price_history.filter(previous_price__isnull=True).delete()
        output = StringIO()

        call_command(
            "audit_listing_price_history_integrity",
            "--json",
            stdout=output,
        )
        payload = json.loads(output.getvalue())

        self.assertEqual(payload["finding_count"], 1)
        self.assertEqual(payload["findings"][0]["code"], MISSING_BASELINE_V295)
        self.assertNotIn(listing.title, output.getvalue())
        self.assertNotIn(self.seller.username, output.getvalue())
        self.assertNotIn(self.seller.email, output.getvalue())

        with self.assertRaises(CommandError):
            call_command(
                "audit_listing_price_history_integrity",
                "--fail-on-findings",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_command_rejects_unbounded_finding_limits(self):
        with self.assertRaises(CommandError):
            call_command(
                "audit_listing_price_history_integrity",
                "--max-findings=0",
                stdout=StringIO(),
                stderr=StringIO(),
            )
        with self.assertRaises(CommandError):
            call_command(
                "audit_listing_price_history_integrity",
                "--max-findings=1001",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_audit_is_read_only(self):
        listing = self._listing()
        before_listing = list(
            Listing.objects.values_list("pk", "price", "status")
        )
        before_history = list(
            ListingPriceHistory.objects.values_list(
                "pk",
                "previous_price",
                "new_price",
                "discount_guardrail_status",
            )
        )

        audit_listing_price_history_integrity_v295()

        self.assertEqual(
            list(Listing.objects.values_list("pk", "price", "status")),
            before_listing,
        )
        self.assertEqual(
            list(
                ListingPriceHistory.objects.values_list(
                    "pk",
                    "previous_price",
                    "new_price",
                    "discount_guardrail_status",
                )
            ),
            before_history,
        )
        self.assertEqual(listing.price_history.count(), 1)

    def test_query_count_is_constant_as_listings_and_histories_grow(self):
        self._listing("One audited listing")
        with CaptureQueriesContext(connection) as one_capture:
            audit_listing_price_history_integrity_v295()

        for index in range(8):
            listing = self._listing(f"Additional audit listing {index}")
            listing.price = Decimal("80.00")
            listing.save(update_fields=["price"])

        with CaptureQueriesContext(connection) as many_capture:
            audit_listing_price_history_integrity_v295()

        self.assertEqual(len(one_capture), 2)
        self.assertEqual(len(many_capture), 2)

    def test_v295_adds_no_schema_migration(self):
        migration_dir = Path(__file__).resolve().parent / "migrations"
        self.assertEqual(list(migration_dir.glob("*v295*.py")), [])
