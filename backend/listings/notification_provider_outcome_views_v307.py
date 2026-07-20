"""Authenticated provider-outcome webhook for v307."""

from __future__ import annotations

from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from listings.notification_provider_outcomes_v307 import (
    NotificationProviderOutcomeAuthenticationErrorV307,
    NotificationProviderOutcomeConflictV307,
    NotificationProviderOutcomePayloadErrorV307,
    NotificationProviderOutcomeUnavailableV307,
    authenticate_and_parse_notification_provider_outcome_v307,
    ingest_notification_provider_outcome_v307,
)


@csrf_exempt
@never_cache
@require_POST
def notification_provider_outcome_webhook_v307(
    request,
):
    try:
        payload = (
            authenticate_and_parse_notification_provider_outcome_v307(
                body=request.body,
                timestamp=request.headers.get(
                    "X-Notification-Provider-Timestamp",
                    "",
                ),
                signature=request.headers.get(
                    "X-Notification-Provider-Signature",
                    "",
                ),
            )
        )

        result = (
            ingest_notification_provider_outcome_v307(
                payload
            )
        )
    except NotificationProviderOutcomeUnavailableV307:
        return JsonResponse(
            {
                "status": "unavailable",
            },
            status=503,
        )
    except NotificationProviderOutcomeAuthenticationErrorV307:
        return JsonResponse(
            {
                "status": "unauthorized",
            },
            status=401,
        )
    except NotificationProviderOutcomePayloadErrorV307:
        return JsonResponse(
            {
                "status": "invalid",
            },
            status=400,
        )
    except NotificationProviderOutcomeConflictV307:
        return JsonResponse(
            {
                "status": "conflict",
            },
            status=409,
        )

    response_status = (
        200
        if result.matched_event_count
        or result.duplicate
        else 202
    )

    return JsonResponse(
        {
            "status": "accepted",
            "duplicate": result.duplicate,
            "matched_event_count": (
                result.matched_event_count
            ),
            "applied_event_count": (
                result.applied_event_count
            ),
        },
        status=response_status,
    )
