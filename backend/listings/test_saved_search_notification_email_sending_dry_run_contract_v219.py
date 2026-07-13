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


V219_SAVED_SEARCH_NOTIFICATION_EMAIL_SENDING_DRY_RUN_CONTRACT = (
    "V219_SAVED_SEARCH_NOTIFICATION_EMAIL_SENDING_DRY_RUN_CONTRACT"
)


class SavedSearchNotificationEmailSendingDryRunContractV219Tests(TestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
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

    def _test_only_dry_run_preview(self, saved_search, *, match_count: int) -> dict[str, Any]:
        rendered = render_saved_search_notification_email(
            saved_search,
            match_count=match_count,
            matching_listings=(
                {
                    "title": "Dry-run oak listing",
                    "url": "/listings/dry-run-oak-listing/",
                    "price": "€300",
                },
            ),
            site_url="https://example.test",
            manage_path="/listings/saved-searches/",
        )

        return {
            "dry_run": True,
            "would_send": False,
            "send_gate": "requires explicit future execute flag",
            "recipient_email": rendered.context["recipient_email"],
            "subject": rendered.subject,
            "text_body": rendered.text_body,
            "html_body": rendered.html_body,
            "saved_search_id": rendered.context["saved_search_id"],
            "match_count": rendered.context["match_count"],
        }

    def test_v219_marker_is_declared_for_email_sending_dry_run_contract(self):
        self.assertEqual(
            V219_SAVED_SEARCH_NOTIFICATION_EMAIL_SENDING_DRY_RUN_CONTRACT,
            "V219_SAVED_SEARCH_NOTIFICATION_EMAIL_SENDING_DRY_RUN_CONTRACT",
        )

    def test_v219_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v219_uses_v218_renderer_without_replacing_it(self):
        self.assertEqual(
            V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING,
            "V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING",
        )

        renderer_source = self._read("listings/saved_search_notification_email_renderer.py")
        self.assertIn("render_saved_search_notification_email", renderer_source)
        self.assertIn("SavedSearchNotificationEmailRenderResult", renderer_source)
        self.assertIn("build_saved_search_notification_email_context", renderer_source)

    def test_v219_saved_search_model_has_sending_contract_ready_fields(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v219_dry_run_preview_renders_email_without_delivery_or_mutation(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v219-owner",
            email="v219-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Oak storage alerts",
        )

        before_checked = getattr(saved_search, "last_notification_checked_at", None)
        before_sent = getattr(saved_search, "last_notification_sent_at", None)
        mail.outbox = []

        preview = self._test_only_dry_run_preview(saved_search, match_count=2)

        self.assertTrue(preview["dry_run"])
        self.assertFalse(preview["would_send"])
        self.assertEqual(preview["recipient_email"], "v219-owner@example.com")
        self.assertEqual(
            preview["subject"],
            "New matches for your saved search: Oak storage alerts",
        )
        self.assertIn("2 new matches", preview["text_body"])
        self.assertIn("Dry-run oak listing", preview["html_body"])
        self.assertEqual(preview["match_count"], 2)
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

    def test_v219_disabled_saved_searches_are_rejected_before_any_delivery_step(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v219-disabled-owner",
            email="v219-disabled-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=False,
            name="Disabled dry-run alerts",
        )
        mail.outbox = []

        with self.assertRaisesMessage(
            ValueError,
            "Saved search email notifications are disabled.",
        ):
            self._test_only_dry_run_preview(saved_search, match_count=1)

        self.assertEqual(len(mail.outbox), 0)

    def test_v219_dry_run_contract_is_owner_scoped_and_opt_in_only(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v219-scope-owner",
            email="v219-scope-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v219-scope-other",
            email="v219-scope-other@example.com",
            password="password",
        )

        enabled = self._create_saved_search(owner, enabled=True, name="Enabled alert")
        self._create_saved_search(owner, enabled=False, name="Disabled alert")
        self._create_saved_search(other_owner, enabled=True, name="Other alert")

        owner_opt_in = SavedSearch.objects.filter(
            user=owner,
            email_notifications_enabled=True,
        )

        self.assertEqual(list(owner_opt_in), [enabled])

        preview = self._test_only_dry_run_preview(enabled, match_count=1)
        self.assertEqual(preview["recipient_email"], "v219-scope-owner@example.com")
        self.assertEqual(preview["saved_search_id"], enabled.pk)

    def test_v219_scheduler_and_command_remain_non_delivery_dry_run_surfaces(self):
        scheduler_source = self._read("listings/saved_search_notification_scheduler.py")
        command_source = self._read("listings/management/commands/process_saved_search_notifications.py")
        combined_source = scheduler_source + "\n" + command_source

        self.assertIn("sent=0", scheduler_source)
        self.assertIn("last_notification_checked_at", scheduler_source)
        self.assertIn("does not send email", command_source)
        self.assertNotIn("saved_search_notification_email_renderer", combined_source)

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
            self.assertNotIn(term, combined_source)

    def test_v219_renderer_and_templates_still_contain_no_delivery_implementation(self):
        renderer_source = self._read("listings/saved_search_notification_email_renderer.py")
        text_template = self._read("listings/templates/listings/email/saved_search_notification.txt")
        html_template = self._read("listings/templates/listings/email/saved_search_notification.html")
        combined_source = renderer_source + "\n" + text_template + "\n" + html_template

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
            self.assertNotIn(term, combined_source)

    def test_v219_contract_does_not_patch_runtime_templates_or_existing_surfaces(self):
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
                "V219_SAVED_SEARCH_NOTIFICATION_EMAIL_SENDING_DRY_RUN_CONTRACT",
                self._read(relative_path),
                f"v219 marker should not patch existing runtime/template surface {relative_path}",
            )

    def test_v219_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_local_release_archive_export_dry_run_v213.py": (
                "V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
