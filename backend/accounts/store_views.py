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


SELLER_STORE_SORT_OPTIONS_V111 = (
    ("newest", "Newest first"),
    ("oldest", "Oldest first"),
    ("price_asc", "Price: low to high"),
    ("price_desc", "Price: high to low"),
)

SELLER_STORE_SORT_ORDERINGS_V111 = {
    "newest": ("-top_listing_priority", "-created_at", "-id"),
    "oldest": ("created_at", "id"),
    "price_asc": ("price", "-created_at", "-id"),
    "price_desc": ("-price", "-created_at", "-id"),
}

SELLER_STORE_PINNED_LIMIT_V112 = 3


def _seller_store_pinned_listing_filter(now):
    active_top_listing = (
        Q(top_listing_priority__gt=0)
        & (Q(top_listing_until__isnull=True) | Q(top_listing_until__gt=now))
    )
    active_featured_listing = (
        (Q(is_featured=True) | Q(featured_priority__gt=0))
        & (Q(featured_until__isnull=True) | Q(featured_until__gt=now))
    )
    return active_top_listing | active_featured_listing


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
    requested_sort = request.GET.get("sort", "newest").strip()
    selected_sort = (
        requested_sort
        if requested_sort in SELLER_STORE_SORT_ORDERINGS_V111
        else "newest"
    )
    sort_options = [
        {
            "value": value,
            "label": label,
            "is_selected": selected_sort == value,
        }
        for value, label in SELLER_STORE_SORT_OPTIONS_V111
    ]

    category_counts = {
        row["category_id"]: row["listing_count"]
        for row in (
            base_listings_queryset
            .order_by()
            .values("category_id")
            .annotate(listing_count=Count("id"))
        )
    }

    category_options = list(
        Category.objects
        .filter(id__in=category_counts.keys())
        .order_by("name")
        .distinct()
    )

    for category in category_options:
        category.store_listing_count = category_counts.get(category.id, 0)

    def build_store_tab_url(category_slug=None):
        tab_query_params = request.GET.copy()
        tab_query_params.pop("page", None)

        if selected_sort == "newest":
            tab_query_params.pop("sort", None)
        else:
            tab_query_params["sort"] = selected_sort

        if category_slug:
            tab_query_params["category"] = category_slug
        else:
            tab_query_params.pop("category", None)

        tab_query = tab_query_params.urlencode()
        tab_suffix = f"?{tab_query}" if tab_query else ""
        return f"{request.path}{tab_suffix}#store-listings-v109"

    all_listings_tab = {
        "label": "All listings",
        "count": listing_count,
        "url": build_store_tab_url(),
        "is_active": not selected_category_slug,
    }

    category_tabs = [
        {
            "label": category.name,
            "slug": category.slug,
            "count": category.store_listing_count,
            "url": build_store_tab_url(category.slug),
            "is_active": selected_category_slug == category.slug,
        }
        for category in category_options
    ]

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

    filtered_listings_queryset = listings_queryset
    filtered_listing_count = filtered_listings_queryset.count()
    now = timezone.now()

    pinned_store_listings = list(
        filtered_listings_queryset
        .filter(_seller_store_pinned_listing_filter(now))
        .order_by(
            "-top_listing_priority",
            "-featured_priority",
            "-created_at",
            "-id",
        )[:SELLER_STORE_PINNED_LIMIT_V112]
    )
    pinned_listing_ids = [listing.pk for listing in pinned_store_listings]

    listings_queryset = (
        filtered_listings_queryset
        .exclude(pk__in=pinned_listing_ids)
        .order_by(*SELLER_STORE_SORT_ORDERINGS_V111[selected_sort])
    )

    query_params = request.GET.copy()
    query_params.pop("page", None)
    if selected_sort == "newest":
        query_params.pop("sort", None)
    else:
        query_params["sort"] = selected_sort
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
            "all_listings_tab": all_listings_tab,
            "category_tabs": category_tabs,
            "pinned_store_listings": pinned_store_listings,
            "q": q,
            "selected_category_slug": selected_category_slug,
            "selected_sort": selected_sort,
            "sort_options": sort_options,
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

