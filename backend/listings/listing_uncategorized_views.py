"""
Dedicated uncategorized listing views extracted from listings.views in v159.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from accounts.models import SellerStore
from categories.models import Category
from .forms import ListingForm
from .models import Listing, ListingFavorite, ListingImage
from .listing_promotion_views import listing_feature_priority_update  # V152 re-export
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from .listing_filter_helpers import apply_listing_filters  # LISTING_FILTER_HELPER_EXTRACTION_V142
from .listing_moderation_helpers import _create_moderation_notice  # LISTING_MODERATION_HELPER_EXTRACTION_V143
from .listing_lifecycle_helpers import default_listing_expiry  # DEFAULT_LISTING_EXPIRY_HELPER_EXTRACTION_V145
from .listing_visibility_helpers import active_approved_listings  # ACTIVE_APPROVED_LISTINGS_HELPER_EXTRACTION_V146
from .listing_image_helpers import save_uploaded_listing_images  # SAVE_UPLOADED_LISTING_IMAGES_HELPER_EXTRACTION_V147
from .listing_image_helpers import validate_uploaded_images  # VALIDATE_UPLOADED_IMAGES_HELPER_EXTRACTION_V148
from .listing_favorite_views import listing_favorite_toggle  # V155 re-export
from .listing_browse_detail_views import ListingDetailView  # V157 re-export


LISTING_UNCATEGORIZED_VIEWS_V159 = True
UNCATEGORIZED_VIEW_EXPORTS_V159 = [
    "SidebarCategoriesMixin",
    "ListingListView",
    "listing_approve",
    "listing_reject",
    "listing_archive",
    "listing_renew",
    "listing_feature_toggle"
]

UNCATEGORIZED_AUDIT_LINES_V159 = 100
UNCATEGORIZED_AST_BODY_LINES_V159 = 94
UNCATEGORIZED_SPAN_LINES_WITH_DECORATORS_V159 = 104
UNCATEGORIZED_DUPLICATE_TARGETS_REMOVED_V159 = {
    "ListingListView": [
        {
            "start": 66,
            "body_start": 66,
            "end": 84
        },
        {
            "start": 1595,
            "body_start": 1595,
            "end": 1617
        }
    ]
}
UNCATEGORIZED_INTERNAL_DEPENDENCIES_V159 = ["_BaseAttributeListingListView"]


class SidebarCategoriesMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["root_categories"] = Category.objects.filter(parent__isnull=True).order_by("name")
        context["all_categories"] = Category.objects.all().order_by("name")
        context["search_q"] = self.request.GET.get("q", "")
        context["search_location"] = self.request.GET.get("location", "")
        context["search_min_price"] = self.request.GET.get("min_price", "")
        context["search_max_price"] = self.request.GET.get("max_price", "")
        context["search_category"] = self.request.GET.get("category", "")
        context["search_sort"] = self.request.GET.get("sort", "newest")
        return context

class ListingListView(SidebarCategoriesMixin, ListView):
    model = Listing
    template_name = "listings/listing_list.html"
    context_object_name = "listings"
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Listing.objects
            .select_related("category", "owner")
            .prefetch_related("images")
            .filter(status=Listing.Status.APPROVED).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        )
        return apply_listing_filters(queryset, self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Latest Listings"
        return context

_BaseAttributeListingListView = ListingListView

class ListingListView(_BaseAttributeListingListView):
    def get_queryset(self):
        from .attribute_filters import apply_attribute_filters

        queryset = super().get_queryset()
        category_slug = self.request.GET.get("category", "").strip()
        return apply_attribute_filters(queryset, self.request, category_slug)

    def get_context_data(self, **kwargs):
        from .attribute_filters import get_attribute_filter_context, get_page_querystring

        context = super().get_context_data(**kwargs)
        category_slug = (
            context.get("search_category")
            or self.request.GET.get("category", "").strip()
        )
        context.update(get_attribute_filter_context(self.request, category_slug))
        context["page_querystring"] = get_page_querystring(self.request)

        from .saved_searches import get_saved_search_context
        context.update(get_saved_search_context(self.request))

        return context

@staff_member_required
@require_POST
def listing_approve(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    listing.status = Listing.Status.APPROVED
    listing.save(update_fields=["status"])
    return redirect("listings:moderation_queue")

@staff_member_required
@require_POST
def listing_reject(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    listing.status = Listing.Status.REJECTED
    listing.save(update_fields=["status"])
    return redirect("listings:moderation_queue")

@login_required
@require_POST
def listing_archive(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if listing.owner != request.user and not request.user.is_staff:
        messages.warning(request, "You cannot archive this listing.")
        return redirect("accounts:my_listings")

    listing.status = Listing.Status.ARCHIVED
    listing.save(update_fields=["status"])

    messages.success(request, "Listing archived.")
    return redirect("accounts:my_listings")

@login_required
@require_POST
def listing_renew(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if listing.owner != request.user and not request.user.is_staff:
        messages.warning(request, "You cannot renew this listing.")
        return redirect("accounts:my_listings")

    listing.status = Listing.Status.PENDING
    listing.expires_at = default_listing_expiry()
    listing.save(update_fields=["status", "expires_at"])

    messages.success(request, "Listing renewed and sent for approval.")
    return redirect("accounts:my_listings")

@login_required
@require_POST
def listing_feature_toggle(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if not request.user.is_staff:
        messages.warning(request, "Only staff can change featured status.")
        return redirect(listing.get_absolute_url())

    listing.is_featured = not listing.is_featured

    if listing.is_featured and not listing.featured_until:
        listing.featured_until = timezone.now() + timedelta(days=30)

    if not listing.is_featured:
        listing.featured_until = None
        listing.featured_priority = 0

    listing.save(update_fields=["is_featured", "featured_until", "featured_priority"])

    if listing.is_featured:
        messages.success(request, "Listing marked as featured.")
    else:
        messages.success(request, "Listing removed from featured listings.")

    return redirect(request.POST.get("next") or listing.get_absolute_url())
