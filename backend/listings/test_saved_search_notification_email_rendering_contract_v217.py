from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from listings.models import SavedSearch


V217_SAVED_SEARCH_NOTIFICATION_EMAIL_RENDERING_CONTRACT = (
    "V217_SAVED_SEARCH_NOTIFICATION_EMAIL_RENDERING_CONTRACT"
)


class SavedSearchNotificationEmailRenderingContractV217Tests(TestCase):
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

    def _test_only_rendering_contract_context(self, saved_search, *, match_count: int) -> dict:
        owner = saved_search.user
        return {
            "recipient_email": owner.email,
            "recipient_username": owner.get_username(),
            "saved_search_id": saved_search.pk,
            "saved_search_name": getattr(saved_search, "name", ""),
            "saved_search_querystring": getattr(saved_search, "querystring", ""),
            "match_count": match_count,
            "subject_prefix": "New matches for your saved search",
            "manage_url_name": "saved_search_list",
            "unsubscribe_guidance": "Manage saved-search email notifications from Saved Searches.",
        }

    def test_v217_marker_is_declared_for_email_rendering_contract(self):
        self.assertEqual(
            V217_SAVED_SEARCH_NOTIFICATION_EMAIL_RENDERING_CONTRACT,
            "V217_SAVED_SEARCH_NOTIFICATION_EMAIL_RENDERING_CONTRACT",
        )

    def test_v217_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v217_saved_search_model_has_rendering_ready_notification_fields(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v217_rendering_contract_context_is_owner_scoped_and_opt_in_ready(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v217-owner",
            email="v217-owner@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v217-other",
            email="v217-other@example.com",
            password="password",
        )

        enabled = self._create_saved_search(owner, enabled=True, name="Furniture alerts")
        self._create_saved_search(owner, enabled=False, name="Disabled alerts")
        self._create_saved_search(other_owner, enabled=True, name="Other alerts")

        context = self._test_only_rendering_contract_context(enabled, match_count=3)

        self.assertEqual(context["recipient_email"], "v217-owner@example.com")
        self.assertEqual(context["recipient_username"], "v217-owner")
        self.assertEqual(context["saved_search_id"], enabled.pk)
        self.assertEqual(context["saved_search_name"], "Furniture alerts")
        self.assertEqual(context["match_count"], 3)
        self.assertEqual(context["manage_url_name"], "saved_search_list")
        self.assertIn("Manage saved-search email notifications", context["unsubscribe_guidance"])

        owner_opt_in = SavedSearch.objects.filter(
            user=owner,
            email_notifications_enabled=True,
        )
        self.assertEqual(list(owner_opt_in), [enabled])

    def test_v217_email_rendering_contract_is_explicit_in_test_source(self):
        source = self._read("listings/test_saved_search_notification_email_rendering_contract_v217.py")

        required_terms = (
            "recipient_email",
            "recipient_username",
            "saved_search_id",
            "saved_search_name",
            "saved_search_querystring",
            "match_count",
            "subject_prefix",
            "manage_url_name",
            "unsubscribe_guidance",
        )

        for term in required_terms:
            self.assertIn(term, source)

    def test_v217_existing_scheduler_remains_dry_run_or_timestamp_only(self):
        scheduler_source = self._read("listings/saved_search_notification_scheduler.py")
        command_source = self._read("listings/management/commands/process_saved_search_notifications.py")
        combined_source = scheduler_source + "\n" + command_source

        self.assertIn("sent=0", scheduler_source)
        self.assertIn("last_notification_checked_at", scheduler_source)
        self.assertIn("does not send email", command_source)

        forbidden_runtime_send_terms = (
            "send_" + "mail",
            "Email" + "Message",
            "Email" + "MultiAlternatives",
            "mail_" + "admins",
            "mail_" + "managers",
            "." + "send(",
            "last_notification_sent_at" + "=",
        )

        for term in forbidden_runtime_send_terms:
            self.assertNotIn(term, combined_source)

    def test_v217_contract_does_not_patch_existing_runtime_or_template_surfaces(self):
        untouched_surfaces = (
            "accounts/admin.py",
            "accounts/models.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/management/commands/process_saved_search_notifications.py",
            "listings/templates/listings/saved_search_list.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in untouched_surfaces:
            self.assertNotIn(
                "V217_SAVED_SEARCH_NOTIFICATION_EMAIL_RENDERING_CONTRACT",
                self._read(relative_path),
                f"v217 marker should not patch runtime/template surface {relative_path}",
            )

    def test_v217_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_saved_search_notification_scheduler_design_audit_v211.py": (
                "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )

    def test_v217_contract_is_not_email_sending_implementation(self):
        source = self._read("listings/test_saved_search_notification_email_rendering_contract_v217.py")

        self.assertIn("rendering contract", source)

        forbidden_terms = (
            "send_" + "mail",
            "Email" + "MultiAlternatives",
            "Email" + "Message(",
            "mail." + "send",
            "last_notification_sent_at" + " =",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, source)
