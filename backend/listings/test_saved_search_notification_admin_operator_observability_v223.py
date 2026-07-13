from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import models
from django.test import TestCase
from django.utils import timezone

from listings.models import SavedSearch
from listings.saved_search_notification_observability import (
    V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY,
    build_saved_search_notification_observability_snapshot,
    format_saved_search_notification_observability_lines,
)


class SavedSearchNotificationAdminOperatorObservabilityV223Tests(TestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read_backend(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _saved_search_defaults(self, user, *, enabled: bool, name: str) -> dict[str, Any]:
        fields = {field.name: field for field in SavedSearch._meta.fields}
        data: dict[str, Any] = {"user": user}

        if "name" in fields:
            data["name"] = name
        if "querystring" in fields:
            data["querystring"] = "q=observability&sort=newest"
        if "search_type" in fields:
            field = fields["search_type"]
            if getattr(field, "choices", None):
                data["search_type"] = next(iter(field.choices))[0]
            else:
                data["search_type"] = "listing"
        if "email_notifications_enabled" in fields:
            data["email_notifications_enabled"] = enabled

        return data

    def _create_saved_search(self, user, *, enabled: bool, name: str):
        return SavedSearch.objects.create(
            **self._saved_search_defaults(user, enabled=enabled, name=name)
        )

    def test_v223_marker_is_declared_for_admin_operator_observability(self):
        self.assertEqual(
            V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY,
            "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY",
        )

    def test_v223_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v223_saved_search_model_still_has_notification_fields_without_migrations(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v223_snapshot_reports_counts_read_only_without_delivery_or_mutation(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v223-owner",
            email="v223-owner@example.com",
            password="password",
        )
        no_email_owner = user_model.objects.create_user(
            username="v223-no-email-owner",
            email="",
            password="password",
        )

        first = self._create_saved_search(owner, enabled=True, name="Ready alert")
        second = self._create_saved_search(owner, enabled=False, name="Disabled alert")
        third = self._create_saved_search(no_email_owner, enabled=True, name="Missing email alert")

        timestamp = timezone.now()
        first.last_notification_checked_at = timestamp
        first.last_notification_sent_at = timestamp
        first.save(update_fields=["last_notification_checked_at", "last_notification_sent_at"])

        before_values = {
            saved_search.pk: (
                saved_search.last_notification_checked_at,
                saved_search.last_notification_sent_at,
            )
            for saved_search in (first, second, third)
        }
        mail.outbox = []

        snapshot = build_saved_search_notification_observability_snapshot(limit=10)

        self.assertEqual(
            snapshot["marker"],
            "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY",
        )
        self.assertEqual(snapshot["mode"], "observability")
        self.assertTrue(snapshot["read_only"])
        self.assertFalse(snapshot["delivery_enabled"])
        self.assertFalse(snapshot["mutation_allowed"])
        self.assertFalse(snapshot["owner_scoped"])
        self.assertEqual(snapshot["total_count"], 3)
        self.assertEqual(snapshot["enabled_count"], 2)
        self.assertEqual(snapshot["disabled_count"], 1)
        self.assertEqual(snapshot["enabled_with_email_count"], 1)
        self.assertEqual(snapshot["missing_recipient_email_count"], 1)
        self.assertEqual(snapshot["checked_timestamp_count"], 1)
        self.assertEqual(snapshot["sent_timestamp_count"], 1)
        self.assertEqual(snapshot["sample_count"], 3)
        self.assertEqual(len(mail.outbox), 0)

        for saved_search in (first, second, third):
            saved_search.refresh_from_db()
            self.assertEqual(
                (
                    saved_search.last_notification_checked_at,
                    saved_search.last_notification_sent_at,
                ),
                before_values[saved_search.pk],
            )

    def test_v223_snapshot_can_be_owner_scoped_and_limited(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v223-scope-owner",
            email="v223-scope-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v223-scope-other",
            email="v223-scope-other@example.com",
            password="password",
        )

        self._create_saved_search(owner, enabled=True, name="Owner first")
        self._create_saved_search(owner, enabled=True, name="Owner second")
        self._create_saved_search(other_owner, enabled=True, name="Other owner")

        snapshot = build_saved_search_notification_observability_snapshot(
            owner=owner,
            limit=1,
        )

        self.assertTrue(snapshot["owner_scoped"])
        self.assertEqual(snapshot["total_count"], 2)
        self.assertEqual(snapshot["enabled_count"], 2)
        self.assertEqual(snapshot["sample_count"], 1)
        self.assertEqual(snapshot["samples"][0]["owner_id"], owner.pk)
        self.assertEqual(snapshot["samples"][0]["recipient_email"], "v223-scope-owner@example.com")

    def test_v223_observability_lines_are_operator_readable(self):
        snapshot = {
            "owner_scoped": False,
            "total_count": 2,
            "enabled_count": 1,
            "disabled_count": 1,
            "enabled_with_email_count": 1,
            "missing_recipient_email_count": 0,
            "checked_timestamp_count": 1,
            "sent_timestamp_count": 0,
            "sample_count": 1,
            "samples": [
                {
                    "saved_search_id": 7,
                    "owner_id": 3,
                    "email_notifications_enabled": True,
                    "recipient_email": "operator@example.com",
                    "last_notification_checked_at": None,
                    "last_notification_sent_at": None,
                    "label": "Operator sample",
                }
            ],
        }

        lines = format_saved_search_notification_observability_lines(snapshot)

        self.assertIn(
            "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY",
            lines[0],
        )
        self.assertIn("mode=observability", lines[0])
        self.assertIn("read_only=True", lines[0])
        self.assertIn("delivery_enabled=False", lines[0])
        self.assertIn("mutation_allowed=False", lines[0])
        self.assertIn("total=2", lines[0])
        self.assertIn("enabled=1", lines[0])
        self.assertIn("OBSERVABILITY saved_search", lines[1])
        self.assertIn("recipient=operator@example.com", lines[1])
        self.assertIn("label=Operator sample", lines[1])

    def test_v223_management_command_report_is_read_only_and_does_not_deliver(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v223-command-owner",
            email="v223-command-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Command observability alert",
        )

        before_checked = saved_search.last_notification_checked_at
        before_sent = saved_search.last_notification_sent_at
        mail.outbox = []

        stdout = StringIO()
        call_command(
            "process_saved_search_notifications",
            "--notification-observability-report",
            "--limit",
            "5",
            stdout=stdout,
        )
        output = stdout.getvalue()

        self.assertIn(
            "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY",
            output,
        )
        self.assertIn("mode=observability", output)
        self.assertIn("read_only=True", output)
        self.assertIn("delivery_enabled=False", output)
        self.assertIn("mutation_allowed=False", output)
        self.assertIn("total=1", output)
        self.assertIn("enabled=1", output)
        self.assertIn("v223-command-owner@example.com", output)
        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertEqual(saved_search.last_notification_checked_at, before_checked)
        self.assertEqual(saved_search.last_notification_sent_at, before_sent)

    def test_v223_default_command_path_still_does_not_print_report_or_deliver(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v223-default-owner",
            email="v223-default-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Default command no observability",
        )
        mail.outbox = []

        stdout = StringIO()
        call_command("process_saved_search_notifications", stdout=stdout)
        output = stdout.getvalue()

        self.assertNotIn(
            "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY",
            output,
        )
        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_v223_command_source_exposes_observability_flag_without_delivery_terms(self):
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )

        self.assertIn("--notification-observability-report", command_source)
        self.assertIn("notification_observability_report", command_source)
        self.assertIn("build_saved_search_notification_observability_snapshot", command_source)
        self.assertIn("format_saved_search_notification_observability_lines", command_source)

        forbidden_terms = (
            "send_" + "mail",
            "Email" + "Message",
            "Email" + "MultiAlternatives",
            "mail_" + "admins",
            "mail_" + "managers",
            "." + "send(",
            "last_notification_sent_at" + " =",
            "last_notification_sent_at" + "=",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, command_source)

    def test_v223_observability_source_avoids_delivery_and_background_process_terms(self):
        observability_source = self._read_backend("listings/saved_search_notification_observability.py")
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )
        scheduler_source = self._read_backend("listings/saved_search_notification_scheduler.py")
        sender_source = self._read_backend("listings/saved_search_notification_email_sender.py")
        dockerfile = self._read_backend("Dockerfile")

        forbidden_delivery_terms = (
            "send_" + "mail",
            "Email" + "Message",
            "Email" + "MultiAlternatives",
            "mail_" + "admins",
            "mail_" + "managers",
            "." + "send(",
            "last_notification_sent_at" + " =",
            "last_notification_sent_at=",
        )

        for source in (observability_source, command_source, scheduler_source):
            for term in forbidden_delivery_terms:
                self.assertNotIn(term, source)

        combined = (
            observability_source
            + "\n"
            + command_source
            + "\n"
            + scheduler_source
            + "\n"
            + sender_source
            + "\n"
            + dockerfile
        )
        forbidden_process_terms = (
            "celery",
            "beat",
            "rq",
            "huey",
            "apscheduler",
            "crontab",
            "cron:",
            "worker:",
        )

        for term in forbidden_process_terms:
            self.assertNotIn(term, combined.lower())

    def test_v223_does_not_patch_unrelated_runtime_or_template_surfaces(self):
        untouched_surfaces = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
            "listings/templates/listings/email/saved_search_notification.txt",
            "listings/templates/listings/email/saved_search_notification.html",
            "accounts/admin.py",
            "accounts/models.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in untouched_surfaces:
            self.assertNotIn(
                "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY",
                self._read_backend(relative_path),
                f"v223 marker should not patch unrelated surface {relative_path}",
            )

    def test_v223_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
            "listings/test_saved_search_notification_explicit_send_test_backend_v222.py": (
                "V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND"
            ),
            "listings/test_saved_search_notification_scheduler_email_dry_run_integration_v221.py": (
                "V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION"
            ),
            "listings/test_saved_search_notification_execution_guardrails_runbook_v220.py": (
                "V220_SAVED_SEARCH_NOTIFICATION_EXECUTION_GUARDRAILS_RUNBOOK"
            ),
            "listings/test_saved_search_notification_email_sending_dry_run_contract_v219.py": (
                "V219_SAVED_SEARCH_NOTIFICATION_EMAIL_SENDING_DRY_RUN_CONTRACT"
            ),
            "listings/test_saved_search_notification_email_template_rendering_v218.py": (
                "V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING"
            ),
            "listings/test_saved_search_notification_email_rendering_contract_v217.py": (
                "V217_SAVED_SEARCH_NOTIFICATION_EMAIL_RENDERING_CONTRACT"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read_backend(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
