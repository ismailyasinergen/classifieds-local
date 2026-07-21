from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone

from accounts.models import EmailVerificationState
from listings.listing_price_alerts_v285 import (
    send_listing_price_alert_v285,
)
from listings.notification_delivery_policy_v304 import (
    build_notification_delivery_policy_baseline_v304,
    get_notification_delivery_policy_baseline_v304,
)
from listings.notification_delivery_runtime_enforcement_v309 import (
    notification_delivery_recipient_decision_v309,
    notification_delivery_recipient_email_v309,
)
from listings.saved_search_notification_email_sender import (
    SavedSearchNotificationEmailDeliveryBlocked,
    send_saved_search_notification_email,
)
from listings.saved_search_notifications import (
    get_saved_search_recipient_email,
)


class NotificationDeliveryRuntimeEnforcementV309Tests(
    TestCase
):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="v309-recipient",
            email="v309-recipient@classifieds.local",
            password="test-pass-v309",
        )

        mail.outbox = []

    def _verification_state(self):
        return EmailVerificationState.objects.get(
            user=self.user
        )

    def _mark_verified(self):
        state = self._verification_state()
        state.email_snapshot = self.user.email
        state.verified_at = timezone.now()
        state.verification_method = (
            EmailVerificationState
            .METHOD_SIGNED_LINK_V306
        )
        state.save(
            update_fields=[
                "email_snapshot",
                "verified_at",
                "verification_method",
                "updated_at",
            ]
        )
        return state

    def test_default_off_preserves_current_recipient(self):
        decision = (
            notification_delivery_recipient_decision_v309(
                self.user
            )
        )

        self.assertFalse(
            decision.enforcement_enabled
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(
            decision.recipient_email,
            self.user.email,
        )
        self.assertEqual(
            decision.reason_code,
            "runtime_enforcement_disabled",
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_enabled_gate_blocks_unverified_recipient(self):
        decision = (
            notification_delivery_recipient_decision_v309(
                self.user
            )
        )

        self.assertTrue(
            decision.enforcement_enabled
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.recipient_email,
            "",
        )
        self.assertEqual(
            decision.reason_code,
            "recipient_unverified",
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_enabled_gate_allows_current_verified_recipient(self):
        self._mark_verified()

        decision = (
            notification_delivery_recipient_decision_v309(
                self.user
            )
        )

        self.assertTrue(decision.allowed)
        self.assertTrue(
            decision.recipient_verified
        )
        self.assertEqual(
            decision.recipient_email,
            self.user.email,
        )
        self.assertEqual(
            decision.reason_code,
            "recipient_verified",
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_email_change_fails_closed(self):
        self._mark_verified()

        self.user.email = (
            "v309-changed@classifieds.local"
        )
        self.user.save(
            update_fields=["email"]
        )

        decision = (
            notification_delivery_recipient_decision_v309(
                self.user
            )
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.reason_code,
            "recipient_unverified",
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_database_failure_fails_closed(self):
        with patch.object(
            EmailVerificationState.objects,
            "filter",
            side_effect=DatabaseError(
                "verification table unavailable"
            ),
        ):
            decision = (
                notification_delivery_recipient_decision_v309(
                    self.user
                )
            )

        self.assertFalse(decision.allowed)
        self.assertFalse(
            decision.verification_state_available
        )
        self.assertEqual(
            decision.reason_code,
            "verification_state_unavailable",
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_saved_search_recipient_getter_uses_gate(self):
        saved_search = SimpleNamespace(
            user=self.user
        )

        self.assertEqual(
            get_saved_search_recipient_email(
                saved_search
            ),
            "",
        )

        self._mark_verified()

        self.assertEqual(
            get_saved_search_recipient_email(
                saved_search
            ),
            self.user.email,
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_price_alert_sender_blocks_before_message_build(self):
        alert = SimpleNamespace(
            user=self.user
        )

        with patch(
            "listings.listing_price_alerts_v285."
            "build_listing_price_alert_email_v285"
        ) as build_message:
            delivered = (
                send_listing_price_alert_v285(
                    alert
                )
            )

        self.assertEqual(delivered, 0)
        build_message.assert_not_called()

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_mature_sender_blocks_before_backend_build(self):
        saved_search = SimpleNamespace(
            pk=309,
            user_id=self.user.pk,
            user=self.user,
            email_notifications_enabled=True,
            last_notification_checked_at=None,
            last_notification_sent_at=None,
        )

        rendered = SimpleNamespace(
            context={
                "recipient_email": self.user.email,
            },
            subject="V309",
            text_body="V309",
            html_body="",
        )

        runtime_context = MagicMock()
        runtime_context.for_surface.return_value = (
            runtime_context
        )

        with (
            patch(
                "listings.saved_search_notification_email_sender."
                "saved_search_includes_price_drops_v287",
                return_value=False,
            ),
            patch(
                "listings.saved_search_notification_email_sender."
                "notification_type_enabled_for_user_v288",
                return_value=True,
            ),
            patch(
                "listings.saved_search_notification_email_sender."
                "build_saved_search_notification_fingerprint",
                return_value="v309-fingerprint",
            ),
            patch(
                "listings.saved_search_notification_email_sender."
                "render_saved_search_notification_email",
                return_value=rendered,
            ),
            patch(
                "listings.saved_search_notification_email_sender."
                "record_saved_search_notification_runtime_event"
            ) as record_event,
            patch(
                "listings.saved_search_notification_email_sender."
                "_build_email_message"
            ) as build_message,
        ):
            with self.assertRaisesMessage(
                SavedSearchNotificationEmailDeliveryBlocked,
                "eligible verified recipient",
            ):
                send_saved_search_notification_email(
                    saved_search,
                    matching_listings=(),
                    execute_send=True,
                    require_test_email_backend=False,
                    runtime_context=runtime_context,
                    notification_preference_map_v288={},
                )

        build_message.assert_not_called()
        self.assertEqual(
            record_event.call_args.kwargs[
                "reason_code"
            ],
            "recipient_unverified",
        )

    def test_policy_builder_reports_disabled_by_default(self):
        policy = (
            build_notification_delivery_policy_baseline_v304(
                verified_recipient_state=True,
                provider_message_id_state=True,
                provider_outcome_state=True,
                retention_days=90,
                retention_legal_hold_state=True,
                retention_deletion_evidence_state=True,
                retention_backup_policy=(
                    "restore_requires_recleanup"
                ),
                retention_cleanup_dry_run_contract=True,
                operator_recipient_output_policy=(
                    "redacted_by_default"
                ),
                legacy_recipient_output_surfaces=(),
            )
        )

        self.assertTrue(
            policy["runtime_enforcement_ready"]
        )
        self.assertFalse(
            policy["runtime_enforcement_enabled"]
        )
        self.assertEqual(
            policy["status"],
            "implementation_ready_enforcement_disabled",
        )

    def test_policy_builder_reports_effective_enforcement(self):
        policy = (
            build_notification_delivery_policy_baseline_v304(
                verified_recipient_state=True,
                provider_message_id_state=True,
                provider_outcome_state=True,
                retention_days=90,
                retention_legal_hold_state=True,
                retention_deletion_evidence_state=True,
                retention_backup_policy=(
                    "restore_requires_recleanup"
                ),
                retention_cleanup_dry_run_contract=True,
                operator_recipient_output_policy=(
                    "redacted_by_default"
                ),
                runtime_enforcement_enabled=True,
                legacy_recipient_output_surfaces=(),
            )
        )

        self.assertTrue(
            policy["runtime_enforcement_ready"]
        )
        self.assertTrue(
            policy["runtime_enforcement_enabled"]
        )
        self.assertEqual(
            policy["status"],
            "runtime_enforcement_enabled",
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_recipient_email_helper_returns_no_raw_address_when_blocked(
        self,
    ):
        self.assertEqual(
            notification_delivery_recipient_email_v309(
                self.user
            ),
            "",
        )

    def test_saved_search_command_preserves_gate_reason_code(
        self,
    ):
        command_source = (
            Path(
                "listings/management/commands/"
                "check_saved_search_notifications.py"
            )
            .read_text(encoding="utf-8")
        )

        self.assertIn(
            "notification_delivery_recipient_decision_v309",
            command_source,
        )
        self.assertIn(
            "reason=reason_code_v309",
            command_source,
        )
        self.assertIn(
            "has no eligible verified recipient address",
            command_source,
        )

    @override_settings(
        NOTIFICATION_DELIVERY_RUNTIME_ENFORCEMENT_ENABLED=True
    )
    def test_repository_policy_reports_enabled_gate(self):
        policy = (
            get_notification_delivery_policy_baseline_v304()
        )

        self.assertTrue(
            policy["runtime_enforcement_ready"]
        )
        self.assertTrue(
            policy["runtime_enforcement_enabled"]
        )
        self.assertEqual(
            policy["status"],
            "runtime_enforcement_enabled",
        )
