"""
Dedicated browse/detail listing views extracted from listings.views in v157.
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
from .listing_recommendations import (
    RELATED_LISTINGS_DEFAULT_LIMIT_V271,
    get_related_listings_v271,
)

from .listing_recently_viewed import (
    RECENTLY_VIEWED_DISPLAY_LIMIT_V272,
    get_recently_viewed_listings_v272,
    record_recently_viewed_listing_v272,
)
from .listing_public_price_history_v283 import (
    PublicPriceHistoryContextMixinV283,
)
from .listing_price_alerts_v285 import (
    get_listing_price_alert_context_v285,
)


LISTING_BROWSE_DETAIL_VIEWS_V157 = True


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




# RECENTLY_VIEWED_LISTINGS_V272
class RecentlyViewedListingsContextMixinV272:
    recently_viewed_limit_v272 = (
        RECENTLY_VIEWED_DISPLAY_LIMIT_V272
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )

        listing = getattr(
            self,
            "object",
            None,
        )

        context["recently_viewed_listings"] = (
            get_recently_viewed_listings_v272(
                self.request,
                current_listing=listing,
                limit=(
                    self.recently_viewed_limit_v272
                ),
            )
        )

        record_recently_viewed_listing_v272(
            self.request,
            listing,
        )

        return context


# RELATED_LISTINGS_RECOMMENDATIONS_V271
class RelatedListingsContextMixinV271:
    related_listings_limit_v271 = (
        RELATED_LISTINGS_DEFAULT_LIMIT_V271
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(
            **kwargs
        )
        context["related_listings"] = (
            get_related_listings_v271(
                getattr(
                    self,
                    "object",
                    None,
                ),
                limit=(
                    self.related_listings_limit_v271
                ),
            )
        )
        return context


class ListingDetailView(RecentlyViewedListingsContextMixinV272, RelatedListingsContextMixinV271, PublicPriceHistoryContextMixinV283, SidebarCategoriesMixin, DetailView):
    model = Listing
    template_name = "listings/listing_detail.html"
    context_object_name = "listing"

    def get_queryset(self):
        queryset = (
            Listing.objects
            .select_related("category", "owner", "owner__profile", "owner__seller_store")
            .prefetch_related("images")
        )

        if self.request.user.is_staff:
            return queryset

        if self.request.user.is_authenticated:
            return queryset.filter(
                Q(status=Listing.Status.APPROVED)
                | Q(owner=self.request.user)
            )

        return queryset.filter(status=Listing.Status.APPROVED).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))


    def get_context_data(self, **kwargs):
        context = {**super().get_context_data(**kwargs), **get_listing_price_alert_context_v285(self.request, self.object)}

        seller_store = None
        try:
            seller_store = self.object.owner.seller_store
        except SellerStore.DoesNotExist:
            seller_store = None

        can_preview_store = (
            self.request.user.is_authenticated
            and (self.request.user.is_staff or self.request.user == self.object.owner)
        )

        if seller_store and (seller_store.is_active or can_preview_store):
            context["seller_store"] = seller_store
            context["seller_store_listing_count"] = (
                Listing.objects
                .filter(owner=self.object.owner, status=Listing.Status.APPROVED)
                .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
                .count()
            )

        return context
