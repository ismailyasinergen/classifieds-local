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

from listings.models import SavedSearch
from listings.saved_search_notification_scheduler import (
    V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION,
    build_saved_search_notification_email_dry_run_preview,
    build_saved_search_notification_scheduler_email_previews,
)


class SavedSearchNotificationSchedulerEmailDryRunIntegrationV221Tests(TestCase):
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
            data["querystring"] = "q=oak&sort=newest"
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

    def test_v221_marker_is_declared_for_scheduler_email_dry_run_integration(self):
        self.assertEqual(
            V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION,
            "V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION",
        )

    def test_v221_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v221_saved_search_model_still_has_notification_fields_without_migrations(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v221_scheduler_builds_email_preview_without_delivery_or_timestamp_mutation(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v221-owner",
            email="v221-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="V221 oak alerts",
        )

        before_checked = getattr(saved_search, "last_notification_checked_at", None)
        before_sent = getattr(saved_search, "last_notification_sent_at", None)
        mail.outbox = []

        preview = build_saved_search_notification_email_dry_run_preview(
            saved_search,
            match_count=2,
            matching_listings=(
                {
                    "title": "V221 oak cabinet",
                    "url": "/listings/v221-oak-cabinet/",
                    "price": "€410",
                },
            ),
            site_url="https://example.test",
            manage_path="/listings/saved-searches/",
        )

        self.assertEqual(
            preview["marker"],
            "V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION",
        )
        self.assertEqual(preview["mode"], "dry_run")
        self.assertTrue(preview["dry_run"])
        self.assertFalse(preview["would_send"])
        self.assertFalse(preview["delivery_enabled"])
        self.assertTrue(preview["requires_explicit_execute"])
        self.assertEqual(preview["recipient_email"], "v221-owner@example.com")
        self.assertEqual(
            preview["subject"],
            "New matches for your saved search: V221 oak alerts",
        )
        self.assertIn("2 new matches", preview["text_body"])
        self.assertIn("V221 oak cabinet", preview["html_body"])
        self.assertFalse(preview["checked_timestamp_mutation_allowed"])
        self.assertFalse(preview["sent_timestamp_mutation_allowed"])
        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertEqual(
            getattr(saved_search, "last_notification_checked_at", None),
            before_checked,
        )
        self.assertEqual(
            getattr(saved_search, "last_notification_sent_at", None),
            before_sent,
        )

    def test_v221_scheduler_preview_queryset_is_owner_scoped_opt_in_only_and_limited(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v221-scope-owner",
            email="v221-scope-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v221-scope-other",
            email="v221-scope-other@example.com",
            password="password",
        )

        first = self._create_saved_search(owner, enabled=True, name="First alert")
        second = self._create_saved_search(owner, enabled=True, name="Second alert")
        self._create_saved_search(owner, enabled=False, name="Disabled alert")
        self._create_saved_search(other_owner, enabled=True, name="Other alert")

        previews = build_saved_search_notification_scheduler_email_previews(
            owner=owner,
            limit=1,
            match_count=1,
            site_url="https://example.test",
            manage_path="/listings/saved-searches/",
        )

        self.assertEqual(len(previews), 1)
        self.assertEqual(previews[0]["saved_search_id"], first.pk)
        self.assertEqual(previews[0]["recipient_email"], "v221-scope-owner@example.com")

        list_previews = build_saved_search_notification_scheduler_email_previews(
            saved_searches=[first, second],
            limit=5,
            match_count=1,
        )

        self.assertEqual(
            [preview["saved_search_id"] for preview in list_previews],
            [first.pk, second.pk],
        )

    def test_v221_disabled_saved_search_is_rejected_by_single_preview_builder(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v221-disabled-owner",
            email="v221-disabled-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=False,
            name="Disabled v221 alert",
        )
        mail.outbox = []

        with self.assertRaisesMessage(
            ValueError,
            "Saved search email notifications are disabled.",
        ):
            build_saved_search_notification_email_dry_run_preview(
                saved_search,
                match_count=1,
            )

        self.assertEqual(len(mail.outbox), 0)

    def test_v221_management_command_exposes_explicit_preview_flag_only(self):
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )

        self.assertIn("--render-email-previews", command_source)
        self.assertIn("render_email_previews", command_source)
        self.assertIn(
            "V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION",
            command_source,
        )
        self.assertIn("dry_run=True", command_source)
        self.assertIn("delivery_enabled=False", command_source)
        self.assertIn("sent=0", command_source)
        self.assertIn("DRY RUN email preview", command_source)

    def test_v221_management_command_preview_flag_does_not_deliver_or_mutate(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v221-command-owner",
            email="v221-command-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Command preview alert",
        )

        before_checked = getattr(saved_search, "last_notification_checked_at", None)
        before_sent = getattr(saved_search, "last_notification_sent_at", None)
        mail.outbox = []

        stdout = StringIO()
        call_command("process_saved_search_notifications", "--render-email-previews", stdout=stdout)
        output = stdout.getvalue()

        self.assertIn(
            "V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION",
            output,
        )
        self.assertIn("dry_run=True", output)
        self.assertIn("delivery_enabled=False", output)
        self.assertIn("sent=0", output)
        self.assertIn("DRY RUN email preview", output)
        self.assertIn("recipient=[redacted]", output)
        self.assertNotIn(
            "v221-command-owner@example.com",
            output,
        )
        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertEqual(
            getattr(saved_search, "last_notification_checked_at", None),
            before_checked,
        )
        self.assertEqual(
            getattr(saved_search, "last_notification_sent_at", None),
            before_sent,
        )

    def test_v221_default_command_path_still_does_not_enable_preview_or_delivery(self):
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )

        self.assertIn("does not send email", command_source)

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

    def test_v221_runtime_surfaces_contain_no_delivery_implementation_terms(self):
        runtime_paths = (
            "listings/saved_search_notification_scheduler.py",
            "listings/management/commands/process_saved_search_notifications.py",
            "listings/saved_search_notification_email_renderer.py",
            "listings/templates/listings/email/saved_search_notification.txt",
            "listings/templates/listings/email/saved_search_notification.html",
        )
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

        for relative_path in runtime_paths:
            source = self._read_backend(relative_path)
            for term in forbidden_terms:
                self.assertNotIn(term, source, f"{term} leaked into {relative_path}")

    def test_v221_no_uncontrolled_sender_module_or_background_worker_was_added(self):
        sender_path = self._backend_root() / "listings/saved_search_notification_email_sender.py"
        if sender_path.exists():
            sender_source = sender_path.read_text(encoding="utf-8", errors="ignore")
            self.assertIn(
                "V222_SAVED_SEARCH_NOTIFICATION_" "EXPLICIT_SEND_TEST_BACKEND",
                sender_source,
            )
            self.assertIn("require_test_email_backend", sender_source)
            self.assertIn("execute_send", sender_source)
        else:
            self.assertFalse(sender_path.exists())

        dockerfile = self._read_backend("Dockerfile")
        scheduler_source = self._read_backend("listings/saved_search_notification_scheduler.py")
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )
        combined = dockerfile + "\n" + scheduler_source + "\n" + command_source

        forbidden_worker_terms = (
            "celery",
            "beat",
            "rq",
            "huey",
            "apscheduler",
            "crontab",
            "cron:",
            "worker:",
        )

        for term in forbidden_worker_terms:
            self.assertNotIn(term, combined.lower())

    def test_v221_does_not_patch_unrelated_runtime_or_template_surfaces(self):
        untouched_surfaces = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
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
                "V221_SAVED_SEARCH_NOTIFICATION_SCHEDULER_EMAIL_DRY_RUN_INTEGRATION",
                self._read_backend(relative_path),
                f"v221 marker should not patch unrelated surface {relative_path}",
            )

    def test_v221_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_local_release_restore_rehearsal_audit_v216.py": (
                "V216_LOCAL_RELEASE_RESTORE_REHEARSAL_AUDIT"
            ),
            "accounts/tests/test_seller_store_admin_action_implementation_v215.py": (
                "V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read_backend(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
