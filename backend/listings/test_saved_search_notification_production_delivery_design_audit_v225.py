from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.db import models
from django.test import TestCase

from listings.models import SavedSearch


V225_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_DESIGN_AUDIT = (
    "V225_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_DESIGN_AUDIT"
)


class SavedSearchNotificationProductionDeliveryDesignAuditV225Tests(TestCase):
    def _backend_root(self) -> Path:
        return Path(settings.BASE_DIR)

    def _read_backend(self, relative_path: str) -> str:
        return (self._backend_root() / relative_path).read_text(
            encoding="utf-8",
            errors="ignore",
        )

    def test_v225_marker_is_declared_for_production_delivery_design_audit(self):
        self.assertEqual(
            V225_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_DESIGN_AUDIT,
            "V225_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_DESIGN_AUDIT",
        )

    def test_v225_backend_docs_directory_is_absent(self):
        self.assertFalse(
            (self._backend_root() / "docs").exists(),
            "backend/docs must remain absent; project docs belong in top-level docs/.",
        )

    def test_v225_saved_search_model_still_has_notification_fields_without_migrations(self):
        fields = {field.name: field for field in SavedSearch._meta.fields}

        self.assertIn("email_notifications_enabled", fields)
        self.assertIsInstance(fields["email_notifications_enabled"], models.BooleanField)

        self.assertIn("last_notification_checked_at", fields)
        self.assertIsInstance(fields["last_notification_checked_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_checked_at"].null)

        self.assertIn("last_notification_sent_at", fields)
        self.assertIsInstance(fields["last_notification_sent_at"], models.DateTimeField)
        self.assertTrue(fields["last_notification_sent_at"].null)

    def test_v225_current_sender_remains_test_backend_gated_not_production_delivery(self):
        sender_source = self._read_backend("listings/saved_search_notification_email_sender.py")

        self.assertIn("V222_SAVED_SEARCH_NOTIFICATION_EXPLICIT_SEND_TEST_BACKEND", sender_source)
        self.assertIn("V222_LOC_MEM_TEST_EMAIL_BACKEND", sender_source)
        self.assertIn("django.core.mail.backends.locmem.EmailBackend", sender_source)
        self.assertIn("require_saved_search_notification_test_email_backend", sender_source)
        self.assertIn("require_test_email_backend", sender_source)
        self.assertIn("execute_send", sender_source)
        self.assertIn("SavedSearchNotificationEmailDeliveryBlocked", sender_source)

        forbidden_production_backend_terms = (
            "SMTPEmailBackend",
            "smtp.EmailBackend",
            "EMAIL_HOST_USER",
            "EMAIL_HOST_PASSWORD",
            "ANYMAIL",
            "mailgun",
            "sendgrid",
            "postmark",
            "ses",
            "production_delivery_enabled",
            "production_email_backend",
        )

        for term in forbidden_production_backend_terms:
            self.assertNotIn(term, sender_source)

    def test_v225_management_command_has_no_production_send_bypass_flags(self):
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )

        self.assertIn("--render-email-previews", command_source)
        self.assertIn("--execute-email-send", command_source)
        self.assertIn("--notification-observability-report", command_source)
        self.assertIn("--notification-rollback-report", command_source)
        self.assertIn("require_test_email_backend=True", command_source)

        forbidden_command_terms = (
            "--execute-production-email-send",
            "--production-email-send",
            "--production-email-backend",
            "--smtp",
            "--skip-test-email-backend",
            "--disable-test-email-backend-requirement",
            "require_test_email_backend=False",
            "production_delivery_enabled",
            "production_email_backend",
        )

        for term in forbidden_command_terms:
            self.assertNotIn(term, command_source)

    def test_v225_no_scheduler_auto_delivery_or_background_process_wiring_exists(self):
        scheduler_source = self._read_backend("listings/saved_search_notification_scheduler.py")
        command_source = self._read_backend(
            "listings/management/commands/process_saved_search_notifications.py"
        )
        dockerfile = self._read_backend("Dockerfile")

        # Top-level docker-compose.yml is intentionally verified by the host-side
        # repair script, because it is not mounted inside the Docker web container.
        combined = scheduler_source + "\n" + command_source + "\n" + dockerfile

        forbidden_process_terms = (
            "celery",
            "beat",
            "rq",
            "huey",
            "apscheduler",
            "crontab",
            "cron:",
            "worker:",
        )

        for term in forbidden_process_terms:
            self.assertNotIn(term, combined.lower())

        self.assertNotIn("send_saved_search_notification_email_batch(", scheduler_source)
        self.assertNotIn("execute_email_send", scheduler_source)
        self.assertNotIn("--execute-email-send", scheduler_source)

    def test_v225_no_production_email_settings_or_secrets_are_wired(self):
        settings_source = self._read_backend("config/settings.py")
        dockerfile = self._read_backend("Dockerfile")
        # Top-level docker-compose.yml is intentionally verified by the host-side
        # repair script, because it is not mounted inside the Docker web container.
        combined = settings_source + "\n" + dockerfile

        forbidden_secret_terms = (
            "EMAIL_HOST_USER",
            "EMAIL_HOST_PASSWORD",
            "EMAIL_USE_TLS",
            "EMAIL_USE_SSL",
            "SMTP_PASSWORD",
            "SMTP_USERNAME",
            "SENDGRID_API_KEY",
            "MAILGUN_API_KEY",
            "POSTMARK_TOKEN",
            "AWS_SES",
            "ANYMAIL",
        )

        for term in forbidden_secret_terms:
            self.assertNotIn(term, combined)

    def test_v225_rollback_and_audit_safeguards_remain_packaged_before_production_delivery(self):
        audit_source = self._read_backend("listings/saved_search_notification_audit.py")
        observability_source = self._read_backend("listings/saved_search_notification_observability.py")

        self.assertIn("V224_SAVED_SEARCH_NOTIFICATION_ROLLBACK_AUDIT_HARDENING", audit_source)
        self.assertIn("build_saved_search_notification_audit_event", audit_source)
        self.assertIn("build_saved_search_notification_rollback_plan", audit_source)
        self.assertIn("rollback_saved_search_notification_sent_timestamp", audit_source)
        self.assertIn("execute_rollback", audit_source)
        self.assertIn("audit_fingerprint", audit_source)
        self.assertIn("hashlib.sha256", audit_source)

        self.assertIn("V223_SAVED_SEARCH_NOTIFICATION_ADMIN_OPERATOR_OBSERVABILITY", observability_source)
        self.assertIn("build_saved_search_notification_observability_snapshot", observability_source)
        self.assertIn("missing_recipient_email_count", observability_source)

    def test_v225_contract_terms_are_declared_for_future_production_delivery_gate(self):
        source = self._read_backend(
            "listings/test_saved_search_notification_production_delivery_design_audit_v225.py"
        )

        required_terms = (
            "production-delivery design audit",
            "locmem test email backend remains required",
            "no production SMTP backend",
            "no scheduler auto-delivery",
            "no background process",
            "no production secrets",
            "operator confirmation before production delivery",
            "audit event before and after production delivery",
            "rollback plan before production delivery",
            "rate limit and batch limit before production delivery",
            "deliverability failure handling before production delivery",
            "unsubscribe and preference compliance before production delivery",
        )

        # Contract phrase block:
        # production-delivery design audit
        # locmem test email backend remains required
        # no production SMTP backend
        # no scheduler auto-delivery
        # no background process
        # no production secrets
        # operator confirmation before production delivery
        # audit event before and after production delivery
        # rollback plan before production delivery
        # rate limit and batch limit before production delivery
        # deliverability failure handling before production delivery
        # unsubscribe and preference compliance before production delivery

        for term in required_terms:
            self.assertIn(term, source)

    def test_v225_does_not_patch_unrelated_runtime_or_template_surfaces(self):
        untouched_surfaces = (
            "listings/models.py",
            "listings/forms.py",
            "listings/urls.py",
            "listings/views.py",
            "listings/saved_searches_views.py",
            "listings/templates/listings/saved_search_list.html",
            "listings/templates/listings/email/saved_search_notification.txt",
            "listings/templates/listings/email/saved_search_notification.html",
            "listings/saved_search_notification_scheduler.py",
            "listings/saved_search_notification_email_sender.py",
            "listings/saved_search_notification_email_renderer.py",
            "listings/saved_search_notification_observability.py",
            "listings/saved_search_notification_audit.py",
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
                "V225_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_DESIGN_AUDIT",
                self._read_backend(relative_path),
                f"v225 marker should not patch unrelated surface {relative_path}",
            )

    def test_v225_recent_checkpoint_markers_remain_packaged(self):
        expected_markers = {
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
            "listings/test_saved_search_notification_email_sending_dry_run_contract_v219.py": (
                "V219_SAVED_SEARCH_NOTIFICATION_EMAIL_SENDING_DRY_RUN_CONTRACT"
            ),
        }

        for relative_path, marker in expected_markers.items():
            self.assertIn(
                marker,
                self._read_backend(relative_path),
                f"Expected marker {marker} in {relative_path}",
            )
