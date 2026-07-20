from __future__ import annotations


V305_NOTIFICATION_RECIPIENT_OUTPUT_REDACTION_MIGRATION = (
    "V305_NOTIFICATION_RECIPIENT_OUTPUT_REDACTION_MIGRATION"
)

V305_OPERATOR_RECIPIENT_REDACTION_TEXT = "[redacted]"
V305_OPERATOR_RECIPIENT_MISSING_TEXT = "<missing>"

V305_MIGRATED_RECIPIENT_OUTPUT_SURFACES = (
    "process_saved_search_notifications:execute_email_send",
    "process_saved_search_notifications:render_email_previews",
    "saved_search_notification_observability:sample_output",
    "saved_search_notification_audit:rollback_output",
)


def redact_notification_recipient_for_operator_v305(
    recipient,
) -> str:
    normalized = str(recipient or "").strip()

    if (
        not normalized
        or normalized
        == V305_OPERATOR_RECIPIENT_MISSING_TEXT
    ):
        return V305_OPERATOR_RECIPIENT_MISSING_TEXT

    if (
        normalized
        == V305_OPERATOR_RECIPIENT_REDACTION_TEXT
    ):
        return V305_OPERATOR_RECIPIENT_REDACTION_TEXT

    return V305_OPERATOR_RECIPIENT_REDACTION_TEXT


__all__ = [
    "V305_MIGRATED_RECIPIENT_OUTPUT_SURFACES",
    "V305_NOTIFICATION_RECIPIENT_OUTPUT_REDACTION_MIGRATION",
    "V305_OPERATOR_RECIPIENT_MISSING_TEXT",
    "V305_OPERATOR_RECIPIENT_REDACTION_TEXT",
    "redact_notification_recipient_for_operator_v305",
]
