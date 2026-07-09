"""
Dedicated listing CRUD/upload views extracted from listings.views in v161.
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
from .listing_uncategorized_views import (
    SidebarCategoriesMixin,
    ListingListView,
    listing_approve,
    listing_reject,
    listing_archive,
    listing_renew,
    listing_feature_toggle,
)  # V159 re-export
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


LISTING_CRUD_UPLOADS_VIEWS_V161 = True
LISTING_CRUD_UPLOADS_VIEW_EXPORTS_V161 = [
    "ListingCreateView",
    "ListingUpdateView",
    "ListingDeleteView",
    "listing_image_delete",
    "listing_feature_days_update"
]

LISTING_CRUD_UPLOADS_DEFINITION_OCCURRENCES_V161 = [
    {
        "name": "ListingCreateView",
        "kind": "class",
        "start_line": 52,
        "end_line": 84,
        "line_count": 33
    },
    {
        "name": "ListingUpdateView",
        "kind": "class",
        "start_line": 87,
        "end_line": 126,
        "line_count": 40
    },
    {
        "name": "ListingDeleteView",
        "kind": "class",
        "start_line": 129,
        "end_line": 143,
        "line_count": 15
    },
    {
        "name": "listing_image_delete",
        "kind": "function",
        "start_line": 148,
        "end_line": 161,
        "line_count": 14
    },
    {
        "name": "listing_feature_days_update",
        "kind": "function",
        "start_line": 241,
        "end_line": 261,
        "line_count": 21
    },
    {
        "name": "ListingCreateView",
        "kind": "class",
        "start_line": 1152,
        "end_line": 1162,
        "line_count": 11
    },
    {
        "name": "ListingUpdateView",
        "kind": "class",
        "start_line": 1166,
        "end_line": 1176,
        "line_count": 11
    }
]
LISTING_CRUD_UPLOADS_TARGET_NAME_COUNTS_V161 = {
    "ListingCreateView": 2,
    "ListingUpdateView": 2,
    "ListingDeleteView": 1,
    "listing_image_delete": 1,
    "listing_feature_days_update": 1
}
LISTING_CRUD_UPLOADS_AUDIT_LINES_V161 = 145
LISTING_CRUD_UPLOADS_SPAN_LINES_WITH_DECORATORS_V161 = 149
LISTING_CRUD_UPLOADS_INTERNAL_DEPENDENCIES_V161 = ["_ReportOriginalListingCreateView", "_ReportOriginalListingUpdateView"]


class ListingCreateView(LoginRequiredMixin, SidebarCategoriesMixin, CreateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/listing_form.html"
    success_url = reverse_lazy("accounts:my_listings")

    def form_valid(self, form):
        uploaded_files = self.request.FILES.getlist("images")
        image_errors = validate_uploaded_images(uploaded_files)

        if image_errors:
            for error in image_errors:
                form.add_error(None, error)
            return self.form_invalid(form)

        form.instance.owner = self.request.user
        form.instance.status = Listing.Status.PENDING
        form.instance.expires_at = default_listing_expiry()
        SellerStore.objects.get_or_create(owner=self.request.user)

        response = super().form_valid(form)

        saved_count = save_uploaded_listing_images(self.object, uploaded_files)

        if saved_count:
            messages.success(self.request, f"{saved_count} image(s) uploaded.")

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Create Listing"
        return context

class ListingUpdateView(LoginRequiredMixin, UserPassesTestMixin, SidebarCategoriesMixin, UpdateView):
    model = Listing
    form_class = ListingForm
    template_name = "listings/listing_form.html"
    success_url = reverse_lazy("accounts:my_listings")

    def get_queryset(self):
        return (
            Listing.objects
            .select_related("category", "owner")
            .prefetch_related("images")
        )

    def test_func(self):
        return self.get_object().owner == self.request.user

    def form_valid(self, form):
        uploaded_files = self.request.FILES.getlist("images")
        image_errors = validate_uploaded_images(uploaded_files)

        if image_errors:
            for error in image_errors:
                form.add_error(None, error)
            return self.form_invalid(form)

        form.instance.status = Listing.Status.PENDING

        response = super().form_valid(form)

        saved_count = save_uploaded_listing_images(self.object, uploaded_files)

        if saved_count:
            messages.success(self.request, f"{saved_count} image(s) uploaded.")

        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Edit Listing"
        return context

# V161 internal aliases preserved before duplicate/shadowed active CRUD classes.
_ReportOriginalListingCreateView = ListingCreateView
_ReportOriginalListingUpdateView = ListingUpdateView

class ListingDeleteView(LoginRequiredMixin, UserPassesTestMixin, SidebarCategoriesMixin, DeleteView):
    model = Listing
    template_name = "listings/listing_confirm_delete.html"
    success_url = reverse_lazy("accounts:my_listings")

    def get_queryset(self):
        return Listing.objects.select_related("category", "owner")

    def test_func(self):
        return self.get_object().owner == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = "Delete Listing"
        return context

@login_required
@require_POST
def listing_image_delete(request, pk):
    image = get_object_or_404(
        ListingImage.objects.select_related("listing", "listing__owner"),
        pk=pk,
    )

    if image.listing.owner != request.user:
        return redirect("accounts:my_listings")

    listing_pk = image.listing.pk
    image.image.delete(save=False)
    image.delete()

    return redirect("listings:listing_update", pk=listing_pk)

@login_required
@require_POST
def listing_feature_days_update(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if not request.user.is_staff:
        messages.warning(request, "Only staff can change featured expiry.")
        return redirect(listing.get_absolute_url())

    try:
        days = int(request.POST.get("featured_days", 30))
    except ValueError:
        days = 30

    if days < 1:
        days = 1

    listing.is_featured = True
    listing.featured_until = timezone.now() + timedelta(days=days)
    listing.save(update_fields=["is_featured", "featured_until"])

    messages.success(request, f"Featured expiry set for {days} day(s).")
    return redirect(request.POST.get("next") or listing.get_absolute_url())

class ListingCreateView(_ReportOriginalListingCreateView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile and profile.is_seller_suspended:
                messages.warning(
                    request,
                    "Your seller account is temporarily suspended. You cannot post listings right now.",
                )
                return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)

class ListingUpdateView(_ReportOriginalListingUpdateView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if profile and profile.is_seller_suspended:
                messages.warning(
                    request,
                    "Your seller account is temporarily suspended. You cannot edit listings right now.",
                )
                return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)
