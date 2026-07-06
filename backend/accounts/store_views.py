from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from listings.models import Listing

from .forms import SellerStoreForm
from .models import SellerStore


def _get_or_create_store_for_user(user):
    store, created = SellerStore.objects.get_or_create(owner=user)

    profile = getattr(user, "profile", None)
    update_fields = []

    if created and profile:
        if profile.business_name and not store.name:
            store.name = profile.business_name
            update_fields.append("name")
        if profile.location and not store.location:
            store.location = profile.location
            update_fields.append("location")

    if update_fields:
        store.save(update_fields=update_fields + ["updated_at"])

    return store


def _active_public_listings_for_user(user):
    return (
        Listing.objects
        .select_related("category", "owner")
        .prefetch_related("images")
        .filter(owner=user, status=Listing.Status.APPROVED)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        .order_by("-top_listing_priority", "-created_at")
    )


@login_required
def seller_store_settings(request):
    store = _get_or_create_store_for_user(request.user)

    if request.method == "POST":
        form = SellerStoreForm(request.POST, instance=store)
        if form.is_valid():
            form.save()
            messages.success(request, "Store settings saved.")
            return redirect("accounts:seller_store_settings")
    else:
        form = SellerStoreForm(instance=store)

    return render(
        request,
        "accounts/seller_store_settings.html",
        {
            "form": form,
            "store": store,
            "page_title": "Store Settings",
        },
    )


def seller_store_public(request, slug):
    store = get_object_or_404(
        SellerStore.objects.select_related("owner", "owner__profile"),
        slug=slug,
    )

    can_preview = (
        request.user.is_authenticated
        and (request.user.is_staff or request.user == store.owner)
    )

    if not store.is_active and not can_preview:
        raise Http404("Store not found.")

    listings_queryset = _active_public_listings_for_user(store.owner)
    paginator = Paginator(listings_queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/seller_store_public.html",
        {
            "store": store,
            "listings": page_obj.object_list,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "listing_count": listings_queryset.count(),
            "can_preview": can_preview,
            "page_title": store.display_name,
        },
    )
