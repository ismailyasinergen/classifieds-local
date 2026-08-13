from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import Any

from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.db import models
from django.test import SimpleTestCase, TestCase, override_settings

from listings.models import SavedSearch
from listings.saved_search_notification_email_sender import (
    V222_LOC_MEM_TEST_EMAIL_BACKEND,
    V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND,
    SavedSearchNotificationEmailDeliveryBlocked,
    saved_search_notification_email_backend_is_test_safe,
    send_saved_search_notification_email,
    send_saved_search_notification_email_batch,
)


class SavedSearchNotificationExplicitSendTestBackendV222SimpleTests(SimpleTestCase):
    @patch("listings.saved_search_notification_email_sender.get_saved_search_notification_email_backend_path")
    def test_v222_detects_locmem_test_email_backend_as_safe_with_mock(self, mock_get_path):
        mock_get_path.return_value = V222_LOC_MEM_TEST_EMAIL_BACKEND
        self.assertTrue(saved_search_notification_email_backend_is_test_safe())

    @patch("listings.saved_search_notification_email_sender.get_saved_search_notification_email_backend_path")
    def test_v222_rejects_non_locmem_backend_as_unsafe_with_mock(self, mock_get_path):
        mock_get_path.return_value = "django.core.mail.backends.console.EmailBackend"
        self.assertFalse(saved_search_notification_email_backend_is_test_safe())

class SavedSearchNotificationExplicitSendTestBackendV222Tests(TestCase):
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
            data["querystring"] = "q=walnut&sort=newest"
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

    def test_v222_marker_is_declared_for_explicit_send_test_backend(self):
        self.assertEqual(
            V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND,
            "V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND",
        )

    def test_v222_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v222_saved_search_model_still_has_notification_fields_without_migrations(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_v222_detects_locmem_test_email_backend_as_safe(self):
        self.assertEqual(settings.EMAIL_BACKEND, V222_LOC_MEM_TEST_EMAIL_BACKEND)
        self.assertTrue(saved_search_notification_email_backend_is_test_safe())

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_v222_rejects_non_locmem_backend_before_delivery(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v222-console-owner",
            email="v222-console-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Console backend blocked",
        )
        mail.outbox = []

        with self.assertRaisesMessage(
            SavedSearchNotificationEmailDeliveryBlocked,
            "locmem test email backend",
        ):
            send_saved_search_notification_email(
                saved_search,
                match_count=1,
                execute_send=True,
                require_test_email_backend=True,
            )

        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertIsNone(getattr(saved_search, "last_notification_sent_at", None))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_v222_refuses_send_without_explicit_execute_flag(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v222-no-execute-owner",
            email="v222-no-execute-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="No execute flag",
        )
        mail.outbox = []

        with self.assertRaisesMessage(
            SavedSearchNotificationEmailDeliveryBlocked,
            "execute_send=True",
        ):
            send_saved_search_notification_email(
                saved_search,
                match_count=1,
                execute_send=False,
            )

        self.assertEqual(len(mail.outbox), 0)
        saved_search.refresh_from_db()
        self.assertIsNone(getattr(saved_search, "last_notification_sent_at", None))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_v222_explicit_send_delivers_to_locmem_and_updates_sent_timestamp_only(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v222-owner",
            email="v222-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="V222 walnut alerts",
        )

        before_checked = getattr(saved_search, "last_notification_checked_at", None)
        before_sent = getattr(saved_search, "last_notification_sent_at", None)
        mail.outbox = []

        result = send_saved_search_notification_email(
            saved_search,
            match_count=2,
            matching_listings=(
                {
                    "title": "V222 walnut cabinet",
                    "url": "/listings/v222-walnut-cabinet/",
                    "price": "€430",
                },
            ),
            site_url="https://example.test",
            manage_path="/listings/saved-searches/",
            execute_send=True,
            require_test_email_backend=True,
        )

        self.assertEqual(
            result["marker"],
            "V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND",
        )
        self.assertTrue(result["execute_send"])
        self.assertTrue(result["delivery_enabled"])
        self.assertEqual(result["delivered_count"], 1)
        self.assertEqual(result["recipient_email"], "v222-owner@example.com")
        self.assertEqual(
            result["subject"],
            "New matches for your saved search: V222 walnut alerts",
        )
        self.assertEqual(result["sent_timestamp_before"], before_sent)
        self.assertEqual(result["checked_timestamp_before"], before_checked)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["v222-owner@example.com"])
        self.assertIn("2 new matches", mail.outbox[0].body)
        self.assertIn("V222 walnut cabinet", mail.outbox[0].alternatives[0][0])

        saved_search.refresh_from_db()
        self.assertEqual(
            getattr(saved_search, "last_notification_checked_at", None),
            before_checked,
        )
        self.assertIsNotNone(getattr(saved_search, "last_notification_sent_at", None))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_v222_disabled_saved_search_is_rejected_before_delivery(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v222-disabled-owner",
            email="v222-disabled-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=False,
            name="Disabled v222 alert",
        )
        mail.outbox = []

        with self.assertRaisesMessage(
            ValueError,
            "Saved search email notifications are disabled.",
        ):
            send_saved_search_notification_email(
                saved_search,
                match_count=1,
                execute_send=True,
                require_test_email_backend=True,
            )

        self.assertEqual(len(mail.outbox), 0)
        saved_search.refresh_from_db()
        self.assertIsNone(getattr(saved_search, "last_notification_sent_at", None))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_v222_batch_send_is_owner_scoped_opt_in_only_and_limited(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v222-batch-owner",
            email="v222-batch-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v222-batch-other",
            email="v222-batch-other@example.com",
            password="password",
        )

        first = self._create_saved_search(owner, enabled=True, name="First batch")
        self._create_saved_search(owner, enabled=True, name="Second batch")
        self._create_saved_search(owner, enabled=False, name="Disabled batch")
        self._create_saved_search(other_owner, enabled=True, name="Other batch")
        mail.outbox = []

        result = send_saved_search_notification_email_batch(
            owner=owner,
            limit=1,
            match_count=1,
            execute_send=True,
            require_test_email_backend=True,
        )

        self.assertEqual(result["attempted_count"], 1)
        self.assertEqual(result["delivered_count"], 1)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["saved_search_id"], first.pk)
        self.assertEqual(result["results"][0]["recipient_email"], "v222-batch-owner@example.com")
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_v222_management_command_explicit_send_flag_delivers_with_test_backend(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v222-command-owner",
            email="v222-command-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Command explicit delivery",
        )
        before_checked = getattr(saved_search, "last_notification_checked_at", None)
        mail.outbox = []

        stdout = StringIO()
        call_command("process_saved_search_notifications", "--execute-email-send", "--limit", "1", stdout=stdout)
        output = stdout.getvalue()

        self.assertIn(
            "V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND",
            output,
        )
        self.assertIn("execute_send=True", output)
        self.assertIn("delivery_enabled=True", output)
        self.assertIn("attempted=1", output)
        self.assertIn("delivered=1", output)
        self.assertIn("recipient=[redacted]", output)
        self.assertNotIn(
            "v222-command-owner@example.com",
            output,
        )
        self.assertEqual(len(mail.outbox), 1)

        saved_search.refresh_from_db()
        self.assertEqual(
            getattr(saved_search, "last_notification_checked_at", None),
            before_checked,
        )
        self.assertIsNotNone(getattr(saved_search, "last_notification_sent_at", None))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_v222_default_command_path_still_does_not_deliver(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v222-default-command-owner",
            email="v222-default-command-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Default command no delivery",
        )
        mail.outbox = []

        stdout = StringIO()
        call_command("process_saved_search_notifications", stdout=stdout)
        output = stdout.getvalue()

        self.assertNotIn(
            "V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND",
            output,
        )
        self.assertEqual(len(mail.outbox), 0)

        saved_search.refresh_from_db()
        self.assertIsNone(getattr(saved_search, "last_notification_sent_at", None))

    def test_v222_source_avoids_unsafe_delivery_helpers_and_background_workers(self):
        sender_source = self._read_backend("listings/saved_search_notification_email_sender.py")
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )
        scheduler_source = self._read_backend("listings/saved_search_notification_scheduler.py")
        dockerfile = self._read_backend("Dockerfile")

        forbidden_source_terms = (
            "send_" + "mail",
            "Email" + "Message",
            "Email" + "MultiAlternatives",
            "mail_" + "admins",
            "mail_" + "managers",
            "." + "send(",
            "last_notification_sent_at" + " =",
            "last_notification_sent_at" + "=",
        )

        for source in (sender_source, command_source, scheduler_source):
            for term in forbidden_source_terms:
                self.assertNotIn(term, source)

        combined = sender_source + "\n" + command_source + "\n" + scheduler_source + "\n" + dockerfile
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

    def test_v222_does_not_patch_unrelated_runtime_or_template_surfaces(self):
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
                "V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND",
                self._read_backend(relative_path),
                f"v222 marker should not patch unrelated surface {relative_path}",
            )

    def test_v222_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_local_release_restore_rehearsal_audit_v216.py": (
                "V216_LOCAL_RELEASE_RESTORE_REHEARSAL_AUDIT"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read_backend(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
