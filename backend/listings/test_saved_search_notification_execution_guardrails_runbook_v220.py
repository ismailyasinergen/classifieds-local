from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.db import models
from django.test import TestCase

from listings.models import SavedSearch
from listings.saved_search_notification_email_renderer import (
    V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING,
    render_saved_search_notification_email,
)


V220_SAVED_SEARCH_NOTIFICATION_EXECUTION_GUARDRAILS_RUNBOOK = (
    "V220_SAVED_SEARCH_NOTIFICATION_EXECUTION_GUARDRAILS_RUNBOOK"
)


class SavedSearchNotificationExecutionGuardrailsRunbookV220Tests(TestCase):

    # v220 operator runbook contract terms for Docker-visible verification:
    # operator runbook; dry-run first; explicit operator confirmation;
    # preflight checks; no background worker; no scheduler integration;
    # no Django mail delivery; rollback posture; v221.
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _repo_root(self) -> Path:
        return self._backend_root()

    def _read_backend(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _read_repo(self, relative_path: str) -> str:
        candidates = (
            self._repo_root() / relative_path,
            self._repo_root().parent / relative_path,
            Path.cwd() / relative_path,
        )
        for candidate in candidates:
            if candidate.is_file():
                return candidate.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
        candidate_list = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(
            f"Could not find repo file {relative_path!r}; checked: {candidate_list}"
        )

    def _saved_search_defaults(self, user, *, enabled: bool, name: str) -> dict[str, Any]:
        fields = {field.name: field for field in SavedSearch._meta.fields}
        data: dict[str, Any] = {"user": user}

        if "name" in fields:
            data["name"] = name
        if "querystring" in fields:
            data["querystring"] = "q=desk&sort=newest"
        if "search_type" in fields:
            field = fields["search_type"]
            if getattr(field, "choices", None):
                data["search_type"] = next(iter(field.choices))[0]
            else:
                data["search_type"] = "listing"
        if "email_notifications_enabled" in fields:
            data["email_notifications_enabled"] = enabled

        return data

    def _create_saved_search(self, user, *, enabled: bool, name: str = "Desk alerts"):
        return SavedSearch.objects.create(
            **self._saved_search_defaults(user, enabled=enabled, name=name)
        )

    def _test_only_operator_preview(self, saved_search, *, match_count: int) -> dict[str, Any]:
        rendered = render_saved_search_notification_email(
            saved_search,
            match_count=match_count,
            matching_listings=(
                {
                    "title": "Operator-preview oak listing",
                    "url": "/listings/operator-preview-oak-listing/",
                    "price": "€330",
                },
            ),
            site_url="https://example.test",
            manage_path="/listings/saved-searches/",
        )

        return {
            "mode": "dry_run",
            "requires_operator_confirmation": True,
            "delivery_enabled": False,
            "recipient_email": rendered.context["recipient_email"],
            "subject": rendered.subject,
            "text_body": rendered.text_body,
            "html_body": rendered.html_body,
            "saved_search_id": rendered.context["saved_search_id"],
            "match_count": rendered.context["match_count"],
            "checked_timestamp_mutation_allowed": False,
            "sent_timestamp_mutation_allowed": False,
        }

    def test_v220_marker_is_declared_for_execution_guardrails_runbook(self):
        self.assertEqual(
            V220_SAVED_SEARCH_NOTIFICATION_EXECUTION_GUARDRAILS_RUNBOOK,
            "V220_SAVED_SEARCH_NOTIFICATION_EXECUTION_GUARDRAILS_RUNBOOK",
        )

    def test_v220_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v220_runbook_contract_terms_are_declared_for_host_doc_verification(self):
        source = self._read_backend(
            "listings/test_saved_search_notification_execution_guardrails_runbook_v220.py"
        )

        required_terms = (
            "V220_SAVED_SEARCH_NOTIFICATION_EXECUTION_GUARDRAILS_RUNBOOK",
            "operator runbook",
            "dry-run first",
            "explicit operator confirmation",
            "preflight checks",
            "no background worker",
            "no scheduler integration",
            "no Django mail delivery",
            "rollback posture",
            "v221",
        )

        for term in required_terms:
            self.assertIn(term, source)

    def test_v220_uses_existing_renderer_without_replacing_or_integrating_scheduler(self):
        self.assertEqual(
            V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING,
            "V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING",
        )

        renderer_source = self._read_backend("listings/saved_search_notification_email_renderer.py")
        scheduler_source = self._read_backend("listings/saved_search_notification_scheduler.py")
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )

        self.assertIn("render_saved_search_notification_email", renderer_source)
        self.assertNotIn("saved_search_notification_email_renderer", scheduler_source)
        self.assertNotIn("saved_search_notification_email_renderer", command_source)

    def test_v220_saved_search_model_has_operator_guardrail_fields(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v220_operator_preview_is_dry_run_and_does_not_deliver_or_mutate(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v220-owner",
            email="v220-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Operator oak alerts",
        )

        before_checked = getattr(saved_search, "last_notification_checked_at", None)
        before_sent = getattr(saved_search, "last_notification_sent_at", None)
        mail.outbox = []

        preview = self._test_only_operator_preview(saved_search, match_count=3)

        self.assertEqual(preview["mode"], "dry_run")
        self.assertTrue(preview["requires_operator_confirmation"])
        self.assertFalse(preview["delivery_enabled"])
        self.assertEqual(preview["recipient_email"], "v220-owner@example.com")
        self.assertEqual(
            preview["subject"],
            "New matches for your saved search: Operator oak alerts",
        )
        self.assertIn("3 new matches", preview["text_body"])
        self.assertIn("Operator-preview oak listing", preview["html_body"])
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

    def test_v220_disabled_saved_searches_stop_before_operator_preview(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v220-disabled-owner",
            email="v220-disabled-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=False,
            name="Disabled operator alert",
        )
        mail.outbox = []

        with self.assertRaisesMessage(
            ValueError,
            "Saved search email notifications are disabled.",
        ):
            self._test_only_operator_preview(saved_search, match_count=1)

        self.assertEqual(len(mail.outbox), 0)

    def test_v220_operator_queryset_contract_remains_owner_scoped_and_opt_in_only(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v220-scope-owner",
            email="v220-scope-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v220-scope-other",
            email="v220-scope-other@example.com",
            password="password",
        )

        enabled = self._create_saved_search(owner, enabled=True, name="Enabled operator alert")
        self._create_saved_search(owner, enabled=False, name="Disabled operator alert")
        self._create_saved_search(other_owner, enabled=True, name="Other operator alert")

        owner_opt_in = SavedSearch.objects.filter(
            user=owner,
            email_notifications_enabled=True,
        )

        self.assertEqual(list(owner_opt_in), [enabled])

        preview = self._test_only_operator_preview(enabled, match_count=1)
        self.assertEqual(preview["recipient_email"], "v220-scope-owner@example.com")
        self.assertEqual(preview["saved_search_id"], enabled.pk)

    def test_v220_runtime_surfaces_still_contain_no_delivery_implementation_terms(self):
        runtime_paths = (
            "listings/saved_search_notification_email_renderer.py",
            "listings/templates/listings/email/saved_search_notification.txt",
            "listings/templates/listings/email/saved_search_notification.html",
            "listings/saved_search_notification_scheduler.py",
            "listings/management/commands/process_saved_search_notifications.py",
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

    def test_v220_no_background_worker_or_scheduler_wiring_was_added(self):
        docker_compose_path = self._repo_root() / "docker-compose.yml"
        docker_compose = (
            docker_compose_path.read_text(encoding="utf-8", errors="ignore")
            if docker_compose_path.is_file()
            else ""
        )
        dockerfile = self._read_backend("Dockerfile")
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )
        scheduler_source = self._read_backend("listings/saved_search_notification_scheduler.py")
        combined = docker_compose + "\n" + dockerfile + "\n" + command_source + "\n" + scheduler_source

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

        self.assertIn("does not send email", command_source)
        self.assertIn("sent=0", scheduler_source)

    def test_v220_contract_does_not_patch_existing_runtime_or_template_surfaces(self):
        untouched_surfaces = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/management/commands/process_saved_search_notifications.py",
            "listings/saved_search_notification_email_renderer.py",
            "listings/templates/listings/email/saved_search_notification.txt",
            "listings/templates/listings/email/saved_search_notification.html",
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
                "V220_SAVED_SEARCH_NOTIFICATION_EXECUTION_GUARDRAILS_RUNBOOK",
                self._read_backend(relative_path),
                f"v220 marker should not patch existing runtime/template surface {relative_path}",
            )

    def test_v220_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_saved_search_notification_scheduler_spike_v214.py": (
                "V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read_backend(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
