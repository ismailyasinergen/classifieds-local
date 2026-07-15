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


V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CONTRACT = (
    "V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CONTRACT"
)

V252_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_closeout_audit_v252.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "controlled_rollout_closeout_audit_v252.md"
    ),
)

V253_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_contract_v253.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_readiness_contract_v253.md"
    ),
)

V254_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_readiness_v254.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_readiness_v254.md"
    ),
)

PILOT_LIMIT_BAND = (
    1,
    3,
)

PILOT_OWNER_ELIGIBILITY = (
    "positive owner identifier is recorded",
    "owner approval is explicit",
    "owner scope can be isolated",
    "owner has an enabled notification opt-in",
    "owner has at least one eligible due saved search",
    "owner has a usable recipient address",
    "pilot candidate count fits within 1 through 3",
    "no concurrent run targets the same owner",
    "no unresolved delivery incident targets the owner",
    "no unresolved rollback incident targets the owner",
    "owner and limit approval remain valid for the execution window",
)

PILOT_ENVIRONMENT_EVIDENCE = (
    "feature gate is explicitly enabled",
    "approved production email backend is configured",
    "default sender is configured",
    "sender identity or domain is provider verified",
    "provider credentials are available outside retained evidence",
    "provider quota is sufficient for a maximum of three deliveries",
    "provider status is operational",
    "bounce and complaint review ownership is assigned",
    "execution window is approved",
    "rollback reviewer is available",
)

PILOT_READINESS_GATES = (
    "strict readiness reports ready",
    "all nine readiness checks are present",
    "sanitized readiness JSON is retained",
    "owner eligibility is complete",
    "environment evidence is complete",
    "pilot limit is between 1 and 3",
    "preview owner matches approved owner",
    "preview limit matches approved limit",
    "preview contains no production confirmation flags",
    "preview candidate count is greater than zero",
    "preview candidate count does not exceed approved limit",
    "preview skip reasons are understood",
    "no unexpected refusal exists",
    "no unresolved incident exists",
    "persistent audit interface is accessible to the authorized reviewer",
    "deployed production command help has been reviewed",
    "rollback controls have been source verified",
)

PILOT_PREVIEW_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

PILOT_PRODUCTION_COMMAND = (
    "docker compose exec -T web python manage.py "
    "process_saved_search_notifications "
    "--execute-production-send "
    "--confirm-production-delivery "
    "--owner-id <POSITIVE_OWNER_ID> "
    "--limit <1-3>"
)

PILOT_GO_GATES = (
    "strict readiness passed immediately before preview",
    "sanitized readiness JSON was retained",
    "approved owner remained unchanged",
    "approved limit remained unchanged",
    "preview owner matched approved owner",
    "preview limit matched approved limit",
    "preview candidate count was between 1 and 3",
    "preview classifications were understood",
    "provider status remained operational",
    "no concurrent owner-scoped run was detected",
    "reviewer approved the pilot invocation",
)

PILOT_POST_RUN_SUCCESS_GATES = (
    "failed count equals zero",
    "unexpected refusal count equals zero",
    "delivery counts reconcile",
    "delivery_attempted event exists",
    "delivery_succeeded event exists for each success",
    "sent_timestamp_recorded event exists for each success",
    "sent timestamp evidence is consistent",
    "no sent timestamp exists for a failed item",
    "duplicate-attempt review is clean",
    "no unexplained audit gap exists",
    "no provider anomaly exists",
    "no privacy or secret incident is open",
    "reviewer records go or stop decision",
)

PILOT_STOP_CONDITIONS = (
    "readiness status is not ready",
    "one or more readiness checks are absent",
    "feature gate is disabled",
    "email backend is rejected",
    "default sender is missing",
    "sender identity or domain is unverified",
    "provider status is degraded or unknown",
    "provider quota is insufficient",
    "owner eligibility is incomplete",
    "owner authorization is missing",
    "owner scope cannot be isolated",
    "pilot limit is outside 1 through 3",
    "preview owner differs from approved owner",
    "preview limit differs from approved limit",
    "preview candidate count is zero",
    "preview candidate count exceeds approved limit",
    "preview classifications are not understood",
    "another operator may be running the same owner scope",
    "configuration refusal is reported",
    "delivery failure is reported",
    "persistent audit evidence is incomplete",
    "sent timestamp evidence is inconsistent",
    "duplicate-attempt protection activates unexpectedly",
    "provider behavior is unexpected",
    "sanitized counts cannot be reconciled",
    "an unknown reason code appears",
    "private data or a secret may have appeared",
    "an incident remains open",
)

PILOT_EVIDENCE_FIELDS = (
    "change_record_id",
    "pilot_owner_id",
    "approved_limit",
    "operator_identity",
    "reviewer_identity",
    "execution_window",
    "started_at_utc",
    "finished_at_utc",
    "feature_gate_verified",
    "backend_policy_verified",
    "sender_verification_status",
    "provider_status",
    "provider_quota_verified",
    "readiness_status",
    "readiness_ready_count",
    "readiness_not_ready_count",
    "readiness_warning_count",
    "preview_candidate_count",
    "preview_skipped_count",
    "production_delivered_count",
    "production_skipped_count",
    "production_refused_count",
    "production_failed_count",
    "audit_verified",
    "sent_timestamp_verified",
    "duplicate_attempt_verified",
    "rollback_readiness_verified",
    "decision",
    "incident_reference",
)

PILOT_PRIVACY_EXCLUSIONS = (
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

PILOT_PROHIBITED_ACTIONS = (
    "production delivery during contract checkpoint",
    "pilot execution without explicit owner approval",
    "pilot execution without reviewer approval",
    "pilot limit above 3",
    "pilot limit below 1",
    "global all-owner execution",
    "multi-owner command execution",
    "owner change after preview",
    "limit change after preview",
    "readiness bypass",
    "preview bypass",
    "production confirmation bypass",
    "provider verification bypass",
    "blind retry",
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
    "silent partial-failure handling",
)

V253_ACCEPTANCE_GATES = (
    "v252 controlled-rollout closeout remains packaged",
    "v253 scope is exactly two contract files",
    "v254 implementation scope is exactly two files",
    "v254 implementation is documentation and test only",
    "pilot limit band is exactly 1 through 3",
    "pilot execution remains single-owner scoped",
    "owner eligibility requirements are explicit",
    "environment evidence requirements are explicit",
    "strict readiness is mandatory",
    "all nine readiness checks remain required",
    "sanitized readiness JSON evidence is mandatory",
    "provider and sender verification are mandatory",
    "matching owner-scoped preview is mandatory",
    "preview contains no production confirmation flags",
    "production requires both confirmation flags",
    "preview candidate count must be between 1 and 3",
    "go gates are explicit",
    "post-run success gates are explicit",
    "stop conditions are explicit",
    "failed count must be zero",
    "unexpected refusal count must be zero",
    "delivery counts must reconcile",
    "persistent audit verification is mandatory",
    "sent timestamp verification is mandatory",
    "duplicate-attempt review is mandatory",
    "rollback readiness is mandatory",
    "open incidents block execution",
    "evidence fields are explicit",
    "privacy exclusions are explicit",
    "contract checkpoint performs no delivery",
    "global all-owner execution is prohibited",
    "multi-owner execution is prohibited",
    "pilot limit above 3 is prohibited",
    "blind retry is prohibited",
    "manual database repair is prohibited",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service and command remain unchanged",
    "scheduler remains nonautomatic",
    "models admin URLs templates and migrations remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v254: saved-search notification production delivery pilot readiness implementation"

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
        "controlled_rollout_closeout_audit_v252.py"
    ),
)

HISTORICAL_SAFETY_TEST_PATHS = (
    (
        "listings/"
        "test_saved_search_notification_explicit_send_"
        "test_backend_v222.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_rollback_audit_"
        "hardening_v224.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "design_audit_v225.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_audit_runtime_"
        "integration_v232.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_persistent_audit_"
        "operator_shared_shell_integration_closeout_audit_v240.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_contract_v241.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "implementation_v242.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "closeout_audit_v243.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_contract_v244.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_v245.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operational_readiness_closeout_audit_v246.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_contract_v247.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_v248.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "operator_runbook_closeout_audit_v249.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_contract_v250.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_v251.py"
    ),
    (
        "listings/"
        "test_saved_search_notification_production_delivery_"
        "controlled_rollout_closeout_audit_v252.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotReadinessContractV253Tests(
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

    def test_v253_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CONTRACT,
            (
                "V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_READINESS_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V252_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V253_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V254_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v254: saved-search notification production "
                "delivery pilot readiness implementation"
            ),
        )

    def test_v253_v254_scope_is_documentation_and_test_only(self):
        self.assertEqual(
            V254_ALLOWED_SCOPE,
            (
                (
                    "backend/listings/"
                    "test_saved_search_notification_production_delivery_"
                    "pilot_readiness_v254.py"
                ),
                (
                    "docs/"
                    "saved_search_notification_production_delivery_"
                    "pilot_readiness_v254.md"
                ),
            ),
        )

        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V254_ALLOWED_SCOPE
            )
        )

    def test_v253_pilot_limit_band_is_exact(self):
        self.assertEqual(
            PILOT_LIMIT_BAND,
            (
                1,
                3,
            ),
        )

    def test_v253_owner_eligibility_contract_is_complete(self):
        required = {
            "positive owner identifier is recorded",
            "owner approval is explicit",
            "owner scope can be isolated",
            "owner has an enabled notification opt-in",
            "owner has at least one eligible due saved search",
            "owner has a usable recipient address",
            "pilot candidate count fits within 1 through 3",
            "no concurrent run targets the same owner",
            "no unresolved delivery incident targets the owner",
            "no unresolved rollback incident targets the owner",
            "owner and limit approval remain valid for the execution window",
        }

        self.assertEqual(
            set(PILOT_OWNER_ELIGIBILITY),
            required,
        )

    def test_v253_environment_evidence_contract_is_complete(self):
        required = {
            "feature gate is explicitly enabled",
            "approved production email backend is configured",
            "default sender is configured",
            "sender identity or domain is provider verified",
            "provider credentials are available outside retained evidence",
            "provider quota is sufficient for a maximum of three deliveries",
            "provider status is operational",
            "bounce and complaint review ownership is assigned",
            "execution window is approved",
            "rollback reviewer is available",
        }

        self.assertEqual(
            set(PILOT_ENVIRONMENT_EVIDENCE),
            required,
        )

    def test_v253_readiness_gate_contract_is_complete(self):
        required = {
            "strict readiness reports ready",
            "all nine readiness checks are present",
            "sanitized readiness JSON is retained",
            "owner eligibility is complete",
            "environment evidence is complete",
            "pilot limit is between 1 and 3",
            "preview owner matches approved owner",
            "preview limit matches approved limit",
            "preview contains no production confirmation flags",
            "preview candidate count is greater than zero",
            "preview candidate count does not exceed approved limit",
            "preview skip reasons are understood",
            "no unexpected refusal exists",
            "no unresolved incident exists",
            "persistent audit interface is accessible to the authorized reviewer",
            "deployed production command help has been reviewed",
            "rollback controls have been source verified",
        }

        self.assertEqual(
            set(PILOT_READINESS_GATES),
            required,
        )

    def test_v253_preview_command_is_owner_scoped_and_nonproduction(self):
        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            PILOT_PREVIEW_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            PILOT_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--execute-production-send",
            PILOT_PREVIEW_COMMAND,
        )

        self.assertNotIn(
            "--confirm-production-delivery",
            PILOT_PREVIEW_COMMAND,
        )

    def test_v253_production_command_has_all_controls(self):
        self.assertIn(
            "--execute-production-send",
            PILOT_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--confirm-production-delivery",
            PILOT_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--owner-id <POSITIVE_OWNER_ID>",
            PILOT_PRODUCTION_COMMAND,
        )

        self.assertIn(
            "--limit <1-3>",
            PILOT_PRODUCTION_COMMAND,
        )

    def test_v253_go_gates_are_complete(self):
        required = {
            "strict readiness passed immediately before preview",
            "sanitized readiness JSON was retained",
            "approved owner remained unchanged",
            "approved limit remained unchanged",
            "preview owner matched approved owner",
            "preview limit matched approved limit",
            "preview candidate count was between 1 and 3",
            "preview classifications were understood",
            "provider status remained operational",
            "no concurrent owner-scoped run was detected",
            "reviewer approved the pilot invocation",
        }

        self.assertEqual(
            set(PILOT_GO_GATES),
            required,
        )

    def test_v253_post_run_success_gates_are_complete(self):
        required = {
            "failed count equals zero",
            "unexpected refusal count equals zero",
            "delivery counts reconcile",
            "delivery_attempted event exists",
            "delivery_succeeded event exists for each success",
            "sent_timestamp_recorded event exists for each success",
            "sent timestamp evidence is consistent",
            "no sent timestamp exists for a failed item",
            "duplicate-attempt review is clean",
            "no unexplained audit gap exists",
            "no provider anomaly exists",
            "no privacy or secret incident is open",
            "reviewer records go or stop decision",
        }

        self.assertEqual(
            set(PILOT_POST_RUN_SUCCESS_GATES),
            required,
        )

    def test_v253_stop_conditions_are_complete(self):
        required = {
            "readiness status is not ready",
            "one or more readiness checks are absent",
            "feature gate is disabled",
            "email backend is rejected",
            "default sender is missing",
            "sender identity or domain is unverified",
            "provider status is degraded or unknown",
            "provider quota is insufficient",
            "owner eligibility is incomplete",
            "owner authorization is missing",
            "owner scope cannot be isolated",
            "pilot limit is outside 1 through 3",
            "preview owner differs from approved owner",
            "preview limit differs from approved limit",
            "preview candidate count is zero",
            "preview candidate count exceeds approved limit",
            "preview classifications are not understood",
            "another operator may be running the same owner scope",
            "configuration refusal is reported",
            "delivery failure is reported",
            "persistent audit evidence is incomplete",
            "sent timestamp evidence is inconsistent",
            "duplicate-attempt protection activates unexpectedly",
            "provider behavior is unexpected",
            "sanitized counts cannot be reconciled",
            "an unknown reason code appears",
            "private data or a secret may have appeared",
            "an incident remains open",
        }

        self.assertEqual(
            set(PILOT_STOP_CONDITIONS),
            required,
        )

    def test_v253_evidence_fields_are_complete(self):
        required = {
            "change_record_id",
            "pilot_owner_id",
            "approved_limit",
            "operator_identity",
            "reviewer_identity",
            "execution_window",
            "started_at_utc",
            "finished_at_utc",
            "feature_gate_verified",
            "backend_policy_verified",
            "sender_verification_status",
            "provider_status",
            "provider_quota_verified",
            "readiness_status",
            "readiness_ready_count",
            "readiness_not_ready_count",
            "readiness_warning_count",
            "preview_candidate_count",
            "preview_skipped_count",
            "production_delivered_count",
            "production_skipped_count",
            "production_refused_count",
            "production_failed_count",
            "audit_verified",
            "sent_timestamp_verified",
            "duplicate_attempt_verified",
            "rollback_readiness_verified",
            "decision",
            "incident_reference",
        }

        self.assertEqual(
            set(PILOT_EVIDENCE_FIELDS),
            required,
        )

    def test_v253_privacy_exclusions_are_complete(self):
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
            set(PILOT_PRIVACY_EXCLUSIONS),
            required,
        )

    def test_v253_prohibited_actions_are_complete(self):
        required = {
            "production delivery during contract checkpoint",
            "pilot execution without explicit owner approval",
            "pilot execution without reviewer approval",
            "pilot limit above 3",
            "pilot limit below 1",
            "global all-owner execution",
            "multi-owner command execution",
            "owner change after preview",
            "limit change after preview",
            "readiness bypass",
            "preview bypass",
            "production confirmation bypass",
            "provider verification bypass",
            "blind retry",
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
            "silent partial-failure handling",
        }

        self.assertEqual(
            set(PILOT_PROHIBITED_ACTIONS),
            required,
        )

    def test_v253_default_readiness_remains_not_ready(self):
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
    def test_v253_production_like_readiness_remains_ready(self):
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
    def test_v253_readiness_execution_opens_no_email_connection(self):
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

    def test_v253_command_surfaces_remain_unchanged(self):
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

    def test_v253_production_batch_cap_remains_25(self):
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

    def test_v253_scheduler_remains_nonautomatic(self):
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

    def test_v253_v252_closeout_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "controlled_rollout_closeout_audit_v252.py"
        )

        self.assertIn(
            (
                "V252_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_CONTROLLED_ROLLOUT_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            (
                "v253: saved-search notification production "
                "delivery pilot readiness contract"
            ),
            source,
        )

    def test_v253_historical_safety_package_is_present(self):
        for relative_path in HISTORICAL_SAFETY_TEST_PATHS:
            with self.subTest(
                relative_path=relative_path
            ):
                self.assertTrue(
                    (
                        self._backend_root()
                        / relative_path
                    ).is_file()
                )

    def test_v253_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V253_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_READINESS_CONTRACT
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

    def test_v253_no_migration_0017_exists(self):
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

    def test_v253_acceptance_gate_matrix_is_complete(self):
        required = {
            "v252 controlled-rollout closeout remains packaged",
            "v253 scope is exactly two contract files",
            "v254 implementation scope is exactly two files",
            "v254 implementation is documentation and test only",
            "pilot limit band is exactly 1 through 3",
            "pilot execution remains single-owner scoped",
            "owner eligibility requirements are explicit",
            "environment evidence requirements are explicit",
            "strict readiness is mandatory",
            "all nine readiness checks remain required",
            "sanitized readiness JSON evidence is mandatory",
            "provider and sender verification are mandatory",
            "matching owner-scoped preview is mandatory",
            "preview contains no production confirmation flags",
            "production requires both confirmation flags",
            "preview candidate count must be between 1 and 3",
            "go gates are explicit",
            "post-run success gates are explicit",
            "stop conditions are explicit",
            "failed count must be zero",
            "unexpected refusal count must be zero",
            "persistent audit verification is mandatory",
            "sent timestamp verification is mandatory",
            "duplicate-attempt review is mandatory",
            "rollback readiness is mandatory",
            "open incidents block execution",
            "contract checkpoint performs no delivery",
            "global all-owner execution is prohibited",
            "multi-owner execution is prohibited",
            "pilot limit above 3 is prohibited",
            "blind retry is prohibited",
            "manual database repair is prohibited",
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
                set(V253_ACCEPTANCE_GATES)
            )
        )
