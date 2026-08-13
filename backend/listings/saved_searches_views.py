from __future__ import annotations

from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qsl, urlencode, urlparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.models import SellerStore
from categories.models import Category

from .listing_filter_helpers import apply_listing_filters
from .models import Listing, ListingFavorite, ListingImage, ListingReport, SavedSearch


# V166 extracted from listings.views.


@login_required
@require_POST
def saved_search_create(request):
    # SELLER_STORE_DIRECTORY_SAVED_SEARCH_UX_POLISH_V125
    from .saved_searches import create_saved_search_from_request

    saved_search_result = create_saved_search_from_request(
        request,
        request.POST.get("querystring", ""),
        name=request.POST.get("name", ""),
        path=request.POST.get("path", ""),
    )
    saved_search = (
        saved_search_result[0]
        if isinstance(saved_search_result, (tuple, list))
        else saved_search_result
    )

    if saved_search.is_seller_store_directory_search:
        messages.success(
            request,
            "Seller store search saved. You can reopen it from Saved Searches.",
        )
    else:
        messages.success(
            request,
            "Search saved. You can reopen it from Saved Searches.",
        )

    return redirect(saved_search.get_absolute_url())


@login_required
def saved_search_list(request):
    # SAVED_SEARCH_TYPE_FILTER_TABS_V127
    # SAVED_SEARCH_TAB_COUNT_POLISH_V128
    # SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136_CONTEXT
    request.renamed_saved_search_id_v136 = request.session.pop("saved_search_renamed_id_v136", None)

    # SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_CONTEXT
    request.saved_search_rename_error_id_v137 = request.session.pop("saved_search_rename_error_id_v137", None)
    request.saved_search_rename_error_message_v137 = request.session.pop(
        "saved_search_rename_error_message_v137",
        None,
    )

    from django.core.paginator import Paginator
    from django.db.models import Q
    from django.shortcuts import render
    from django.urls import reverse
    from .models import SavedSearch

    search_query = request.GET.get("q", "").strip()
    raw_type_filter = request.GET.get("type", "all").strip()

    type_aliases = {
        "all": "all",
        "listing": "listings",
        "listings": "listings",
        "seller-store": "seller-stores",
        "seller-stores": "seller-stores",
        "seller_store": "seller-stores",
        "seller_stores": "seller-stores",
    }
    saved_search_type_filter = type_aliases.get(raw_type_filter, "all")
    seller_store_directory_path = reverse("accounts:seller_store_directory")

    field_names = {field.name for field in SavedSearch._meta.get_fields()}
    order_fields = []
    if "updated_at" in field_names:
        order_fields.append("-updated_at")
    if "created_at" in field_names:
        order_fields.append("-created_at")
    order_fields.append("-id")

    all_saved_searches = SavedSearch.objects.filter(user=request.user).order_by(*order_fields)
    listing_saved_searches = all_saved_searches.exclude(path=seller_store_directory_path)
    seller_store_saved_searches = all_saved_searches.filter(path=seller_store_directory_path)

    # SAVED_SEARCH_TAB_COUNT_POLISH_V128_QUERY_AWARE_COUNTS
    def apply_saved_search_keyword_filter(queryset):
        if not search_query:
            return queryset

        search_filter = Q()
        if "name" in field_names:
            search_filter |= Q(name__icontains=search_query)
        if "querystring" in field_names:
            search_filter |= Q(querystring__icontains=search_query)
        if "path" in field_names:
            search_filter |= Q(path__icontains=search_query)

        if search_filter.children:
            return queryset.filter(search_filter)

        return queryset

    filtered_all_saved_searches = apply_saved_search_keyword_filter(all_saved_searches)
    filtered_listing_saved_searches = apply_saved_search_keyword_filter(listing_saved_searches)
    filtered_seller_store_saved_searches = apply_saved_search_keyword_filter(seller_store_saved_searches)

    all_saved_search_count = all_saved_searches.count()
    listing_saved_search_count = listing_saved_searches.count()
    seller_store_saved_search_count = seller_store_saved_searches.count()

    all_tab_count = filtered_all_saved_searches.count()
    listing_tab_count = filtered_listing_saved_searches.count()
    seller_store_tab_count = filtered_seller_store_saved_searches.count()

    if saved_search_type_filter == "listings":
        saved_searches = filtered_listing_saved_searches
    elif saved_search_type_filter == "seller-stores":
        saved_searches = filtered_seller_store_saved_searches
    else:
        saved_searches = filtered_all_saved_searches

    paginator = Paginator(saved_searches, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    def build_type_url(filter_value):
        params = request.GET.copy()
        params.pop("page", None)
        if filter_value == "all":
            params.pop("type", None)
        else:
            params["type"] = filter_value

        querystring = params.urlencode()
        return f"?{querystring}" if querystring else request.path

    saved_search_type_tabs = [
        {
            "key": "all",
            "label": "All",
            "count": all_tab_count,
            "total_count": all_saved_search_count,
            "url": build_type_url("all"),
            "active": saved_search_type_filter == "all",
        },
        {
            "key": "listings",
            "label": "Listing searches",
            "count": listing_tab_count,
            "total_count": listing_saved_search_count,
            "url": build_type_url("listings"),
            "active": saved_search_type_filter == "listings",
        },
        {
            "key": "seller-stores",
            "label": "Seller store searches",
            "count": seller_store_tab_count,
            "total_count": seller_store_saved_search_count,
            "url": build_type_url("seller-stores"),
            "active": saved_search_type_filter == "seller-stores",
        },
    ]

    active_type_label = ""
    if saved_search_type_filter == "listings":
        active_type_label = "Listing searches"
    elif saved_search_type_filter == "seller-stores":
        active_type_label = "Seller store searches"

    saved_search_active_filter_summary = []
    if search_query:
        saved_search_active_filter_summary.append(
            {
                "label": "Search",
                "value": search_query,
            }
        )
    if active_type_label:
        saved_search_active_filter_summary.append(
            {
                "label": "Type",
                "value": active_type_label,
            }
        )

    saved_search_tab_count_note = ""
    if search_query:
        saved_search_tab_count_note = (
            f'Tab counts are narrowed by “{search_query}”. '
            "Clear the search to see all saved-search totals."
        )

    has_results = page_obj.paginator.count > 0
    type_empty_title = ""
    type_empty_message = ""
    if not has_results and saved_search_type_filter == "listings":
        type_empty_title = "No listing searches saved yet"
        if search_query and listing_saved_search_count:
            type_empty_message = "No listing saved searches match this keyword. Try another search or clear the search."
        else:
            type_empty_message = "Save a filtered listing search to return to matching listings faster."
    elif not has_results and saved_search_type_filter == "seller-stores":
        type_empty_title = "No seller store searches saved yet"
        if search_query and seller_store_saved_search_count:
            type_empty_message = "No seller store saved searches match this keyword. Try another search or clear the search."
        else:
            type_empty_message = "Save a seller store directory search to revisit matching stores later."
    elif not has_results and search_query:
        type_empty_title = "No saved searches match"
        type_empty_message = "Try another keyword or switch saved-search type."

    # SAVED_SEARCH_TYPE_FILTER_TABS_V127_LEGACY_CONTEXT
    shown_count = len(page_obj.object_list)
    total_count = saved_searches.count()
    per_page = paginator.per_page

    if "email_notifications_enabled" in field_names:
        email_alert_count = (
            all_saved_searches
            .exclude(path=seller_store_directory_path)
            .filter(email_notifications_enabled=True)
            .count()
        )
    else:
        email_alert_count = 0

    preserved_query_params = request.GET.copy()
    preserved_query_params.pop("page", None)
    preserved_querystring = preserved_query_params.urlencode()
    page_url_prefix = f"{preserved_querystring}&" if preserved_querystring else ""

    # SAVED_SEARCH_TYPE_FILTER_TABS_V127_EXACT_TEMPLATE_CONTEXT
    saved_search_search_query = search_query
    saved_search_total_count = all_saved_search_count
    saved_search_filtered_count = saved_searches.count()
    saved_search_page_size = paginator.per_page
    saved_search_pagination_querystring = preserved_querystring
    saved_search_current_path = request.path
    current_querystring = request.GET.urlencode()
    if current_querystring:
        saved_search_current_path = f"{saved_search_current_path}?{current_querystring}"
    saved_search_email_alert_count = email_alert_count

    return render(
        request,
        "listings/saved_search_list.html",
        {
            "saved_searches": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "search_query": search_query,
            "saved_search_search_query": saved_search_search_query,
            "q": search_query,
            "query": search_query,
            "saved_search_type_filter": saved_search_type_filter,
            "saved_search_type_tabs": saved_search_type_tabs,
            "saved_search_active_filter_summary": saved_search_active_filter_summary,
            "saved_search_tab_count_note": saved_search_tab_count_note,
            "listing_saved_search_count": listing_saved_search_count,
            "saved_search_total_count": saved_search_total_count,
            "seller_store_saved_search_count": seller_store_saved_search_count,
            "all_saved_search_count": all_saved_search_count,
            "saved_search_filtered_count": saved_search_filtered_count,
            "shown_count": shown_count,
            "total_count": total_count,
            "saved_search_page_size": saved_search_page_size,
            "per_page": per_page,
            "saved_search_pagination_querystring": saved_search_pagination_querystring,
            "saved_search_type_has_results": has_results,
            "saved_search_type_empty_title": type_empty_title,
            "saved_search_type_empty_message": type_empty_message,
            "saved_search_preserved_querystring": preserved_querystring,
            "saved_search_current_path": saved_search_current_path,
            "saved_search_email_alert_count": saved_search_email_alert_count,
            "email_alert_count": email_alert_count,
            "page_url_prefix": page_url_prefix,
            "is_paginated": paginator.num_pages > 1,
            "has_saved_searches": all_saved_search_count > 0,
        },
    )


    def build_type_url(filter_value):
        params = request.GET.copy()
        params.pop("page", None)
        if filter_value == "all":
            params.pop("type", None)
        else:
            params["type"] = filter_value

        querystring = params.urlencode()
        return f"?{querystring}" if querystring else request.path

    saved_search_type_tabs = [
        {
            "key": "all",
            "label": "All",
            "count": all_saved_search_count,
            "url": build_type_url("all"),
            "active": saved_search_type_filter == "all",
        },
        {
            "key": "listings",
            "label": "Listing searches",
            "count": listing_saved_search_count,
            "url": build_type_url("listings"),
            "active": saved_search_type_filter == "listings",
        },
        {
            "key": "seller-stores",
            "label": "Seller store searches",
            "count": seller_store_saved_search_count,
            "url": build_type_url("seller-stores"),
            "active": saved_search_type_filter == "seller-stores",
        },
    ]

    has_results = page_obj.paginator.count > 0
    type_empty_title = ""
    type_empty_message = ""
    if not has_results and saved_search_type_filter == "listings":
        type_empty_title = "No listing searches saved yet"
        type_empty_message = "Save a filtered listing search to return to matching listings faster."
    elif not has_results and saved_search_type_filter == "seller-stores":
        type_empty_title = "No seller store searches saved yet"
        type_empty_message = "Save a seller store directory search to revisit matching stores later."
    elif not has_results and search_query:
        type_empty_title = "No saved searches match"
        type_empty_message = "Try another keyword or switch saved-search type."

    # SAVED_SEARCH_TYPE_FILTER_TABS_V127_LEGACY_CONTEXT
    shown_count = len(page_obj.object_list)
    total_count = saved_searches.count()
    per_page = paginator.per_page

    if "email_notifications_enabled" in field_names:
        email_alert_count = (
            all_saved_searches
            .exclude(path=seller_store_directory_path)
            .filter(email_notifications_enabled=True)
            .count()
        )
    else:
        email_alert_count = 0

    preserved_query_params = request.GET.copy()
    preserved_query_params.pop("page", None)
    preserved_querystring = preserved_query_params.urlencode()
    page_url_prefix = f"{preserved_querystring}&" if preserved_querystring else ""

    # SAVED_SEARCH_TYPE_FILTER_TABS_V127_EXACT_TEMPLATE_CONTEXT
    saved_search_search_query = search_query
    saved_search_total_count = all_saved_search_count
    saved_search_filtered_count = saved_searches.count()
    saved_search_page_size = paginator.per_page
    saved_search_pagination_querystring = preserved_querystring
    saved_search_current_path = request.path
    current_querystring = request.GET.urlencode()
    if current_querystring:
        saved_search_current_path = f"{saved_search_current_path}?{current_querystring}"
    saved_search_email_alert_count = email_alert_count

    return render(
        request,
        "listings/saved_search_list.html",
        {
            "saved_searches": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "search_query": search_query,
            "saved_search_search_query": saved_search_search_query,
            "q": search_query,
            "query": search_query,
            "saved_search_type_filter": saved_search_type_filter,
            "saved_search_total_count": saved_search_total_count,
            "saved_search_type_tabs": saved_search_type_tabs,
            "shown_count": shown_count,
            "total_count": total_count,
            "per_page": per_page,
            "email_alert_count": email_alert_count,
            "page_url_prefix": page_url_prefix,
            "is_paginated": paginator.num_pages > 1,
            "listing_saved_search_count": listing_saved_search_count,
            "saved_search_filtered_count": saved_search_filtered_count,
            "seller_store_saved_search_count": seller_store_saved_search_count,
            "saved_search_page_size": saved_search_page_size,
            "all_saved_search_count": all_saved_search_count,
            "saved_search_pagination_querystring": saved_search_pagination_querystring,
            "saved_search_type_has_results": has_results,
            "saved_search_type_empty_title": type_empty_title,
            "saved_search_type_empty_message": type_empty_message,
            "saved_search_preserved_querystring": preserved_querystring,
            "saved_search_current_path": saved_search_current_path,
            "saved_search_email_alert_count": saved_search_email_alert_count,
            "has_saved_searches": all_saved_search_count > 0,
        },
    )


@login_required
@require_POST
def saved_search_notifications_toggle(request, pk):
    # SELLER_STORE_SAVED_SEARCH_EMAIL_ALERT_GUARDRAILS_V124
    from django.urls import reverse
    from django.utils.http import url_has_allowed_host_and_scheme
    from .models import SavedSearch

    saved_search = get_object_or_404(SavedSearch, pk=pk, user=request.user)

    next_url = request.POST.get("next") or reverse("listings:saved_search_list")
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
    ):
        next_url = reverse("listings:saved_search_list")

    if saved_search.is_seller_store_directory_search:
        if saved_search.email_notifications_enabled:
            saved_search.email_notifications_enabled = False
            saved_search.save(update_fields=["email_notifications_enabled", "updated_at"])

        messages.info(
            request,
            "Email alerts are available for listing searches only.",
        )
        return redirect(next_url)

    enabled = request.POST.get("enabled") == "on"
    saved_search.email_notifications_enabled = enabled
    saved_search.save(update_fields=["email_notifications_enabled", "updated_at"])

    if enabled:
        messages.success(request, "Email alerts enabled for this saved search.")
    else:
        messages.info(request, "Email alerts disabled for this saved search.")

    return redirect(next_url)


@login_required
@require_POST
def saved_search_delete(request, pk):
    from .models import SavedSearch

    saved_search = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    saved_search.delete()
    messages.success(request, "Saved search removed.")
    return redirect("listings:saved_search_list")


@login_required
def saved_search_bulk_action(request):
    # SAVED_SEARCH_BULK_ACTIONS_V130
    from django.contrib import messages
    from django.http import HttpResponseNotAllowed
    from django.shortcuts import redirect
    from django.urls import reverse

    from .models import SavedSearch

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    saved_search_list_url = reverse("listings:saved_search_list")
    next_url = request.POST.get("next", "").strip()

    # SAVED_SEARCH_BULK_ACTIONS_V130_SAFE_NEXT
    if not (
        next_url == saved_search_list_url
        or next_url.startswith(f"{saved_search_list_url}?")
    ):
        next_url = saved_search_list_url

    action = request.POST.get("bulk_action", "").strip()
    selected_ids = request.POST.getlist("selected_saved_searches")

    if action != "delete":
        messages.error(request, "Choose a valid bulk action.")
        return redirect(next_url)

    if not selected_ids:
        messages.warning(request, "Select at least one saved search first.")
        return redirect(next_url)

    # SAVED_SEARCH_BULK_ACTIONS_V130_OWNER_SCOPED
    selected_searches = SavedSearch.objects.filter(
        user=request.user,
        pk__in=selected_ids,
    )
    deleted_count = selected_searches.count()
    selected_searches.delete()

    if deleted_count == 1:
        messages.success(request, "Deleted 1 saved search.")
    elif deleted_count > 1:
        messages.success(request, f"Deleted {deleted_count} saved searches.")
    else:
        messages.warning(request, "No matching saved searches were deleted.")

    return redirect(next_url)


@login_required
def saved_search_rename(request, pk):
    # SAVED_SEARCH_RENAME_EDIT_FLOW_V132
    from django.contrib import messages
    from django.http import HttpResponseNotAllowed
    from django.shortcuts import get_object_or_404, redirect
    from django.urls import reverse

    from .models import SavedSearch

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    saved_search_list_url = reverse("listings:saved_search_list")
    next_url = request.POST.get("next", "").strip()

    # SAVED_SEARCH_RENAME_EDIT_FLOW_V132_SAFE_NEXT
    if not (
        next_url == saved_search_list_url
        or next_url.startswith(f"{saved_search_list_url}?")
    ):
        next_url = saved_search_list_url

    # SAVED_SEARCH_RENAME_EDIT_FLOW_V132_OWNER_SCOPED
    saved_search = get_object_or_404(
        SavedSearch,
        user=request.user,
        pk=pk,
    )

    # SAVED_SEARCH_RENAME_EDIT_FLOW_V132_NAME_CLEAN
    new_name = " ".join(request.POST.get("name", "").split()).strip()
    if not new_name:
        # SAVED_SEARCH_RENAME_ERROR_FEEDBACK_V137_SESSION
        request.session["saved_search_rename_error_id_v137"] = saved_search.pk
        request.session["saved_search_rename_error_message_v137"] = "Type a new name before saving this saved search."
        messages.error(request, "Saved search name cannot be blank.")
        return redirect(next_url)

    max_length = SavedSearch._meta.get_field("name").max_length or 120
    if len(new_name) > max_length:
        new_name = new_name[:max_length].rstrip()

    saved_search.name = new_name
    saved_search.save(update_fields=["name"])
    # SAVED_SEARCH_RENAME_VISUAL_FEEDBACK_V136_SESSION
    request.session["saved_search_renamed_id_v136"] = saved_search.pk
    messages.success(request, "Saved search name updated.")
    return redirect(next_url)
