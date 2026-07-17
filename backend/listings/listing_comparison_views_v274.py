"""
LISTING_COMPARISON_V274

Public GET comparison page and CSRF-protected POST selection controls.
"""

from __future__ import annotations

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.http import (
    url_has_allowed_host_and_scheme,
)
from django.views.decorators.http import (
    require_GET,
    require_POST,
)

from .listing_comparison_v274 import (
    build_listing_comparison_context_v274,
    clear_comparison_listings_v274,
    toggle_comparison_listing_v274,
)
from .models import Listing


LISTING_COMPARISON_V274 = True


def _safe_comparison_next_url_v274(
    request,
) -> str:
    candidate = str(
        request.POST.get(
            "next",
            "",
        )
        or ""
    ).strip()

    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={
            request.get_host(),
        },
        require_https=request.is_secure(),
    ):
        return candidate

    return reverse(
        "listings:listing_compare"
    )


def _public_comparison_queryset_v274():
    return (
        Listing.objects
        .select_related(
            "category",
            "owner",
            "owner__profile",
            "owner__seller_store",
        )
        .filter(
            status=Listing.Status.APPROVED,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=timezone.now())
        )
    )


@require_GET
def listing_comparison_view_v274(
    request,
):
    context = (
        build_listing_comparison_context_v274(
            request
        )
    )

    return render(
        request,
        (
            "listings/"
            "listing_comparison_v274.html"
        ),
        context,
    )


@require_POST
def listing_comparison_toggle_v274(
    request,
    pk,
):
    listing = get_object_or_404(
        _public_comparison_queryset_v274(),
        pk=pk,
    )

    result = (
        toggle_comparison_listing_v274(
            request,
            listing,
        )
    )

    action = result[
        "action"
    ]

    if action == "added":
        messages.success(
            request,
            (
                "Listing added to comparison. "
                f"{result['count']} of 4 slots used."
            ),
        )
    elif action == "removed":
        messages.info(
            request,
            "Listing removed from comparison.",
        )
    elif action == "full":
        messages.error(
            request,
            (
                "You can compare up to four listings. "
                "Remove one before adding another."
            ),
        )
    else:
        messages.error(
            request,
            (
                "This listing is no longer available "
                "for comparison."
            ),
        )

    return redirect(
        _safe_comparison_next_url_v274(
            request
        )
    )


@require_POST
def listing_comparison_clear_v274(
    request,
):
    removed_count = (
        clear_comparison_listings_v274(
            request
        )
    )

    if removed_count:
        messages.info(
            request,
            "Comparison selection cleared.",
        )

    return redirect(
        _safe_comparison_next_url_v274(
            request
        )
    )
