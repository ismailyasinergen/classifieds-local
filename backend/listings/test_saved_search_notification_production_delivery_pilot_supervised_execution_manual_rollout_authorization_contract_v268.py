from __future__ import annotations

import ast
from io import StringIO
from pathlib import Path
from typing import Any
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
from listings.test_saved_search_notification_production_delivery_pilot_supervised_execution_manual_rollout_consideration_closeout_audit_v267 import (
    MANUAL_ROLLOUT_AUTHORIZATION_PRECONDITIONS,
    V267_CLOSEOUT_GATES,
)


V268_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CONTRACT = (
    "V268_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CONTRACT"
)

V267_COMMITTED_SCOPE = (
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

V268_ALLOWED_SCOPE = (
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

V269_PROPOSED_SCOPE = (
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

MANUAL_ROLLOUT_AUTHORIZATION_MAX_OWNER_COUNT = 1
MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT = 3
MANUAL_ROLLOUT_AUTHORIZATION_READINESS_FRESHNESS_SECONDS = 300
MANUAL_ROLLOUT_AUTHORIZATION_PREVIEW_FRESHNESS_SECONDS = 300
MANUAL_ROLLOUT_AUTHORIZATION_PROVIDER_STATE_FRESHNESS_SECONDS = 300
MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS = 600

MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS = (
    "authorization_id",
    "source_consideration_id",
    "source_change_record_id",
    "historical_source_authorization_id",
    "source_consideration_decision",
    "source_consideration_eligible",
    "source_consideration_reason_codes",
    "source_evidence_sanitized",
    "source_immutable_snapshot_complete",
    "source_owner_id",
    "source_approved_limit",
    "source_considered_owner_ids",
    "source_considered_limit",
    "source_authorization_preconditions_complete",
    "owner_id",
    "approved_limit",
    "decision_owner_identity",
    "authorizing_operator_identity",
    "evidence_reviewer_identity",
    "privacy_reviewer_identity",
    "incident_reviewer_identity",
    "rollback_reviewer_identity",
    "incident_commander_identity",
    "readiness_generated_at_utc",
    "readiness_evidence_fingerprint",
    "preview_generated_at_utc",
    "preview_evidence_fingerprint",
    "provider_state_generated_at_utc",
    "provider_state_fingerprint",
    "sender_state_fingerprint",
    "email_backend_state_fingerprint",
    "authorization_command_fingerprint",
    "pre_send_freeze_fingerprint",
    "authorization_created_at_utc",
    "authorization_expires_at_utc",
    "production_confirmation_primary",
    "production_confirmation_secondary",
    "feature_gate_expected_enabled",
    "authorization_consumption_count",
    "production_invocation_count",
    "production_delivery_performed",
    "retry_performed",
    "scheduler_enabled",
    "automatic_promotion_performed",
    "authorization_state",
    "reason_codes",
)

MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST = (
    MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS
)

MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS = (
    "authorization_id",
    "source_consideration_id",
    "source_change_record_id",
    "historical_source_authorization_id",
    "owner_id",
    "approved_limit",
    "readiness_evidence_fingerprint",
    "preview_evidence_fingerprint",
    "provider_state_fingerprint",
    "sender_state_fingerprint",
    "email_backend_state_fingerprint",
    "authorization_command_fingerprint",
    "pre_send_freeze_fingerprint",
    "authorization_expires_at_utc",
)

MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_ROLES = (
    "decision_owner",
    "authorizing_operator",
    "evidence_reviewer",
    "privacy_reviewer",
    "incident_reviewer",
    "rollback_reviewer",
    "incident_commander",
)

MANUAL_ROLLOUT_AUTHORIZATION_ROLE_SEPARATION_RULES = (
    "authorizing operator differs from decision owner",
    "authorizing operator differs from every reviewer",
    "decision owner differs from every reviewer",
    "evidence privacy incident and rollback reviewers are pairwise distinct",
    "incident commander differs from authorizing operator",
    "incident commander differs from decision owner",
    "incident commander differs from rollback reviewer",
)

MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS = (
    "not_authorized",
    "authorized_to_prepare_single_manual_execution",
)

MANUAL_ROLLOUT_AUTHORIZATION_DECISION_PRECEDENCE = (
    MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS
)

MANUAL_ROLLOUT_AUTHORIZATION_COMPLETENESS_REASON_CODES = (
    "missing_authorization_id",
    "missing_source_consideration_id",
    "missing_source_change_record_id",
    "missing_historical_source_authorization_id",
    "missing_owner_id",
    "missing_approved_limit",
    "missing_authorizing_operator_identity",
    "missing_required_reviewer_identity",
    "missing_readiness_evidence",
    "missing_preview_evidence",
    "missing_provider_state_evidence",
    "missing_command_fingerprint",
    "missing_freeze_fingerprint",
    "missing_authorization_window",
)

MANUAL_ROLLOUT_AUTHORIZATION_SOURCE_REASON_CODES = (
    "source_consideration_not_eligible",
    "source_consideration_reason_codes_nonempty",
    "source_evidence_not_sanitized",
    "source_immutable_snapshot_incomplete",
    "historical_authorization_reuse_attempted",
    "source_owner_mismatch",
    "source_limit_mismatch",
    "source_considered_owner_scope_invalid",
    "source_considered_limit_invalid",
    "source_preconditions_incomplete",
)

MANUAL_ROLLOUT_AUTHORIZATION_SCOPE_ROLE_REASON_CODES = (
    "invalid_owner_id",
    "invalid_approved_limit",
    "owner_scope_expanded",
    "limit_expanded",
    "authorizing_operator_role_overlap",
    "decision_owner_role_overlap",
    "required_reviewer_identity_not_distinct",
    "readiness_evidence_stale_or_changed",
    "preview_evidence_stale_or_changed",
    "provider_state_stale_or_changed",
    "command_or_freeze_fingerprint_changed",
    "authorization_expired_or_future_dated",
)

MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTION_REASON_CODES = (
    "production_delivery_performed_during_authorization",
    "authorization_consumed_before_execution",
    "retry_performed_during_authorization",
    "scheduler_enabled_during_authorization",
    "automatic_promotion_performed_during_authorization",
)

MANUAL_ROLLOUT_AUTHORIZATION_REASON_ORDER = (
    MANUAL_ROLLOUT_AUTHORIZATION_COMPLETENESS_REASON_CODES
    + MANUAL_ROLLOUT_AUTHORIZATION_SOURCE_REASON_CODES
    + MANUAL_ROLLOUT_AUTHORIZATION_SCOPE_ROLE_REASON_CODES
    + MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTION_REASON_CODES
)

MANUAL_ROLLOUT_AUTHORIZATION_SENSITIVE_INPUT_KEYS = (
    "smtp_password",
    "smtp_username",
    "api_key",
    "access_token",
    "recipient_email",
    "default_from_email",
    "raw_email_backend",
    "saved_search_name",
    "saved_search_querystring",
    "rendered_subject",
    "rendered_body",
    "provider_response_body",
    "raw_exception_traceback",
)

MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS = (
    "SMTP password",
    "confidential SMTP username",
    "API key",
    "access token",
    "recipient email address",
    "default sender value",
    "raw email-backend path",
    "saved-search name",
    "saved-search querystring",
    "rendered email subject",
    "rendered email body",
    "provider response body",
    "raw exception traceback",
)

MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS = (
    "production delivery during authorization preparation",
    "authorization consumption during authorization preparation",
    "delivery retry during authorization preparation",
    "scheduler enablement",
    "automatic rollout promotion",
    "production feature-gate mutation",
    "owner-scope expansion",
    "limit expansion",
    "historical source authorization reuse",
    "consideration result reused as executable command",
    "global all-owner execution",
    "multi-owner execution",
    "blind retry",
    "direct SQL repair",
    "Django shell timestamp repair",
    "privacy sanitizer bypass",
    "computed authorization decision spoofing",
    "reason-code spoofing",
    "silent fingerprint mismatch acceptance",
    "automatic authorization renewal",
)

MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS = (
    "authorization decision is authorized_to_prepare_single_manual_execution",
    "authorization reason-code collection is empty",
    "authorization identifier is new",
    "historical source authorization remains nonreusable",
    "one explicit positive owner identifier",
    "owner scope contains exactly one owner",
    "explicit limit between one and three",
    "execution limit cannot exceed authorization limit",
    "current readiness evidence",
    "current preview evidence",
    "current provider sender and backend state",
    "current authorization command fingerprint",
    "current pre-send freeze fingerprint",
    "both production confirmations",
    "authorization remains unconsumed and unexpired",
    "one-shot consumption occurs only at execution boundary",
    "automatic retry and automatic promotion remain disabled",
    "scheduler remains disabled",
)

V268_ACCEPTANCE_GATES = (
    "v267 closeout package remains present",
    "v267 committed scope remains exactly two files",
    "v268 scope remains exactly two contract files",
    "v269 proposed scope remains exactly two implementation files",
    "v269 remains documentation and test only",
    "contract remains documentation and test only",
    "forty-six required fields remain exact",
    "forty-six required fields remain unique",
    "evidence allowlist matches required fields",
    "fourteen immutable bindings remain exact",
    "seven required roles remain exact",
    "seven role-separation rules remain packaged",
    "two authorization decisions remain exact",
    "not-authorized remains fail-closed precedence",
    "forty-one reason codes remain exact",
    "forty-one reason codes remain unique",
    "four reason families remain disjoint",
    "source consideration must be eligible",
    "source reason-code collection must be empty",
    "source evidence must remain sanitized",
    "source immutable snapshot must remain complete",
    "all forty-seven source preconditions must remain complete",
    "authorization identifier must be new",
    "historical authorization cannot be reused",
    "source owner must be positive",
    "authorization owner must be positive",
    "source and authorization owners must match",
    "owner scope contains exactly one owner",
    "owner scope cannot expand",
    "source approved limit remains one through three",
    "source considered limit remains one through three",
    "authorization limit remains one through three",
    "authorization limit cannot expand source considered limit",
    "decision owner remains mandatory",
    "authorizing operator remains mandatory",
    "all reviewer identities remain mandatory",
    "authorizing operator remains role-separated",
    "decision owner remains role-separated",
    "reviewers remain pairwise distinct",
    "incident commander remains role-separated",
    "readiness freshness remains inclusive at three hundred seconds",
    "preview freshness remains inclusive at three hundred seconds",
    "provider-state freshness remains inclusive at three hundred seconds",
    "authorization lifetime remains inclusive at six hundred seconds",
    "future timestamps fail closed",
    "stale readiness fails closed",
    "stale preview fails closed",
    "stale provider state fails closed",
    "changed readiness fingerprint fails closed",
    "changed preview fingerprint fails closed",
    "changed provider fingerprint fails closed",
    "changed command fingerprint fails closed",
    "changed freeze fingerprint fails closed",
    "authorization expiration remains mandatory",
    "both production confirmations remain mandatory",
    "feature-gate expected state remains explicit",
    "authorization begins unconsumed",
    "authorization begins with zero production invocations",
    "positive decision permits preparation only",
    "positive decision produces no production command",
    "positive decision performs no production delivery",
    "positive decision consumes no authorization",
    "positive decision performs no retry",
    "positive decision enables no scheduler",
    "positive decision performs no automatic promotion",
    "production delivery during preparation is prohibited",
    "authorization consumption during preparation is prohibited",
    "retry during preparation is prohibited",
    "scheduler enablement during preparation is prohibited",
    "automatic promotion during preparation is prohibited",
    "strict evidence allowlist remains exact",
    "unknown evidence fields remain excluded",
    "sensitive evidence fields remain excluded",
    "privacy exclusions remain complete",
    "authorization decision cannot be spoofed",
    "authorization reason codes cannot be spoofed",
    "single-execution requirements remain explicit",
    "contract helper remains pure",
    "contract helper invokes no subprocess",
    "contract helper invokes no management command",
    "contract helper opens no email connection",
    "production sender remains unchanged",
    "production command remains unchanged",
    "readiness service remains unchanged",
    "readiness command remains unchanged",
    "scheduler remains nonautomatic",
    "matcher renderer and audit layers remain unchanged",
    "models admin URLs templates and UI remain unchanged",
    "production batch maximum remains twenty-five",
    "migration 0016 remains latest",
    "migration 0017 remains absent",
    "historical safety tests remain green",
    "full regression remains green",
)

NEXT_CHECKPOINT = "v269: saved-search notification production delivery pilot supervised execution manual rollout authorization implementation"

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
        "pilot_supervised_execution_manual_rollout_consideration_"
        "closeout_audit_v267.py"
    ),
)


def build_complete_manual_rollout_authorization_candidate(
    **changes: Any,
) -> dict[str, Any]:
    candidate: dict[str, Any] = {
        "authorization_id": "manual-authorization-002",
        "source_consideration_id": "consideration-001",
        "source_change_record_id": "change-001",
        "historical_source_authorization_id": "authorization-001",
        "source_consideration_decision": (
            "eligible_to_prepare_future_authorization"
        ),
        "source_consideration_eligible": True,
        "source_consideration_reason_codes": (),
        "source_evidence_sanitized": True,
        "source_immutable_snapshot_complete": True,
        "source_owner_id": 101,
        "source_approved_limit": 3,
        "source_considered_owner_ids": (101,),
        "source_considered_limit": 3,
        "source_authorization_preconditions_complete": True,
        "owner_id": 101,
        "approved_limit": 3,
        "decision_owner_identity": "decision-owner-a",
        "authorizing_operator_identity": "authorizing-operator-a",
        "evidence_reviewer_identity": "evidence-reviewer-a",
        "privacy_reviewer_identity": "privacy-reviewer-a",
        "incident_reviewer_identity": "incident-reviewer-a",
        "rollback_reviewer_identity": "rollback-reviewer-a",
        "incident_commander_identity": "incident-commander-a",
        "readiness_generated_at_utc": 1200,
        "readiness_evidence_fingerprint": "readiness-fingerprint-002",
        "preview_generated_at_utc": 1200,
        "preview_evidence_fingerprint": "preview-fingerprint-002",
        "provider_state_generated_at_utc": 1200,
        "provider_state_fingerprint": "provider-fingerprint-002",
        "sender_state_fingerprint": "sender-fingerprint-002",
        "email_backend_state_fingerprint": "backend-fingerprint-002",
        "authorization_command_fingerprint": "command-fingerprint-002",
        "pre_send_freeze_fingerprint": "freeze-fingerprint-002",
        "authorization_created_at_utc": 1200,
        "authorization_expires_at_utc": 1800,
        "production_confirmation_primary": True,
        "production_confirmation_secondary": True,
        "feature_gate_expected_enabled": True,
        "authorization_consumption_count": 0,
        "production_invocation_count": 0,
        "production_delivery_performed": False,
        "retry_performed": False,
        "scheduler_enabled": False,
        "automatic_promotion_performed": False,
        "authorization_state": "prepared",
        "reason_codes": (),
    }

    candidate.update(
        changes
    )

    return candidate


def manual_rollout_authorization_source_is_eligible(
    candidate: dict[str, Any],
) -> bool:
    owner_id = candidate.get(
        "owner_id"
    )

    source_owner_id = candidate.get(
        "source_owner_id"
    )

    approved_limit = candidate.get(
        "approved_limit"
    )

    source_approved_limit = candidate.get(
        "source_approved_limit"
    )

    source_considered_limit = candidate.get(
        "source_considered_limit"
    )

    source_considered_owner_ids = candidate.get(
        "source_considered_owner_ids"
    )

    integer_values = (
        owner_id,
        source_owner_id,
        approved_limit,
        source_approved_limit,
        source_considered_limit,
    )

    integers_valid = all(
        isinstance(value, int)
        and not isinstance(value, bool)
        for value in integer_values
    )

    if not integers_valid:
        return False

    return all(
        (
            candidate.get(
                "source_consideration_decision"
            )
            == "eligible_to_prepare_future_authorization",
            candidate.get(
                "source_consideration_eligible"
            )
            is True,
            candidate.get(
                "source_consideration_reason_codes"
            )
            == (),
            candidate.get(
                "source_evidence_sanitized"
            )
            is True,
            candidate.get(
                "source_immutable_snapshot_complete"
            )
            is True,
            candidate.get(
                "source_authorization_preconditions_complete"
            )
            is True,
            candidate.get(
                "authorization_id"
            )
            != candidate.get(
                "historical_source_authorization_id"
            ),
            owner_id > 0,
            source_owner_id > 0,
            owner_id == source_owner_id,
            source_considered_owner_ids == (
                source_owner_id,
            ),
            1
            <= source_approved_limit
            <= MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT,
            1
            <= source_considered_limit
            <= source_approved_limit,
            1
            <= approved_limit
            <= source_considered_limit,
            candidate.get(
                "production_confirmation_primary"
            )
            is True,
            candidate.get(
                "production_confirmation_secondary"
            )
            is True,
            candidate.get(
                "authorization_consumption_count"
            )
            == 0,
            candidate.get(
                "production_invocation_count"
            )
            == 0,
            candidate.get(
                "production_delivery_performed"
            )
            is False,
            candidate.get(
                "retry_performed"
            )
            is False,
            candidate.get(
                "scheduler_enabled"
            )
            is False,
            candidate.get(
                "automatic_promotion_performed"
            )
            is False,
            candidate.get(
                "authorization_state"
            )
            == "prepared",
            candidate.get(
                "reason_codes"
            )
            == (),
        )
    )


def build_manual_rollout_authorization_contract_summary(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    eligible = (
        manual_rollout_authorization_source_is_eligible(
            candidate
        )
    )

    return {
        "decision": (
            "authorized_to_prepare_single_manual_execution"
            if eligible
            else "not_authorized"
        ),
        "authorized": eligible,
        "owner_id": (
            candidate.get(
                "owner_id"
            )
            if eligible
            else None
        ),
        "approved_limit": (
            candidate.get(
                "approved_limit"
            )
            if eligible
            else None
        ),
        "single_execution_requirements": (
            MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS
            if eligible
            else ()
        ),
        "production_command": None,
        "production_delivery_performed": False,
        "authorization_consumed": False,
    }


class SavedSearchNotificationProductionDeliveryPilotSupervisedExecutionManualRolloutAuthorizationContractV268Tests(
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

    def test_v268_marker_scopes_and_next_lane_are_stable(self):
        self.assertEqual(
            V268_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CONTRACT,
            (
                "V268_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_AUTHORIZATION_CONTRACT"
            ),
        )

        self.assertEqual(
            len(V267_COMMITTED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V268_ALLOWED_SCOPE),
            2,
        )

        self.assertEqual(
            len(V269_PROPOSED_SCOPE),
            2,
        )

        self.assertEqual(
            NEXT_CHECKPOINT,
            (
                "v269: saved-search notification production delivery "
                "pilot supervised execution manual rollout "
                "authorization implementation"
            ),
        )

    def test_v268_and_v269_scopes_are_documentation_and_test_only(self):
        for scope in (
            V268_ALLOWED_SCOPE,
            V269_PROPOSED_SCOPE,
        ):
            self.assertFalse(
                any(
                    "/migrations/" in path
                    or "/management/commands/" in path
                    or "/templates/" in path
                    for path in scope
                )
            )

    def test_v268_v267_precondition_package_remains_exact(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_PRECONDITIONS
            ),
            47,
        )

        self.assertGreaterEqual(
            len(V267_CLOSEOUT_GATES),
            90,
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
            "closeout performs no production delivery",
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

    def test_v268_required_fields_are_exact_and_unique(self):
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

    def test_v268_evidence_allowlist_matches_required_fields(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST,
            MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS,
        )

    def test_v268_immutable_bindings_are_exact(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS
            ),
            14,
        )

        self.assertEqual(
            len(
                set(
                    MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS
                )
            ),
            14,
        )

        self.assertTrue(
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_IMMUTABLE_BINDINGS
            ).issubset(
                set(
                    MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_FIELDS
                )
            )
        )

    def test_v268_roles_and_separation_rules_are_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_REQUIRED_ROLES,
            (
                "decision_owner",
                "authorizing_operator",
                "evidence_reviewer",
                "privacy_reviewer",
                "incident_reviewer",
                "rollback_reviewer",
                "incident_commander",
            ),
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_ROLE_SEPARATION_RULES
            ),
            7,
        )

    def test_v268_decisions_are_exact_and_fail_closed(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS,
            (
                "not_authorized",
                "authorized_to_prepare_single_manual_execution",
            ),
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_DECISION_PRECEDENCE,
            MANUAL_ROLLOUT_AUTHORIZATION_DECISIONS,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_DECISION_PRECEDENCE[0],
            "not_authorized",
        )

    def test_v268_reason_families_are_exact_and_unique(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_COMPLETENESS_REASON_CODES
            ),
            14,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_SOURCE_REASON_CODES
            ),
            10,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_SCOPE_ROLE_REASON_CODES
            ),
            12,
        )

        self.assertEqual(
            len(
                MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTION_REASON_CODES
            ),
            5,
        )

        families = (
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_COMPLETENESS_REASON_CODES
            ),
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_SOURCE_REASON_CODES
            ),
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_SCOPE_ROLE_REASON_CODES
            ),
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTION_REASON_CODES
            ),
        )

        for index, family in enumerate(
            families
        ):
            for other in families[
                index + 1:
            ]:
                self.assertTrue(
                    family.isdisjoint(
                        other
                    )
                )

    def test_v268_global_reason_order_is_exact_and_unique(self):
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

    def test_v268_owner_limit_and_time_boundaries_are_exact(self):
        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_MAX_OWNER_COUNT,
            1,
        )

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_MAX_LIMIT,
            3,
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

        self.assertEqual(
            MANUAL_ROLLOUT_AUTHORIZATION_LIFETIME_SECONDS,
            600,
        )

    def test_v268_complete_candidate_is_authorizable_for_preparation_only(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate()
        )

        self.assertTrue(
            manual_rollout_authorization_source_is_eligible(
                candidate
            )
        )

        summary = (
            build_manual_rollout_authorization_contract_summary(
                candidate
            )
        )

        self.assertEqual(
            summary["decision"],
            "authorized_to_prepare_single_manual_execution",
        )

        self.assertTrue(
            summary["authorized"]
        )

        self.assertEqual(
            summary["owner_id"],
            101,
        )

        self.assertEqual(
            summary["approved_limit"],
            3,
        )

        self.assertEqual(
            summary["single_execution_requirements"],
            MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS,
        )

        self.assertIsNone(
            summary["production_command"]
        )

        self.assertFalse(
            summary["production_delivery_performed"]
        )

        self.assertFalse(
            summary["authorization_consumed"]
        )

    def test_v268_noneligible_source_is_not_authorized(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                source_consideration_eligible=False,
            )
        )

        summary = (
            build_manual_rollout_authorization_contract_summary(
                candidate
            )
        )

        self.assertEqual(
            summary["decision"],
            "not_authorized",
        )

        self.assertFalse(
            summary["authorized"]
        )

        self.assertIsNone(
            summary["owner_id"]
        )

        self.assertIsNone(
            summary["approved_limit"]
        )

        self.assertEqual(
            summary["single_execution_requirements"],
            (),
        )

    def test_v268_source_reason_codes_must_be_empty(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                source_consideration_reason_codes=(
                    "source-error",
                ),
            )
        )

        self.assertFalse(
            manual_rollout_authorization_source_is_eligible(
                candidate
            )
        )

    def test_v268_source_evidence_and_snapshot_are_mandatory(self):
        cases = (
            {
                "source_evidence_sanitized": False,
            },
            {
                "source_immutable_snapshot_complete": False,
            },
            {
                "source_authorization_preconditions_complete": False,
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertFalse(
                    manual_rollout_authorization_source_is_eligible(
                        candidate
                    )
                )

    def test_v268_historical_authorization_cannot_be_reused(self):
        candidate = (
            build_complete_manual_rollout_authorization_candidate(
                authorization_id="authorization-001",
            )
        )

        self.assertFalse(
            manual_rollout_authorization_source_is_eligible(
                candidate
            )
        )

    def test_v268_owner_scope_cannot_expand(self):
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
            {
                "source_considered_owner_ids": (
                    202,
                ),
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertFalse(
                    manual_rollout_authorization_source_is_eligible(
                        candidate
                    )
                )

    def test_v268_limit_cannot_expand(self):
        cases = (
            {
                "source_approved_limit": 4,
            },
            {
                "source_considered_limit": 4,
            },
            {
                "approved_limit": 4,
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
                candidate = (
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertFalse(
                    manual_rollout_authorization_source_is_eligible(
                        candidate
                    )
                )

    def test_v268_both_confirmations_are_mandatory(self):
        for field in (
            "production_confirmation_primary",
            "production_confirmation_secondary",
        ):
            with self.subTest(
                field=field
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate(
                        **{
                            field: False,
                        }
                    )
                )

                self.assertFalse(
                    manual_rollout_authorization_source_is_eligible(
                        candidate
                    )
                )

    def test_v268_authorization_begins_unconsumed_and_nonexecuted(self):
        cases = (
            {
                "authorization_consumption_count": 1,
            },
            {
                "production_invocation_count": 1,
            },
            {
                "production_delivery_performed": True,
            },
            {
                "retry_performed": True,
            },
            {
                "scheduler_enabled": True,
            },
            {
                "automatic_promotion_performed": True,
            },
            {
                "authorization_state": "consumed",
            },
        )

        for changes in cases:
            with self.subTest(
                changes=changes
            ):
                candidate = (
                    build_complete_manual_rollout_authorization_candidate(
                        **changes
                    )
                )

                self.assertFalse(
                    manual_rollout_authorization_source_is_eligible(
                        candidate
                    )
                )

    def test_v268_contract_helpers_perform_no_external_action(self):
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
            summary = (
                build_manual_rollout_authorization_contract_summary(
                    candidate
                )
            )

        subprocess_run.assert_not_called()
        get_connection.assert_not_called()
        call_command_mock.assert_not_called()

        self.assertTrue(
            summary["authorized"]
        )

    def test_v268_single_execution_requirements_are_complete(self):
        self.assertEqual(
            len(
                MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS
            ),
            18,
        )

        required = {
            "authorization decision is authorized_to_prepare_single_manual_execution",
            "authorization identifier is new",
            "historical source authorization remains nonreusable",
            "one explicit positive owner identifier",
            "owner scope contains exactly one owner",
            "explicit limit between one and three",
            "execution limit cannot exceed authorization limit",
            "current readiness evidence",
            "current preview evidence",
            "current provider sender and backend state",
            "both production confirmations",
            "authorization remains unconsumed and unexpired",
            "one-shot consumption occurs only at execution boundary",
            "automatic retry and automatic promotion remain disabled",
            "scheduler remains disabled",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_SINGLE_EXECUTION_REQUIREMENTS
                )
            )
        )

    def test_v268_privacy_exclusions_are_complete(self):
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
            "raw exception traceback",
            MANUAL_ROLLOUT_AUTHORIZATION_PRIVACY_EXCLUSIONS,
        )

    def test_v268_allowlist_excludes_sensitive_fields(self):
        self.assertTrue(
            set(
                MANUAL_ROLLOUT_AUTHORIZATION_EVIDENCE_ALLOWLIST
            ).isdisjoint(
                MANUAL_ROLLOUT_AUTHORIZATION_SENSITIVE_INPUT_KEYS
            )
        )

    def test_v268_prohibited_actions_are_complete(self):
        required = {
            "production delivery during authorization preparation",
            "authorization consumption during authorization preparation",
            "delivery retry during authorization preparation",
            "scheduler enablement",
            "automatic rollout promotion",
            "production feature-gate mutation",
            "owner-scope expansion",
            "limit expansion",
            "historical source authorization reuse",
            "global all-owner execution",
            "multi-owner execution",
            "blind retry",
            "direct SQL repair",
            "Django shell timestamp repair",
            "privacy sanitizer bypass",
            "automatic authorization renewal",
        }

        self.assertTrue(
            required.issubset(
                set(
                    MANUAL_ROLLOUT_AUTHORIZATION_PROHIBITED_ACTIONS
                )
            )
        )

    def test_v268_default_readiness_remains_not_ready(self):
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
    def test_v268_production_like_readiness_remains_ready(self):
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
    def test_v268_readiness_execution_opens_no_email_connection(self):
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

    def test_v268_command_surfaces_remain_unchanged(self):
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

    def test_v268_production_batch_cap_remains_25(self):
        source = self._read_backend(
            "listings/"
            "saved_search_notification_email_sender.py"
        )

        self.assertIn(
            "V242_PRODUCTION_DELIVERY_BATCH_MAX = 25",
            source,
        )

    def test_v268_scheduler_remains_nonautomatic(self):
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

    def test_v268_v267_package_remains_present(self):
        source = self._read_backend(
            "listings/"
            "test_saved_search_notification_production_delivery_"
            "pilot_supervised_execution_manual_rollout_consideration_"
            "closeout_audit_v267.py"
        )

        self.assertIn(
            (
                "V267_SAVED_SEARCH_NOTIFICATION_PRODUCTION_"
                "DELIVERY_PILOT_SUPERVISED_EXECUTION_"
                "MANUAL_ROLLOUT_CONSIDERATION_CLOSEOUT_AUDIT"
            ),
            source,
        )

        self.assertIn(
            (
                "v268: saved-search notification production delivery "
                "pilot supervised execution manual rollout "
                "authorization contract"
            ),
            source,
        )

    def test_v268_marker_does_not_leak_into_protected_runtime(self):
        marker = (
            V268_SAVED_SEARCH_NOTIFICATION_PRODUCTION_DELIVERY_PILOT_SUPERVISED_EXECUTION_MANUAL_ROLLOUT_AUTHORIZATION_CONTRACT
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

    def test_v268_no_migration_0017_exists(self):
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

    def test_v268_acceptance_gate_matrix_is_complete(self):
        required = {
            "v267 closeout package remains present",
            "v268 scope remains exactly two contract files",
            "v269 proposed scope remains exactly two implementation files",
            "forty-six required fields remain exact",
            "forty-one reason codes remain exact",
            "source consideration must be eligible",
            "authorization identifier must be new",
            "historical authorization cannot be reused",
            "owner scope contains exactly one owner",
            "authorization limit cannot expand source considered limit",
            "both production confirmations remain mandatory",
            "positive decision permits preparation only",
            "positive decision produces no production command",
            "positive decision performs no production delivery",
            "positive decision consumes no authorization",
            "positive decision performs no retry",
            "positive decision enables no scheduler",
            "positive decision performs no automatic promotion",
            "strict evidence allowlist remains exact",
            "contract helper invokes no subprocess",
            "contract helper invokes no management command",
            "contract helper opens no email connection",
            "production sender remains unchanged",
            "production command remains unchanged",
            "readiness service remains unchanged",
            "scheduler remains nonautomatic",
            "migration 0016 remains latest",
            "migration 0017 remains absent",
            "full regression remains green",
        }

        self.assertGreaterEqual(
            len(V268_ACCEPTANCE_GATES),
            85,
        )

        self.assertTrue(
            required.issubset(
                set(V268_ACCEPTANCE_GATES)
            )
        )
