"""
Focused contracts for v301 notification scheduler leasing.
"""

from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from threading import Event, Thread
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.management import call_command
from django.db import (
    DEFAULT_DB_ALIAS,
    close_old_connections,
    connections,
)
from django.test import SimpleTestCase, TransactionTestCase

from .notification_scheduler_lease_v301 import (
    LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301,
    NOTIFICATION_SCHEDULER_LEASE_V301,
    SAVED_SEARCH_SCHEDULER_LEASE_NAME_V301,
    build_notification_scheduler_lock_key_v301,
    notification_scheduler_lease_v301,
    try_acquire_notification_scheduler_lease_v301,
)


@contextmanager
def denied_scheduler_lease_v301(*_args, **_kwargs):
    yield SimpleNamespace(acquired=False)


class NotificationSchedulerLeaseV301Tests(
    SimpleTestCase
):
    @property
    def backend_root(self):
        return Path(settings.BASE_DIR)

    def read_backend(self, relative_path):
        return (
            self.backend_root
            / relative_path
        ).read_text(
            encoding="utf-8",
        )

    def test_marker_and_scheduler_keys_are_stable_and_distinct(self):
        self.assertTrue(
            NOTIFICATION_SCHEDULER_LEASE_V301
        )

        listing_key = (
            build_notification_scheduler_lock_key_v301(
                LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301
            )
        )
        saved_key = (
            build_notification_scheduler_lock_key_v301(
                SAVED_SEARCH_SCHEDULER_LEASE_NAME_V301
            )
        )

        self.assertEqual(
            listing_key,
            build_notification_scheduler_lock_key_v301(
                LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301
            ),
        )
        self.assertNotEqual(
            listing_key,
            saved_key,
        )
        self.assertEqual(
            len(listing_key),
            2,
        )

    def test_listing_alert_dry_run_bypasses_scheduler_lease(self):
        preview = SimpleNamespace(
            match_count=0,
            alerts=[],
        )
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "check_listing_price_alerts."
                    "notification_scheduler_lease_v301"
                )
            ) as lease_mock,
            patch(
                (
                    "listings.management.commands."
                    "check_listing_price_alerts."
                    "build_listing_price_alert_preview_v285"
                ),
                return_value=preview,
            ),
        ):
            call_command(
                "check_listing_price_alerts",
                stdout=output,
            )

        lease_mock.assert_not_called()
        self.assertIn(
            "Mode: DRY RUN",
            output.getvalue(),
        )

    def test_listing_alert_send_stops_before_candidate_scan_when_busy(self):
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "check_listing_price_alerts."
                    "notification_scheduler_lease_v301"
                ),
                denied_scheduler_lease_v301,
            ),
            patch(
                (
                    "listings.management.commands."
                    "check_listing_price_alerts."
                    "build_listing_price_alert_preview_v285"
                )
            ) as preview_mock,
        ):
            call_command(
                "check_listing_price_alerts",
                "--send",
                stdout=output,
            )

        preview_mock.assert_not_called()
        text = output.getvalue()
        self.assertIn(
            "Scheduler lease unavailable",
            text,
        )
        self.assertIn(
            "no candidates were scanned",
            text,
        )
        self.assertIn(
            "no email was sent",
            text,
        )

    def test_saved_search_dry_run_bypasses_scheduler_lease(self):
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "check_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                )
            ) as lease_mock,
            patch(
                (
                    "listings.management.commands."
                    "check_saved_search_notifications."
                    "iter_enabled_saved_search_match_previews"
                ),
                return_value=iter(()),
            ),
        ):
            call_command(
                "check_saved_search_notifications",
                stdout=output,
            )

        lease_mock.assert_not_called()
        self.assertIn(
            "No enabled saved searches found",
            output.getvalue(),
        )

    def test_saved_search_mark_checked_stops_before_scan_when_busy(self):
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "check_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                ),
                denied_scheduler_lease_v301,
            ),
            patch(
                (
                    "listings.management.commands."
                    "check_saved_search_notifications."
                    "iter_enabled_saved_search_match_previews"
                )
            ) as preview_mock,
        ):
            call_command(
                "check_saved_search_notifications",
                "--mark-checked",
                stdout=output,
            )

        preview_mock.assert_not_called()
        self.assertIn(
            "no email or timestamp update occurred",
            output.getvalue(),
        )

    def test_saved_search_send_stops_before_scan_when_busy(self):
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "check_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                ),
                denied_scheduler_lease_v301,
            ),
            patch(
                (
                    "listings.management.commands."
                    "check_saved_search_notifications."
                    "iter_enabled_saved_search_match_previews"
                )
            ) as preview_mock,
        ):
            call_command(
                "check_saved_search_notifications",
                "--send",
                stdout=output,
            )

        preview_mock.assert_not_called()
        text = output.getvalue()
        self.assertIn(
            "Scheduler lease unavailable",
            text,
        )
        self.assertNotIn(
            "Email recipient:",
            text,
        )


    def test_process_command_default_dry_run_bypasses_scheduler_lease(self):
        output = StringIO()
        result = SimpleNamespace(
            checked=0,
            sent=0,
            dry_run=True,
        )

        with (
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                )
            ) as lease_mock,
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "SavedSearchNotificationAuditRuntimeContext.create"
                ),
                return_value=SimpleNamespace(),
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "run_saved_search_notification_scheduler"
                ),
                return_value=result,
            ),
        ):
            call_command(
                "process_saved_search_notifications",
                stdout=output,
            )

        lease_mock.assert_not_called()
        self.assertIn(
            "dry_run=True",
            output.getvalue(),
        )


    def test_process_preview_wins_over_execute_and_bypasses_lease(self):
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                )
            ) as lease_mock,
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "SavedSearchNotificationAuditRuntimeContext.create"
                ),
                return_value=SimpleNamespace(),
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "build_saved_search_notification_scheduler_email_previews"
                ),
                return_value=[],
            ) as preview_builder,
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "run_saved_search_notification_scheduler"
                )
            ) as scheduler,
        ):
            call_command(
                "process_saved_search_notifications",
                "--render-email-previews",
                "--execute",
                stdout=output,
            )

        lease_mock.assert_not_called()
        preview_builder.assert_called_once()
        scheduler.assert_not_called()
        self.assertIn(
            "dry_run=True",
            output.getvalue(),
        )

    def test_process_report_wins_over_execute_and_bypasses_lease(self):
        output = StringIO()
        snapshot = SimpleNamespace()

        with (
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                )
            ) as lease_mock,
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "SavedSearchNotificationAuditRuntimeContext.create"
                ),
                return_value=SimpleNamespace(),
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "build_saved_search_notification_observability_snapshot"
                ),
                return_value=snapshot,
            ) as report_builder,
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "format_saved_search_notification_observability_lines"
                ),
                return_value=["read-only report"],
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "run_saved_search_notification_scheduler"
                )
            ) as scheduler,
        ):
            call_command(
                "process_saved_search_notifications",
                "--notification-observability-report",
                "--execute",
                stdout=output,
            )

        lease_mock.assert_not_called()
        report_builder.assert_called_once_with(
            limit=None,
        )
        scheduler.assert_not_called()
        self.assertIn(
            "read-only report",
            output.getvalue(),
        )

    def test_process_execute_stops_before_audit_and_scheduler_when_busy(self):
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                ),
                denied_scheduler_lease_v301,
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "SavedSearchNotificationAuditRuntimeContext.create"
                )
            ) as audit_context,
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "run_saved_search_notification_scheduler"
                )
            ) as scheduler,
        ):
            call_command(
                "process_saved_search_notifications",
                "--execute",
                stdout=output,
            )

        audit_context.assert_not_called()
        scheduler.assert_not_called()
        self.assertIn(
            "no candidate scan",
            output.getvalue(),
        )
        self.assertIn(
            "no timestamp update",
            output.getvalue(),
        )

    def test_process_test_send_stops_before_audit_and_sender_when_busy(self):
        output = StringIO()

        with (
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                ),
                denied_scheduler_lease_v301,
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "SavedSearchNotificationAuditRuntimeContext.create"
                )
            ) as audit_context,
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "send_saved_search_notification_email_batch"
                )
            ) as sender,
        ):
            call_command(
                "process_saved_search_notifications",
                "--execute-email-send",
                "--limit",
                "1",
                stdout=output,
            )

        audit_context.assert_not_called()
        sender.assert_not_called()
        self.assertIn(
            "no email delivery",
            output.getvalue(),
        )

    def test_process_production_send_validates_then_stops_when_busy(self):
        output = StringIO()
        manager = Mock()
        manager.filter.return_value.first.return_value = object()
        user_model = SimpleNamespace(
            objects=manager,
        )

        with (
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "_v242_get_user_model"
                ),
                return_value=user_model,
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "notification_scheduler_lease_v301"
                ),
                denied_scheduler_lease_v301,
            ),
            patch(
                (
                    "listings.management.commands."
                    "process_saved_search_notifications."
                    "send_saved_search_notification_email_production_batch"
                )
            ) as sender,
        ):
            call_command(
                "process_saved_search_notifications",
                "--execute-production-send",
                "--confirm-production-delivery",
                "--owner-id",
                "1",
                "--limit",
                "1",
                stdout=output,
            )

        manager.filter.assert_called_once_with(
            pk=1,
        )
        sender.assert_not_called()
        text = output.getvalue()
        self.assertIn(
            "no production candidate scan",
            text,
        )
        self.assertNotIn(
            "recipient=",
            text,
        )

    def test_event_claims_remain_delivery_correctness_boundary(self):
        listing_source = self.read_backend(
            (
                "listings/management/commands/"
                "check_listing_price_alerts.py"
            )
        )
        saved_source = self.read_backend(
            (
                "listings/management/commands/"
                "check_saved_search_notifications.py"
            )
        )
        process_source = self.read_backend(
            (
                "listings/management/commands/"
                "process_saved_search_notifications.py"
            )
        )

        for source in (
            listing_source,
            saved_source,
        ):
            with self.subTest(
                source_length=len(source)
            ):
                self.assertIn(
                    "claim_notification_events_v287",
                    source,
                )
                self.assertIn(
                    "notification_scheduler_lease_v301",
                    source,
                )

        self.assertIn(
            "notification_scheduler_lease_v301",
            process_source,
        )
        self.assertIn(
            "send_saved_search_notification_email_production_batch",
            process_source,
        )
        self.assertIn(
            "send_saved_search_notification_email_batch",
            process_source,
        )
        self.assertIn(
            "run_saved_search_notification_scheduler",
            process_source,
        )

    def test_v301_adds_no_route_model_or_migration(self):
        urls_source = self.read_backend(
            "listings/urls.py"
        )
        root_urls_source = self.read_backend(
            "config/urls.py"
        )
        models_source = self.read_backend(
            "listings/models.py"
        )
        migration_directory = (
            self.backend_root
            / "listings"
            / "migrations"
        )

        self.assertNotIn(
            "v301",
            urls_source.lower(),
        )
        self.assertNotIn(
            "v301",
            root_urls_source.lower(),
        )
        self.assertNotIn(
            "v301",
            models_source.lower(),
        )
        self.assertEqual(
            list(
                migration_directory.glob(
                    "*v301*"
                )
            ),
            [],
        )
        self.assertTrue(
            (
                migration_directory
                / (
                    "0023_listingpricehistory_"
                    "discount_guardrail_v293.py"
                )
            ).is_file()
        )


class NotificationSchedulerLeaseConcurrencyV301Tests(
    TransactionTestCase
):
    reset_sequences = False

    def test_concurrent_database_sessions_allow_only_one_active_run(self):
        holder_ready = Event()
        release_holder = Event()
        results = {}

        def hold_lease():
            close_old_connections()

            with notification_scheduler_lease_v301(
                SAVED_SEARCH_SCHEDULER_LEASE_NAME_V301
            ) as lease:
                results["holder"] = lease.acquired
                holder_ready.set()
                release_holder.wait(timeout=10)

            close_old_connections()

        thread = Thread(
            target=hold_lease,
            daemon=True,
        )
        thread.start()

        self.assertTrue(
            holder_ready.wait(timeout=10)
        )
        self.assertTrue(
            results["holder"]
        )

        with notification_scheduler_lease_v301(
            SAVED_SEARCH_SCHEDULER_LEASE_NAME_V301
        ) as competing:
            self.assertFalse(
                competing.acquired
            )

        release_holder.set()
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive())

        with notification_scheduler_lease_v301(
            SAVED_SEARCH_SCHEDULER_LEASE_NAME_V301
        ) as later:
            self.assertTrue(
                later.acquired
            )

    def test_database_connection_close_recovers_abandoned_lease(self):
        worker_finished = Event()
        results = {}

        def acquire_then_close():
            close_old_connections()

            lease = (
                try_acquire_notification_scheduler_lease_v301(
                    LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301
                )
            )
            results["acquired"] = lease.acquired

            connections[
                DEFAULT_DB_ALIAS
            ].close()
            worker_finished.set()

        thread = Thread(
            target=acquire_then_close,
            daemon=True,
        )
        thread.start()

        self.assertTrue(
            worker_finished.wait(timeout=10)
        )
        thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertTrue(
            results["acquired"]
        )

        with notification_scheduler_lease_v301(
            LISTING_PRICE_ALERT_SCHEDULER_LEASE_NAME_V301
        ) as recovered:
            self.assertTrue(
                recovered.acquired
            )
