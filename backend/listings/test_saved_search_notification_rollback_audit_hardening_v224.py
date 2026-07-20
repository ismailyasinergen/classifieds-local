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
from listings.saved_search_notification_audit import (
    V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING,
    SavedSearchNotificationRollbackBlocked,
    build_saved_search_notification_audit_event,
    build_saved_search_notification_rollback_plan,
    format_saved_search_notification_rollback_plan_lines,
    rollback_saved_search_notification_sent_timestamp,
)


class SavedSearchNotificationRollbackAuditHardeningV224Tests(TestCase):
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
            data["querystring"] = "q=rollback&sort=newest"
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

    def test_v224_marker_is_declared_for_rollback_audit_hardening(self):
        self.assertEqual(
            V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING,
            "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
        )

    def test_v224_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v224_saved_search_model_still_has_notification_fields_without_migrations(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v224_audit_event_has_stable_fingerprint_and_no_delivery(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v224-audit-owner",
            email="v224-audit-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Audit event alert",
        )
        mail.outbox = []

        delivery_result = {
            "mode": "execute_send",
            "execute_send": True,
            "delivery_enabled": True,
            "delivered_count": 1,
            "sent_timestamp_before": None,
            "sent_timestamp_after": timezone.now(),
            "saved_search_id": saved_search.pk,
            "recipient_email": "v224-audit-owner@example.com",
        }

        first_event = build_saved_search_notification_audit_event(
            action="explicit_send",
            saved_search=saved_search,
            delivery_result=delivery_result,
            operator="tester",
            reason="unit test",
        )
        second_event = build_saved_search_notification_audit_event(
            action="explicit_send",
            saved_search=saved_search,
            delivery_result=delivery_result,
            operator="tester",
            reason="unit test",
        )

        self.assertEqual(
            first_event["marker"],
            "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
        )
        self.assertEqual(first_event["schema_version"], 1)
        self.assertEqual(first_event["action"], "explicit_send")
        self.assertEqual(first_event["operator"], "tester")
        self.assertEqual(first_event["reason"], "unit test")
        self.assertEqual(first_event["saved_search_id"], saved_search.pk)
        self.assertEqual(first_event["recipient_email"], "v224-audit-owner@example.com")
        self.assertEqual(first_event["delivery_result"]["delivered_count"], 1)
        self.assertRegex(first_event["audit_fingerprint"], r"^[a-f0-9]{64}$")
        self.assertEqual(
            first_event["audit_fingerprint"],
            second_event["audit_fingerprint"],
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_v224_rollback_plan_is_read_only_owner_scoped_and_limited(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v224-plan-owner",
            email="v224-plan-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v224-plan-other",
            email="v224-plan-other@example.com",
            password="password",
        )

        timestamp = timezone.now()
        first = self._create_saved_search(owner, enabled=True, name="Rollback candidate")
        first.last_notification_sent_at = timestamp
        first.save(update_fields=["last_notification_sent_at"])

        second = self._create_saved_search(owner, enabled=True, name="No sent timestamp")
        other = self._create_saved_search(other_owner, enabled=True, name="Other owner candidate")
        other.last_notification_sent_at = timestamp
        other.save(update_fields=["last_notification_sent_at"])

        before_values = {
            saved_search.pk: saved_search.last_notification_sent_at
            for saved_search in (first, second, other)
        }

        plan = build_saved_search_notification_rollback_plan(
            owner=owner,
            limit=10,
        )

        self.assertEqual(
            plan["marker"],
            "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
        )
        self.assertEqual(plan["mode"], "rollback_plan")
        self.assertTrue(plan["read_only"])
        self.assertFalse(plan["mutation_allowed"])
        self.assertTrue(plan["owner_scoped"])
        self.assertEqual(plan["candidate_count"], 2)
        self.assertEqual(plan["rollback_candidate_count"], 1)
        self.assertEqual(plan["untouched_candidate_count"], 1)
        self.assertEqual(
            plan["rollback_candidates"][0]["saved_search_id"],
            first.pk,
        )
        self.assertEqual(
            plan["rollback_candidates"][0]["recipient_email"],
            "[redacted]",
        )
        self.assertEqual(plan["untouched_candidates"][0]["saved_search_id"], second.pk)

        for saved_search in (first, second, other):
            saved_search.refresh_from_db()
            self.assertEqual(
                saved_search.last_notification_sent_at,
                before_values[saved_search.pk],
            )

    def test_v224_rollback_plan_lines_are_operator_readable(self):
        plan = {
            "owner_scoped": False,
            "candidate_count": 2,
            "rollback_candidate_count": 1,
            "untouched_candidate_count": 1,
            "rollback_candidates": [
                {
                    "saved_search_id": 9,
                    "owner_id": 4,
                    "recipient_email": "rollback@example.com",
                    "last_notification_sent_at": "2026-07-13T10:00:00+00:00",
                    "label": "Rollback sample",
                }
            ],
        }

        lines = format_saved_search_notification_rollback_plan_lines(plan)

        self.assertIn(
            "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
            lines[0],
        )
        self.assertIn("mode=rollback_plan", lines[0])
        self.assertIn("read_only=True", lines[0])
        self.assertIn("mutation_allowed=False", lines[0])
        self.assertIn("candidates=2", lines[0])
        self.assertIn("rollback_candidates=1", lines[0])
        self.assertIn("ROLLBACK CANDIDATE saved_search", lines[1])
        self.assertIn("recipient=[redacted]", lines[1])
        self.assertNotIn(
            "rollback@example.com",
            lines[1],
        )
        self.assertIn("label=Rollback sample", lines[1])

    def test_v224_rollback_requires_explicit_execute_flag(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v224-blocked-owner",
            email="v224-blocked-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Blocked rollback",
        )
        timestamp = timezone.now()
        saved_search.last_notification_sent_at = timestamp
        saved_search.save(update_fields=["last_notification_sent_at"])

        with self.assertRaisesMessage(
            SavedSearchNotificationRollbackBlocked,
            "execute_rollback=True",
        ):
            rollback_saved_search_notification_sent_timestamp(
                saved_search,
                previous_sent_at=None,
                execute_rollback=False,
            )

        saved_search.refresh_from_db()
        self.assertEqual(saved_search.last_notification_sent_at, timestamp)

    def test_v224_explicit_rollback_restores_sent_timestamp_and_preserves_checked_timestamp(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v224-rollback-owner",
            email="v224-rollback-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Executed rollback",
        )

        checked_at = timezone.now()
        sent_at = timezone.now()
        saved_search.last_notification_checked_at = checked_at
        saved_search.last_notification_sent_at = sent_at
        saved_search.save(update_fields=["last_notification_checked_at", "last_notification_sent_at"])

        result = rollback_saved_search_notification_sent_timestamp(
            saved_search,
            previous_sent_at=None,
            execute_rollback=True,
            operator="tester",
            reason="restore test",
        )

        self.assertEqual(
            result["marker"],
            "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
        )
        self.assertTrue(result["execute_rollback"])
        self.assertTrue(result["rollback_applied"])
        self.assertEqual(result["sent_timestamp_before"], sent_at)
        self.assertIsNone(result["sent_timestamp_after"])
        self.assertEqual(result["checked_timestamp_before"], checked_at)
        self.assertEqual(result["checked_timestamp_after"], checked_at)
        self.assertEqual(result["audit_event"]["action"], "rollback_sent_timestamp")
        self.assertEqual(result["audit_event"]["operator"], "tester")
        self.assertEqual(result["audit_event"]["reason"], "restore test")
        self.assertRegex(result["audit_event"]["audit_fingerprint"], r"^[a-f0-9]{64}$")

        saved_search.refresh_from_db()
        self.assertIsNone(saved_search.last_notification_sent_at)
        self.assertEqual(saved_search.last_notification_checked_at, checked_at)

    def test_v224_management_command_rollback_report_is_read_only(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v224-command-owner",
            email="v224-command-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Command rollback report",
        )
        timestamp = timezone.now()
        saved_search.last_notification_sent_at = timestamp
        saved_search.save(update_fields=["last_notification_sent_at"])

        mail.outbox = []

        stdout = StringIO()
        call_command(
            "process_saved_search_notifications",
            "--notification-rollback-report",
            "--limit",
            "5",
            stdout=stdout,
        )
        output = stdout.getvalue()

        self.assertIn(
            "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
            output,
        )
        self.assertIn("mode=rollback_plan", output)
        self.assertIn("read_only=True", output)
        self.assertIn("mutation_allowed=False", output)
        self.assertIn("rollback_candidates=1", output)
        self.assertIn("recipient=[redacted]", output)
        self.assertNotIn(
            "v224-command-owner@example.com",
            output,
        )
        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertEqual(saved_search.last_notification_sent_at, timestamp)

    def test_v224_default_command_path_still_does_not_print_rollback_report_or_deliver(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v224-default-owner",
            email="v224-default-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Default command no rollback",
        )
        mail.outbox = []

        stdout = StringIO()
        call_command("process_saved_search_notifications", stdout=stdout)
        output = stdout.getvalue()

        self.assertNotIn(
            "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
            output,
        )
        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_v224_command_source_exposes_rollback_report_without_delivery_terms(self):
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )

        self.assertIn("--notification-rollback-report", command_source)
        self.assertIn("notification_rollback_report", command_source)
        self.assertIn("build_saved_search_notification_rollback_plan", command_source)
        self.assertIn("format_saved_search_notification_rollback_plan_lines", command_source)

        forbidden_terms = (
            "send_" + "mail",
            "Email" + "Message",
            "Email" + "MultiAlternatives",
            "mail_" + "admins",
            "mail_" + "managers",
            "." + "send(",
            "last_notification_sent_at" + " =",
            "last_notification_sent_at=",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, command_source)

    def test_v224_audit_source_avoids_delivery_and_background_process_terms(self):
        audit_source = self._read_backend("listings/saved_search_notification_audit.py")
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )
        observability_source = self._read_backend("listings/saved_search_notification_observability.py")
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

        for source in (audit_source, command_source, observability_source, scheduler_source):
            for term in forbidden_delivery_terms:
                self.assertNotIn(term, source)

        combined = (
            audit_source
            + "\n"
            + command_source
            + "\n"
            + observability_source
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

    def test_v224_does_not_patch_unrelated_runtime_or_template_surfaces(self):
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
                "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING",
                self._read_backend(relative_path),
                f"v224 marker should not patch unrelated surface {relative_path}",
            )

    def test_v224_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
            "listings/test_saved_search_notification_admin_operator_observability_v223.py": (
                "V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY"
            ),
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
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read_backend(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
