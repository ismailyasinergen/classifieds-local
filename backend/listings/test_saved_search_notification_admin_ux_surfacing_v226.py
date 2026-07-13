from __future__ import annotations

from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib import admin as django_admin
from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase
from django.utils import timezone

from listings.admin import (
    V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING,
    SavedSearchNotificationAdmin,
)
from listings.models import SavedSearch


class SavedSearchNotificationAdminUxSurfacingV226Tests(TestCase):
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
            data["querystring"] = "q=admin-ux&sort=newest"
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

    def test_v226_marker_is_declared_for_admin_ux_surfacing(self):
        self.assertEqual(
            V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING,
            "V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING",
        )

    def test_v226_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v226_saved_search_model_still_has_notification_fields_without_migrations(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v226_saved_search_admin_is_registered_with_notification_columns(self):
        admin_instance = django_admin.site._registry.get(SavedSearch)

        self.assertIsNotNone(admin_instance)
        self.assertIsInstance(admin_instance, SavedSearchNotificationAdmin)

        self.assertEqual(
            admin_instance.list_display,
            (
                "saved_search_label",
                "owner_display",
                "notification_status",
                "notification_preference",
                "recipient_email",
                "last_checked_display",
                "last_sent_display",
            ),
        )
        self.assertEqual(admin_instance.list_filter, ("email_notifications_enabled",))
        self.assertEqual(
            admin_instance.search_fields,
            ("name", "querystring", "user__username", "user__email"),
        )
        self.assertIn("notification_status", admin_instance.readonly_fields)
        self.assertIn("recipient_email", admin_instance.readonly_fields)
        self.assertIn("delivery_readiness", admin_instance.readonly_fields)
        self.assertEqual(
            admin_instance.actions,
            (
                "enable_saved_search_email_notifications",
                "disable_saved_search_email_notifications",
            ),
        )

    def test_v226_admin_methods_surface_ready_enabled_saved_search_state(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v226-ready-owner",
            email="v226-ready-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Ready admin alert",
        )

        checked_at = timezone.now()
        sent_at = timezone.now()
        saved_search.last_notification_checked_at = checked_at
        saved_search.last_notification_sent_at = sent_at
        saved_search.save(update_fields=["last_notification_checked_at", "last_notification_sent_at"])

        admin_instance = django_admin.site._registry[SavedSearch]

        self.assertEqual(admin_instance.saved_search_label(saved_search), "Ready admin alert")
        self.assertEqual(admin_instance.owner_display(saved_search), "v226-ready-owner")
        self.assertIn("Enabled, checked", admin_instance.notification_status(saved_search))
        self.assertTrue(admin_instance.notification_preference(saved_search))
        self.assertEqual(admin_instance.recipient_email(saved_search), "v226-ready-owner@example.com")
        self.assertEqual(admin_instance.delivery_readiness(saved_search), "Ready for guarded notification flow")
        self.assertEqual(admin_instance.last_checked_display(saved_search), checked_at)
        self.assertEqual(admin_instance.last_sent_display(saved_search), sent_at)

    def test_v226_admin_methods_surface_disabled_and_missing_email_states(self):
        user_model = get_user_model()
        disabled_owner = user_model.objects.create_user(
            username="v226-disabled-owner",
            email="v226-disabled-owner@example.com",
            password="password",
        )
        missing_email_owner = user_model.objects.create_user(
            username="v226-missing-email-owner",
            email="",
            password="password",
        )

        disabled = self._create_saved_search(
            disabled_owner,
            enabled=False,
            name="Disabled admin alert",
        )
        missing_email = self._create_saved_search(
            missing_email_owner,
            enabled=True,
            name="Missing email admin alert",
        )

        admin_instance = django_admin.site._registry[SavedSearch]

        self.assertEqual(admin_instance.notification_status(disabled), "Disabled, never checked")
        self.assertFalse(admin_instance.notification_preference(disabled))
        self.assertEqual(admin_instance.recipient_email(disabled), "v226-disabled-owner@example.com")
        self.assertEqual(admin_instance.delivery_readiness(disabled), "Not ready: notifications disabled")
        self.assertEqual(admin_instance.last_checked_display(disabled), "Never checked")
        self.assertEqual(admin_instance.last_sent_display(disabled), "Never sent")

        self.assertEqual(admin_instance.notification_status(missing_email), "Enabled, never checked")
        self.assertTrue(admin_instance.notification_preference(missing_email))
        self.assertEqual(admin_instance.recipient_email(missing_email), "Missing recipient email")
        self.assertEqual(admin_instance.delivery_readiness(missing_email), "Not ready: missing recipient email")

    def test_v226_preserves_legacy_email_alerts_column_and_preference_actions(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v226-legacy-owner",
            email="v226-legacy-owner@example.com",
            password="password",
        )
        first = self._create_saved_search(
            owner,
            enabled=False,
            name="Legacy first",
        )
        second = self._create_saved_search(
            owner,
            enabled=False,
            name="Legacy second",
        )

        admin_instance = django_admin.site._registry[SavedSearch]

        self.assertEqual(
            admin_instance.notification_preference.short_description,
            "Email alerts",
        )
        self.assertIn("notification_preference", admin_instance.list_display)
        self.assertEqual(admin_instance.notification_status(first), "Disabled, never checked")
        self.assertIn(
            "enable_saved_search_email_notifications",
            admin_instance.actions,
        )
        self.assertIn(
            "disable_saved_search_email_notifications",
            admin_instance.actions,
        )

        queryset = SavedSearch.objects.filter(pk__in=[first.pk, second.pk])
        admin_instance.enable_saved_search_email_notifications(None, queryset)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertTrue(first.email_notifications_enabled)
        self.assertTrue(second.email_notifications_enabled)

        admin_instance.disable_saved_search_email_notifications(None, queryset)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertFalse(first.email_notifications_enabled)
        self.assertFalse(second.email_notifications_enabled)

    def test_v226_admin_queryset_selects_related_user_without_mutation(self):
        user_model = get_user_model()
        owner = user_model.objects.create_user(
            username="v226-queryset-owner",
            email="v226-queryset-owner@example.com",
            password="password",
        )
        saved_search = self._create_saved_search(
            owner,
            enabled=True,
            name="Queryset admin alert",
        )

        before_checked = saved_search.last_notification_checked_at
        before_sent = saved_search.last_notification_sent_at

        admin_instance = django_admin.site._registry[SavedSearch]
        queryset = admin_instance.get_queryset(request=None)

        self.assertIn(saved_search.pk, list(queryset.values_list("pk", flat=True)))

        saved_search.refresh_from_db()
        self.assertEqual(saved_search.last_notification_checked_at, before_checked)
        self.assertEqual(saved_search.last_notification_sent_at, before_sent)

    def test_v226_admin_source_adds_no_delivery_rollback_or_background_controls(self):
        admin_source = self._read_backend("listings/admin.py")
        v226_block = admin_source.split("V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING", 1)[1]

        required_terms = (
            "SavedSearchNotificationAdmin",
            "list_display",
            "list_filter",
            "search_fields",
            "readonly_fields",
            "notification_status",
            "notification_preference",
            "Email alerts",
            "recipient_email",
            "delivery_readiness",
            "last_checked_display",
            "last_sent_display",
            "enable_saved_search_email_notifications",
            "disable_saved_search_email_notifications",
        )

        for term in required_terms:
            self.assertIn(term, v226_block)

        forbidden_terms = (
            "send_" + "mail",
            "Email" + "Message",
            "Email" + "MultiAlternatives",
            "mail_" + "admins",
            "mail_" + "managers",
            "." + "send(",
            "execute_email_send",
            "--execute-email-send",
            "send_saved_search_notification_email_batch",
            "rollback_saved_search_notification_sent_timestamp",
            "last_notification_sent_at" + " =",
            "last_notification_sent_at" + "=",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, v226_block)

    def test_v226_runtime_delivery_surfaces_remain_unchanged_by_admin_ux_surfacing(self):
        runtime_surfaces = (
            "listings/saved_search_notification_email_sender.py",
            "listings/saved_search_notification_scheduler.py",
            "listings/saved_search_notification_email_renderer.py",
            "listings/saved_search_notification_observability.py",
            "listings/saved_search_notification_audit.py",
            "listings/management/commands/process_saved_search_notifications.py",
        )

        for relative_path in runtime_surfaces:
            source = self._read_backend(relative_path)
            self.assertNotIn(
                "V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING",
                source,
                f"v226 marker should not patch runtime delivery surface {relative_path}",
            )

    def test_v226_does_not_patch_unrelated_runtime_or_template_surfaces(self):
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
                "V226_SAVED_SEARCH_NOTIFICATION_ADMIN_UX_SURFACING",
                self._read_backend(relative_path),
                f"v226 marker should not patch unrelated surface {relative_path}",
            )

    def test_v226_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
            "listings/test_saved_search_notification_production_delivery_design_audit_v225.py": (
                "V225_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_DESIGN_AUDIT"
            ),
            "listings/test_saved_search_notification_rollback_audit_hardening_v224.py": (
                "V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING"
            ),
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
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read_backend(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
