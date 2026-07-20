from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from listings.notification_delivery_policy_v304 import (
    V304_LEGACY_RECIPIENT_OUTPUT_SURFACES,
    V304_NOTIFICATION_DELIVERY_POLICY_BASELINE,
    V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT,
    build_notification_delivery_policy_baseline_v304,
    discover_notification_delivery_policy_capabilities_v304,
    get_notification_delivery_policy_baseline_v304,
)


class NotificationDeliveryPolicyBuilderV304Tests(
    SimpleTestCase
):
    def _build(
        self,
        **overrides,
    ):
        values = {
            "verified_recipient_state": False,
            "provider_message_id_state": False,
            "provider_outcome_state": False,
            "retention_days": None,
            "operator_recipient_output_policy": "",
        }
        values.update(overrides)

        return (
            build_notification_delivery_policy_baseline_v304(
                **values
            )
        )

    def _check(
        self,
        result,
        check_id,
    ):
        return next(
            check
            for check in result["checks"]
            if check["check_id"] == check_id
        )

    def test_repository_discovery_reports_current_policy_gaps(
        self,
    ):
        capabilities = (
            discover_notification_delivery_policy_capabilities_v304()
        )

        self.assertFalse(
            capabilities["verified_recipient_state"]
        )
        self.assertFalse(
            capabilities["provider_message_id_state"]
        )
        self.assertFalse(
            capabilities["provider_outcome_state"]
        )
        self.assertIsNone(
            capabilities["retention_days"]
        )
        self.assertEqual(
            capabilities[
                "operator_recipient_output_policy"
            ],
            "",
        )
        self.assertEqual(
            capabilities[
                "legacy_recipient_output_surfaces"
            ],
            list(
                V304_LEGACY_RECIPIENT_OUTPUT_SURFACES
            ),
        )

    def test_default_baseline_is_defined_but_not_ready(
        self,
    ):
        result = (
            get_notification_delivery_policy_baseline_v304()
        )

        self.assertEqual(
            result["marker"],
            V304_NOTIFICATION_DELIVERY_POLICY_BASELINE,
        )
        self.assertEqual(
            result["schema_version"],
            1,
        )
        self.assertTrue(
            result["policy_defined"]
        )
        self.assertTrue(
            result["read_only"]
        )
        self.assertFalse(
            result["mutation_allowed"]
        )
        self.assertFalse(
            result["delivery_attempted"]
        )
        self.assertFalse(
            result["provider_accessed"]
        )
        self.assertFalse(
            result["runtime_enforcement_ready"]
        )
        self.assertFalse(
            result["runtime_enforcement_enabled"]
        )
        self.assertEqual(
            result["blocking_not_ready_count"],
            4,
        )

    def test_current_delivery_guardrails_remain_ready(
        self,
    ):
        result = self._build()

        check = self._check(
            result,
            "current_delivery_guardrails",
        )

        self.assertTrue(
            check["ready"]
        )
        self.assertFalse(
            check["blocking"]
        )
        self.assertTrue(
            check["enforcement_enabled"]
        )
        self.assertEqual(
            check["status"],
            "ready",
        )

    def test_ready_state_requires_all_four_policy_capabilities(
        self,
    ):
        result = self._build(
            verified_recipient_state=True,
            provider_message_id_state=True,
            provider_outcome_state=True,
            retention_days=90,
            operator_recipient_output_policy=(
                V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT
            ),
        )

        self.assertTrue(
            result["runtime_enforcement_ready"]
        )
        self.assertFalse(
            result["runtime_enforcement_enabled"]
        )
        self.assertEqual(
            result["blocking_not_ready_count"],
            0,
        )
        self.assertEqual(
            result["status"],
            "implementation_ready_enforcement_disabled",
        )

    def test_provider_policy_requires_identity_and_outcome_state(
        self,
    ):
        combinations = (
            (False, False),
            (True, False),
            (False, True),
        )

        for message_id, outcome in combinations:
            with self.subTest(
                message_id=message_id,
                outcome=outcome,
            ):
                result = self._build(
                    verified_recipient_state=True,
                    provider_message_id_state=message_id,
                    provider_outcome_state=outcome,
                    retention_days=90,
                    operator_recipient_output_policy=(
                        V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT
                    ),
                )

                check = self._check(
                    result,
                    "provider_delivery_outcomes",
                )

                self.assertFalse(
                    check["ready"]
                )
                self.assertEqual(
                    check["status"],
                    "deferred",
                )

    def test_retention_requires_positive_integer_days(
        self,
    ):
        for value in (
            None,
            0,
            -1,
            True,
            "invalid",
        ):
            with self.subTest(value=value):
                result = self._build(
                    retention_days=value
                )

                check = self._check(
                    result,
                    "delivery_event_retention",
                )

                self.assertFalse(
                    check["ready"]
                )
                self.assertIsNone(
                    result["retention_days"]
                )

        ready = self._build(
            retention_days="30"
        )

        self.assertTrue(
            self._check(
                ready,
                "delivery_event_retention",
            )["ready"]
        )
        self.assertEqual(
            ready["retention_days"],
            30,
        )

    def test_operator_policy_is_normalized_and_exact(
        self,
    ):
        ready = self._build(
            operator_recipient_output_policy=(
                " REDACTED_BY_DEFAULT "
            )
        )

        self.assertTrue(
            self._check(
                ready,
                "operator_recipient_output",
            )["ready"]
        )

        incomplete = self._build(
            operator_recipient_output_policy="redacted"
        )

        self.assertFalse(
            self._check(
                incomplete,
                "operator_recipient_output",
            )["ready"]
        )

    def test_structured_policy_result_contains_no_address_values(
        self,
    ):
        result = self._build()

        serialized = json.dumps(
            result,
            sort_keys=True,
        )

        self.assertNotIn(
            "person@example.test",
            serialized,
        )
        self.assertNotIn(
            "@classifieds.local",
            serialized,
        )
        self.assertEqual(
            result[
                "legacy_recipient_output_surface_count"
            ],
            len(
                V304_LEGACY_RECIPIENT_OUTPUT_SURFACES
            ),
        )


class NotificationDeliveryPolicyCommandV304Tests(
    SimpleTestCase
):
    def test_text_command_is_sanitized_and_read_only(
        self,
    ):
        output = StringIO()

        call_command(
            "check_notification_delivery_policy",
            stdout=output,
        )

        rendered = output.getvalue()

        self.assertIn(
            V304_NOTIFICATION_DELIVERY_POLICY_BASELINE,
            rendered,
        )
        self.assertIn(
            "read_only=true",
            rendered,
        )
        self.assertIn(
            "runtime_enforcement_ready=false",
            rendered,
        )
        self.assertIn(
            "check=verified_recipient",
            rendered,
        )
        self.assertIn(
            "check=provider_delivery_outcomes",
            rendered,
        )
        self.assertIn(
            "check=delivery_event_retention",
            rendered,
        )
        self.assertIn(
            "check=operator_recipient_output",
            rendered,
        )
        self.assertNotIn(
            "@",
            rendered,
        )

    def test_json_command_is_structured_and_sanitized(
        self,
    ):
        output = StringIO()

        call_command(
            "check_notification_delivery_policy",
            "--json",
            stdout=output,
        )

        result = json.loads(
            output.getvalue()
        )

        self.assertEqual(
            result["marker"],
            V304_NOTIFICATION_DELIVERY_POLICY_BASELINE,
        )
        self.assertTrue(
            result["read_only"]
        )
        self.assertFalse(
            result["runtime_enforcement_ready"]
        )
        self.assertNotIn(
            "@",
            output.getvalue(),
        )

    def test_strict_command_fails_while_capabilities_are_missing(
        self,
    ):
        with self.assertRaisesMessage(
            CommandError,
            "blocking implementation capabilities remain unavailable",
        ):
            call_command(
                "check_notification_delivery_policy",
                "--strict",
                stdout=StringIO(),
                stderr=StringIO(),
            )

    def test_strict_command_passes_for_ready_mocked_policy(
        self,
    ):
        ready = (
            build_notification_delivery_policy_baseline_v304(
                verified_recipient_state=True,
                provider_message_id_state=True,
                provider_outcome_state=True,
                retention_days=90,
                operator_recipient_output_policy=(
                    V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT
                ),
            )
        )

        with patch(
            (
                "listings.management.commands."
                "check_notification_delivery_policy."
                "get_notification_delivery_policy_baseline_v304"
            ),
            return_value=ready,
        ):
            output = StringIO()

            call_command(
                "check_notification_delivery_policy",
                "--strict",
                stdout=output,
            )

        self.assertIn(
            "runtime_enforcement_ready=true",
            output.getvalue(),
        )
        self.assertNotIn(
            "@",
            output.getvalue(),
        )
