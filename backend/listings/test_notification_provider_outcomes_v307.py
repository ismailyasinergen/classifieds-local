from __future__ import annotations

from datetime import timedelta
import json

from django.contrib.auth import get_user_model
from django.core.mail.backends.locmem import (
    EmailBackend as LocmemEmailBackend,
)
from django.test import (
    Client,
    TestCase,
    override_settings,
)
from django.urls import reverse
from django.utils import timezone

from categories.models import Category
from listings.models import (
    Listing,
    NotificationDeliveryEvent,
    NotificationProviderOutcomeReceipt,
    SavedSearch,
)
from listings.notification_delivery_policy_v304 import (
    discover_notification_delivery_policy_capabilities_v304,
    get_notification_delivery_policy_baseline_v304,
)
from listings.notification_provider_outcomes_v307 import (
    build_notification_provider_signature_v307,
    record_notification_provider_message_identity_v307,
)
from listings.saved_search_notification_email_sender import (
    send_saved_search_notification_email,
)


class ProviderIdentityEmailBackendV307(
    LocmemEmailBackend
):
    def send_messages(
        self,
        email_messages,
    ):
        for index, message in enumerate(
            email_messages,
            start=1,
        ):
            message.provider_message_id = (
                f"provider-message-{index}"
            )

        return super().send_messages(
            email_messages
        )


PROVIDER_BACKEND_V307 = (
    "listings.test_notification_provider_outcomes_v307."
    "ProviderIdentityEmailBackendV307"
)


@override_settings(
    NOTIFICATION_PROVIDER_NAME="test-provider",
    NOTIFICATION_PROVIDER_WEBHOOK_SECRET="webhook-secret",
    NOTIFICATION_PROVIDER_WEBHOOK_MAX_AGE_SECONDS=300,
)
class NotificationProviderOutcomesV307Tests(
    TestCase
):
    def setUp(self):
        User = get_user_model()

        self.buyer = User.objects.create_user(
            username="v307-buyer",
            email="v307-buyer@example.test",
            password="test-pass-123",
        )

        self.seller = User.objects.create_user(
            username="v307-seller",
            email="v307-seller@example.test",
            password="test-pass-123",
        )

        self.category = Category.objects.create(
            name="V307",
            slug="v307",
        )

        self.listing = Listing.objects.create(
            title="V307 provider outcome listing",
            description="Provider outcome fixture.",
            price="100.00",
            category=self.category,
            owner=self.seller,
            location="Berlin",
            status=Listing.Status.APPROVED,
            expires_at=(
                timezone.now()
                + timedelta(days=30)
            ),
        )

        self.saved_search = SavedSearch.objects.create(
            user=self.buyer,
            name="V307 provider search",
            path="/listings/",
            query_params={
                "q": "V307",
            },
            querystring="q=V307",
            email_notifications_enabled=True,
            last_notification_checked_at=(
                timezone.now()
                - timedelta(days=1)
            ),
        )

        self.event = NotificationDeliveryEvent.objects.create(
            recipient=self.buyer,
            listing=self.listing,
            saved_search=self.saved_search,
            notification_type=(
                NotificationDeliveryEvent
                .NotificationType
                .SAVED_SEARCH_NEW_LISTING
            ),
            event_key="a" * 64,
            status=(
                NotificationDeliveryEvent
                .Status
                .SENT
            ),
            sent_at=timezone.now(),
            provider_name="test-provider",
            provider_message_id="provider-message-1",
        )

        self.url = reverse(
            "listings:"
            "notification_provider_outcome_webhook_v307"
        )

        self.client = Client(
            enforce_csrf_checks=True
        )

    def _payload(
        self,
        *,
        event_id="provider-event-1",
        message_id="provider-message-1",
        outcome="delivered",
        occurred_at=None,
    ):
        return {
            "provider": "test-provider",
            "event_id": event_id,
            "message_id": message_id,
            "outcome": outcome,
            "occurred_at": (
                occurred_at
                or timezone.now()
            ).isoformat(),
        }

    def _signed_request(
        self,
        payload,
        *,
        timestamp=None,
        signature=None,
    ):
        body = json.dumps(
            payload,
            sort_keys=True,
            separators=(
                ",",
                ":",
            ),
        ).encode("utf-8")

        timestamp_value = str(
            timestamp
            if timestamp is not None
            else int(
                timezone.now().timestamp()
            )
        )

        supplied_signature = (
            signature
            if signature is not None
            else build_notification_provider_signature_v307(
                timestamp=timestamp_value,
                body=body,
                secret="webhook-secret",
            )
        )

        return self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_NOTIFICATION_PROVIDER_TIMESTAMP=(
                timestamp_value
            ),
            HTTP_X_NOTIFICATION_PROVIDER_SIGNATURE=(
                supplied_signature
            ),
        )

    @override_settings(
        EMAIL_BACKEND=PROVIDER_BACKEND_V307,
        DEFAULT_FROM_EMAIL="alerts@example.test",
    )
    def test_sender_persists_provider_message_identity(
        self,
    ):
        NotificationDeliveryEvent.objects.all().delete()

        result = send_saved_search_notification_email(
            self.saved_search,
            match_count=1,
            matching_listings=[
                self.listing,
            ],
            execute_send=True,
            require_test_email_backend=False,
        )

        event = NotificationDeliveryEvent.objects.get()

        self.assertEqual(
            result["delivered_count"],
            1,
        )
        self.assertEqual(
            result["provider_name"],
            "test-provider",
        )
        self.assertEqual(
            result["provider_message_id"],
            "provider-message-1",
        )
        self.assertEqual(
            result[
                "provider_identity_recorded_count"
            ],
            1,
        )
        self.assertEqual(
            event.provider_name,
            "test-provider",
        )
        self.assertEqual(
            event.provider_message_id,
            "provider-message-1",
        )
        self.assertEqual(
            event.status,
            NotificationDeliveryEvent.Status.SENT,
        )

    @override_settings(
        NOTIFICATION_PROVIDER_NAME="",
        NOTIFICATION_PROVIDER_WEBHOOK_SECRET="",
    )
    def test_webhook_fails_closed_when_unconfigured(
        self,
    ):
        response = self._signed_request(
            self._payload()
        )

        self.assertEqual(
            response.status_code,
            503,
        )
        self.assertFalse(
            NotificationProviderOutcomeReceipt
            .objects
            .exists()
        )

    def test_invalid_signature_is_rejected(
        self,
    ):
        response = self._signed_request(
            self._payload(),
            signature="sha256=invalid",
        )

        self.assertEqual(
            response.status_code,
            401,
        )
        self.assertFalse(
            NotificationProviderOutcomeReceipt
            .objects
            .exists()
        )

    def test_stale_signature_is_rejected(
        self,
    ):
        stale = int(
            (
                timezone.now()
                - timedelta(minutes=10)
            ).timestamp()
        )

        response = self._signed_request(
            self._payload(),
            timestamp=stale,
        )

        self.assertEqual(
            response.status_code,
            401,
        )

    def test_malformed_payload_is_rejected(
        self,
    ):
        body = b"not-json"
        timestamp = str(
            int(
                timezone.now().timestamp()
            )
        )
        signature = (
            build_notification_provider_signature_v307(
                timestamp=timestamp,
                body=body,
                secret="webhook-secret",
            )
        )

        response = self.client.post(
            self.url,
            data=body,
            content_type="application/json",
            HTTP_X_NOTIFICATION_PROVIDER_TIMESTAMP=timestamp,
            HTTP_X_NOTIFICATION_PROVIDER_SIGNATURE=signature,
        )

        self.assertEqual(
            response.status_code,
            400,
        )

    def test_signed_delivery_outcome_updates_matching_event(
        self,
    ):
        response = self._signed_request(
            self._payload()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.event.refresh_from_db()

        self.assertEqual(
            self.event.provider_outcome,
            NotificationDeliveryEvent
            .ProviderOutcome
            .DELIVERED,
        )
        self.assertEqual(
            self.event.provider_event_id,
            "provider-event-1",
        )
        self.assertIsNotNone(
            self.event.provider_outcome_at
        )
        self.assertEqual(
            self.event.status,
            NotificationDeliveryEvent.Status.SENT,
        )
        self.assertNotIn(
            self.buyer.email,
            response.content.decode("utf-8"),
        )

    def test_exact_replay_is_idempotent(
        self,
    ):
        payload = self._payload()

        first = self._signed_request(
            payload
        )
        second = self._signed_request(
            payload
        )

        self.assertEqual(
            first.status_code,
            200,
        )
        self.assertEqual(
            second.status_code,
            200,
        )
        self.assertTrue(
            second.json()["duplicate"]
        )
        self.assertEqual(
            NotificationProviderOutcomeReceipt
            .objects
            .count(),
            1,
        )

    def test_event_id_semantic_conflict_is_rejected(
        self,
    ):
        first = self._signed_request(
            self._payload(
                outcome="delivered"
            )
        )
        conflict = self._signed_request(
            self._payload(
                outcome="bounced"
            )
        )

        self.assertEqual(
            first.status_code,
            200,
        )
        self.assertEqual(
            conflict.status_code,
            409,
        )
        self.assertEqual(
            NotificationProviderOutcomeReceipt
            .objects
            .count(),
            1,
        )

    def test_late_bounce_upgrades_delivery_and_cannot_downgrade(
        self,
    ):
        base = timezone.now()

        delivered = self._payload(
            event_id="provider-event-delivered",
            outcome="delivered",
            occurred_at=(
                base
                - timedelta(minutes=2)
            ),
        )

        bounced = self._payload(
            event_id="provider-event-bounced",
            outcome="bounced",
            occurred_at=(
                base
                - timedelta(minutes=1)
            ),
        )

        later_delivery = self._payload(
            event_id="provider-event-delivered-late",
            outcome="delivered",
            occurred_at=base,
        )

        self._signed_request(delivered)
        self._signed_request(bounced)
        self._signed_request(later_delivery)

        self.event.refresh_from_db()

        self.assertEqual(
            self.event.provider_outcome,
            NotificationDeliveryEvent
            .ProviderOutcome
            .BOUNCED,
        )
        self.assertEqual(
            self.event.provider_event_id,
            "provider-event-bounced",
        )

    def test_complaint_is_not_downgraded_by_bounce(
        self,
    ):
        base = timezone.now()

        self._signed_request(
            self._payload(
                event_id="provider-event-complaint",
                outcome="complained",
                occurred_at=(
                    base
                    - timedelta(minutes=1)
                ),
            )
        )

        self._signed_request(
            self._payload(
                event_id="provider-event-bounce-later",
                outcome="bounced",
                occurred_at=base,
            )
        )

        self.event.refresh_from_db()

        self.assertEqual(
            self.event.provider_outcome,
            NotificationDeliveryEvent
            .ProviderOutcome
            .COMPLAINED,
        )

    def test_unmatched_outcome_is_accepted_for_later_reconciliation(
        self,
    ):
        response = self._signed_request(
            self._payload(
                event_id="provider-event-unmatched",
                message_id="unknown-message",
            )
        )

        self.assertEqual(
            response.status_code,
            202,
        )
        self.assertEqual(
            response.json()[
                "matched_event_count"
            ],
            0,
        )

        receipt = (
            NotificationProviderOutcomeReceipt
            .objects
            .get()
        )

        self.assertEqual(
            receipt.matched_event_count,
            0,
        )

    def test_unmatched_receipt_reconciles_when_identity_arrives(
        self,
    ):
        self.event.provider_name = ""
        self.event.provider_message_id = ""

        self.event.save(
            update_fields=[
                "provider_name",
                "provider_message_id",
                "updated_at",
            ]
        )

        response = self._signed_request(
            self._payload(
                event_id="provider-event-late",
                message_id="late-message",
                outcome="bounced",
            )
        )

        self.assertEqual(
            response.status_code,
            202,
        )

        recorded = (
            record_notification_provider_message_identity_v307(
                event_keys=[
                    self.event.event_key,
                ],
                provider_name="test-provider",
                provider_message_id="late-message",
            )
        )

        self.assertEqual(
            recorded,
            1,
        )

        self.event.refresh_from_db()

        receipt = (
            NotificationProviderOutcomeReceipt
            .objects
            .get(
                provider_event_id="provider-event-late"
            )
        )

        self.assertEqual(
            self.event.provider_name,
            "test-provider",
        )
        self.assertEqual(
            self.event.provider_message_id,
            "late-message",
        )
        self.assertEqual(
            self.event.provider_outcome,
            NotificationDeliveryEvent
            .ProviderOutcome
            .BOUNCED,
        )
        self.assertEqual(
            self.event.provider_event_id,
            "provider-event-late",
        )
        self.assertEqual(
            receipt.matched_event_count,
            1,
        )

    def test_webhook_is_post_only_and_csrf_independent(
        self,
    ):
        response = self.client.get(
            self.url
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        signed = self._signed_request(
            self._payload()
        )

        self.assertEqual(
            signed.status_code,
            200,
        )

    def test_policy_discovers_provider_outcome_contract(
        self,
    ):
        capabilities = (
            discover_notification_delivery_policy_capabilities_v304()
        )

        self.assertTrue(
            capabilities[
                "provider_message_id_state"
            ]
        )
        self.assertTrue(
            capabilities[
                "provider_outcome_state"
            ]
        )

        policy = (
            get_notification_delivery_policy_baseline_v304()
        )

        provider_check = next(
            check
            for check in policy["checks"]
            if check["check_id"]
            == "provider_delivery_outcomes"
        )

        self.assertTrue(
            provider_check["ready"]
        )
        self.assertEqual(
            provider_check["reason_code"],
            "provider_outcome_contract_available",
        )
        self.assertEqual(
            policy["blocking_not_ready_count"],
            1,
        )
        self.assertFalse(
            policy["runtime_enforcement_ready"]
        )
