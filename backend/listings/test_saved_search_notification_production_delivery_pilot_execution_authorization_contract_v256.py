from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.test import (
    SimpleTestCase,
    override_settings,
)

from listings.saved_search_notification_production_readiness import (
    READINESS_CHECK_IDS,
    get_saved_search_notification_production_readiness,
)
from listings.test_saved_search_notification_production_delivery_pilot_readiness_closeout_audit_v255 import (
    PILOT_EXECUTION_AUTHORIZATION_PRECONDITIONS,
)


V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT = (
    "V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT"
)

V255_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_closeout_audit_v255.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_readiness_closeout_audit_v255.md"
    ),
)

V256_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_contract_v256.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_execution_authorization_contract_v256.md"
    ),
)

V257_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_execution_authorization_v257.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_execution_authorization_v257.md"
    ),
)

AUTHORIZATION_LIMIT_BAND = (
    1,
    3,
)

AUTHORIZATION_TIME_WINDOWS_SECONDS = {
    "readiness_max_age": 300,
    "preview_max_age": 300,
    "authorization_ttl": 600,
}

AUTHORIZATION_STAGE_ORDER = (
    "collect immutable bindings",
    "verify fresh readiness",
    "verify fresh matching preview",
    "verify provider and sender state",
    "verify reviewer approvals",
    "issue one-shot authorization",
    "consume or terminate authorization",
    "perform mandatory post-run review",
)

AUTHORIZATION_REQUIRED_FIELDS = (
    "authorization_id",
    "change_record_id",
    "pilot_owner_id",
    "approved_limit",
    "preview_owner_id",
    "preview_limit",
    "preview_candidate_count",
    "readiness_status",
    "readiness_checked_at_utc",
    "preview_checked_at_utc",
    "issued_at_utc",
    "expires_at_utc",
    "operator_identity",
    "primary_reviewer_identity",
    "secondary_reviewer_identity",
    "provider_status",
    "sender_verification_status",
    "feature_gate_verified",
    "backend_policy_verified",
    "rollback_reviewer_identity",
    "command_fingerprint",
    "authorization_state",
    "consumed_at_utc",
    "incident_reference",
)

AUTHORIZATION_IMMUTABLE_BINDINGS = (
    "authorization_id",
    "change_record_id",
    "pilot_owner_id",
    "approved_limit",
    "preview_owner_id",
    "preview_limit",
    "preview_candidate_count",
    "operator_identity",
    "primary_reviewer_identity",
    "secondary_reviewer_identity",
    "command_fingerprint",
    "issued_at_utc",
    "expires_at_utc",
)

AUTHORIZATION_LIFECYCLE_STATES = (
    "draft",
    "ready_for_review",
    "authorized",
    "consumed",
    "expired",
    "revoked",
    "failed_closed",
)

AUTHORIZATION_TERMINAL_STATES = (
    "consumed",
    "expired",
    "revoked",
    "failed_closed",
)

AUTHORIZATION_PRECONDITIONS = (
    "pilot-readiness lane is closed",
    "authorization checkpoint remains documentation and test only",
    "positive owner identifier is approved",
    "pilot limit is between 1 and 3",
    "preview owner matches approved owner",
    "preview limit matches approved limit",
    "preview candidate count is between 1 and approved limit",
    "strict readiness status is ready",
    "all nine readiness checks are present",
    "readiness evidence age is at most 300 seconds",
    "preview evidence age is at most 300 seconds",
    "authorization lifetime is at most 600 seconds",
    "feature gate remains enabled",
    "approved email backend remains configured",
    "default sender remains configured",
    "sender identity or domain remains verified",
    "provider credentials remain available",
    "provider quota covers approved limit",
    "provider status remains operational",
    "no concurrent owner-scoped run exists",
    "no unresolved incident exists",
    "rollback reviewer remains available",
    "primary reviewer approval is explicit",
    "secondary reviewer approval is explicit",
    "operator and reviewers are recorded",
    "command fingerprint matches approved owner and limit",
    "production command retains both confirmation flags",
    "authorization permits exactly one invocation",
)

AUTHORIZATION_COMMAND_FINGERPRINT_FIELDS = (
    "command_name",
    "execute_production_send",
    "confirm_production_delivery",
    "owner_id",
    "limit",
)

AUTHORIZATION_PREVIEW_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

AUTHORIZATION_PRODUCTION_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--execute-production-send "
    "--confirm-production-delivery "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

AUTHORIZATION_STOP_REASONS = (
    "pilot_readiness_lane_not_closed",
    "invalid_owner_id",
    "invalid_pilot_limit",
    "preview_owner_mismatch",
    "preview_limit_mismatch",
    "preview_candidate_count_invalid",
    "readiness_not_ready",
    "readiness_check_count_mismatch",
    "readiness_evidence_stale",
    "preview_evidence_stale",
    "authorization_ttl_invalid",
    "authorization_expired",
    "authorization_already_consumed",
    "authorization_revoked",
    "authorization_failed_closed",
    "feature_gate_disabled",
    "email_backend_rejected",
    "default_sender_missing",
    "sender_unverified",
    "provider_credentials_unavailable",
    "provider_quota_insufficient",
    "provider_not_operational",
    "concurrent_owner_run",
    "unresolved_incident",
    "rollback_reviewer_missing",
    "primary_reviewer_missing",
    "secondary_reviewer_missing",
    "reviewer_identity_collision",
    "operator_identity_missing",
    "command_fingerprint_mismatch",
    "production_confirmation_missing",
)

AUTHORIZATION_EVIDENCE_FIELDS = (
    "authorization_id",
    "change_record_id",
    "pilot_owner_id",
    "approved_limit",
    "preview_candidate_count",
    "readiness_status",
    "readiness_ready_count",
    "readiness_not_ready_count",
    "readiness_warning_count",
    "readiness_checked_at_utc",
    "preview_checked_at_utc",
    "issued_at_utc",
    "expires_at_utc",
    "operator_identity",
    "primary_reviewer_identity",
    "secondary_reviewer_identity",
    "provider_status",
    "sender_verification_status",
    "feature_gate_verified",
    "backend_policy_verified",
    "rollback_reviewer_identity",
    "command_fingerprint",
    "authorization_state",
    "consumed_at_utc",
    "decision",
    "reason_codes",
    "incident_reference",
)

AUTHORIZATION_PRIVACY_EXCLUSIONS = (
    "SMTP password",
    "confidential SMTP username",
    "API key",
    "access token",
    "recipient email address",
    "default sender value",
    "raw backend path",
    "saved-search name",
    "saved-search querystring",
    "rendered email subject",
    "rendered email body",
    "provider response body",
    "raw exception traceback",
)

AUTHORIZATION_PROHIBITED_ACTIONS = (
    "production delivery during contract checkpoint",
    "authorization without positive owner identifier",
    "authorization without explicit pilot limit",
    "authorization with limit below 1",
    "authorization with limit above 3",
    "authorization with stale readiness evidence",
    "authorization with stale preview evidence",
    "authorization longer than 600 seconds",
    "authorization without two reviewer approvals",
    "authorization with identical reviewer identities",
    "owner change after authorization",
    "limit change after authorization",
    "command fingerprint change after authorization",
    "authorization reuse",
    "authorization after expiration",
    "authorization after revocation",
    "global all-owner execution",
    "multi-owner command execution",
    "readiness bypass",
    "preview bypass",
    "production confirmation bypass",
    "provider verification bypass",
    "blind retry",
    "automatic authorization renewal",
    "automatic phase promotion",
    "automatic scheduler enablement",
    "Celery enablement",
    "cron enablement",
    "startup-time delivery",
    "request-time delivery",
    "manual sent timestamp edit",
    "manual audit-event deletion",
    "direct SQL repair",
    "Django shell timestamp repair",
    "credential logging",
    "recipient payload logging",
    "saved-search payload logging",
)

V256_ACCEPTANCE_GATES = (
    "v255 pilot-readiness closeout remains packaged",
    "v256 scope is exactly two contract files",
    "v257 implementation scope is exactly two files",
    "v257 remains documentation and test only",
    "authorization limit band is exactly 1 through 3",
    "readiness evidence freshness is 300 seconds",
    "preview evidence freshness is 300 seconds",
    "authorization lifetime is 600 seconds",
    "authorization stage order is deterministic",
    "authorization required fields are explicit",
    "authorization immutable bindings are explicit",
    "authorization lifecycle states are explicit",
    "terminal states are explicit",
    "authorization is one-shot",
    "authorization cannot be reused",
    "owner binding is immutable",
    "limit binding is immutable",
    "preview owner must match approved owner",
    "preview limit must match approved limit",
    "preview candidate count is bounded",
    "strict readiness must report ready",
    "all nine readiness checks remain required",
    "provider and sender verification remain current",
    "two explicit reviewer approvals are required",
    "reviewer identities must be distinct",
    "command fingerprint is mandatory",
    "command fingerprint binds owner and limit",
    "production retains both confirmation flags",
    "authorization stop reasons are explicit",
    "authorization evidence fields are explicit",
    "privacy exclusions are explicit",
    "contract checkpoint performs no delivery",
    "global execution is prohibited",
    "multi-owner execution is prohibited",
    "authorization reuse is prohibited",
    "automatic renewal is prohibited",
    "blind retry is prohibited",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v257: saved-search notification production delivery pilot execution authorization implementation"

PRODUCTION_LIKE_SETTINGS = {
    "SAVED_SEARCH_PRODUCTION_DELIVERY_ENABLED": True,
    "EMAIL_BACKEND": (
        "project.production_mail."
        "ProductionEmailBackend"
    ),
    "DEFAULT_FROM_EMAIL": (
        "saved-search-alerts@example.invalid"
    ),
}

PROTECTED_RUNTIME_PATHS = (
    "config/settings.py",
    "listings/saved_search_notification_email_sender.py",
    (
        "listings/management/commands/"
        "process_saved_search_notifications.py"
    ),
    (
        "listings/"
        "saved_search_notification_production_readiness.py"
    ),
    (
        "listings/management/commands/"
        "check_saved_search_notification_production_readiness.py"
    ),
    "listings/saved_search_notification_scheduler.py",
    "listings/saved_search_notifications.py",
    "listings/saved_search_notification_audit_runtime.py",
    "listings/saved_search_notification_audit_persistence.py",
    "listings/saved_search_notification_audit.py",
    "listings/saved_search_notification_email_renderer.py",
    "listings/models.py",
    "listings/admin.py",
    "listings/urls.py",
    "templates/base.html",
    (
        "listings/templates/listings/"
        "saved_search_notification_audit_events.html"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_closeout_audit_v255.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotExecutionAuthorizationContractV256Tests(
    SimpleTestCase
):
    maxDiff = None

    def _backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    def _read_backend(
        self,
        relative_path: str,
    ) -> str:
        return (
            self._backend_root()
            / relative_path
        ).read_text(
            encoding="utf-8",
            errors="strict",
        )

    def test_v256_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT,
            (
                "V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V255_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V256_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V257_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v257: saved-search notification production "
                "delivery pilot execution authorization implementation"
            ),
        )

    def test_v256_v257_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V257_ALLOWED_SCOPE,
            (
                (
                    "backend/listings/"
                    "test_saved_search_notification_production_delivery_"
                    "pilot_execution_authorization_v257.py"
                ),
                (
                    "docs/"
                    "saved_search_notification_production_delivery_"
                    "pilot_execution_authorization_v257.md"
                ),
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V257_ALLOWED_SCOPE
            )
        )

    def test_v256_limit_and_time_windows_are_exact(self):
        self.assertEqual(
            AUTHORIZATION_LIMIT_BAND,
            (
                1,
                3,
            ),
        )

        self.assertEqual(
            AUTHORIZATION_TIME_WINDOWS_SECONDS,
            {
                "readiness_max_age": 300,
                "preview_max_age": 300,
                "authorization_ttl": 600,
            },
        )

    def test_v256_authorization_stage_order_is_exact(self):
        self.assertEqual(
            AUTHORIZATION_STAGE_ORDER,
            (
                "collect immutable bindings",
                "verify fresh readiness",
                "verify fresh matching preview",
                "verify provider and sender state",
                "verify reviewer approvals",
                "issue one-shot authorization",
                "consume or terminate authorization",
                "perform mandatory post-run review",
            ),
        )

    def test_v256_required_fields_are_complete(self):
        required = {
            "authorization_id",
            "change_record_id",
            "pilot_owner_id",
            "approved_limit",
            "preview_owner_id",
            "preview_limit",
            "preview_candidate_count",
            "readiness_status",
            "readiness_checked_at_utc",
            "preview_checked_at_utc",
            "issued_at_utc",
            "expires_at_utc",
            "operator_identity",
            "primary_reviewer_identity",
            "secondary_reviewer_identity",
            "provider_status",
            "sender_verification_status",
            "feature_gate_verified",
            "backend_policy_verified",
            "rollback_reviewer_identity",
            "command_fingerprint",
            "authorization_state",
            "consumed_at_utc",
            "incident_reference",
        }

        self.assertEqual(
            set(AUTHORIZATION_REQUIRED_FIELDS),
            required,
        )

    def test_v256_immutable_bindings_are_complete(self):
        required = {
            "authorization_id",
            "change_record_id",
            "pilot_owner_id",
            "approved_limit",
            "preview_owner_id",
            "preview_limit",
            "preview_candidate_count",
            "operator_identity",
            "primary_reviewer_identity",
            "secondary_reviewer_identity",
            "command_fingerprint",
            "issued_at_utc",
            "expires_at_utc",
        }

        self.assertEqual(
            set(AUTHORIZATION_IMMUTABLE_BINDINGS),
            required,
        )

    def test_v256_lifecycle_and_terminal_states_are_exact(self):
        self.assertEqual(
            AUTHORIZATION_LIFECYCLE_STATES,
            (
                "draft",
                "ready_for_review",
                "authorized",
                "consumed",
                "expired",
                "revoked",
                "failed_closed",
            ),
        )

        self.assertEqual(
            AUTHORIZATION_TERMINAL_STATES,
            (
                "consumed",
                "expired",
                "revoked",
                "failed_closed",
            ),
        )

        self.assertTrue(
            set(AUTHORIZATION_TERMINAL_STATES).issubset(
                AUTHORIZATION_LIFECYCLE_STATES
            )
        )

    def test_v256_preconditions_are_complete(self):
        required = {
            "pilot-readiness lane is closed",
            "authorization checkpoint remains documentation and test only",
            "positive owner identifier is approved",
            "pilot limit is between 1 and 3",
            "preview owner matches approved owner",
            "preview limit matches approved limit",
            "preview candidate count is between 1 and approved limit",
            "strict readiness status is ready",
            "all nine readiness checks are present",
            "readiness evidence age is at most 300 seconds",
            "preview evidence age is at most 300 seconds",
            "authorization lifetime is at most 600 seconds",
            "feature gate remains enabled",
            "approved email backend remains configured",
            "default sender remains configured",
            "sender identity or domain remains verified",
            "provider credentials remain available",
            "provider quota covers approved limit",
            "provider status remains operational",
            "no concurrent owner-scoped run exists",
            "no unresolved incident exists",
            "rollback reviewer remains available",
            "primary reviewer approval is explicit",
            "secondary reviewer approval is explicit",
            "operator and reviewers are recorded",
            "command fingerprint matches approved owner and limit",
            "production command retains both confirmation flags",
            "authorization permits exactly one invocation",
        }

        self.assertEqual(
            set(AUTHORIZATION_PRECONDITIONS),
            required,
        )

    def test_v256_v255_preconditions_remain_included(self):
        self.assertEqual(
            len(PILOT_EXECUTION_AUTHORIZATION_PRECONDITIONS),
            16,
        )

        self.assertIn(
            "authorization permits at most one invocation",
            PILOT_EXECUTION_AUTHORIZATION_PRECONDITIONS,
        )

        self.assertIn(
            "production requires both confirmation flags",
            PILOT_EXECUTION_AUTHORIZATION_PRECONDITIONS,
        )

    def test_v256_command_fingerprint_fields_are_exact(self):
        self.assertEqual(
            AUTHORIZATION_COMMAND_FINGERPRINT_FIELDS,
            (
                "command_name",
                "execute_production_send",
                "confirm_production_delivery",
                "owner_id",
                "limit",
            ),
        )

    def test_v256_preview_command_is_nonproduction(self):
        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            AUTHORIZATION_PREVIEW_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            AUTHORIZATION_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--execute-production-send",
            AUTHORIZATION_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--confirm-production-delivery",
            AUTHORIZATION_PREVIEW_COMMAND,
        )

    def test_v256_production_command_retains_all_controls(self):
        self.assertIn(
            "--execute-production-send",
            AUTHORIZATION_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--confirm-production-delivery",
            AUTHORIZATION_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            AUTHORIZATION_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            AUTHORIZATION_PRODUCTION_COMMAND,
        )

    def test_v256_stop_reasons_are_complete(self):
        required = {
            "pilot_readiness_lane_not_closed",
            "invalid_owner_id",
            "invalid_pilot_limit",
            "preview_owner_mismatch",
            "preview_limit_mismatch",
            "preview_candidate_count_invalid",
            "readiness_not_ready",
            "readiness_check_count_mismatch",
            "readiness_evidence_stale",
            "preview_evidence_stale",
            "authorization_ttl_invalid",
            "authorization_expired",
            "authorization_already_consumed",
            "authorization_revoked",
            "authorization_failed_closed",
            "feature_gate_disabled",
            "email_backend_rejected",
            "default_sender_missing",
            "sender_unverified",
            "provider_credentials_unavailable",
            "provider_quota_insufficient",
            "provider_not_operational",
            "concurrent_owner_run",
            "unresolved_incident",
            "rollback_reviewer_missing",
            "primary_reviewer_missing",
            "secondary_reviewer_missing",
            "reviewer_identity_collision",
            "operator_identity_missing",
            "command_fingerprint_mismatch",
            "production_confirmation_missing",
        }

        self.assertEqual(
            set(AUTHORIZATION_STOP_REASONS),
            required,
        )

    def test_v256_evidence_fields_are_complete(self):
        required = {
            "authorization_id",
            "change_record_id",
            "pilot_owner_id",
            "approved_limit",
            "preview_candidate_count",
            "readiness_status",
            "readiness_ready_count",
            "readiness_not_ready_count",
            "readiness_warning_count",
            "readiness_checked_at_utc",
            "preview_checked_at_utc",
            "issued_at_utc",
            "expires_at_utc",
            "operator_identity",
            "primary_reviewer_identity",
            "secondary_reviewer_identity",
            "provider_status",
            "sender_verification_status",
            "feature_gate_verified",
            "backend_policy_verified",
            "rollback_reviewer_identity",
            "command_fingerprint",
            "authorization_state",
            "consumed_at_utc",
            "decision",
            "reason_codes",
            "incident_reference",
        }

        self.assertEqual(
            set(AUTHORIZATION_EVIDENCE_FIELDS),
            required,
        )

    def test_v256_privacy_exclusions_are_complete(self):
        required = {
            "SMTP password",
            "confidential SMTP username",
            "API key",
            "access token",
            "recipient email address",
            "default sender value",
            "raw backend path",
            "saved-search name",
            "saved-search querystring",
            "rendered email subject",
            "rendered email body",
            "provider response body",
            "raw exception traceback",
        }

        self.assertEqual(
            set(AUTHORIZATION_PRIVACY_EXCLUSIONS),
            required,
        )

    def test_v256_prohibited_actions_are_complete(self):
        required = {
            "production delivery during contract checkpoint",
            "authorization without positive owner identifier",
            "authorization without explicit pilot limit",
            "authorization with limit below 1",
            "authorization with limit above 3",
            "authorization with stale readiness evidence",
            "authorization with stale preview evidence",
            "authorization longer than 600 seconds",
            "authorization without two reviewer approvals",
            "authorization with identical reviewer identities",
            "owner change after authorization",
            "limit change after authorization",
            "command fingerprint change after authorization",
            "authorization reuse",
            "authorization after expiration",
            "authorization after revocation",
            "global all-owner execution",
            "multi-owner command execution",
            "readiness bypass",
            "preview bypass",
            "production confirmation bypass",
            "provider verification bypass",
            "blind retry",
            "automatic authorization renewal",
            "automatic phase promotion",
            "automatic scheduler enablement",
            "Celery enablement",
            "cron enablement",
            "startup-time delivery",
            "request-time delivery",
            "manual sent timestamp edit",
            "manual audit-event deletion",
            "direct SQL repair",
            "Django shell timestamp repair",
            "credential logging",
            "recipient payload logging",
            "saved-search payload logging",
        }

        self.assertEqual(
            set(AUTHORIZATION_PROHIBITED_ACTIONS),
            required,
        )

    def test_v256_default_readiness_remains_not_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        self.assertFalse(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "not_ready",
        )

        self.assertEqual(
            tuple(
                check["check_id"]
                for check in result["checks"]
            ),
            READINESS_CHECK_IDS,
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v256_production_like_readiness_remains_ready(self):
        result = (
            get_saved_search_notification_production_readiness()
        )

        self.assertTrue(
            result["ready"]
        )

        self.assertEqual(
            result["status"],
            "ready",
        )

        self.assertEqual(
            result["ready_count"],
            len(READINESS_CHECK_IDS),
        )

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v256_readiness_execution_opens_no_email_connection(self):
        stdout = StringIO()

        with patch(
            "django.core.mail.get_connection"
        ) as get_connection:
            call_command(
                "check_saved_search_notification_production_readiness",
                "--strict",
                stdout=stdout,
            )

        get_connection.assert_not_called()

        self.assertIn(
            "status=ready",
            stdout.getvalue(),
        )

    def test_v256_command_surfaces_remain_unchanged(self):
        readiness_source = self._read_backend(
            "listings/management/commands/"
            "check_saved_search_notification_production_readiness.py"
        )

        production_source = self._read_backend(
            "listings/management/commands/"
            "process_saved_search_notifications.py"
        )

        readiness_tree = ast.parse(
            readiness_source
        )

        production_tree = ast.parse(
            production_source
        )

        readiness_options = {
            argument.value
            for node in ast.walk(readiness_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        }

        production_options = {
            argument.value
            for node in ast.walk(production_tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
            for argument in node.args
            if isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
            and argument.value.startswith("--")
        }

        self.assertEqual(
            readiness_options,
            {
                "--strict",
                "--json",
            },
        )

        self.assertTrue(
            {
                "--execute-production-send",
                "--confirm-production-delivery",
                "--owner-id",
                "--limit",
            }.issubset(
                production_options
            )
        )

    def test_v256_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

        self.assertIn(
            "send_saved_search_notification_email_production",
            source,
        )

    def test_v256_scheduler_remains_nonautomatic(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_scheduler.py"
        )

        forbidden = (
            "--execute-production-send",
            "--confirm-production-delivery",
            "send_saved_search_notification_email_production",
            "Celery",
            "celery",
            "cron",
            "startup",
            "ready(",
        )

        for term in forbidden:
            with self.subTest(
                term=term
            ):
                self.assertNotIn(
                    term,
                    source,
                )

    def test_v256_v255_closeout_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_readiness_closeout_audit_v255.py"
        )

        self.assertIn(
            (
                "V255_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_READINESS_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            (
                "v256: saved-search notification production "
                "delivery pilot execution authorization contract"
            ),
            source,
        )

    def test_v256_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V256_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_EXECUTION_AUTHORIZATION_CONTRACT
        )

        for relative_path in PROTECTED_RUNTIME_PATHS:
            source = self._read_backend(
                relative_path
            )

            with self.subTest(
                relative_path=relative_path
            ):
                self.assertNotIn(
                    marker,
                    source,
                )

    def test_v256_no_migration_0017_exists(self):
        migration_directory = (
            self._backend_root()
            / "listings"
            / "migrations"
        )

        self.assertEqual(
            list(
                migration_directory.glob(
                    "0017*"
                )
            ),
            [],
        )

    def test_v256_acceptance_gate_matrix_is_complete(self):
        required = {
            "v255 pilot-readiness closeout remains packaged",
            "v256 scope is exactly two contract files",
            "v257 implementation scope is exactly two files",
            "v257 remains documentation and test only",
            "authorization limit band is exactly 1 through 3",
            "readiness evidence freshness is 300 seconds",
            "preview evidence freshness is 300 seconds",
            "authorization lifetime is 600 seconds",
            "authorization stage order is deterministic",
            "authorization required fields are explicit",
            "authorization immutable bindings are explicit",
            "authorization lifecycle states are explicit",
            "terminal states are explicit",
            "authorization is one-shot",
            "authorization cannot be reused",
            "owner binding is immutable",
            "limit binding is immutable",
            "strict readiness must report ready",
            "all nine readiness checks remain required",
            "two explicit reviewer approvals are required",
            "reviewer identities must be distinct",
            "command fingerprint is mandatory",
            "production retains both confirmation flags",
            "contract checkpoint performs no delivery",
            "global execution is prohibited",
            "multi-owner execution is prohibited",
            "authorization reuse is prohibited",
            "automatic renewal is prohibited",
            "blind retry is prohibited",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service and command remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(V256_ACCEPTANCE_GATES)
            )
        )
