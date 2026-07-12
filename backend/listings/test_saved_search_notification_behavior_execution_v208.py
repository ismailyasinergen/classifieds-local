from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from listings.models import SavedSearch


V208_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_EXECUTION_MARKER = (
    "V208_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_EXECUTION_TESTS"
)


class SavedSearchNotificationBehaviorExecutionV208Tests(TestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _field_names(self) -> set[str]:
        return {field.name for field in SavedSearch._meta.fields}

    def _choice_value(self, field: models.Field, preferred: str | None = None) -> Any:
        choices = list(field.choices or [])
        if preferred is not None:
            for value, _label in choices:
                if value == preferred:
                    return value

        for value, _label in choices:
            if value in {"listing", "listings", "search", "seller_store"}:
                return value

        if choices:
            return choices[0][0]

        return preferred

    def _saved_search_kwargs(
        self,
        *,
        user,
        name: str,
        path: str,
        querystring: str,
        email_notifications_enabled: bool,
        last_notification_checked_at=None,
        last_notification_sent_at=None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        fields_by_name = {field.name: field for field in SavedSearch._meta.fields}

        if "user" not in fields_by_name:
            self.fail("SavedSearch must expose a user field for owner-scoped notification behavior.")

        kwargs["user"] = user

        preferred_values: dict[str, Any] = {
            "name": name,
            "path": path,
            "querystring": querystring,
            "email_notifications_enabled": email_notifications_enabled,
            "last_notification_checked_at": last_notification_checked_at,
            "last_notification_sent_at": last_notification_sent_at,
        }

        for field_name, value in preferred_values.items():
            if field_name in fields_by_name:
                kwargs[field_name] = value

        if "search_type" in fields_by_name:
            kwargs["search_type"] = self._choice_value(fields_by_name["search_type"], "listing")

        for field in SavedSearch._meta.fields:
            if field.primary_key or field.name in kwargs:
                continue

            if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
                continue

            if field.default is not models.NOT_PROVIDED:
                continue

            if getattr(field, "null", False) or getattr(field, "blank", False):
                continue

            if isinstance(field, models.ForeignKey):
                if field.remote_field and field.remote_field.model == type(user):
                    kwargs[field.name] = user
                continue

            if isinstance(field, (models.CharField, models.TextField, models.SlugField)):
                kwargs[field.name] = f"v208-{field.name}-{name}".replace(" ", "-").lower()
            elif isinstance(field, models.BooleanField):
                kwargs[field.name] = False
            elif isinstance(field, (models.IntegerField, models.PositiveIntegerField)):
                kwargs[field.name] = 1
            elif isinstance(field, models.DateTimeField):
                kwargs[field.name] = timezone.now()
            elif isinstance(field, models.DateField):
                kwargs[field.name] = timezone.localdate()

        return kwargs

    def _create_user(self, username: str):
        UserModel = get_user_model()
        return UserModel.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password="test-pass-12345",
        )

    def _create_saved_search(
        self,
        *,
        user,
        name: str = "V208 saved search",
        path: str = "/listings/",
        querystring: str = "q=v208",
        email_notifications_enabled: bool = True,
        last_notification_checked_at=None,
        last_notification_sent_at=None,
    ) -> SavedSearch:
        return SavedSearch.objects.create(
            **self._saved_search_kwargs(
                user=user,
                name=name,
                path=path,
                querystring=querystring,
                email_notifications_enabled=email_notifications_enabled,
                last_notification_checked_at=last_notification_checked_at,
                last_notification_sent_at=last_notification_sent_at,
            )
        )

    def test_v208_marker_is_declared_for_saved_search_notification_behavior_execution(self):
        self.assertEqual(
            V208_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_EXECUTION_MARKER,
            "V208_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_EXECUTION_TESTS",
        )

    def test_v208_saved_search_notification_fields_can_be_created_and_reloaded(self):
        user = self._create_user("v208-create-reload")
        checked_at = timezone.now()
        sent_at = checked_at - timezone.timedelta(minutes=10)

        saved_search = self._create_saved_search(
            user=user,
            name="V208 persisted opt out",
            path="/listings/",
            querystring="q=v208-persisted-opt-out",
            email_notifications_enabled=False,
            last_notification_checked_at=checked_at,
            last_notification_sent_at=sent_at,
        )

        reloaded = SavedSearch.objects.get(pk=saved_search.pk)

        self.assertIs(reloaded.email_notifications_enabled, False)
        self.assertEqual(reloaded.last_notification_checked_at, checked_at)
        self.assertEqual(reloaded.last_notification_sent_at, sent_at)

    def test_v208_saved_search_notification_opt_in_toggle_persists_without_runtime_patch(self):
        user = self._create_user("v208-toggle")
        saved_search = self._create_saved_search(
            user=user,
            name="V208 toggle notification",
            path="/listings/",
            querystring="q=v208-toggle",
            email_notifications_enabled=False,
        )

        self.assertIs(SavedSearch.objects.get(pk=saved_search.pk).email_notifications_enabled, False)

        saved_search.email_notifications_enabled = True
        saved_search.save(update_fields=["email_notifications_enabled"])

        saved_search.refresh_from_db()
        self.assertIs(saved_search.email_notifications_enabled, True)

        saved_search.email_notifications_enabled = False
        saved_search.save(update_fields=["email_notifications_enabled"])

        saved_search.refresh_from_db()
        self.assertIs(saved_search.email_notifications_enabled, False)

    def test_v208_saved_search_notification_timestamps_accept_null_and_aware_values(self):
        user = self._create_user("v208-timestamps")
        saved_search = self._create_saved_search(
            user=user,
            name="V208 timestamp execution",
            path="/listings/",
            querystring="q=v208-timestamps",
            email_notifications_enabled=True,
            last_notification_checked_at=None,
            last_notification_sent_at=None,
        )

        saved_search.refresh_from_db()
        self.assertIsNone(saved_search.last_notification_checked_at)
        self.assertIsNone(saved_search.last_notification_sent_at)

        checked_at = timezone.now()
        sent_at = checked_at + timezone.timedelta(seconds=30)

        saved_search.last_notification_checked_at = checked_at
        saved_search.last_notification_sent_at = sent_at
        saved_search.save(
            update_fields=[
                "last_notification_checked_at",
                "last_notification_sent_at",
            ]
        )

        saved_search.refresh_from_db()
        self.assertEqual(saved_search.last_notification_checked_at, checked_at)
        self.assertEqual(saved_search.last_notification_sent_at, sent_at)

    def test_v208_saved_search_notification_owner_scoping_executes_with_real_rows(self):
        owner = self._create_user("v208-owner")
        other_user = self._create_user("v208-other")

        owner_search = self._create_saved_search(
            user=owner,
            name="V208 owner search",
            path="/listings/",
            querystring="q=v208-owner",
            email_notifications_enabled=True,
        )
        other_search = self._create_saved_search(
            user=other_user,
            name="V208 other search",
            path="/listings/",
            querystring="q=v208-other",
            email_notifications_enabled=True,
        )

        owner_queryset = SavedSearch.objects.filter(
            user=owner,
            email_notifications_enabled=True,
        )

        self.assertIn(owner_search, owner_queryset)
        self.assertNotIn(other_search, owner_queryset)
        self.assertEqual(owner_queryset.count(), 1)

    def test_v208_saved_search_disabled_notifications_are_excluded_from_enabled_execution_queryset(self):
        user = self._create_user("v208-enabled-queryset")

        enabled_search = self._create_saved_search(
            user=user,
            name="V208 enabled notification",
            path="/listings/",
            querystring="q=v208-enabled",
            email_notifications_enabled=True,
        )
        disabled_search = self._create_saved_search(
            user=user,
            name="V208 disabled notification",
            path="/listings/",
            querystring="q=v208-disabled",
            email_notifications_enabled=False,
        )

        enabled_queryset = SavedSearch.objects.filter(
            user=user,
            email_notifications_enabled=True,
        )

        self.assertIn(enabled_search, enabled_queryset)
        self.assertNotIn(disabled_search, enabled_queryset)
        self.assertEqual(enabled_queryset.count(), 1)

    def test_v208_saved_search_notification_template_contracts_remain_present(self):
        saved_search_template = self._read("listings/templates/listings/saved_search_list.html")

        self.assertIn("V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH", saved_search_template)
        self.assertIn("V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH", saved_search_template)
        self.assertIn("saved-search-notification-settings-v197", saved_search_template)
        self.assertIn("saved-search-notification-a11y-v205", saved_search_template)
        self.assertIn("Accessible saved search notifications", saved_search_template)
        self.assertIn(":focus-visible", saved_search_template)

    def test_v208_recent_release_candidate_audit_markers_remain_available(self):
        expected_markers = {
            "listings/test_release_candidate_final_hardening_audit_v207.py": (
                "V207_RELEASE_CANDIDATE_FINAL_HARDENING_AUDIT"
            ),
            "accounts/tests/test_seller_store_admin_detail_polish_audit_v206.py": (
                "V206_SELLER_STORE_ADMIN_DETAIL_POLISH_AUDIT"
            ),
            "listings/test_saved_search_notification_ui_accessibility_polish_v205.py": (
                "V205_SAVED_SEARCH_NOTIFICATION_UI_ACCESSIBILITY_POLISH"
            ),
            "listings/test_release_candidate_dry_run_checklist_v204.py": (
                "V204_RELEASE_CANDIDATE_DRY_RUN_CHECKLIST"
            ),
            "listings/test_saved_search_notification_behavior_contract_audit_v202.py": (
                "V202_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_CONTRACT_AUDIT"
            ),
            "listings/test_saved_search_notification_settings_polish_v197.py": (
                "V197_SAVED_SEARCH_NOTIFICATION_SETTINGS_POLISH"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )

    def test_v208_marker_does_not_patch_runtime_or_template_surfaces(self):
        runtime_surfaces = (
            "listings/models.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
            "accounts/models.py",
            "accounts/admin.py",
            "accounts/views.py",
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in runtime_surfaces:
            self.assertNotIn(
                "V208_SAVED_SEARCH_NOTIFICATION_BEHAVIOR_EXECUTION_TESTS",
                self._read(relative_path),
                f"v208 marker should not be in runtime/template surface {relative_path}",
            )

    def test_v208_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
