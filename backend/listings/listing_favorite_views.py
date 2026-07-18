"""
Dedicated favorite listing views extracted from listings.views in v155.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import Listing, ListingFavorite
from .listing_action_redirects_r001 import (
    get_safe_listing_action_redirect_r001,
)


LISTING_FAVORITE_VIEWS_V155 = True


@login_required
@require_POST
def listing_favorite_toggle(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        status=Listing.Status.APPROVED,
    )

    if listing.owner == request.user:
        messages.warning(request, "You cannot save your own listing.")
        return redirect(
            get_safe_listing_action_redirect_r001(
                request,
                listing.get_absolute_url(),
            )
        )

    favorite, created = ListingFavorite.objects.get_or_create(
        user=request.user,
        listing=listing,
    )

    if created:
        messages.success(request, "Listing saved.")
    else:
        favorite.delete()
        messages.success(request, "Listing removed from saved listings.")

    return redirect(
        get_safe_listing_action_redirect_r001(
            request,
            listing.get_absolute_url(),
        )
    )
