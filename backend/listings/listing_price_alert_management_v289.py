"""Authenticated listing-specific price-alert management for v289."""

from __future__ import annotations

from dataclasses import dataclass

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Listing, ListingPriceAlert, NotificationDeliveryPreference


PRICE_ALERT_MANAGEMENT_UI_V289 = True
PRICE_ALERT_MANAGEMENT_PAGE_SIZE_V289 = 20


@dataclass(frozen=True)
class PriceAlertManagementEntryV289:
    alert: ListingPriceAlert
    listing_is_public: bool

    @property
    def delivery_status(self):
        if not self.listing_is_public:
            return "Paused while listing is unavailable"
        return "Watching for a lower price"


@dataclass(frozen=True)
class PriceAlertManagementPageV289:
    page_obj: object
    entries: tuple[PriceAlertManagementEntryV289, ...]
    listing_price_alert_email_enabled: bool


def _listing_is_public_v289(listing, *, now):
    return bool(
        listing.status == Listing.Status.APPROVED
        and (listing.expires_at is None or listing.expires_at > now)
    )


def get_listing_price_alert_management_queryset_v289(user):
    return (
        ListingPriceAlert.objects
        .filter(user=user)
        .select_related("listing", "listing__category")
        .order_by("-created_at", "-pk")
    )


def build_price_alert_management_page_v289(user, *, page_number=None, now=None):
    reference_time = now or timezone.now()
    paginator = Paginator(
        get_listing_price_alert_management_queryset_v289(user),
        PRICE_ALERT_MANAGEMENT_PAGE_SIZE_V289,
    )
    page_obj = paginator.get_page(page_number)
    entries = tuple(
        PriceAlertManagementEntryV289(
            alert=alert,
            listing_is_public=_listing_is_public_v289(
                alert.listing,
                now=reference_time,
            ),
        )
        for alert in page_obj.object_list
    )
    preference_value = (
        NotificationDeliveryPreference.objects
        .filter(user=user)
        .values_list("listing_price_alert_email_enabled", flat=True)
        .first()
    )
    return PriceAlertManagementPageV289(
        page_obj=page_obj,
        entries=entries,
        listing_price_alert_email_enabled=(
            True if preference_value is None else bool(preference_value)
        ),
    )


@login_required
def listing_price_alert_management_v289(request):
    management_page = build_price_alert_management_page_v289(
        request.user,
        page_number=request.GET.get("page"),
    )
    return render(
        request,
        "listings/listing_price_alert_management_v289.html",
        {
            "page_title": "Price alerts",
            "page_obj": management_page.page_obj,
            "price_alert_entries_v289": management_page.entries,
            "listing_price_alert_email_enabled_v289": (
                management_page.listing_price_alert_email_enabled
            ),
        },
    )


@login_required
@require_POST
def listing_price_alert_remove_v289(request, pk):
    alert = get_object_or_404(
        ListingPriceAlert.objects.filter(user=request.user),
        pk=pk,
    )
    alert.delete()
    messages.success(request, "Price alert removed.")
    return redirect("listings:listing_price_alert_management_v289")
