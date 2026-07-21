from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from listings.notification_delivery_policy_v304 import (
    V304_LEGACY_RECIPIENT_OUTPUT_SURFACES,
    V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT,
    discover_notification_delivery_policy_capabilities_v304,
    get_notification_delivery_policy_baseline_v304,
)
from listings.notification_recipient_output_redaction_v305 import (
    V305_MIGRATED_RECIPIENT_OUTPUT_SURFACES,
    V305_NOTIFICATION_RECIPIENT_OUTPUT_REDACTION_MIGRATION,
    V305_OPERATOR_RECIPIENT_MISSING_TEXT,
    V305_OPERATOR_RECIPIENT_REDACTION_TEXT,
    redact_notification_recipient_for_operator_v305,
)
from listings.saved_search_notification_audit import (
    format_saved_search_notification_rollback_plan_lines,
)
from listings.saved_search_notification_observability import (
    format_saved_search_notification_observability_lines,
)


class NotificationRecipientOutputRedactionV305Tests(
    SimpleTestCase
):
    def test_v305_surface_inventory_is_exact(self):
        self.assertEqual(
            V305_NOTIFICATION_RECIPIENT_OUTPUT_REDACTION_MIGRATION,
            "V305_NOTIFICATION_RECIPIENT_OUTPUT_REDACTION_MIGRATION",
        )
        self.assertEqual(
            V305_MIGRATED_RECIPIENT_OUTPUT_SURFACES,
            (
                "process_saved_search_notifications:"
                "execute_email_send",
                "process_saved_search_notifications:"
                "render_email_previews",
                "saved_search_notification_observability:"
                "sample_output",
                "saved_search_notification_audit:"
                "rollback_output",
            ),
        )
        self.assertEqual(
            len(
                set(
                    V305_MIGRATED_RECIPIENT_OUTPUT_SURFACES
                )
            ),
            4,
        )

    def test_v305_shared_helper_redacts_or_marks_missing(self):
        self.assertEqual(
            redact_notification_recipient_for_operator_v305(
                "private@example.test"
            ),
            V305_OPERATOR_RECIPIENT_REDACTION_TEXT,
        )
        self.assertEqual(
            redact_notification_recipient_for_operator_v305(
                "  private@example.test  "
            ),
            V305_OPERATOR_RECIPIENT_REDACTION_TEXT,
        )

        for value in (
            None,
            "",
            "   ",
            V305_OPERATOR_RECIPIENT_MISSING_TEXT,
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    redact_notification_recipient_for_operator_v305(
                        value
                    ),
                    V305_OPERATOR_RECIPIENT_MISSING_TEXT,
                )

        self.assertEqual(
            redact_notification_recipient_for_operator_v305(
                V305_OPERATOR_RECIPIENT_REDACTION_TEXT
            ),
            V305_OPERATOR_RECIPIENT_REDACTION_TEXT,
        )

    def test_v305_observability_formatter_is_fail_closed(self):
        snapshot = {
            "owner_scoped": False,
            "total_count": 1,
            "enabled_count": 1,
            "disabled_count": 0,
            "enabled_with_email_count": 1,
            "missing_recipient_email_count": 0,
            "checked_timestamp_count": 0,
            "sent_timestamp_count": 0,
            "sample_count": 1,
            "samples": [
                {
                    "saved_search_id": 7,
                    "owner_id": 3,
                    "email_notifications_enabled": True,
                    "recipient_email": "private@example.test",
                    "last_notification_checked_at": None,
                    "last_notification_sent_at": None,
                    "label": "Private sample",
                }
            ],
        }

        rendered = "\n".join(
            format_saved_search_notification_observability_lines(
                snapshot
            )
        )

        self.assertIn("recipient=[redacted]", rendered)
        self.assertNotIn(
            "private@example.test",
            rendered,
        )

        snapshot["samples"][0]["recipient_email"] = (
            V305_OPERATOR_RECIPIENT_MISSING_TEXT
        )

        missing_rendered = "\n".join(
            format_saved_search_notification_observability_lines(
                snapshot
            )
        )

        self.assertIn(
            "recipient=<missing>",
            missing_rendered,
        )
        self.assertNotIn(
            "recipient=[redacted]",
            missing_rendered,
        )

    def test_v305_rollback_formatter_is_fail_closed(self):
        plan = {
            "owner_scoped": False,
            "candidate_count": 1,
            "rollback_candidate_count": 1,
            "untouched_candidate_count": 0,
            "rollback_candidates": [
                {
                    "saved_search_id": 9,
                    "owner_id": 4,
                    "recipient_email": "private@example.test",
                    "last_notification_sent_at": (
                        "2026-07-20T00:00:00+00:00"
                    ),
                    "label": "Private rollback",
                }
            ],
        }

        rendered = "\n".join(
            format_saved_search_notification_rollback_plan_lines(
                plan
            )
        )

        self.assertIn("recipient=[redacted]", rendered)
        self.assertNotIn(
            "private@example.test",
            rendered,
        )

    def test_v305_redaction_remains_ready_after_v306_verified_recipient(self):
        self.assertEqual(
            settings.NOTIFICATION_OPERATOR_RECIPIENT_OUTPUT_POLICY,
            V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT,
        )

        capabilities = (
            discover_notification_delivery_policy_capabilities_v304()
        )

        self.assertEqual(
            capabilities[
                "operator_recipient_output_policy"
            ],
            V304_OPERATOR_OUTPUT_REDACTED_BY_DEFAULT,
        )
        self.assertEqual(
            capabilities[
                "legacy_recipient_output_surfaces"
            ],
            [],
        )
        self.assertEqual(
            V304_LEGACY_RECIPIENT_OUTPUT_SURFACES,
            (),
        )

        result = (
            get_notification_delivery_policy_baseline_v304()
        )

        operator_check = next(
            check
            for check in result["checks"]
            if check["check_id"]
            == "operator_recipient_output"
        )

        self.assertTrue(operator_check["ready"])
        self.assertEqual(
            operator_check["status"],
            "ready",
        )
        self.assertEqual(
            operator_check["reason_code"],
            "operator_output_redacted_by_default",
        )
        self.assertEqual(
            result["blocking_not_ready_count"],
            0,
        )
        self.assertTrue(
            result["runtime_enforcement_ready"]
        )

    def test_v305_process_command_uses_shared_redaction(self):
        command_path = (
            Path(__file__).resolve().parent
            / "management"
            / "commands"
            / "process_saved_search_notifications.py"
        )

        source = command_path.read_text(
            encoding="utf-8"
        )

        self.assertGreaterEqual(
            source.count(
                "redact_notification_recipient_for_operator_v305"
            ),
            3,
        )
        self.assertNotIn(
            "f\"recipient={item['recipient_email']} \"",
            source,
        )
        self.assertNotIn(
            "f\"recipient={preview['recipient_email']} \"",
            source,
        )
