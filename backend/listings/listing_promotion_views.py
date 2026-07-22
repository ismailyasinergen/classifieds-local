"""Promotion-related listing views extracted from listings.views in v152."""

from __future__ import annotations

LISTING_PROMOTION_VIEWS_V152 = True

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .listing_action_redirects_r001 import (
    get_safe_listing_action_redirect_r001,
)
from .models import Listing, ListingFavorite, ListingImage

@login_required
@require_POST
def listing_feature_priority_update(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if not request.user.is_staff:
        messages.warning(request, "Only staff can change featured priority.")
        return redirect(listing.get_absolute_url())

    try:
        priority = int(request.POST.get("featured_priority", 0))
    except ValueError:
        priority = 0

    if priority < 0:
        priority = 0

    listing.featured_priority = priority
    listing.save(update_fields=["featured_priority"])

    messages.success(request, "Featured priority updated.")
    return redirect(get_safe_listing_action_redirect_r001(request, listing.get_absolute_url()))
