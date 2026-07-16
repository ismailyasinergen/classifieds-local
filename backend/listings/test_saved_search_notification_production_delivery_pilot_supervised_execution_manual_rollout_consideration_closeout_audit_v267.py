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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_contract_v265 import (
    MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES,
    MANUAL_ROLLOUT_CONSIDERATION_LIFETIME_SECONDS,
    MANUAL_ROLLOUT_DECISIONS,
    MANUAL_ROLLOUT_DECISION_PRECEDENCE,
    MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST,
    MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS,
    MANUAL_ROLLOUT_IMMUTABLE_BINDINGS,
    MANUAL_ROLLOUT_MAX_LIMIT,
    MANUAL_ROLLOUT_MAX_OWNER_COUNT,
    MANUAL_ROLLOUT_PREVIEW_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS,
    MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES,
    MANUAL_ROLLOUT_PROHIBITED_ACTIONS,
    MANUAL_ROLLOUT_READINESS_FRESHNESS_SECONDS,
    MANUAL_ROLLOUT_REASON_ORDER,
    MANUAL_ROLLOUT_REQUIRED_FIELDS,
    MANUAL_ROLLOUT_REQUIRED_ROLES,
    MANUAL_ROLLOUT_ROLE_SEPARATION_RULES,
    MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES,
    MANUAL_ROLLOUT_SENSITIVE_INPUT_KEYS,
    MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES,
    V265_ACCEPTANCE_GATES,
)
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_v266 import (
    MANUAL_ROLLOUT_PAIRWISE_REVIEWER_FIELDS,
    MANUAL_ROLLOUT_RESULT_FIELDS,
    MANUAL_ROLLOUT_REVIEWER_FIELDS,
    MANUAL_ROLLOUT_SOURCE_DELIVERY_COUNT_FIELDS,
    V266_IMPLEMENTATION_GATES,
    V266_REASON_REACHABILITY_CASES,
    build_complete_manual_rollout_consideration,
    build_manual_rollout_evaluation_context,
    collect_manual_rollout_completeness_reasons,
    collect_manual_rollout_prohibited_action_reasons,
    collect_manual_rollout_scope_role_reasons,
    collect_manual_rollout_source_eligibility_reasons,
    evaluate_manual_rollout_consideration,
    manual_rollout_immutable_snapshot,
    ordered_unique_manual_rollout_reasons,
    sanitize_manual_rollout_evidence,
)


V267_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CLOSEOUT_AUDIT = (
    "V267_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CLOSEOUT_AUDIT"
)

V266_COMMITTED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_v266.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_v266.md"
    ),
)

V267_ALLOWED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_"
        "closeout_audit_v267.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_consideration_"
        "closeout_audit_v267.md"
    ),
)

V268_PROPOSED_SCOPE = (
    (
        "backend/listings/"
        "test_saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "contract_v268.py"
    ),
    (
        "docs/"
        "saved_search_notification_production_delivery_"
        "pilot_supervised_execution_manual_rollout_authorization_"
        "contract_v268.md"
    ),
)

MANUAL_ROLLOUT_AUTHORIZATION_PRECONDITIONS = (
    "manual-rollout consideration lane is closed",
    "source decision is eligible_to_prepare_future_authorization",
    "source eligibility flag is true",
    "source reason-code collection is empty",
    "source evidence remains sanitized",
    "source immutable snapshot is complete",
    "source consideration identifier is bound",
    "source change-record identifier is bound",
    "source authorization identifier is historical only",
    "source authorization cannot be reused",
    "source owner identifier is positive",
    "source owner scope contains exactly one owner",
    "source considered owner matches source owner",
    "source approved limit is between one and three",
    "source considered limit is between one and three",
    "source considered limit does not exceed source approved limit",
    "source readiness evidence fingerprint is present",
    "source preview evidence fingerprint is present",
    "readiness evidence must be regenerated",
    "preview evidence must be regenerated",
    "current provider sender and backend state must be regenerated",
    "current command fingerprint must be regenerated",
    "current pre-send freeze fingerprint must be regenerated",
    "decision owner identity is present",
    "evidence reviewer identity is present",
    "privacy reviewer identity is present",
    "incident reviewer identity is present",
    "rollback reviewer identity is present",
    "incident commander identity is present",
    "required roles remain separated",
    "future authorization identifier must be new",
    "future authorization must expire explicitly",
    "future authorization consumption remains one shot",
    "both production confirmations remain mandatory",
    "future authorization remains owner scoped",
    "future authorization remains limit bounded",
    "automatic retry remains disabled",
    "automatic rollout promotion remains disabled",
    "scheduler remains disabled",
    "production feature gate remains unchanged by closeout",
    "closeout performs no production delivery",
    "closeout consumes no authorization",
    "closeout performs no retry",
    "runtime scheduler schema and UI remain unchanged",
    "migration 0017 remains absent",
    "historical safety tests remain green",
    "full regression remains green",
)

V267_CLOSEOUT_GATES = (
    "v265 manual-rollout consideration contract remains packaged",
    "v266 manual-rollout consideration implementation remains packaged",
    "v266 committed scope remains exactly two files",
    "v267 scope remains exactly two closeout files",
    "v268 proposed scope remains exactly two contract files",
    "v268 remains documentation and test only",
    "closeout remains documentation and test only",
    "required fields remain exactly forty-seven",
    "required fields remain unique",
    "two decisions remain exact",
    "not-eligible remains fail-closed precedence",
    "forty-eight reason codes remain exact",
    "forty-eight reason codes remain unique",
    "all forty-eight reason codes remain reachable",
    "reason ordering remains deterministic",
    "all four reason families remain exact",
    "default record remains eligible for preparation only",
    "eligible result returns no production command",
    "eligible result returns no authorization identifier",
    "eligible result returns future authorization requirements only",
    "noneligible result returns no future authorization requirements",
    "source decision remains complete-consistent",
    "source recommendation remains eligible for manual consideration",
    "source reason codes remain empty",
    "source complete flag remains mandatory",
    "source consistent flag remains mandatory",
    "source privacy-safe flag remains mandatory",
    "source incident-clear flag remains mandatory",
    "source policy-compliant flag remains mandatory",
    "source authorization consumption count remains one",
    "source production invocation count remains one",
    "source delivery counts remain reconciled",
    "source refused count remains zero",
    "source failed count remains zero",
    "source audit remains gap-free",
    "source duplicate review remains clean",
    "source provider anomaly remains absent",
    "source incident state remains closed",
    "source privacy sanitizer remains applied",
    "source automatic retry remains disabled",
    "source automatic promotion remains disabled",
    "source owner remains positive",
    "owner scope remains exactly one",
    "considered owner remains source bound",
    "source approved limit remains one through three",
    "considered limit remains one through three",
    "considered limit cannot expand",
    "decision owner remains distinct",
    "required reviewers remain distinct",
    "six required roles remain exact",
    "readiness freshness remains inclusive at three hundred seconds",
    "preview freshness remains inclusive at three hundred seconds",
    "consideration lifetime remains inclusive at nine hundred seconds",
    "future timestamps fail closed",
    "stale readiness fails closed",
    "stale preview fails closed",
    "expired consideration fails closed",
    "changed readiness fingerprint fails closed",
    "changed preview fingerprint fails closed",
    "future authorization requirement remains mandatory",
    "source authorization reuse remains prohibited",
    "new authorization identifier remains mandatory",
    "authorization expiration remains mandatory",
    "one-shot consumption remains mandatory",
    "both confirmations remain mandatory",
    "production delivery during consideration fails closed",
    "authorization consumption during consideration fails closed",
    "retry during consideration fails closed",
    "scheduler enablement during consideration fails closed",
    "automatic promotion during consideration fails closed",
    "computed decision cannot be spoofed",
    "computed reason codes cannot be spoofed",
    "strict evidence allowlist remains exact",
    "unknown evidence fields remain discarded",
    "sensitive fields remain discarded",
    "sensitive values remain absent from output",
    "immutable snapshot remains exact",
    "immutable snapshot remains deterministic",
    "evaluator remains pure and in-memory",
    "evaluator invokes no subprocess",
    "evaluator invokes no management command",
    "evaluator opens no email connection",
    "closeout performs no database mutation",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service remains unchanged",
    "readiness command remains unchanged",
    "scheduler remains nonautomatic",
    "matcher remains unchanged",
    "renderer remains unchanged",
    "audit runtime remains unchanged",
    "audit persistence remains unchanged",
    "models admin URLs templates and UI remain unchanged",
    "production batch maximum remains twenty-five",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "historical safety tests remain green",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v268: saved-search notification production delivery pilot supervised execution manual rollout authorization contract"

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
        "pilot_supervised_execution_manual_rollout_consideration_v266.py"
    ),
)


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionManualRolloutConsiderationCloseoutAuditV267Tests(
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

    def test_v267_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V267_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CLOSEOUT_AUDIT,
            (
                "V267_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_CONSIDERATION_CLOSEOUT_AUDIT"
            ),
        )

        self.assertEqual(
            len(V266_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V267_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V268_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v268: saved-search notification production delivery "
                "pilot supervised execution manual rollout "
                "authorization contract"
            ),
        )

    def test_v267_and_v268_scopes_are_documentation_and_test_only(self):
        for scope in (
            V267_ALLOWED_SCOPE,
            V268_PROPOSED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v267_contract_packages_remain_exact(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_REQUIRED_FIELDS),
            47,
        )

        self.assertEqual(
            len(set(MANUAL_ROLLOUT_REQUIRED_FIELDS)),
            47,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_DECISIONS,
            (
                "not_eligible",
                "eligible_to_prepare_future_authorization",
            ),
        )

        self.assertEqual(
            MANUAL_ROLLOUT_DECISION_PRECEDENCE,
            MANUAL_ROLLOUT_DECISIONS,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_DECISION_PRECEDENCE[0],
            "not_eligible",
        )

    def test_v267_reason_families_remain_exact(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES),
            14,
        )

        self.assertEqual(
            len(MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES),
            18,
        )

        self.assertEqual(
            len(MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES),
            11,
        )

        self.assertEqual(
            len(MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES),
            5,
        )

        combined = (
            set(MANUAL_ROLLOUT_COMPLETENESS_REASON_CODES)
            | set(
                MANUAL_ROLLOUT_SOURCE_ELIGIBILITY_REASON_CODES
            )
            | set(
                MANUAL_ROLLOUT_SCOPE_AND_ROLE_REASON_CODES
            )
            | set(
                MANUAL_ROLLOUT_PROHIBITED_ACTION_REASON_CODES
            )
        )

        self.assertEqual(
            combined,
            set(MANUAL_ROLLOUT_REASON_ORDER),
        )

    def test_v267_reason_order_remains_exact_and_unique(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_REASON_ORDER),
            48,
        )

        self.assertEqual(
            len(set(MANUAL_ROLLOUT_REASON_ORDER)),
            48,
        )

    def test_v267_v266_implementation_packages_remain_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_RESULT_FIELDS,
            (
                "decision",
                "eligible",
                "reason_codes",
                "sanitized_evidence",
                "immutable_snapshot",
                "future_authorization_requirements",
            ),
        )

        self.assertEqual(
            len(V266_REASON_REACHABILITY_CASES),
            48,
        )

        self.assertGreaterEqual(
            len(V266_IMPLEMENTATION_GATES),
            85,
        )

    def test_v267_default_result_remains_preparation_only(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration()
        )

        self.assertEqual(
            tuple(result),
            MANUAL_ROLLOUT_RESULT_FIELDS,
        )

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

        self.assertTrue(
            result["eligible"]
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["future_authorization_requirements"],
            MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS,
        )

        self.assertNotIn(
            "command",
            result,
        )

        self.assertNotIn(
            "authorization_id",
            result,
        )

    def test_v267_not_eligible_remains_fail_closed(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_consistent=False,
            )
        )

        self.assertEqual(
            result["decision"],
            "not_eligible",
        )

        self.assertFalse(
            result["eligible"]
        )

        self.assertEqual(
            result["future_authorization_requirements"],
            (),
        )

        self.assertIn(
            "source_not_consistent",
            result["reason_codes"],
        )

    def test_v267_all_reason_codes_remain_reachable(self):
        reached: set[str] = set()

        for (
            changes,
            removed_fields,
            context_changes,
            expected_reason,
        ) in V266_REASON_REACHABILITY_CASES:
            with self.subTest(
                expected_reason=expected_reason
            ):
                record = (
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                for field in removed_fields:
                    record.pop(
                        field
                    )

                context = (
                    build_manual_rollout_evaluation_context(
                        **context_changes
                    )
                )

                result = evaluate_manual_rollout_consideration(
                    record,
                    context=context,
                )

                self.assertEqual(
                    result["decision"],
                    "not_eligible",
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
            set(MANUAL_ROLLOUT_REASON_ORDER),
        )

    def test_v267_reason_order_remains_deterministic(self):
        reasons = list(
            reversed(
                MANUAL_ROLLOUT_REASON_ORDER
            )
        )

        reasons.extend(
            MANUAL_ROLLOUT_REASON_ORDER[:8]
        )

        self.assertEqual(
            ordered_unique_manual_rollout_reasons(
                reasons
            ),
            MANUAL_ROLLOUT_REASON_ORDER,
        )

    def test_v267_collectors_remain_empty_for_default_record(self):
        record = (
            build_complete_manual_rollout_consideration()
        )

        context = (
            build_manual_rollout_evaluation_context()
        )

        self.assertEqual(
            collect_manual_rollout_completeness_reasons(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_source_eligibility_reasons(
                record
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_scope_role_reasons(
                record,
                context,
            ),
            (),
        )

        self.assertEqual(
            collect_manual_rollout_prohibited_action_reasons(
                record
            ),
            (),
        )

    def test_v267_missing_evidence_remains_fail_closed(self):
        fields = (
            "consideration_id",
            "source_change_record_id",
            "source_authorization_id",
            "source_owner_id",
            "source_approved_limit",
            "source_authorization_command_fingerprint",
            "source_freeze_fingerprint",
            "decision_owner_identity",
            "considered_owner_ids",
            "considered_limit",
            "readiness_evidence_fingerprint",
            "preview_evidence_fingerprint",
            "consideration_completed_at_utc",
        )

        for field in fields:
            with self.subTest(
                field=field
            ):
                record = (
                    build_complete_manual_rollout_consideration()
                )

                record.pop(
                    field
                )

                result = evaluate_manual_rollout_consideration(
                    record
                )

                self.assertEqual(
                    result["decision"],
                    "not_eligible",
                )

                self.assertTrue(
                    result["reason_codes"]
                )

    def test_v267_required_reviewer_identity_remains_mandatory(self):
        for field in MANUAL_ROLLOUT_REVIEWER_FIELDS:
            with self.subTest(
                field=field
            ):
                record = (
                    build_complete_manual_rollout_consideration()
                )

                record.pop(
                    field
                )

                result = evaluate_manual_rollout_consideration(
                    record
                )

                self.assertIn(
                    "missing_required_reviewer_identity",
                    result["reason_codes"],
                )

    def test_v267_source_decision_and_recommendation_remain_exact(self):
        decision = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_evidence_decision="incomplete",
            )
        )

        recommendation = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_rollout_recommendation="not_eligible",
            )
        )

        self.assertIn(
            "source_decision_not_complete_consistent",
            decision["reason_codes"],
        )

        self.assertIn(
            "source_rollout_recommendation_not_manual_consideration",
            recommendation["reason_codes"],
        )

    def test_v267_source_flags_remain_fail_closed(self):
        cases = (
            (
                "source_complete",
                "source_not_complete",
            ),
            (
                "source_consistent",
                "source_not_consistent",
            ),
            (
                "source_privacy_safe",
                "source_not_privacy_safe",
            ),
            (
                "source_incident_clear",
                "source_incident_not_clear",
            ),
            (
                "source_policy_compliant",
                "source_not_policy_compliant",
            ),
        )

        for field, reason in cases:
            with self.subTest(
                field=field
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **{
                            field: False,
                        }
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v267_source_consumption_and_invocation_remain_exact(self):
        consumption = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_authorization_consumption_count=0,
            )
        )

        invocation = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_production_invocation_count=2,
            )
        )

        self.assertIn(
            "source_authorization_consumption_count_mismatch",
            consumption["reason_codes"],
        )

        self.assertIn(
            "source_production_invocation_count_mismatch",
            invocation["reason_codes"],
        )

    def test_v267_delivery_reconciliation_remains_fail_closed(self):
        cases = (
            {
                "source_delivered_count": -1,
            },
            {
                "source_delivered_count": 0,
            },
            {
                "source_delivered_count": 4,
            },
            {
                "source_refused_count": 1,
            },
            {
                "source_failed_count": 1,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                self.assertIn(
                    "source_delivery_counts_not_reconciled",
                    result["reason_codes"],
                )

    def test_v267_delivery_count_fields_remain_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_SOURCE_DELIVERY_COUNT_FIELDS,
            (
                "source_delivered_count",
                "source_skipped_count",
                "source_refused_count",
                "source_failed_count",
            ),
        )

    def test_v267_audit_incident_and_policy_states_remain_closed(self):
        cases = (
            (
                {
                    "source_audit_gap_free": False,
                },
                "source_audit_not_gap_free",
            ),
            (
                {
                    "source_duplicate_attempt_clean": False,
                },
                "source_duplicate_attempt_not_clean",
            ),
            (
                {
                    "source_provider_anomaly": True,
                },
                "source_provider_anomaly_present",
            ),
            (
                {
                    "source_incident_state": "open",
                },
                "source_incident_state_not_closed",
            ),
            (
                {
                    "source_privacy_sanitizer_applied": False,
                },
                "source_privacy_sanitizer_not_applied",
            ),
            (
                {
                    "source_automatic_retry_enabled": True,
                },
                "source_automatic_retry_enabled",
            ),
            (
                {
                    "source_automatic_rollout_promotion_enabled": True,
                },
                "source_automatic_rollout_promotion_enabled",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v267_owner_scope_remains_single_and_source_bound(self):
        cases = (
            (
                {
                    "source_owner_id": 0,
                },
                "invalid_source_owner_id",
            ),
            (
                {
                    "considered_owner_ids": (),
                },
                "considered_owner_scope_empty",
            ),
            (
                {
                    "considered_owner_ids": (
                        202,
                    ),
                },
                "considered_owner_scope_expanded",
            ),
            (
                {
                    "considered_owner_ids": (
                        101,
                        202,
                    ),
                },
                "considered_owner_scope_expanded",
            ),
        )

        for changes, reason in cases:
            with self.subTest(
                reason=reason
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **changes
                    )
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

        self.assertEqual(
            MANUAL_ROLLOUT_MAX_OWNER_COUNT,
            1,
        )

    def test_v267_limit_cannot_expand(self):
        invalid_source = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_approved_limit=4,
            )
        )

        invalid_considered = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                considered_limit=0,
            )
        )

        expanded = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                source_approved_limit=2,
                considered_limit=3,
                source_delivered_count=2,
            )
        )

        self.assertIn(
            "invalid_source_approved_limit",
            invalid_source["reason_codes"],
        )

        self.assertIn(
            "considered_limit_invalid",
            invalid_considered["reason_codes"],
        )

        self.assertIn(
            "considered_limit_expanded",
            expanded["reason_codes"],
        )

        self.assertEqual(
            MANUAL_ROLLOUT_MAX_LIMIT,
            3,
        )

    def test_v267_role_packages_remain_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_REQUIRED_ROLES,
            (
                "decision_owner",
                "evidence_reviewer",
                "privacy_reviewer",
                "incident_reviewer",
                "rollback_reviewer",
                "incident_commander",
            ),
        )

        self.assertEqual(
            MANUAL_ROLLOUT_PAIRWISE_REVIEWER_FIELDS,
            (
                "evidence_reviewer_identity",
                "privacy_reviewer_identity",
                "incident_reviewer_identity",
                "rollback_reviewer_identity",
            ),
        )

        self.assertEqual(
            len(MANUAL_ROLLOUT_ROLE_SEPARATION_RULES),
            6,
        )

    def test_v267_role_overlap_remains_fail_closed(self):
        decision_overlap = (
            evaluate_manual_rollout_consideration(
                build_complete_manual_rollout_consideration(
                    decision_owner_identity=(
                        "evidence-reviewer-a"
                    ),
                )
            )
        )

        reviewer_overlap = (
            evaluate_manual_rollout_consideration(
                build_complete_manual_rollout_consideration(
                    privacy_reviewer_identity=(
                        "evidence-reviewer-a"
                    ),
                )
            )
        )

        self.assertIn(
            "decision_owner_role_overlap",
            decision_overlap["reason_codes"],
        )

        self.assertIn(
            "required_reviewer_identity_not_distinct",
            reviewer_overlap["reason_codes"],
        )

    def test_v267_freshness_boundaries_remain_inclusive(self):
        record = (
            build_complete_manual_rollout_consideration()
        )

        boundary = (
            build_manual_rollout_evaluation_context(
                current_timestamp_utc=1200,
                readiness_generated_at_utc=900,
                preview_generated_at_utc=900,
                consideration_started_at_utc=300,
            )
        )

        result = evaluate_manual_rollout_consideration(
            record,
            context=boundary,
        )

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

        self.assertEqual(
            MANUAL_ROLLOUT_READINESS_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_PREVIEW_FRESHNESS_SECONDS,
            300,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_CONSIDERATION_LIFETIME_SECONDS,
            900,
        )

    def test_v267_stale_and_expired_context_remains_rejected(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(),
            context=(
                build_manual_rollout_evaluation_context(
                    readiness_generated_at_utc=899,
                    preview_generated_at_utc=899,
                    consideration_started_at_utc=299,
                )
            ),
        )

        self.assertIn(
            "readiness_evidence_stale_or_changed",
            result["reason_codes"],
        )

        self.assertIn(
            "preview_evidence_stale_or_changed",
            result["reason_codes"],
        )

    def test_v267_future_timestamp_context_remains_rejected(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(),
            context=(
                build_manual_rollout_evaluation_context(
                    readiness_generated_at_utc=1201,
                    preview_generated_at_utc=1201,
                    consideration_started_at_utc=1201,
                )
            ),
        )

        self.assertIn(
            "readiness_evidence_stale_or_changed",
            result["reason_codes"],
        )

        self.assertIn(
            "preview_evidence_stale_or_changed",
            result["reason_codes"],
        )

    def test_v267_fingerprint_changes_remain_rejected(self):
        readiness = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                readiness_evidence_fingerprint="changed",
            )
        )

        preview = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                preview_evidence_fingerprint="changed",
            )
        )

        self.assertIn(
            "readiness_evidence_stale_or_changed",
            readiness["reason_codes"],
        )

        self.assertIn(
            "preview_evidence_stale_or_changed",
            preview["reason_codes"],
        )

    def test_v267_future_authorization_requirement_remains_mandatory(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                future_authorization_required=False,
            )
        )

        self.assertEqual(
            result["decision"],
            "not_eligible",
        )

        self.assertIn(
            "future_authorization_not_required",
            result["reason_codes"],
        )

    def test_v267_future_authorization_package_remains_separate(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS
            ),
            13,
        )

        required = {
            "new authorization identifier",
            "one explicit positive owner identifier",
            "explicit limit between one and three",
            "current readiness evidence",
            "current preview evidence",
            "current provider sender and backend state",
            "current authorization command fingerprint",
            "current pre-send freeze fingerprint",
            "both production confirmations",
            "explicit authorization expiration",
            "one-shot authorization consumption",
            "automatic retry and automatic promotion remain disabled",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_FUTURE_AUTHORIZATION_REQUIREMENTS
                )
            )
        )

    def test_v267_all_prohibited_actions_remain_fail_closed(self):
        cases = (
            (
                "production_delivery_performed",
                "production_delivery_performed_during_consideration",
            ),
            (
                "authorization_consumed",
                "authorization_consumed_during_consideration",
            ),
            (
                "retry_performed",
                "retry_performed_during_consideration",
            ),
            (
                "scheduler_enabled",
                "scheduler_enabled_during_consideration",
            ),
            (
                "automatic_promotion_performed",
                "automatic_promotion_performed_during_consideration",
            ),
        )

        for field, reason in cases:
            with self.subTest(
                field=field
            ):
                result = evaluate_manual_rollout_consideration(
                    build_complete_manual_rollout_consideration(
                        **{
                            field: True,
                        }
                    )
                )

                self.assertEqual(
                    result["decision"],
                    "not_eligible",
                )

                self.assertIn(
                    reason,
                    result["reason_codes"],
                )

    def test_v267_decision_and_reason_spoofing_remains_blocked(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
                final_decision="not_eligible",
                reason_codes=(
                    "production_delivery_performed_during_consideration",
                ),
            )
        )

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

        self.assertEqual(
            result["reason_codes"],
            (),
        )

        self.assertEqual(
            result["sanitized_evidence"][
                "final_decision"
            ],
            "eligible_to_prepare_future_authorization",
        )

        self.assertEqual(
            result["sanitized_evidence"][
                "reason_codes"
            ],
            (),
        )

    def test_v267_sanitizer_remains_strict_allowlist_based(self):
        record = (
            build_complete_manual_rollout_consideration(
                unknown_field="discard-me",
            )
        )

        sanitized = sanitize_manual_rollout_evidence(
            record
        )

        self.assertEqual(
            tuple(sanitized),
            tuple(
                field
                for field in MANUAL_ROLLOUT_EVIDENCE_ALLOWLIST
                if field in record
            ),
        )

        self.assertNotIn(
            "unknown_field",
            sanitized,
        )

        self.assertNotIn(
            "discard-me",
            repr(sanitized),
        )

    def test_v267_sensitive_values_remain_discarded(self):
        result = evaluate_manual_rollout_consideration(
            build_complete_manual_rollout_consideration(
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
                MANUAL_ROLLOUT_SENSITIVE_INPUT_KEYS
            )
        )

    def test_v267_privacy_packages_remain_exact(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS),
            13,
        )

        self.assertIn(
            "SMTP password",
            MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS,
        )

        self.assertIn(
            "raw exception traceback",
            MANUAL_ROLLOUT_PRIVACY_EXCLUSIONS,
        )

    def test_v267_immutable_snapshot_remains_exact(self):
        record = (
            build_complete_manual_rollout_consideration()
        )

        first = manual_rollout_immutable_snapshot(
            record
        )

        second = manual_rollout_immutable_snapshot(
            record
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            tuple(first),
            MANUAL_ROLLOUT_IMMUTABLE_BINDINGS,
        )

    def test_v267_evaluator_remains_nonexecuting(self):
        record = (
            build_complete_manual_rollout_consideration()
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
            result = evaluate_manual_rollout_consideration(
                record
            )

        subprocess_run.assert_not_called()
        get_connection.assert_not_called()
        call_command_mock.assert_not_called()

        self.assertEqual(
            result["decision"],
            "eligible_to_prepare_future_authorization",
        )

    def test_v267_prohibited_action_package_remains_complete(self):
        required = {
            "production delivery during consideration",
            "authorization consumption during consideration",
            "delivery retry during consideration",
            "scheduler enablement",
            "automatic rollout promotion",
            "production feature-gate mutation",
            "owner-scope expansion",
            "limit expansion",
            "source authorization reuse",
            "evidence review reused as execution authorization",
            "global all-owner execution",
            "multi-owner execution",
            "blind retry",
            "direct SQL repair",
            "Django shell timestamp repair",
            "privacy sanitizer bypass",
            "computed decision spoofing",
            "silent inconsistency acceptance",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_PROHIBITED_ACTIONS
                )
            )
        )

    def test_v267_v265_and_v266_gate_packages_remain_present(self):
        self.assertGreaterEqual(
            len(V265_ACCEPTANCE_GATES),
            80,
        )

        self.assertGreaterEqual(
            len(V266_IMPLEMENTATION_GATES),
            85,
        )

        self.assertIn(
            "future authorization remains mandatory",
            V265_ACCEPTANCE_GATES,
        )

        self.assertIn(
            "all forty-eight reason codes remain reachable",
            V266_IMPLEMENTATION_GATES,
        )

    def test_v267_authorization_preconditions_are_complete(self):
        self.assertEqual(
            len(MANUAL_ROLLOUT_AUTHORIZATION_PRECONDITIONS),
            47,
        )

        required = {
            "manual-rollout consideration lane is closed",
            "source decision is eligible_to_prepare_future_authorization",
            "source authorization cannot be reused",
            "readiness evidence must be regenerated",
            "preview evidence must be regenerated",
            "future authorization identifier must be new",
            "future authorization consumption remains one shot",
            "both production confirmations remain mandatory",
            "automatic retry remains disabled",
            "automatic rollout promotion remains disabled",
            "closeout performs no production delivery",
            "closeout consumes no authorization",
            "closeout performs no retry",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_AUTHORIZATION_PRECONDITIONS
                )
            )
        )

    def test_v267_default_readiness_remains_not_ready(self):
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
    def test_v267_production_like_readiness_remains_ready(self):
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
    def test_v267_readiness_execution_opens_no_email_connection(self):
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

    def test_v267_command_surfaces_remain_unchanged(self):
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

    def test_v267_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v267_scheduler_remains_nonautomatic(self):
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

    def test_v267_v266_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_manual_rollout_consideration_v266.py"
        )

        self.assertIn(
            (
                "V266_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_CONSIDERATION"
            ),
            source,
        )

        self.assertIn(
            (
                "v267: saved-search notification production delivery "
                "pilot supervised execution manual rollout consideration "
                "closeout audit"
            ),
            source,
        )

    def test_v267_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V267_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_CONSIDERATION_CLOSEOUT_AUDIT
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

    def test_v267_no_migration_0017_exists(self):
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

    def test_v267_closeout_gate_matrix_is_complete(self):
        required = {
            "v265 manual-rollout consideration contract remains packaged",
            "v266 manual-rollout consideration implementation remains packaged",
            "v267 scope remains exactly two closeout files",
            "v268 proposed scope remains exactly two contract files",
            "all forty-eight reason codes remain reachable",
            "default record remains eligible for preparation only",
            "considered limit cannot expand",
            "required reviewers remain distinct",
            "readiness freshness remains inclusive at three hundred seconds",
            "preview freshness remains inclusive at three hundred seconds",
            "consideration lifetime remains inclusive at nine hundred seconds",
            "future authorization requirement remains mandatory",
            "source authorization reuse remains prohibited",
            "new authorization identifier remains mandatory",
            "production delivery during consideration fails closed",
            "authorization consumption during consideration fails closed",
            "retry during consideration fails closed",
            "scheduler enablement during consideration fails closed",
            "automatic promotion during consideration fails closed",
            "strict evidence allowlist remains exact",
            "sensitive values remain absent from output",
            "evaluator invokes no subprocess",
            "evaluator invokes no management command",
            "evaluator opens no email connection",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service remains unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertGreaterEqual(
            len(V267_CLOSEOUT_GATES),
            90,
        )

        self.assertTrue(
            required.issubset(
                set(V267_CLOSEOUT_GATES)
            )
        )
