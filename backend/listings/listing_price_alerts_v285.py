"""Listing-specific price-alert subscriptions and delivery for v285."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urljoin

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.db.models import Exists, F, OuterRef, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from .listing_action_redirects_r001 import (
    get_safe_listing_action_redirect_r001,
)
from .listing_price_drop_filter_v278 import (
    PRICE_DROP_GUARDRAIL_ANNOTATION_V293,
    PRICE_DROP_PREVIOUS_ANNOTATION_V278,
    PRICE_DROP_TRANSITION_ANNOTATION_V278,
    annotate_current_price_transition_v278,
)
from .models import Listing, ListingPriceAlert
from .notification_delivery_runtime_enforcement_v309 import (
    notification_delivery_recipient_decision_v309,
)


LISTING_SPECIFIC_PRICE_ALERTS_V285 = True
LISTING_PRICE_ALERT_BATCH_LIMIT_V285 = 100


@dataclass(frozen=True)
class ListingPriceAlertPreviewV285:
    match_count: int
    alerts: list[ListingPriceAlert]


def _active_public_listing_filter_v285(now):
    return (
        Q(status=Listing.Status.APPROVED)
        & (Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    )


def get_listing_price_alert_context_v285(request, listing) -> dict:
    """Return private subscription state only for an eligible signed-in buyer."""

    now = timezone.now()
    available = bool(
        request.user.is_authenticated
        and request.user != listing.owner
        and listing.status == Listing.Status.APPROVED
        and (listing.expires_at is None or listing.expires_at > now)
        and listing.price > Decimal("0.00")
    )
    active = False
    if available:
        active = ListingPriceAlert.objects.filter(
            user=request.user,
            listing=listing,
        ).exists()

    return {
        "listing_price_alert_available_v285": available,
        "listing_price_alert_active_v285": active,
    }


@login_required
@require_POST
def listing_price_alert_toggle_v285(request, pk):
    now = timezone.now()
    listing = get_object_or_404(
        Listing.objects.filter(_active_public_listing_filter_v285(now)),
        pk=pk,
        price__gt=Decimal("0.00"),
    )

    if listing.owner_id == request.user.pk:
        return HttpResponseForbidden("You cannot create an alert for your own listing.")

    alert, created = ListingPriceAlert.objects.get_or_create(
        user=request.user,
        listing=listing,
        defaults={"baseline_price": listing.price},
    )
    if created:
        messages.success(request, "Price alert enabled.")
    else:
        alert.delete()
        messages.success(request, "Price alert disabled.")

    return redirect(
        get_safe_listing_action_redirect_r001(
            request,
            listing.get_absolute_url(),
        )
    )


def get_listing_price_alert_candidates_v285(now=None):
    """Return alerts whose listing has a promotable valid current reduction."""

    now = now or timezone.now()
    eligible_listing = annotate_current_price_transition_v278(
        Listing.objects.filter(
            pk=OuterRef("listing_id"),
        ).filter(_active_public_listing_filter_v285(now))
    ).filter(
        price__lt=OuterRef("baseline_price"),
        **{
            PRICE_DROP_PREVIOUS_ANNOTATION_V278 + "__gt": F(
                PRICE_DROP_TRANSITION_ANNOTATION_V278
            ),
            PRICE_DROP_TRANSITION_ANNOTATION_V278: F("price"),
            PRICE_DROP_GUARDRAIL_ANNOTATION_V293: "",
        },
    ).filter(
        **{
            PRICE_DROP_PREVIOUS_ANNOTATION_V278 + "__gt": Decimal("0.00"),
        }
    )

    return (
        ListingPriceAlert.objects
        .select_related("user", "listing")
        .filter(Exists(eligible_listing))
        .filter(
            Q(last_notified_price__isnull=True)
            | ~Q(last_notified_price=F("listing__price"))
        )
        .order_by("pk")
    )


def build_listing_price_alert_preview_v285(limit=LISTING_PRICE_ALERT_BATCH_LIMIT_V285, now=None):
    queryset = get_listing_price_alert_candidates_v285(now=now)
    return ListingPriceAlertPreviewV285(
        match_count=queryset.count(),
        alerts=list(queryset[:limit]),
    )


def _listing_alert_url_v285(listing, site_base_url=""):
    path = listing.get_absolute_url()
    if not site_base_url:
        return path
    return urljoin(site_base_url.rstrip("/") + "/", path.lstrip("/"))


def build_listing_price_alert_email_v285(alert, *, site_base_url=""):
    recipient_decision = (
        notification_delivery_recipient_decision_v309(
            alert.user
        )
    )
    recipient = recipient_decision.recipient_email
    if not recipient:
        raise ValueError(
            "Price-alert user has no eligible recipient address."
        )

    listing = alert.listing
    subject = f"Price drop: {listing.title}"
    body = "\n".join(
        [
            "Hi,",
            "",
            f"The price of {listing.title} has dropped.",
            f"Price when you subscribed: {alert.baseline_price} TL",
            f"Current price: {listing.price} TL",
            f"View listing: {_listing_alert_url_v285(listing, site_base_url)}",
            "",
            "You can turn off this alert from the listing page.",
        ]
    )
    return EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )


def send_listing_price_alert_v285(alert, *, site_base_url="") -> int:
    recipient_decision = (
        notification_delivery_recipient_decision_v309(
            alert.user
        )
    )
    if not recipient_decision.allowed:
        return 0
    return build_listing_price_alert_email_v285(
        alert,
        site_base_url=site_base_url,
    ).send(fail_silently=False)


def mark_listing_price_alert_sent_v285(alert, sent_at=None):
    alert.last_notified_price = alert.listing.price
    alert.last_notification_sent_at = sent_at or timezone.now()
    alert.save(
        update_fields=[
            "last_notified_price",
            "last_notification_sent_at",
            "updated_at",
        ]
    )
    return alert
