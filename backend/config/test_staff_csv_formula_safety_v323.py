import csv
import io
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.admin import _v215_seller_store_csv_safe
from accounts.models import ModerationAppeal, TrustSafetyEvent
from categories.models import Category
from config.csv_safety_v323 import (
    csv_safe_cell_v323,
    csv_safe_row_v323,
)
from listings.models import Listing, ListingReport
from listings.saved_search_notification_audit_operator import _csv_safe_cell


class StaffCsvFormulaSafetyV323Tests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="v323-admin",
            email="v323-admin@classifieds.local",
            password="StrongPass123!",
            is_staff=True,
            is_superuser=True,
        )
        self.seller = user_model.objects.create_user(
            username="v323-seller",
            email="v323-seller@classifieds.local",
            password="StrongPass123!",
        )
        self.reporter = user_model.objects.create_user(
            username="v323-reporter",
            email="v323-reporter@classifieds.local",
            password="StrongPass123!",
        )
        self.category = Category.objects.create(
            name="V323 CSV safety",
            slug="v323-csv-safety",
        )
        self.listing = Listing.objects.create(
            title="=SUM(1,1)",
            description="V323 export regression fixture.",
            price=Decimal("323.00"),
            location="Berlin",
            category=self.category,
            owner=self.seller,
            status=Listing.Status.APPROVED,
        )
        self.client = Client(HTTP_HOST="localhost")
        self.client.force_login(self.admin)

    @staticmethod
    def _csv_rows(response):
        return list(
            csv.reader(io.StringIO(response.content.decode("utf-8")))
        )

    def test_shared_cell_contract_is_idempotent_for_all_formula_prefixes(self):
        for prefix in ("=", "+", "-", "@", "\t", "\r"):
            with self.subTest(prefix=repr(prefix)):
                unsafe = f"{prefix}SUM(1,1)"
                safe = csv_safe_cell_v323(unsafe)

                self.assertEqual(safe, f"'{unsafe}")
                self.assertEqual(csv_safe_cell_v323(safe), safe)

    def test_shared_contract_preserves_ordinary_values_and_legacy_helpers(self):
        self.assertEqual(csv_safe_cell_v323(None), "")
        self.assertEqual(csv_safe_cell_v323("ordinary"), "ordinary")
        self.assertEqual(csv_safe_cell_v323(323), "323")
        self.assertEqual(
            csv_safe_row_v323({"safe": "value", "unsafe": "=1+1"}),
            {"safe": "value", "unsafe": "'=1+1"},
        )
        self.assertEqual(_v215_seller_store_csv_safe("+legacy"), "'+legacy")
        self.assertEqual(_csv_safe_cell("@legacy"), "'@legacy")

    def test_listing_report_csv_neutralizes_every_untrusted_text_cell(self):
        report = ListingReport.objects.create(
            listing=self.listing,
            reporter=self.reporter,
            reason=ListingReport.Reason.OTHER,
            details="+unsafe-details",
            reporter_note="-unsafe-public-note",
            admin_note="@unsafe-admin-note",
        )

        response = self.client.get(reverse("listings:report_export_csv"))
        rows = self._csv_rows(response)
        row = next(item for item in rows[1:] if item[0] == str(report.pk))

        self.assertEqual(rows[0][0:3], ["Report ID", "Listing ID", "Listing Title"])
        self.assertEqual(row[2], "'=SUM(1,1)")
        self.assertEqual(row[9], "'+unsafe-details")
        self.assertEqual(row[10], "'-unsafe-public-note")
        self.assertEqual(row[11], "'@unsafe-admin-note")

    def test_appeal_and_action_log_csvs_neutralize_formula_cells(self):
        appeal = ModerationAppeal.objects.create(
            appellant=self.reporter,
            listing=self.listing,
            message="=unsafe-message",
            status=ModerationAppeal.Status.APPROVED,
            extra_evidence_request_note="@unsafe-request-note",
            decision_note="+unsafe-decision",
            admin_note="-unsafe-admin-note",
            reviewed_by=self.admin,
            reviewed_at=timezone.now(),
        )

        appeal_response = self.client.get(
            reverse("accounts:moderation_appeal_export_csv")
        )
        appeal_rows = self._csv_rows(appeal_response)
        appeal_row = next(
            item for item in appeal_rows[1:] if item[0] == str(appeal.pk)
        )

        self.assertEqual(appeal_row[6], "'=SUM(1,1)")
        self.assertEqual(appeal_row[16], "'@unsafe-request-note")
        self.assertEqual(appeal_row[17], "'=unsafe-message")
        self.assertEqual(appeal_row[18], "'+unsafe-decision")
        self.assertEqual(appeal_row[19], "'-unsafe-admin-note")

        action_response = self.client.get(
            reverse("accounts:trust_safety_action_log_export"),
            {"type": "appeal"},
        )
        action_rows = self._csv_rows(action_response)
        action_row = next(
            item
            for item in action_rows[1:]
            if item[0] == "appeal" and item[1] == str(appeal.pk)
        )

        self.assertEqual(action_row[9], "'=SUM(1,1)")
        self.assertEqual(action_row[10], "'=unsafe-message")
        self.assertEqual(action_row[11], "'+unsafe-decision")
        self.assertEqual(action_row[12], "'-unsafe-admin-note")

    def test_trust_safety_event_csv_neutralizes_formula_cells(self):
        event = TrustSafetyEvent.objects.create(
            actor=self.admin,
            target_user=self.seller,
            listing=self.listing,
            event_type=TrustSafetyEvent.EventType.AUDIT_REPAIR,
            title="=unsafe-event-title",
            public_note="+unsafe-public-note",
            internal_note="@unsafe-internal-note",
        )

        response = self.client.get(
            reverse("accounts:trust_safety_event_log_export")
        )
        rows = self._csv_rows(response)
        row = next(item for item in rows[1:] if item[0] == str(event.pk))

        self.assertEqual(row[3], "'=unsafe-event-title")
        self.assertEqual(row[8], "'=SUM(1,1)")
        self.assertEqual(row[12], "'+unsafe-public-note")
        self.assertEqual(row[13], "'@unsafe-internal-note")

    def test_all_staff_csv_modules_use_the_shared_contract(self):
        modules = (
            "accounts/admin.py",
            "accounts/appeal_views.py",
            "accounts/trust_safety_views.py",
            "listings/listing_reports_views.py",
            "listings/saved_search_notification_audit_operator.py",
        )

        for module in modules:
            with self.subTest(module=module):
                source = (Path(settings.BASE_DIR) / module).read_text(
                    encoding="utf-8"
                )
                self.assertIn("csv_safe", source)

    def test_v323_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (Path(settings.BASE_DIR) / app_name / "migrations").glob(
                    "*v323*.py"
                )
            )

        self.assertEqual(matches, [])
