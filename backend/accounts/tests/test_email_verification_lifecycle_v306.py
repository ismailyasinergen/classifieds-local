from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.email_verification_v306 import (
    confirm_email_verification_v306,
    email_verification_token_max_age_seconds_v306,
    prepare_email_verification_request_v306,
)
from accounts.models import EmailVerificationState
from listings.notification_delivery_policy_v304 import (
    V306_VERIFIED_RECIPIENT_REQUIRED_FIELDS,
    V306_VERIFIED_RECIPIENT_STATE_MODEL,
    discover_notification_delivery_policy_capabilities_v304,
    get_notification_delivery_policy_baseline_v304,
)


@override_settings(
    EMAIL_BACKEND=(
        "django.core.mail.backends.locmem.EmailBackend"
    ),
    EMAIL_VERIFICATION_TOKEN_MAX_AGE_SECONDS=3600,
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS=300,
)
class EmailVerificationLifecycleV306Tests(TestCase):
    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="v306-owner",
            email="owner@example.test",
            password="test-pass-123",
        )

    def _state(self):
        return EmailVerificationState.objects.get(
            user=self.user
        )

    def _request_token(self):
        result = prepare_email_verification_request_v306(
            self.user
        )

        self.assertEqual(result.status, "sent")
        self.assertTrue(result.token)

        return result.token

    def test_user_creation_creates_unverified_state(self):
        state = self._state()

        self.assertEqual(
            state.email_snapshot,
            self.user.email,
        )
        self.assertIsNone(state.verified_at)
        self.assertFalse(
            state.is_verified_for_current_email
        )

    def test_request_token_contains_no_raw_email(self):
        token = self._request_token()

        self.assertNotIn(
            self.user.email,
            token,
        )

        state = self._state()

        self.assertEqual(state.token_version, 1)
        self.assertIsNotNone(
            state.last_requested_at
        )

    def test_resend_cooldown_blocks_second_token(self):
        first = prepare_email_verification_request_v306(
            self.user
        )
        second = prepare_email_verification_request_v306(
            self.user
        )

        self.assertEqual(first.status, "sent")
        self.assertEqual(second.status, "cooldown")
        self.assertGreater(
            second.retry_after_seconds,
            0,
        )
        self.assertEqual(
            self._state().token_version,
            1,
        )

    def test_confirmation_marks_current_email_verified(self):
        token = self._request_token()

        result = confirm_email_verification_v306(
            user=self.user,
            token=token,
        )

        self.assertTrue(result.verified)
        self.assertEqual(
            result.status,
            "verified",
        )

        state = self._state()

        self.assertTrue(
            state.is_verified_for_current_email
        )
        self.assertEqual(
            state.verification_method,
            EmailVerificationState.METHOD_SIGNED_LINK_V306,
        )
        self.assertIsNotNone(state.verified_at)

    def test_confirmation_token_is_single_use(self):
        token = self._request_token()

        first = confirm_email_verification_v306(
            user=self.user,
            token=token,
        )
        replay = confirm_email_verification_v306(
            user=self.user,
            token=token,
        )

        self.assertTrue(first.verified)
        self.assertFalse(replay.verified)
        self.assertEqual(
            replay.status,
            "invalid_or_expired",
        )

    def test_expired_token_is_rejected(self):
        issued_at = 1_000_000

        with patch(
            "django.core.signing.time.time",
            return_value=issued_at,
        ):
            token = self._request_token()

        with patch(
            "django.core.signing.time.time",
            return_value=(
                issued_at
                + email_verification_token_max_age_seconds_v306()
                + 1
            ),
        ):
            result = confirm_email_verification_v306(
                user=self.user,
                token=token,
            )

        self.assertFalse(result.verified)
        self.assertEqual(
            result.status,
            "invalid_or_expired",
        )

    def test_email_change_invalidates_state_and_old_token(self):
        token = self._request_token()

        verified = confirm_email_verification_v306(
            user=self.user,
            token=token,
        )

        self.assertTrue(verified.verified)

        old_version = self._state().token_version

        self.user.email = "changed@example.test"
        self.user.save(
            update_fields=["email"]
        )

        state = self._state()

        self.assertEqual(
            state.email_snapshot,
            "changed@example.test",
        )
        self.assertIsNone(state.verified_at)
        self.assertEqual(
            state.verification_method,
            "",
        )
        self.assertGreater(
            state.token_version,
            old_version,
        )

        replay = confirm_email_verification_v306(
            user=self.user,
            token=token,
        )

        self.assertFalse(replay.verified)

    def test_token_cannot_verify_another_user(self):
        token = self._request_token()

        other = get_user_model().objects.create_user(
            username="v306-other",
            email="other@example.test",
            password="test-pass-123",
        )

        result = confirm_email_verification_v306(
            user=other,
            token=token,
        )

        self.assertFalse(result.verified)
        self.assertFalse(
            other.email_verification_state
            .is_verified_for_current_email
        )

    def test_status_page_requires_login(self):
        response = self.client.get(
            reverse(
                "accounts:email_verification_status_v306"
            )
        )

        self.assertEqual(
            response.status_code,
            302,
        )

    def test_status_page_is_owner_only(self):
        other = get_user_model().objects.create_user(
            username="private-other",
            email="private-other@example.test",
            password="test-pass-123",
        )

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "accounts:email_verification_status_v306"
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            self.user.email,
        )
        self.assertNotContains(
            response,
            other.email,
        )

    def test_resend_route_sends_verification_email(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "accounts:email_verification_resend_v306"
            ),
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].to,
            [self.user.email],
        )
        self.assertIn(
            "/accounts/email-verification/confirm/",
            mail.outbox[0].body,
        )

    def test_zero_delivery_count_releases_resend_cooldown(self):
        self.client.force_login(self.user)

        url = reverse(
            "accounts:email_verification_resend_v306"
        )

        with patch(
            (
                "accounts.email_verification_views_v306."
                "send_mail"
            ),
            return_value=0,
        ):
            response = self.client.post(
                url,
                follow=True,
            )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "could not be sent",
        )

        state = self._state()

        self.assertIsNone(
            state.last_requested_at
        )
        self.assertEqual(
            state.token_version,
            1,
        )

        retry = prepare_email_verification_request_v306(
            self.user
        )

        self.assertEqual(
            retry.status,
            "sent",
        )
        self.assertEqual(
            retry.token_version,
            2,
        )

    def test_delivery_failure_releases_resend_cooldown(self):
        self.client.force_login(self.user)

        url = reverse(
            "accounts:email_verification_resend_v306"
        )

        with patch(
            (
                "accounts.email_verification_views_v306."
                "send_mail"
            ),
            side_effect=RuntimeError(
                "backend unavailable"
            ),
        ):
            response = self.client.post(
                url,
                follow=True,
            )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "could not be sent",
        )

        state = self._state()

        self.assertIsNone(
            state.last_requested_at
        )
        self.assertEqual(
            state.token_version,
            1,
        )

        retry = prepare_email_verification_request_v306(
            self.user
        )

        self.assertEqual(
            retry.status,
            "sent",
        )
        self.assertEqual(
            retry.token_version,
            2,
        )

    def test_resend_route_honors_cooldown(self):
        self.client.force_login(self.user)

        url = reverse(
            "accounts:email_verification_resend_v306"
        )

        self.client.post(url)

        response = self.client.post(
            url,
            follow=True,
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertContains(
            response,
            "Please try again later.",
        )

    def test_confirm_route_marks_email_verified(self):
        token = self._request_token()

        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "accounts:email_verification_confirm_v306",
                kwargs={"token": token},
            ),
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "Your current email address is now verified.",
        )
        self.assertTrue(
            self._state().is_verified_for_current_email
        )

    def test_invalid_confirmation_message_is_generic(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "accounts:email_verification_confirm_v306",
                kwargs={"token": "invalid-token"},
            ),
            follow=True,
        )

        self.assertEqual(
            response.status_code,
            200,
        )
        self.assertContains(
            response,
            "invalid or has expired",
        )
        self.assertNotContains(
            response,
            "invalid-token",
        )

    def test_policy_discovers_v306_state_and_two_blockers(self):
        capabilities = (
            discover_notification_delivery_policy_capabilities_v304()
        )

        self.assertTrue(
            capabilities["verified_recipient_state"]
        )
        self.assertEqual(
            capabilities["verified_recipient_model"],
            V306_VERIFIED_RECIPIENT_STATE_MODEL,
        )
        self.assertEqual(
            capabilities["verified_recipient_fields"],
            sorted(
                V306_VERIFIED_RECIPIENT_REQUIRED_FIELDS
            ),
        )

        result = get_notification_delivery_policy_baseline_v304()

        self.assertEqual(
            result["blocking_not_ready_count"],
            2,
        )
        self.assertFalse(
            result["runtime_enforcement_ready"]
        )
        self.assertFalse(
            result["runtime_enforcement_enabled"]
        )
