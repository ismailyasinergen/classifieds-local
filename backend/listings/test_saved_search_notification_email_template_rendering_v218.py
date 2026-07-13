from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from listings.models import SavedSearch
from listings.saved_search_notification_email_renderer import (
    V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING,
    SavedSearchNotificationEmailRenderResult,
    build_saved_search_notification_email_context,
    render_saved_search_notification_email,
)


class SavedSearchNotificationEmailTemplateRenderingV218Tests(TestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _saved_search_defaults(self, user, *, enabled: bool, name: str) -> dict:
        fields = {field.name: field for field in SavedSearch._meta.fields}
        data = {"user": user}

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

    def test_v218_marker_is_declared_for_email_template_rendering(self):
        self.assertEqual(
            V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING,
            "V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING",
        )

    def test_v218_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v218_renderer_and_templates_are_packaged(self):
        required_paths = (
            "listings/saved_search_notification_email_renderer.py",
            "listings/templates/listings/email/saved_search_notification.txt",
            "listings/templates/listings/email/saved_search_notification.html",
        )

        for relative_path in required_paths:
            self.assertTrue(
                (self._backend_root() / relative_path).is_file(),
                f"v218 renderer/template file should be packaged: {relative_path}",
            )

    def test_v218_rendering_context_is_owner_scoped_and_opt_in_only(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v218-owner",
            email="v218-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v218-other",
            email="v218-other@example.com",
            password="password",
        )

        enabled = self._create_saved_search(owner, enabled=True, name="Furniture alerts")
        self._create_saved_search(owner, enabled=False, name="Disabled alerts")
        self._create_saved_search(other_owner, enabled=True, name="Other alerts")

        context = build_saved_search_notification_email_context(
            enabled,
            match_count=4,
            site_url="https://example.test",
            manage_path="/listings/saved-searches/",
        )

        self.assertEqual(context["recipient_email"], "v218-owner@example.com")
        self.assertEqual(context["recipient_username"], "v218-owner")
        self.assertEqual(context["saved_search_id"], enabled.pk)
        self.assertEqual(context["saved_search_name"], "Furniture alerts")
        self.assertEqual(context["match_count"], 4)
        self.assertEqual(context["match_label"], "matches")
        self.assertEqual(
            context["manage_url"],
            "https://example.test/listings/saved-searches/",
        )
        self.assertIn(
            "Manage saved-search email notifications",
            context["unsubscribe_guidance"],
        )

        owner_opt_in = SavedSearch.objects.filter(
            user=owner,
            email_notifications_enabled=True,
        )
        self.assertEqual(list(owner_opt_in), [enabled])

    def test_v218_renderer_returns_subject_text_html_and_context_without_mutation(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v218-render-owner",
            email="v218-render-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Oak cabinet alerts",
        )

        before_checked = getattr(saved_search, "last_notification_checked_at", None)
        before_sent = getattr(saved_search, "last_notification_sent_at", None)

        result = render_saved_search_notification_email(
            saved_search,
            match_count=2,
            matching_listings=(
                {
                    "title": "Oak record cabinet",
                    "url": "/listings/oak-record-cabinet/",
                    "price": "€240",
                },
            ),
            site_url="https://example.test",
            manage_path="/listings/saved-searches/",
        )

        self.assertIsInstance(result, SavedSearchNotificationEmailRenderResult)
        self.assertEqual(
            result.subject,
            "New matches for your saved search: Oak cabinet alerts",
        )
        self.assertIn("Hello v218-render-owner", result.text_body)
        self.assertIn("2 new matches", result.text_body)
        self.assertIn("Oak record cabinet", result.text_body)
        self.assertIn("https://example.test/listings/oak-record-cabinet/", result.text_body)
        self.assertIn("Manage this saved search alert", result.html_body)
        self.assertIn("Oak record cabinet", result.html_body)
        self.assertEqual(result.context["recipient_email"], "v218-render-owner@example.com")

        saved_search.refresh_from_db()
        self.assertEqual(
            getattr(saved_search, "last_notification_checked_at", None),
            before_checked,
        )
        self.assertEqual(
            getattr(saved_search, "last_notification_sent_at", None),
            before_sent,
        )

    def test_v218_renderer_refuses_disabled_saved_searches(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v218-disabled-owner",
            email="v218-disabled-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=False,
            name="Disabled alerts",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Saved search email notifications are disabled.",
        ):
            render_saved_search_notification_email(saved_search, match_count=1)

    def test_v218_html_template_escapes_saved_search_name(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v218-escape-owner",
            email="v218-escape-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="<script>alert(1)</script>",
        )

        result = render_saved_search_notification_email(
            saved_search,
            match_count=1,
            manage_path="/listings/saved-searches/",
        )

        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", result.html_body)
        self.assertNotIn("<script>alert(1)</script>", result.html_body)
        self.assertIn("1 new match", result.text_body)

    def test_v218_rendering_source_and_templates_do_not_deliver_email(self):
        renderer_source = self._read("listings/saved_search_notification_email_renderer.py")
        text_template = self._read("listings/templates/listings/email/saved_search_notification.txt")
        html_template = self._read("listings/templates/listings/email/saved_search_notification.html")
        combined = renderer_source + "\n" + text_template + "\n" + html_template

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
            self.assertNotIn(term, combined)

    def test_v218_does_not_patch_scheduler_command_models_or_existing_templates(self):
        untouched_surfaces = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/management/commands/process_saved_search_notifications.py",
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
                "V218_SAVED_SEARCH_NOTIFICATION_EMAIL_TEMPLATE_RENDERING",
                self._read(relative_path),
                f"v218 marker should not patch existing surface {relative_path}",
            )

    def test_v218_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "accounts/tests/test_seller_store_admin_action_safety_v212.py": (
                "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
