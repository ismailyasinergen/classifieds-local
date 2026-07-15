from __future__ import annotations

from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
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
    send_saved_search_notification_email_production_batch,
)


NEXT_CHECKPOINT = (
    "v243: saved-search notification production delivery "
    "closeout audit"
)


class ProductionCaptureEmailBackend(
    LocmemEmailBackend
):
    pass


PRODUCTION_CAPTURE_BACKEND = (
    "listings."
    "test_saved_search_notification_production_delivery_"
    "implementation_v242.ProductionCaptureEmailBackend"
)


class SavedSearchNotificationProductionDeliveryImplementationV242Tests(
    TestCase
):
    def setUp(self):
        user_model = get_user_model()

        self.owner = user_model.objects.create_user(
            username="v242-owner",
            email="v242-owner@example.com",
            password="v242-password",
        )

        self.other_owner = (
            user_model.objects.create_user(
                username="v242-other",
                email="v242-other@example.com",
                password="v242-password",
            )
        )

        self.saved_search = SavedSearch.objects.create(
            user=self.owner,
            name="V242 search",
            path="/listings/",
            query_params={"q": "v242"},
            querystring="q=v242",
            email_notifications_enabled=True,
        )

    def _backend_root(self):
        return Path(__file__).resolve().parents[1]

    def test_v242_marker_and_limit_are_stable(self):
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

    def test_v242_gate_defaults_off(self):
        self.assertFalse(
            settings.SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED
        )

    def test_v242_both_confirmations_are_required(self):
        with override_settings(
            EMAIL_BACKEND=PRODUCTION_CAPTURE_BACKEND,
            SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
        ):
            for execute, confirm in (
                (False, False),
                (True, False),
                (False, True),
            ):
                with self.subTest(
                    execute=execute,
                    confirm=confirm,
                ):
                    with self.assertRaises(
                        SavedSearchNotificationProductionDeliveryRefused
                    ):
                        send_saved_search_notification_email_production(
                            self.saved_search,
                            match_count=1,
                            matching_listings=(),
                            execute_production_send=execute,
                            confirm_production_delivery=confirm,
                        )

    def test_v242_disabled_gate_refuses_before_rendering(self):
        with override_settings(
            EMAIL_BACKEND=PRODUCTION_CAPTURE_BACKEND,
            SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=False,
        ):
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

    def test_v242_nonproduction_backends_are_rejected(self):
        for backend_path in (
            "django.core.mail.backends.locmem.EmailBackend",
            "django.core.mail.backends.dummy.EmailBackend",
            "django.core.mail.backends.console.EmailBackend",
            "django.core.mail.backends.filebased.EmailBackend",
        ):
            with self.subTest(
                backend_path=backend_path
            ):
                with override_settings(
                    EMAIL_BACKEND=backend_path,
                    SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
                ):
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

    @override_settings(
        EMAIL_BACKEND=PRODUCTION_CAPTURE_BACKEND,
        SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
    )
    def test_v242_custom_backend_delivers(self):
        result = (
            send_saved_search_notification_email_production(
                self.saved_search,
                match_count=1,
                matching_listings=(),
                execute_production_send=True,
                confirm_production_delivery=True,
            )
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

    def test_v242_limit_is_explicit_and_bounded(self):
        for invalid in (
            None,
            0,
            -1,
            26,
            "invalid",
            True,
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(
                    SavedSearchNotificationProductionDeliveryRefused
                ):
                    send_saved_search_notification_email_production_batch(
                        owner=self.owner,
                        limit=invalid,
                        execute_production_send=True,
                        confirm_production_delivery=True,
                    )

    def test_v242_zero_match_is_skipped(self):
        preview = SimpleNamespace(
            match_count=0,
            listings=(),
        )

        with override_settings(
            EMAIL_BACKEND=PRODUCTION_CAPTURE_BACKEND,
            SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED=True,
        ):
            with patch(
                "listings."
                "saved_search_notification_email_sender."
                "_v242_build_match_preview",
                return_value=preview,
            ):
                result = (
                    send_saved_search_notification_email_production_batch(
                        owner=self.owner,
                        limit=1,
                        execute_production_send=True,
                        confirm_production_delivery=True,
                    )
                )

        self.assertEqual(
            result["attempted_count"],
            0,
        )

        self.assertEqual(
            result["skipped_count"],
            1,
        )

    def test_v242_command_requires_owner_and_limit(self):
        with self.assertRaises(CommandError):
            call_command(
                "process_saved_search_notifications",
                "--execute-production-send",
            )

        with self.assertRaises(CommandError):
            call_command(
                "process_saved_search_notifications",
                "--execute-production-send",
                "--confirm-production-delivery",
                "--limit",
                "1",
            )

        with self.assertRaises(CommandError):
            call_command(
                "process_saved_search_notifications",
                "--execute-production-send",
                "--confirm-production-delivery",
                "--owner-id",
                str(self.owner.pk),
            )

    def test_v242_command_output_is_sanitized(self):
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

        self.assertNotIn(
            self.owner.email,
            output,
        )

        self.assertNotIn(
            "q=v242",
            output,
        )

    def test_v242_next_lane_is_closeout(self):
        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v243: saved-search notification production "
                "delivery closeout audit"
            ),
        )
