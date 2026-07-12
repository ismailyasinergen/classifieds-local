from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from listings.models import SavedSearch
from listings.saved_search_notification_scheduler import (
    V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE_MARKER,
    get_saved_search_notification_candidates,
    run_saved_search_notification_scheduler,
)


class SavedSearchNotificationSchedulerSpikeV214Tests(TestCase):
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

    def test_v214_marker_is_declared_for_scheduler_spike(self):
        self.assertEqual(
            V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE_MARKER,
            "V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE",
        )

    def test_v214_candidate_queryset_is_opt_in_only_and_owner_packaged(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v214-owner",
            email="owner-v214@example.com",
            password="password",
        )
        other_owner = user_model.objects.create_user(
            username="v214-other",
            email="other-v214@example.com",
            password="password",
        )

        enabled = self._create_saved_search(owner, enabled=True, name="Enabled")
        self._create_saved_search(owner, enabled=False, name="Disabled")
        other_enabled = self._create_saved_search(other_owner, enabled=True, name="Other")

        candidates = list(get_saved_search_notification_candidates())

        self.assertEqual(
            [saved_search.pk for saved_search in candidates],
            [enabled.pk, other_enabled.pk],
        )
        self.assertEqual(candidates[0].user, owner)
        self.assertEqual(candidates[1].user, other_owner)

    def test_v214_default_scheduler_run_is_dry_run_and_does_not_write_timestamps(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v214-dry-run",
            email="dry-run-v214@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(owner, enabled=True)

        result = run_saved_search_notification_scheduler()

        self.assertEqual(result.checked, 1)
        self.assertEqual(result.sent, 0)
        self.assertTrue(result.dry_run)

        saved_search.refresh_from_db()
        self.assertIsNone(saved_search.last_notification_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_v214_execute_scheduler_records_checked_timestamp_without_sending(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v214-execute",
            email="execute-v214@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(owner, enabled=True)

        result = run_saved_search_notification_scheduler(dry_run=False)

        self.assertEqual(result.checked, 1)
        self.assertEqual(result.sent, 0)
        self.assertFalse(result.dry_run)

        saved_search.refresh_from_db()
        self.assertIsNotNone(saved_search.last_notification_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_v214_execute_scheduler_does_not_touch_disabled_saved_searches(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v214-disabled",
            email="disabled-v214@example.com",
            password="password",
        )
        disabled = self._create_saved_search(owner, enabled=False)

        result = run_saved_search_notification_scheduler(dry_run=False)

        self.assertEqual(result.checked, 0)
        self.assertEqual(result.sent, 0)

        disabled.refresh_from_db()
        self.assertIsNone(disabled.last_notification_checked_at)
        self.assertIsNone(disabled.last_notification_sent_at)

    def test_v214_limit_bounds_scheduler_pass(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v214-limit",
            email="limit-v214@example.com",
            password="password",
        )
        first = self._create_saved_search(owner, enabled=True, name="First")
        second = self._create_saved_search(owner, enabled=True, name="Second")

        result = run_saved_search_notification_scheduler(dry_run=False, limit=1)

        self.assertEqual(result.checked, 1)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNotNone(first.last_notification_checked_at)
        self.assertIsNone(second.last_notification_checked_at)

    def test_v214_management_command_defaults_to_dry_run(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v214-command-dry-run",
            email="command-dry-run-v214@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(owner, enabled=True)

        stdout = StringIO()
        call_command("process_saved_search_notifications", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE", output)
        self.assertIn("checked=1", output)
        self.assertIn("sent=0", output)
        self.assertIn("dry_run=True", output)

        saved_search.refresh_from_db()
        self.assertIsNone(saved_search.last_notification_checked_at)

    def test_v214_management_command_execute_records_checked_timestamp(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v214-command-execute",
            email="command-execute-v214@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(owner, enabled=True)

        stdout = StringIO()
        call_command("process_saved_search_notifications", "--execute", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("checked=1", output)
        self.assertIn("sent=0", output)
        self.assertIn("dry_run=False", output)

        saved_search.refresh_from_db()
        self.assertIsNotNone(saved_search.last_notification_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

    def test_v214_management_command_rejects_negative_limit(self):
        with self.assertRaises(CommandError):
            call_command("process_saved_search_notifications", "--limit=-1")

    def test_v214_spike_does_not_patch_existing_runtime_surfaces(self):
        untouched_surfaces = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
            "accounts/admin.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in untouched_surfaces:
            self.assertNotIn(
                "V214_SAVED_SEARCH_NOTIFICATION_SCHEDULER_SPIKE",
                self._read(relative_path),
                f"v214 marker should not patch existing surface {relative_path}",
            )

    def test_v214_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
            "listings/test_local_release_archive_export_dry_run_v213.py": (
                "V213_LOCAL_RELEASE_ARCHIVE_EXPORT_DRY_RUN"
            ),
            "accounts/tests/test_seller_store_admin_action_safety_v212.py": (
                "V212_SELLER_STORE_ADMIN_ACTION_SAFETY_TESTS"
            ),
            "listings/test_saved_search_notification_scheduler_design_audit_v211.py": (
                "V211_SAVED_SEARCH_NOTIFICATION_SCHEDULER_DESIGN_AUDIT"
            ),
            "listings/test_final_local_release_packaging_checklist_v210.py": (
                "V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST"
            ),
            "accounts/tests/test_seller_store_admin_ui_polish_v209.py": (
                "V209_SELLER_STORE_ADMIN_UI_POLISH"
            ),
            "listings/test_saved_search_notification_behavior_execution_v208.py": (
                "V208_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_EXECUTION_TESTS"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )

    def test_v214_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
