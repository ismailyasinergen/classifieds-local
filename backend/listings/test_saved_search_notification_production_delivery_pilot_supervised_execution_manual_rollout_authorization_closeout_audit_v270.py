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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_contract_v268 import (
    MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS,
    MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST,
    MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS,
    MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT,
    MANUAL_ROLLOUT_AUTHORIZATION_MAX_OWNER_COUNT,
    MANUAL_ROLLOUT_AUTHORIZATION_PREVIEW_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS,
    MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS,
    MANUAL_ROLLOUT_AUTHORIZATION_PROVIDER_STATE_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_READINESS_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER,
    MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS,
    MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_ROLES,
    MANUAL_ROLLOUT_AUTHORIZATION_ROLE_SEPARATION_RULES,
    MANUAL_ROLLOUT_AUTHORIZATION_SENSITIVE_INPUT_KEYS,
    MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS,
    V268_ACCEPTANCE_GATES,
    build_complete_manual_rollout_authorization_candidate,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_authorization_v269 import (
    MANUAL_ROLLOUT_AUTHORIZATION_RESULT_FIELDS,
    V269_IMPLEMENTATION_GATES,
    V269_REASON_REACHABILITY_CASES,
    build_manual_rollout_authorization_evaluation_context,
    collect_manual_rollout_authorization_completeness_reasons,
    collect_manual_rollout_authorization_prohibited_action_reasons,
    collect_manual_rollout_authorization_scope_role_reasons,
    collect_manual_rollout_authorization_source_reasons,
    evaluate_manual_rollout_authorization,
    manual_rollout_authorization_immutable_snapshot,
    ordered_unique_manual_rollout_authorization_reasons,
    sanitize_manual_rollout_authorization_evidence,
)


V270_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CLOSEOUT_AUDIT = (
    "V270_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CLOSEOUT_AUDIT"
)

V269_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_v269.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_v269.md"
    ),
)

V270_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "closeout_audit_v270.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "closeout_audit_v270.md"
    ),
)

AUDIT_SERIES_STATUS = "closed"
NEXT_CHECKPOINT = None
NEXT_AUDIT_SCOPE = ()
NEXT_PROJECT_ACTION = "return to the product roadmap"

SAVED_SEARCH_NOTIFICATION_RELEASE_READINESS_SUMMARY = (
    "manual-rollout consideration contract is closed",
    "manual-rollout consideration implementation is closed",
    "manual-rollout consideration closeout is complete",
    "manual-rollout authorization contract is closed",
    "manual-rollout authorization implementation is closed",
    "manual-rollout authorization closeout is complete",
    "required authorization fields remain forty-six",
    "authorization reason codes remain forty-one",
    "all authorization reason codes remain reachable",
    "immutable bindings remain fourteen",
    "required roles remain seven",
    "owner scope remains one",
    "authorization limit remains three",
    "readiness freshness remains three hundred seconds",
    "preview freshness remains three hundred seconds",
    "provider-state freshness remains three hundred seconds",
    "authorization lifetime remains six hundred seconds",
    "positive result remains preparation only",
    "production command remains absent",
    "production delivery remains absent",
    "authorization consumption remains absent",
    "delivery retry remains absent",
    "scheduler remains disabled",
    "automatic rollout promotion remains disabled",
    "historical authorization remains nonreusable",
    "sensitive evidence remains excluded",
    "runtime schema scheduler and UI remain unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "saved-search notification audit series is closed",
)

V270_CLOSEOUT_GATES = (
    "v268 authorization contract remains packaged",
    "v269 authorization implementation remains packaged",
    "v269 committed scope remains exactly two files",
    "v270 scope remains exactly two closeout files",
    "no next audit scope is defined",
    "no v271 audit checkpoint is proposed",
    "audit series status is closed",
    "next project action returns to product roadmap",
    "closeout remains documentation and test only",
    "forty-six required fields remain exact",
    "forty-six required fields remain unique",
    "evidence allowlist remains exact",
    "fourteen immutable bindings remain exact",
    "seven required roles remain exact",
    "seven role-separation rules remain exact",
    "two authorization decisions remain exact",
    "not-authorized remains fail-closed",
    "forty-one reason codes remain exact",
    "forty-one reason codes remain unique",
    "all forty-one reason codes remain reachable",
    "reason ordering remains deterministic",
    "default candidate remains authorized for preparation only",
    "positive result returns no production command",
    "positive result performs no production delivery",
    "positive result consumes no authorization",
    "positive result performs no retry",
    "positive result enables no scheduler",
    "positive result performs no automatic promotion",
    "negative result remains fail-closed",
    "source consideration must remain eligible",
    "source reason codes must remain empty",
    "source evidence must remain sanitized",
    "source immutable snapshot must remain complete",
    "source preconditions must remain complete",
    "historical authorization reuse remains prohibited",
    "source owner remains positive",
    "authorization owner remains positive",
    "owners remain bound",
    "owner scope remains exactly one",
    "owner expansion remains rejected",
    "source approved limit remains one through three",
    "source considered limit remains one through three",
    "authorization limit remains one through three",
    "source limit expansion remains rejected",
    "authorization limit expansion remains rejected",
    "decision owner remains mandatory",
    "authorizing operator remains mandatory",
    "reviewer identities remain mandatory",
    "authorizing operator overlap remains rejected",
    "decision owner overlap remains rejected",
    "reviewer duplication remains rejected",
    "readiness freshness remains inclusive at three hundred seconds",
    "preview freshness remains inclusive at three hundred seconds",
    "provider-state freshness remains inclusive at three hundred seconds",
    "authorization lifetime remains inclusive at six hundred seconds",
    "stale readiness remains rejected",
    "stale preview remains rejected",
    "stale provider state remains rejected",
    "future readiness remains rejected",
    "future preview remains rejected",
    "future provider state remains rejected",
    "future authorization creation remains rejected",
    "expired authorization remains rejected",
    "changed readiness fingerprint remains rejected",
    "changed preview fingerprint remains rejected",
    "changed provider fingerprint remains rejected",
    "changed sender fingerprint remains rejected",
    "changed backend fingerprint remains rejected",
    "changed command fingerprint remains rejected",
    "changed freeze fingerprint remains rejected",
    "both production confirmations remain mandatory",
    "feature-gate expected state remains mandatory",
    "authorization begins prepared",
    "authorization begins unconsumed",
    "authorization begins with zero production invocations",
    "production delivery during preparation remains rejected",
    "authorization consumption during preparation remains rejected",
    "production invocation during preparation remains rejected",
    "retry during preparation remains rejected",
    "scheduler enablement during preparation remains rejected",
    "automatic promotion during preparation remains rejected",
    "computed reason codes remain unspoofable",
    "computed authorization state remains unspoofable",
    "strict sanitizer retains exact allowlist",
    "unknown fields remain discarded",
    "sensitive fields remain discarded",
    "sensitive values remain absent from output",
    "immutable snapshot remains exact",
    "immutable snapshot remains deterministic",
    "single-execution requirements remain exact",
    "evaluator remains pure and in-memory",
    "evaluator invokes no subprocess",
    "evaluator invokes no management command",
    "evaluator opens no email connection",
    "evaluator performs no database mutation",
    "default readiness remains not-ready",
    "production-like readiness remains ready",
    "readiness evaluation opens no email connection",
    "production command controls remain unchanged",
    "production batch maximum remains twenty-five",
    "scheduler remains nonautomatic",
    "runtime remains unchanged",
    "schema remains unchanged",
    "browser UI remains unchanged",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "historical safety tests remain green",
    "full regression remains green",
    "release-readiness summary remains packaged",
    "saved-search notification audit series remains closed",
)

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
        "pilot_supervised_execution_manual_rollout_authorization_v269.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionManualRolloutAuthorizationCloseoutAuditV270Tests(
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

    def test_v270_marker_scope_and_final_status_are_stable(self):
        self.assertEqual(
            V270_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CLOSEOUT_AUDIT,
            (
                "V270_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_AUTHORIZATION_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V269_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V270_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            AUDIT_SERIES_STATUS,
            "closed",
        )

        self.assertIsNone(
            NEXT_CHECKPOINT
        )

        self.assertEqual(
            NEXT_AUDIT_SCOPE,
            (),
        )

        self.assertEqual(
            NEXT_PROJECT_ACTION,
            "return to the product roadmap",
        )

    def test_v270_scope_is_documentation_and_test_only(self):
        self.assertFalse(
            any(
                "/migrations/" in path
                or "/management/commands/" in path
                or "/templates/" in path
                for path in V270_ALLOWED_SCOPE
            )
        )

    def test_v270_contract_packages_remain_exact(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS
            ),
            46,
        )

        self.assertEqual(
            len(
                set(
                    MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS
                )
            ),
            46,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS
            ),
            14,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_ROLES
            ),
            7,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_ROLE_SEPARATION_RULES
            ),
            7,
        )

    def test_v270_decisions_and_results_remain_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS,
            (
                "not_authorized",
                "authorized_to_prepare_single_manual_execution",
            ),
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_RESULT_FIELDS
            ),
            11,
        )

    def test_v270_reason_package_remains_exact_and_unique(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
            ),
            41,
        )

        self.assertEqual(
            len(
                set(
                    MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
                )
            ),
            41,
        )

        self.assertEqual(
            len(V269_REASON_REACHABILITY_CASES),
            41,
        )

    def test_v270_default_candidate_remains_preparation_only(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate()
        )

        self.assertEqual(
            tuple(result),
            MANUAL_ROLLOUT_AUTHORIZATION_RESULT_FIELDS,
        )

        self.assertEqual(
            result["decision"],
            "authorized_to_prepare_single_manual_execution",
        )

        self.assertTrue(
            result["authorized"]
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["single_execution_requirements"],
            MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS,
        )

        self.assertIsNone(
            result["production_command"]
        )

        self.assertFalse(
            result["production_delivery_performed"]
        )

        self.assertFalse(
            result["authorization_consumed"]
        )

    def test_v270_negative_result_remains_fail_closed(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                source_consideration_eligible=False,
            )
        )

        self.assertEqual(
            result["decision"],
            "not_authorized",
        )

        self.assertFalse(
            result["authorized"]
        )

        self.assertEqual(
            result["single_execution_requirements"],
            (),
        )

        self.assertIsNone(
            result["owner_id"]
        )

        self.assertIsNone(
            result["approved_limit"]
        )

    def test_v270_all_reason_codes_remain_reachable(self):
        reached: set[str] = set()

        for (
            changes,
            removed_fields,
            context_changes,
            expected_reason,
        ) in V269_REASON_REACHABILITY_CASES:
            with self.subTest(
                expected_reason=expected_reason
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                for field in removed_fields:
                    candidate.pop(
                        field
                    )

                context = (
                    build_manual_rollout_authorization_evaluation_context(
                        **context_changes
                    )
                )

                result = evaluate_manual_rollout_authorization(
                    candidate,
                    context=context,
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

                self.assertIn(
                    expected_reason,
                    result["reason_codes"],
                )

                reached.add(
                    expected_reason
                )

        self.assertEqual(
            reached,
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
            ),
        )

    def test_v270_reason_order_remains_deterministic(self):
        reversed_reasons = tuple(
            reversed(
                MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER
            )
        )

        self.assertEqual(
            ordered_unique_manual_rollout_authorization_reasons(
                reversed_reasons
                + MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER[:10]
            ),
            MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER,
        )

    def test_v270_collectors_remain_empty_for_default_candidate(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        context = (
            build_manual_rollout_authorization_evaluation_context()
        )

        self.assertEqual(
            collect_manual_rollout_authorization_completeness_reasons(
                candidate
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_authorization_source_reasons(
                candidate
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_authorization_scope_role_reasons(
                candidate,
                context,
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_authorization_prohibited_action_reasons(
                candidate
            ),
            (),
        )

    def test_v270_historical_authorization_reuse_remains_rejected(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                authorization_id="authorization-001",
            )
        )

        self.assertIn(
            "historical_authorization_reuse_attempted",
            result["reason_codes"],
        )

    def test_v270_owner_scope_remains_one(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_MAX_OWNER_COUNT,
            1,
        )

        cases = (
            {
                "owner_id": 0,
            },
            {
                "source_owner_id": 0,
            },
            {
                "owner_id": 202,
            },
            {
                "source_considered_owner_ids": (
                    101,
                    202,
                ),
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

    def test_v270_authorization_limit_remains_bounded(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT,
            3,
        )

        cases = (
            {
                "approved_limit": 0,
            },
            {
                "approved_limit": 4,
            },
            {
                "source_approved_limit": 4,
            },
            {
                "source_considered_limit": 4,
            },
            {
                "source_considered_limit": 2,
                "approved_limit": 3,
            },
            {
                "source_approved_limit": 2,
                "source_considered_limit": 3,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

    def test_v270_role_overlap_remains_rejected(self):
        cases = (
            (
                {
                    "authorizing_operator_identity": (
                        "decision-owner-a"
                    ),
                },
                "authorizing_operator_role_overlap",
            ),
            (
                {
                    "decision_owner_identity": (
                        "evidence-reviewer-a"
                    ),
                },
                "decision_owner_role_overlap",
            ),
            (
                {
                    "privacy_reviewer_identity": (
                        "evidence-reviewer-a"
                    ),
                },
                "required_reviewer_identity_not_distinct",
            ),
            (
                {
                    "incident_commander_identity": (
                        "rollback-reviewer-a"
                    ),
                },
                "required_reviewer_identity_not_distinct",
            ),
        )

        for changes, expected_reason in cases:
            with self.subTest(
                expected_reason=expected_reason
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertIn(
                    expected_reason,
                    result["reason_codes"],
                )

    def test_v270_freshness_boundaries_remain_inclusive(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                readiness_generated_at_utc=1500,
                preview_generated_at_utc=1500,
                provider_state_generated_at_utc=1500,
            )
        )

        context = (
            build_manual_rollout_authorization_evaluation_context(
                current_timestamp_utc=1800,
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate,
            context=context,
        )

        self.assertEqual(
            result["decision"],
            "authorized_to_prepare_single_manual_execution",
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_READINESS_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_PREVIEW_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_PROVIDER_STATE_FRESHNESS_SECONDS,
            300,
        )

    def test_v270_authorization_lifetime_boundary_remains_inclusive(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                readiness_generated_at_utc=1500,
                preview_generated_at_utc=1500,
                provider_state_generated_at_utc=1500,
            )
        )

        context = (
            build_manual_rollout_authorization_evaluation_context(
                current_timestamp_utc=1800,
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate,
            context=context,
        )

        self.assertNotIn(
            "authorization_expired_or_future_dated",
            result["reason_codes"],
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS,
            600,
        )

    def test_v270_stale_and_future_evidence_remains_rejected(self):
        cases = (
            {
                "readiness_generated_at_utc": 899,
            },
            {
                "preview_generated_at_utc": 899,
            },
            {
                "provider_state_generated_at_utc": 899,
            },
            {
                "readiness_generated_at_utc": 1201,
            },
            {
                "preview_generated_at_utc": 1201,
            },
            {
                "provider_state_generated_at_utc": 1201,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

    def test_v270_invalid_authorization_windows_remain_rejected(self):
        cases = (
            {
                "authorization_created_at_utc": 1201,
            },
            {
                "authorization_created_at_utc": 500,
            },
            {
                "authorization_expires_at_utc": 1199,
            },
            {
                "authorization_created_at_utc": 1200,
                "authorization_expires_at_utc": 1801,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertIn(
                    "authorization_expired_or_future_dated",
                    result["reason_codes"],
                )

    def test_v270_all_fingerprint_changes_remain_rejected(self):
        cases = (
            {
                "readiness_evidence_fingerprint": "changed",
            },
            {
                "preview_evidence_fingerprint": "changed",
            },
            {
                "provider_state_fingerprint": "changed",
            },
            {
                "sender_state_fingerprint": "changed",
            },
            {
                "email_backend_state_fingerprint": "changed",
            },
            {
                "authorization_command_fingerprint": "changed",
            },
            {
                "pre_send_freeze_fingerprint": "changed",
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

    def test_v270_both_confirmations_remain_mandatory(self):
        for field in (
            "production_confirmation_primary",
            "production_confirmation_secondary",
        ):
            with self.subTest(
                field=field
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **{
                            field: False,
                        }
                    )
                )

                self.assertIn(
                    "source_preconditions_incomplete",
                    result["reason_codes"],
                )

    def test_v270_prohibited_actions_remain_rejected(self):
        cases = (
            (
                {
                    "production_delivery_performed": True,
                },
                "production_delivery_performed_during_authorization",
            ),
            (
                {
                    "authorization_consumption_count": 1,
                },
                "authorization_consumed_before_execution",
            ),
            (
                {
                    "production_invocation_count": 1,
                },
                "authorization_consumed_before_execution",
            ),
            (
                {
                    "retry_performed": True,
                },
                "retry_performed_during_authorization",
            ),
            (
                {
                    "scheduler_enabled": True,
                },
                "scheduler_enabled_during_authorization",
            ),
            (
                {
                    "automatic_promotion_performed": True,
                },
                "automatic_promotion_performed_during_authorization",
            ),
        )

        for changes, expected_reason in cases:
            with self.subTest(
                expected_reason=expected_reason
            ):
                result = evaluate_manual_rollout_authorization(
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_authorized",
                )

                self.assertIn(
                    expected_reason,
                    result["reason_codes"],
                )

    def test_v270_computed_reason_codes_remain_unspoofable(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                reason_codes=(
                    "production_delivery_performed_during_authorization",
                ),
            )
        )

        self.assertEqual(
            result["decision"],
            "authorized_to_prepare_single_manual_execution",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["sanitized_evidence"]["reason_codes"],
            (),
        )

    def test_v270_computed_authorization_state_remains_unspoofable(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                authorization_state="authorized",
            )
        )

        self.assertEqual(
            result["decision"],
            "not_authorized",
        )

        self.assertEqual(
            result["sanitized_evidence"]["authorization_state"],
            "rejected",
        )

    def test_v270_sanitizer_remains_exact(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                unknown_field="discard-me",
            )
        )

        result = evaluate_manual_rollout_authorization(
            candidate
        )

        sanitized = result[
            "sanitized_evidence"
        ]

        self.assertEqual(
            tuple(sanitized),
            MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST,
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        self.assertNotIn(
            "discard-me",
            repr(sanitized),
        )

    def test_v270_sensitive_values_remain_excluded(self):
        result = evaluate_manual_rollout_authorization(
            build_complete_manual_rollout_authorization_candidate(
                smtp_password="secret-value",
                recipient_email="private@example.invalid",
                rendered_body="private-body",
                provider_response_body="provider-private",
            )
        )

        rendered = repr(
            result
        )

        for value in (
            "secret-value",
            "private@example.invalid",
            "private-body",
            "provider-private",
        ):
            with self.subTest(
                value=value
            ):
                self.assertNotIn(
                    value,
                    rendered,
                )

        self.assertTrue(
            set(
                result["sanitized_evidence"]
            ).isdisjoint(
                MANUAL_ROLLOUT_AUTHORIZATION_SENSITIVE_INPUT_KEYS
            )
        )

    def test_v270_privacy_and_prohibition_packages_remain_complete(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS
            ),
            13,
        )

        self.assertIn(
            "SMTP password",
            MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "historical source authorization reuse",
            MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS,
        )

        self.assertIn(
            "automatic authorization renewal",
            MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS,
        )

    def test_v270_immutable_snapshot_remains_exact_and_deterministic(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        first = (
            manual_rollout_authorization_immutable_snapshot(
                candidate
            )
        )

        second = (
            manual_rollout_authorization_immutable_snapshot(
                candidate
            )
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            tuple(first),
            MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS,
        )

    def test_v270_evaluator_remains_nonexecuting(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        with (
            patch(
                "subprocess.run"
            ) as subprocess_run,
            patch(
                "django.core.mail.get_connection"
            ) as get_connection,
            patch(
                "django.core.management.call_command"
            ) as call_command_mock,
        ):
            result = evaluate_manual_rollout_authorization(
                candidate
            )

        subprocess_run.assert_not_called()
        get_connection.assert_not_called()
        call_command_mock.assert_not_called()

        self.assertTrue(
            result["authorized"]
        )

    def test_v270_release_readiness_summary_is_complete(self):
        self.assertEqual(
            len(
                SAVED_SEARCH_NOTIFICATION_RELEASE_READINESS_SUMMARY
            ),
            30,
        )

        required = {
            "manual-rollout consideration closeout is complete",
            "manual-rollout authorization closeout is complete",
            "authorization reason codes remain forty-one",
            "all authorization reason codes remain reachable",
            "owner scope remains one",
            "authorization limit remains three",
            "positive result remains preparation only",
            "production delivery remains absent",
            "authorization consumption remains absent",
            "delivery retry remains absent",
            "scheduler remains disabled",
            "migration 0017 remains absent",
            "saved-search notification audit series is closed",
        }

        self.assertTrue(
            required.issubset(
                set(
                    SAVED_SEARCH_NOTIFICATION_RELEASE_READINESS_SUMMARY
                )
            )
        )

    def test_v270_v268_and_v269_gate_packages_remain_present(self):
        self.assertGreaterEqual(
            len(V268_ACCEPTANCE_GATES),
            85,
        )

        self.assertGreaterEqual(
            len(V269_IMPLEMENTATION_GATES),
            95,
        )

        self.assertIn(
            "positive decision permits preparation only",
            V268_ACCEPTANCE_GATES,
        )

        self.assertIn(
            "all forty-one reason codes remain reachable",
            V269_IMPLEMENTATION_GATES,
        )

    def test_v270_default_readiness_remains_not_ready(self):
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
    def test_v270_production_like_readiness_remains_ready(self):
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

    @override_settings(
        **PRODUCTION_LIKE_SETTINGS
    )
    def test_v270_readiness_execution_opens_no_email_connection(self):
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

    def test_v270_command_surfaces_remain_unchanged(self):
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

    def test_v270_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v270_scheduler_remains_nonautomatic(self):
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

    def test_v270_v269_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_manual_rollout_authorization_v269.py"
        )

        self.assertIn(
            (
                "V269_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_AUTHORIZATION"
            ),
            source,
        )

        self.assertIn(
            (
                "v270: saved-search notification production delivery "
                "pilot supervised execution manual rollout "
                "authorization closeout audit"
            ),
            source,
        )

    def test_v270_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V270_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CLOSEOUT_AUDIT
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

    def test_v270_no_migration_0017_exists(self):
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

    def test_v270_closeout_gate_matrix_is_complete(self):
        required = {
            "v268 authorization contract remains packaged",
            "v269 authorization implementation remains packaged",
            "v270 scope remains exactly two closeout files",
            "no next audit scope is defined",
            "audit series status is closed",
            "next project action returns to product roadmap",
            "all forty-one reason codes remain reachable",
            "positive result returns no production command",
            "positive result performs no production delivery",
            "positive result consumes no authorization",
            "owner scope remains exactly one",
            "authorization limit remains one through three",
            "readiness freshness remains inclusive at three hundred seconds",
            "preview freshness remains inclusive at three hundred seconds",
            "provider-state freshness remains inclusive at three hundred seconds",
            "authorization lifetime remains inclusive at six hundred seconds",
            "strict sanitizer retains exact allowlist",
            "sensitive values remain absent from output",
            "immutable snapshot remains deterministic",
            "evaluator invokes no subprocess",
            "evaluator invokes no management command",
            "evaluator opens no email connection",
            "production command controls remain unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
            "release-readiness summary remains packaged",
            "saved-search notification audit series remains closed",
        }

        self.assertGreaterEqual(
            len(V270_CLOSEOUT_GATES),
            105,
        )

        self.assertTrue(
            required.issubset(
                set(V270_CLOSEOUT_GATES)
            )
        )
