from __future__ import annotations

from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.test import RequestFactory, TestCase
from django.utils import timezone

from accounts import admin as accounts_admin
from accounts.models import SellerStore


class SellerStoreAdminActionImplementationSafeguardsV215Tests(TestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def _seller_store_admin(self):
        registered_admin = admin.site._registry.get(SellerStore)
        self.assertIsNotNone(
            registered_admin,
            "SellerStore should remain registered in Django admin.",
        )
        return registered_admin

    def _superuser_request(self):
        user_model = get_user_model()
        user = user_model.objects.create_superuser(
            username="v215-admin",
            email="v215-admin@example.com",
            password="password",
        )
        request = RequestFactory().get("/admin/accounts/sellerstore/")
        request.user = user
        return request

    def _viewer_request(self):
        request = RequestFactory().get("/admin/accounts/sellerstore/")
        request.user = AnonymousUser()
        return request

    def _create_seller_store(self, *, name: str = "V215 Review Store"):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username=f"v215-owner-{SellerStore.objects.count()}",
            email=f"v215-owner-{SellerStore.objects.count()}@example.com",
            password="password",
        )

        create_data = {}
        user_model_class = get_user_model()

        for field in SellerStore._meta.fields:
            if field.primary_key:
                continue

            if isinstance(field, (models.ForeignKey, models.OneToOneField)):
                remote_model = field.remote_field.model
                if remote_model == user_model_class or getattr(remote_model, "__name__", "") == getattr(user_model_class, "__name__", ""):
                    create_data[field.name] = user
                    continue

            if field.has_default() or getattr(field, "null", False) or getattr(field, "blank", False):
                continue

            if isinstance(field, (models.CharField, models.SlugField, models.EmailField, models.URLField)):
                if getattr(field, "choices", None):
                    create_data[field.name] = next(iter(field.choices))[0]
                elif field.name == "slug":
                    create_data[field.name] = "v215-review-store"
                elif "email" in field.name:
                    create_data[field.name] = "v215-store@example.com"
                elif "url" in field.name:
                    create_data[field.name] = "https://example.test/v215"
                else:
                    create_data[field.name] = name[: getattr(field, "max_length", 255)]
            elif isinstance(field, models.TextField):
                create_data[field.name] = "V215 safe review export test store."
            elif isinstance(field, models.BooleanField):
                create_data[field.name] = False
            elif isinstance(field, models.IntegerField):
                create_data[field.name] = 0
            elif isinstance(field, models.DecimalField):
                create_data[field.name] = Decimal("0")
            elif isinstance(field, models.DateTimeField):
                create_data[field.name] = timezone.now()
            elif isinstance(field, models.DateField):
                create_data[field.name] = timezone.localdate()

        return SellerStore.objects.create(**create_data)

    def test_v215_marker_is_declared_in_accounts_admin(self):
        self.assertEqual(
            accounts_admin.V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS,
            "V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS",
        )

    def test_v215_safe_action_is_installed_without_setting_bulk_actions_attribute(self):
        seller_store_admin = self._seller_store_admin()
        request = self._superuser_request()

        self.assertTrue(
            getattr(
                seller_store_admin.__class__,
                "v215_seller_store_admin_action_installed",
                False,
            )
        )

        configured_actions = getattr(seller_store_admin, "actions", None)
        if configured_actions is not None:
            self.assertEqual(tuple(configured_actions), ())

        actions = seller_store_admin.get_actions(request)

        self.assertIn(
            "v215_export_selected_seller_stores_for_review",
            actions,
        )
        self.assertNotIn(
            "delete_selected",
            actions,
            "SellerStore admin should hide destructive delete_selected action.",
        )

    def test_v215_action_is_hidden_without_view_permission(self):
        seller_store_admin = self._seller_store_admin()
        request = self._viewer_request()

        actions = seller_store_admin.get_actions(request)

        self.assertNotIn(
            "v215_export_selected_seller_stores_for_review",
            actions,
        )

    def test_v215_review_export_action_returns_csv_without_mutating_rows(self):
        seller_store = self._create_seller_store()
        seller_store_admin = self._seller_store_admin()
        request = self._superuser_request()

        actions = seller_store_admin.get_actions(request)
        action, _name, _description = actions[
            "v215_export_selected_seller_stores_for_review"
        ]

        before_count = SellerStore.objects.count()
        response = action(
            seller_store_admin,
            request,
            SellerStore.objects.filter(pk=seller_store.pk),
        )
        after_count = SellerStore.objects.count()

        self.assertEqual(before_count, after_count)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(
            "seller-store-review-export-v215.csv",
            response["Content-Disposition"],
        )

        content = response.content.decode("utf-8", errors="ignore")
        self.assertIn("id,store,owner,profile_status,verified,approved,created_at,updated_at", content)
        self.assertIn(str(seller_store.pk), content)

        seller_store.refresh_from_db()
        self.assertEqual(SellerStore.objects.filter(pk=seller_store.pk).count(), 1)

    def test_v215_review_export_action_rejects_empty_selection(self):
        seller_store_admin = self._seller_store_admin()
        request = self._superuser_request()

        actions = seller_store_admin.get_actions(request)
        action, _name, _description = actions[
            "v215_export_selected_seller_stores_for_review"
        ]

        response = action(
            seller_store_admin,
            request,
            SellerStore.objects.none(),
        )

        self.assertIsNone(response)

    def test_v215_csv_safety_prefixes_spreadsheet_formula_values(self):
        self.assertEqual(accounts_admin._v215_seller_store_csv_safe("=SUM(A1:A2)"), "'=SUM(A1:A2)")
        self.assertEqual(accounts_admin._v215_seller_store_csv_safe("+SUM(A1:A2)"), "'+SUM(A1:A2)")
        self.assertEqual(accounts_admin._v215_seller_store_csv_safe("-SUM(A1:A2)"), "'-SUM(A1:A2)")
        self.assertEqual(accounts_admin._v215_seller_store_csv_safe("@SUM(A1:A2)"), "'@SUM(A1:A2)")
        self.assertEqual(accounts_admin._v215_seller_store_csv_safe("safe"), "safe")

    def test_v215_action_has_explicit_safeguard_terms_in_admin_source(self):
        admin_source = self._read("accounts/admin.py")

        required_terms = (
            "V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS",
            "V215_SELLER_STORE_REVIEW_EXPORT_MAX_ROWS = 250",
            "action_map.pop(\"delete_selected\", None)",
            "has_view_permission",
            "seller-store-review-export-v215.csv",
            "_v215_seller_store_csv_safe",
            "_v215_install_seller_store_admin_actions()",
        )

        for term in required_terms:
            self.assertIn(term, admin_source)

    def test_v215_action_does_not_include_unsafe_state_changing_terms(self):
        v215_block = self._read("accounts/admin.py").split(
            "# V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS START",
            1,
        )[1].split(
            "# V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS END",
            1,
        )[0]

        forbidden_terms = (
            "approve_selected_seller_stores",
            "verify_selected_seller_stores",
            "suspend_seller_stores",
            "delete_seller_stores",
            "bulk_approve",
            "bulk_verify",
            "bulk_suspend",
            "bulk_delete",
            ".delete(",
            "is_verified = True",
            "is_approved = True",
            "status =",
        )

        for term in forbidden_terms:
            self.assertNotIn(term, v215_block)

    def test_v215_marker_does_not_patch_templates_saved_search_scheduler_or_category_surfaces(self):
        untouched_surfaces = (
            "accounts/templates/accounts/seller_store_public.html",
            "accounts/templates/accounts/seller_store_directory.html",
            "listings/saved_search_notification_scheduler.py",
            "listings/management/commands/process_saved_search_notifications.py",
            "listings/templates/listings/saved_search_list.html",
            "categories/admin.py",
            "templates/admin/categories/category/change_list.html",
            "templates/categories/_category_navigation_v186.html",
        )

        for relative_path in untouched_surfaces:
            self.assertNotIn(
                "V215_SELLER_STORE_ADMIN_ACTION_IMPLEMENTATION_SAFEGUARDS",
                self._read(relative_path),
                f"v215 marker should not patch unrelated surface {relative_path}",
            )

    def test_v215_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_final_local_release_packaging_checklist_v210.py": (
                "V210_FINAL_LOCAL_RELEASE_PACKAGING_CHECKLIST"
            ),
            "accounts/tests/test_seller_store_admin_ui_polish_v209.py": (
                "V209_SELLER_STORE_ADMIN_UI_POLISH"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(marker, self._read(relative_path))

    def test_v215_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )
