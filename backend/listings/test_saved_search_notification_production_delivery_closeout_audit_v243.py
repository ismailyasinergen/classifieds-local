from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.mail.backends.locmem import (
    EmailBackend as LocmemEmailBackend,
)
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from listings.models import (
    SavedSearch,
    SavedSearchNotificationAuditEvent,
)
from listings.saved_search_notification_email_sender import (
    V242_PRODUCTION_DELIVERY_BATCH_MAX,
    V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION,
    SavedSearchNotificationProductionDeliveryRefused,
    send_saved_search_notification_email_production,
)


V243_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CLOSEOUT_AUDIT = (
    "V243_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CLOSEOUT_AUDIT"
)

V242_COMMITTED_SCOPE = (
    "backend/config/settings.py",
    "backend/listings/saved_search_notification_email_sender.py",
    (
        "backend/listings/management/commands/"
        "process_saved_search_notifications.py"
    ),
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_v242.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "implementation_v242.md"
    ),
)

V243_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "closeout_audit_v243.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "closeout_audit_v243.md"
    ),
)

CLOSEOUT_GATES = (
    "v241 production-delivery contract remains packaged",
    "v242 implementation remains packaged",
    "production feature gate defaults off",
    "two explicit production confirmations remain required",
    "positive owner ID remains required",
    "explicit production batch limit remains required",
    "production batch maximum remains 25",
    "locmem dummy console and file backends remain rejected",
    "custom configured backend delivery remains available",
    "disabled gate refuses before message rendering",
    "refused delivery does not advance sent timestamp",
    "successful delivery records persistent audit events",
    "successful delivery records sent timestamp",
    "command output remains sanitized",
    "existing locmem test-send path remains separate",
    "one failed item cannot enable global delivery",
    "scheduler remains non-delivery and non-automatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "v243 modifies only audit test and document",
    "full regression remains green",
)

NEXT_CHECKPOINT = (
    "v244: saved-search notification production delivery operational readiness contract"
)

PROTECTED_BACKEND_PATHS = (
    "config/settings.py",
    "listings/saved_search_notification_email_sender.py",
    (
        "listings/management/commands/"
        "process_saved_search_notifications.py"
    ),
    "listings/saved_search_notification_scheduler.py",
    "listings/saved_search_notifications.py",
    "listings/saved_search_notification_audit_runtime.py",
    "listings/saved_search_notification_audit_persistence.py",
    "listings/saved_search_notification_audit.py",
    "listings/saved_search_notification_email_renderer.py",
    "listings/models.py",
    "listings/admin.py",
    "listings/urls.py",
    "templates/base.html",
    (
        "listings/templates/listings/"
        "saved_search_notification_audit_events.html"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_v242.py"
    ),
)


class CloseoutCaptureEmailBackend(
    LocmemEmailBackend
):
    pass


CLOSEOUT_CAPTURE_BACKEND = (
    "listings."
    "test_saved_search_notification_production_delivery_"
    "closeout_audit_v243.CloseoutCaptureEmailBackend"
)


class SavedSearchNotificationProductionDeliveryCloseoutAuditV243Tests(
    TestCase
):
    maxDiff = None

    def setUp(self):
        user_model = get_user_model()

        self.owner = user_model.objects.create_user(
            username="v243-owner",
            email="v243-owner@example.com",
            password="v243-password",
        )

        self.saved_search = SavedSearch.objects.create(
            user=self.owner,
            name="V243 closeout search",
            path="/listings/",
            query_params={
                "q": "v243-private-query",
            },
            querystring="q=v243-private-query",
            email_notifications_enabled=True,
        )

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _read_backend(
        self,
        relative_path: str,
    ) -> str:
        return (
            self._backend_root()
            / relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def test_v243_marker_scope_and_next_lane_are_stable(self):
        self.assertEqual(
            V243_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CLOSEOUT_AUDIT,
            (
                "V243_SAVED_SEARCH_NOTIFICATION_"
                "PRODUCTION_DELIVERY_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V242_COMMITTED_SCOPE),
            5,
        )

        self.assertEqual(
            len(V243_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v244: saved-search notification production "
                "delivery operational readiness contract"
            ),
        )

    def test_v243_v242_public_contract_remains_stable(self):
        self.assertEqual(
            V242_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_IMPLEMENTATION,
            (
                "V242_SAVED_SEARCH_NOTIFICATION_"
                "PRODUCTION_DELIVERY_IMPLEMENTATION"
            ),
        )

        self.assertEqual(
            V242_PRODUCTION_DELIVERY_BATCH_MAX,
            25,
        )

        self.assertFalse(
            settings.SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED
        )

    def test_v243_command_safety_controls_remain_packaged(self):
        source = self._read_backend(
            "listings/management/commands/"
            "process_saved_search_notifications.py"
        )

        required = (
            "--execute-production-send",
            "--confirm-production-delivery",
            "--owner-id",
            "Production delivery requires both",
            "Production delivery requires a positive",
            "Production delivery requires an explicit",
            "between 1 and 25",
            "configuration_refused",
            "failed_count",
            "V242_LEGACY_LIMIT_DEFAULT",
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

    def test_v243_sender_safety_controls_remain_packaged(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        required = (
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED",
            "production_confirmation_required",
            "production_delivery_disabled",
            "nonproduction_delivery_backend",
            "django.core.mail.backends.locmem.",
            "django.core.mail.backends.dummy.",
            "django.core.mail.backends.console.",
            "django.core.mail.backends.filebased.",
            "require_test_email_backend=False",
            "seen_ids",
            "configuration_refused",
        )

        for term in required:
            with self.subTest(term=term):
                self.assertIn(
                    term,
                    source,
                )

        self.assertNotIn(
            "production_email_backend",
            source,
        )

    @override_settings(
        EMAIL_BACKEND=CLOSEOUT_CAPTURE_BACKEND,
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=False,
    )
    def test_v243_disabled_gate_refuses_before_rendering(self):
        with patch(
            "listings."
            "saved_search_notification_email_sender."
            "_build_email_message"
        ) as build_message:
            with self.assertRaises(
                SavedSearchNotificationProductionDeliveryRefused
            ):
                send_saved_search_notification_email_production(
                    self.saved_search,
                    match_count=1,
                    matching_listings=(),
                    execute_production_send=True,
                    confirm_production_delivery=True,
                )

        build_message.assert_not_called()

        self.saved_search.refresh_from_db()

        self.assertIsNone(
            self.saved_search.last_notification_sent_at
        )

        self.assertTrue(
            SavedSearchNotificationAuditEvent.objects.filter(
                saved_search=self.saved_search,
                event_type="delivery_failed",
                reason_code="production_delivery_disabled",
            ).exists()
        )

    @override_settings(
        EMAIL_BACKEND=CLOSEOUT_CAPTURE_BACKEND,
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
    )
    def test_v243_successful_delivery_records_audit_and_timestamp(self):
        result = send_saved_search_notification_email_production(
            self.saved_search,
            match_count=1,
            matching_listings=(),
            execute_production_send=True,
            confirm_production_delivery=True,
        )

        self.assertEqual(
            result["delivered_count"],
            1,
        )

        self.assertEqual(
            len(mail.outbox),
            1,
        )

        self.saved_search.refresh_from_db()

        self.assertIsNotNone(
            self.saved_search.last_notification_sent_at
        )

        event_types = set(
            SavedSearchNotificationAuditEvent.objects
            .filter(
                saved_search=self.saved_search
            )
            .values_list(
                "event_type",
                flat=True,
            )
        )

        self.assertTrue(
            {
                "delivery_attempted",
                "delivery_succeeded",
                "sent_timestamp_recorded",
            }.issubset(event_types)
        )

    def test_v243_command_refusal_output_remains_sanitized(self):
        stdout = StringIO()

        with override_settings(
            EMAIL_BACKEND=(
                "django.core.mail.backends.locmem.EmailBackend"
            ),
            SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
        ):
            with self.assertRaises(CommandError):
                call_command(
                    "process_saved_search_notifications",
                    "--execute-production-send",
                    "--confirm-production-delivery",
                    "--owner-id",
                    str(self.owner.pk),
                    "--limit",
                    "1",
                    stdout=stdout,
                )

        output = stdout.getvalue()

        self.assertIn(
            "refused=1",
            output,
        )

        self.assertNotIn(
            self.owner.email,
            output,
        )

        self.assertNotIn(
            "v243-private-query",
            output,
        )

    def test_v243_scheduler_remains_nonautomatic(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_scheduler.py"
        )

        forbidden = (
            "--execute-production-send",
            "--confirm-production-delivery",
            "send_saved_search_notification_email_production",
            "Celery",
            "celery",
            "cron",
            "startup",
            "ready(",
        )

        for term in forbidden:
            with self.subTest(term=term):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v243_schema_admin_and_ui_boundary_is_closed(self):
        self.assertNotIn(
            SavedSearchNotificationAuditEvent,
            admin.site._registry,
        )

        migration_directory = (
            self._backend_root()
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )

    def test_v243_marker_does_not_leak_into_protected_surfaces(self):
        for relative_path in PROTECTED_BACKEND_PATHS:
            source = self._read_backend(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    V243_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_CLOSEOUT_AUDIT,
                    source,
                )

    def test_v243_closeout_gate_matrix_is_complete(self):
        required = {
            "v241 production-delivery contract remains packaged",
            "v242 implementation remains packaged",
            "production feature gate defaults off",
            "two explicit production confirmations remain required",
            "positive owner ID remains required",
            "explicit production batch limit remains required",
            "production batch maximum remains 25",
            "locmem dummy console and file backends remain rejected",
            "custom configured backend delivery remains available",
            "disabled gate refuses before message rendering",
            "refused delivery does not advance sent timestamp",
            "successful delivery records persistent audit events",
            "successful delivery records sent timestamp",
            "command output remains sanitized",
            "existing locmem test-send path remains separate",
            "one failed item cannot enable global delivery",
            "scheduler remains non-delivery and non-automatic",
            "models admin URLs templates and migrations remain unchanged",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "v243 modifies only audit test and document",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(CLOSEOUT_GATES)
            )
        )
