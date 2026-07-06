from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from categories.models import Category
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


def seller_store_directory(request):
    now = timezone.now()
    q = request.GET.get("q", "").strip()

    active_listing_filter = (
        Q(owner__listings__status=Listing.Status.APPROVED)
        & (
            Q(owner__listings__expires_at__isnull=True)
            | Q(owner__listings__expires_at__gt=now)
        )
    )

    stores_queryset = (
        SellerStore.objects
        .select_related("owner", "owner__profile")
        .filter(is_active=True)
        .annotate(
            active_listing_count=Count(
                "owner__listings",
                filter=active_listing_filter,
                distinct=True,
            )
        )
        .filter(active_listing_count__gt=0)
    )

    if q:
        stores_queryset = stores_queryset.filter(
            Q(name__icontains=q)
            | Q(headline__icontains=q)
            | Q(description__icontains=q)
            | Q(location__icontains=q)
            | Q(owner__username__icontains=q)
            | Q(owner__email__icontains=q)
        )

    stores_queryset = stores_queryset.order_by(
        "-active_listing_count",
        "name",
        "owner__username",
        "id",
    )

    query_params = request.GET.copy()
    query_params.pop("page", None)
    pagination_query = query_params.urlencode()
    page_url_prefix = f"?{pagination_query}&" if pagination_query else "?"

    paginator = Paginator(stores_queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/seller_store_directory.html",
        {
            "stores": page_obj.object_list,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "q": q,
            "page_url_prefix": page_url_prefix,
            "store_count": stores_queryset.count(),
            "page_title": "Seller Stores",
        },
    )


@login_required
def seller_store_settings(request):
    store = _get_or_create_store_for_user(request.user)

    if request.method == "POST":
        form = SellerStoreForm(request.POST, request.FILES, instance=store)
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

    base_listings_queryset = _active_public_listings_for_user(store.owner)
    listing_count = base_listings_queryset.count()
    contact_listing = base_listings_queryset.first()
    owner_profile = getattr(store.owner, "profile", None)
    is_seller_messaging_blocked = bool(
        owner_profile and owner_profile.is_seller_messaging_blocked
    )
    can_message_seller = (
        request.user.is_authenticated
        and request.user != store.owner
        and contact_listing is not None
        and not is_seller_messaging_blocked
    )
    can_report_seller = (
        request.user.is_authenticated
        and request.user != store.owner
    )

    q = request.GET.get("q", "").strip()
    selected_category_slug = request.GET.get("category", "").strip()

    category_options = (
        Category.objects
        .filter(id__in=base_listings_queryset.values("category_id"))
        .order_by("name")
        .distinct()
    )

    listings_queryset = base_listings_queryset

    if q:
        listings_queryset = listings_queryset.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(location__icontains=q)
            | Q(category__name__icontains=q)
        )

    if selected_category_slug:
        listings_queryset = listings_queryset.filter(category__slug=selected_category_slug)

    filtered_listing_count = listings_queryset.count()

    query_params = request.GET.copy()
    query_params.pop("page", None)
    pagination_query = query_params.urlencode()
    page_url_prefix = f"?{pagination_query}&" if pagination_query else "?"

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
            "listing_count": listing_count,
            "filtered_listing_count": filtered_listing_count,
            "category_options": category_options,
            "q": q,
            "selected_category_slug": selected_category_slug,
            "page_url_prefix": page_url_prefix,
            "can_preview": can_preview,
            "owner_profile": owner_profile,
            "contact_listing": contact_listing,
            "can_message_seller": can_message_seller,
            "can_report_seller": can_report_seller,
            "is_seller_messaging_blocked": is_seller_messaging_blocked,
            "page_title": store.display_name,
        },
    )

