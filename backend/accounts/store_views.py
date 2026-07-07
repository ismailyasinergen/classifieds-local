from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from categories.models import Category
from listings.models import Listing

from .forms import SellerStoreForm
from .models import SellerStore, UserProfile


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

SELLER_STORE_DIRECTORY_DEFAULT_SORT_V114 = "most_listings"

SELLER_STORE_DIRECTORY_SORT_OPTIONS_V114 = (
    ("most_listings", "Most listings"),
    ("name_az", "Store name A-Z"),
    ("newest", "Newest stores"),
    ("verified_first", "Verified sellers first"),
)

SELLER_STORE_DIRECTORY_SORT_ORDERINGS_V114 = {
    "most_listings": (
        "-active_listing_count",
        "name",
        "owner__username",
        "id",
    ),
    "name_az": (
        "name",
        "owner__username",
        "id",
    ),
    "newest": (
        "-created_at",
        "-id",
    ),
    "verified_first": (
        "-verified_seller_rank",
        "-active_listing_count",
        "name",
        "owner__username",
        "id",
    ),
}

SELLER_STORE_DIRECTORY_FEATURED_VERIFIED_LIMIT_V116 = 3
SELLER_STORE_DIRECTORY_CATEGORY_LIMIT_V117 = 8
SELLER_STORE_DIRECTORY_LOCATION_LIMIT_V118 = 8
SELLER_STORE_DIRECTORY_EMPTY_SUGGESTION_LIMIT_V120 = 4


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


def _parse_directory_min_listings_v113(value):
    try:
        parsed_value = int(str(value).strip())
    except (TypeError, ValueError):
        return None

    if parsed_value < 1:
        return None

    return parsed_value


def _directory_url_from_query_v115(path, query_params):
    query_string = query_params.urlencode()
    if query_string:
        return f"{path}?{query_string}"
    return path


def _directory_clear_url_v115(path, query_params, field_name):
    updated_params = query_params.copy()
    updated_params.pop(field_name, None)
    return _directory_url_from_query_v115(path, updated_params)


def seller_store_directory(request):
    now = timezone.now()
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    selected_category_slug = request.GET.get("category", "").strip()
    selected_directory_category = None
    if selected_category_slug:
        selected_directory_category = Category.objects.filter(
            slug=selected_category_slug
        ).first()
        if selected_directory_category is None:
            selected_category_slug = ""

    verified_only = request.GET.get("verified_only") == "1"
    min_listings = _parse_directory_min_listings_v113(
        request.GET.get("min_listings", "")
    )
    selected_directory_sort = request.GET.get(
        "sort",
        SELLER_STORE_DIRECTORY_DEFAULT_SORT_V114,
    ).strip()
    if selected_directory_sort not in dict(SELLER_STORE_DIRECTORY_SORT_OPTIONS_V114):
        selected_directory_sort = SELLER_STORE_DIRECTORY_DEFAULT_SORT_V114

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
            ),
            verified_seller_rank=Case(
                When(
                    owner__profile__verification_status=(
                        UserProfile.VerificationStatus.APPROVED
                    ),
                    then=Value(1),
                ),
                default=Value(0),
                output_field=IntegerField(),
            ),
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

    if location:
        stores_queryset = stores_queryset.filter(
            Q(location__icontains=location)
            | Q(owner__profile__location__icontains=location)
        )

    if selected_directory_category is not None:
        stores_queryset = stores_queryset.filter(
            Q(
                owner__listings__category_id__in=(
                    selected_directory_category.get_descendant_ids()
                )
            )
            & Q(owner__listings__status=Listing.Status.APPROVED)
            & (
                Q(owner__listings__expires_at__isnull=True)
                | Q(owner__listings__expires_at__gt=now)
            )
        ).distinct()

    if verified_only:
        stores_queryset = stores_queryset.filter(
            owner__profile__verification_status=(
                UserProfile.VerificationStatus.APPROVED
            )
        )

    if min_listings is not None:
        stores_queryset = stores_queryset.filter(
            active_listing_count__gte=min_listings
        )

    stores_queryset = stores_queryset.order_by(
        *SELLER_STORE_DIRECTORY_SORT_ORDERINGS_V114[selected_directory_sort]
    )

    has_advanced_directory_filters = bool(
        location
        or selected_directory_category is not None
        or verified_only
        or min_listings is not None
    )
    has_directory_filters = bool(q or has_advanced_directory_filters)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    if q:
        query_params["q"] = q
    else:
        query_params.pop("q", None)

    if location:
        query_params["location"] = location
    else:
        query_params.pop("location", None)

    if selected_directory_category is not None:
        query_params["category"] = selected_directory_category.slug
    else:
        query_params.pop("category", None)

    if verified_only:
        query_params["verified_only"] = "1"
    else:
        query_params.pop("verified_only", None)

    if min_listings is not None:
        query_params["min_listings"] = str(min_listings)
    else:
        query_params.pop("min_listings", None)

    if selected_directory_sort != SELLER_STORE_DIRECTORY_DEFAULT_SORT_V114:
        query_params["sort"] = selected_directory_sort
    else:
        query_params.pop("sort", None)

    directory_sort_labels = dict(SELLER_STORE_DIRECTORY_SORT_OPTIONS_V114)
    selected_directory_sort_label = directory_sort_labels[selected_directory_sort]

    directory_active_chips = []
    if q:
        directory_active_chips.append(
            {
                "label": "Search",
                "value": q,
                "clear_url": _directory_clear_url_v115(
                    request.path,
                    query_params,
                    "q",
                ),
            }
        )

    if location:
        directory_active_chips.append(
            {
                "label": "Location",
                "value": location,
                "clear_url": _directory_clear_url_v115(
                    request.path,
                    query_params,
                    "location",
                ),
            }
        )

    if selected_directory_category is not None:
        directory_active_chips.append(
            {
                "label": "Category",
                "value": selected_directory_category.name,
                "clear_url": _directory_clear_url_v115(
                    request.path,
                    query_params,
                    "category",
                ),
            }
        )

    if min_listings is not None:
        directory_active_chips.append(
            {
                "label": "Minimum listings",
                "value": f"{min_listings}+ active listings",
                "clear_url": _directory_clear_url_v115(
                    request.path,
                    query_params,
                    "min_listings",
                ),
            }
        )

    if verified_only:
        directory_active_chips.append(
            {
                "label": "Trust",
                "value": "Verified only",
                "clear_url": _directory_clear_url_v115(
                    request.path,
                    query_params,
                    "verified_only",
                ),
            }
        )

    if selected_directory_sort != SELLER_STORE_DIRECTORY_DEFAULT_SORT_V114:
        directory_active_chips.append(
            {
                "label": "Sort",
                "value": selected_directory_sort_label,
                "clear_url": _directory_clear_url_v115(
                    request.path,
                    query_params,
                    "sort",
                ),
            }
        )

    active_category_listing_filter = (
        Q(listings__status=Listing.Status.APPROVED)
        & (
            Q(listings__expires_at__isnull=True)
            | Q(listings__expires_at__gt=now)
        )
        & Q(listings__owner__seller_store__is_active=True)
    )
    popular_directory_categories = list(
        Category.objects
        .annotate(
            directory_store_count=Count(
                "listings__owner__seller_store",
                filter=active_category_listing_filter,
                distinct=True,
            )
        )
        .filter(directory_store_count__gt=0)
        .order_by("-directory_store_count", "name", "id")[
            :SELLER_STORE_DIRECTORY_CATEGORY_LIMIT_V117
        ]
    )

    for category in popular_directory_categories:
        category_query_params = query_params.copy()
        category_query_params["category"] = category.slug
        category.directory_url = _directory_url_from_query_v115(
            request.path,
            category_query_params,
        )

    directory_category_clear_url = _directory_clear_url_v115(
        request.path,
        query_params,
        "category",
    )

    location_counts = {}
    location_queryset = (
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
        .order_by("location", "owner__profile__location", "id")
    )

    for store in location_queryset:
        owner_profile = getattr(store.owner, "profile", None)
        profile_location = getattr(owner_profile, "location", "")
        display_location = (store.location or profile_location or "").strip()

        if not display_location:
            continue

        normalized_location = display_location.casefold()
        if normalized_location not in location_counts:
            location_counts[normalized_location] = {
                "label": display_location,
                "store_count": 0,
            }
        location_counts[normalized_location]["store_count"] += 1

    popular_directory_locations = sorted(
        location_counts.values(),
        key=lambda location_item: (
            -location_item["store_count"],
            location_item["label"].casefold(),
        ),
    )[:SELLER_STORE_DIRECTORY_LOCATION_LIMIT_V118]

    for location_item in popular_directory_locations:
        location_query_params = query_params.copy()
        location_query_params["location"] = location_item["label"]
        location_item["directory_url"] = _directory_url_from_query_v115(
            request.path,
            location_query_params,
        )
        location_item["is_selected"] = (
            bool(location)
            and location.casefold() == location_item["label"].casefold()
        )

    directory_location_clear_url = _directory_clear_url_v115(
        request.path,
        query_params,
        "location",
    )

    empty_suggestion_base_params = query_params.copy()
    for empty_suggestion_field in (
        "q",
        "location",
        "category",
        "min_listings",
        "verified_only",
        "page",
    ):
        empty_suggestion_base_params.pop(empty_suggestion_field, None)

    if selected_directory_sort != SELLER_STORE_DIRECTORY_DEFAULT_SORT_V114:
        empty_suggestion_base_params["sort"] = selected_directory_sort
    else:
        empty_suggestion_base_params.pop("sort", None)

    directory_empty_category_suggestions = []
    for category in popular_directory_categories[
        :SELLER_STORE_DIRECTORY_EMPTY_SUGGESTION_LIMIT_V120
    ]:
        category_suggestion_params = empty_suggestion_base_params.copy()
        category_suggestion_params["category"] = category.slug
        directory_empty_category_suggestions.append(
            {
                "label": category.name,
                "store_count": category.directory_store_count,
                "url": _directory_url_from_query_v115(
                    request.path,
                    category_suggestion_params,
                ),
            }
        )

    directory_empty_location_suggestions = []
    for location_item in popular_directory_locations[
        :SELLER_STORE_DIRECTORY_EMPTY_SUGGESTION_LIMIT_V120
    ]:
        location_suggestion_params = empty_suggestion_base_params.copy()
        location_suggestion_params["location"] = location_item["label"]
        directory_empty_location_suggestions.append(
            {
                "label": location_item["label"],
                "store_count": location_item["store_count"],
                "url": _directory_url_from_query_v115(
                    request.path,
                    location_suggestion_params,
                ),
            }
        )

    featured_verified_stores = []
    if not directory_active_chips:
        featured_verified_stores = list(
            stores_queryset
            .filter(
                owner__profile__verification_status=(
                    UserProfile.VerificationStatus.APPROVED
                )
            )
            .order_by(
                "-active_listing_count",
                "-created_at",
                "name",
                "owner__username",
                "id",
            )[:SELLER_STORE_DIRECTORY_FEATURED_VERIFIED_LIMIT_V116]
        )

    pagination_query = query_params.urlencode()
    page_url_prefix = f"?{pagination_query}&" if pagination_query else "?"

    # SELLER_STORE_SAVED_SEARCH_CREATE_INTEGRATION_V122
    from listings.saved_searches import (
        canonical_saved_search_querystring,
        clean_saved_search_querydict,
        querydict_to_plain_params,
    )

    directory_saved_search_querydict = clean_saved_search_querydict(query_params)
    directory_saved_search_querystring = canonical_saved_search_querystring(
        directory_saved_search_querydict
    )
    directory_saved_search_params = querydict_to_plain_params(
        directory_saved_search_querydict
    )
    directory_saved_search_path = request.path
    directory_saved_search_url = _directory_url_from_query_v115(
        request.path,
        directory_saved_search_querydict,
    )
    directory_saved_search_active = (
        bool(directory_active_chips) and bool(directory_saved_search_querystring)
    )
    directory_current_saved_search = None

    if directory_saved_search_active and request.user.is_authenticated:
        from listings.models import SavedSearch

        directory_current_saved_search = (
            SavedSearch.objects
            .filter(user=request.user, path=directory_saved_search_path)
            .filter(
                Q(querystring=directory_saved_search_querystring)
                | Q(query_params=directory_saved_search_params)
            )
            .first()
        )

    paginator = Paginator(stores_queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    # SELLER_STORE_SAVED_SEARCH_RESULT_COUNT_PREVIEW_V126
    if "page_obj" in locals() and getattr(page_obj, "paginator", None) is not None:
        directory_saved_search_result_count = page_obj.paginator.count
    elif "paginator" in locals():
        directory_saved_search_result_count = paginator.count
    elif "stores" in locals():
        directory_saved_search_result_count = stores.count() if hasattr(stores, "count") else len(stores)
    elif "seller_stores" in locals():
        directory_saved_search_result_count = seller_stores.count() if hasattr(seller_stores, "count") else len(seller_stores)
    elif "store_queryset" in locals():
        directory_saved_search_result_count = store_queryset.count() if hasattr(store_queryset, "count") else len(store_queryset)
    else:
        directory_saved_search_result_count = 0

    return render(
        request,
        "accounts/seller_store_directory.html",
        {
            "directory_saved_search_result_count": directory_saved_search_result_count,
            "stores": page_obj.object_list,
            "page_obj": page_obj,
            "is_paginated": page_obj.has_other_pages(),
            "q": q,
            "location": location,
            "verified_only": verified_only,
            "min_listings": str(min_listings or ""),
            "has_directory_filters": has_directory_filters,
            "has_advanced_directory_filters": has_advanced_directory_filters,
            "selected_directory_sort": selected_directory_sort,
            "selected_directory_sort_label": selected_directory_sort_label,
            "directory_sort_options": SELLER_STORE_DIRECTORY_SORT_OPTIONS_V114,
            "directory_active_chips": directory_active_chips,
            "directory_clear_all_url": request.path,
            "featured_verified_stores": featured_verified_stores,
            "featured_verified_limit": (
                SELLER_STORE_DIRECTORY_FEATURED_VERIFIED_LIMIT_V116
            ),
            "popular_directory_categories": popular_directory_categories,
            "directory_category_limit": SELLER_STORE_DIRECTORY_CATEGORY_LIMIT_V117,
            "selected_directory_category": selected_directory_category,
            "directory_category_clear_url": directory_category_clear_url,
            "popular_directory_locations": popular_directory_locations,
            "directory_location_limit": SELLER_STORE_DIRECTORY_LOCATION_LIMIT_V118,
            "directory_location_clear_url": directory_location_clear_url,
            "directory_empty_category_suggestions": (
                directory_empty_category_suggestions
            ),
            "directory_empty_location_suggestions": (
                directory_empty_location_suggestions
            ),
            "directory_empty_suggestion_limit": (
                SELLER_STORE_DIRECTORY_EMPTY_SUGGESTION_LIMIT_V120
            ),
            "directory_saved_search_active": directory_saved_search_active,
            "directory_saved_search_url": directory_saved_search_url,
            "directory_saved_search_querystring": (
                directory_saved_search_querystring
            ),
            "directory_saved_search_path": directory_saved_search_path,
            "directory_current_saved_search": directory_current_saved_search,
            "directory_saved_search_filter_count": len(directory_active_chips),
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

