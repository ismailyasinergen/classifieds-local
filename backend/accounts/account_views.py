from django.conf import settings
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from listings.models import Listing, ListingFavorite

from .forms import RegisterForm, UserProfileForm
from .models import SellerStore, UserProfile


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("listings:listing_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        UserProfile.objects.get_or_create(user=self.object)
        SellerStore.objects.get_or_create(owner=self.object)
        auth_backend = getattr(
            settings,
            "AUTHENTICATION_BACKENDS",
            ["django.contrib.auth.backends.ModelBackend"],
        )[0]
        login(self.request, self.object, backend=auth_backend)
        return response


def profile_view(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = UserProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "profile": profile,
        },
    )


def dashboard_view(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    from conversations.models import ListingMessage

    user_listings = Listing.objects.filter(owner=request.user)

    from listings.listing_card_promotions_v343 import (
        annotate_listing_card_promotions_v343,
    )

    my_listings = annotate_listing_card_promotions_v343(
        user_listings
        .select_related(
            "category",
            "owner",
            "owner__profile",
            "owner__seller_store",
        )
        .prefetch_related("images")
    )[:6]

    saved_count = ListingFavorite.objects.filter(user=request.user).count()

    unread_count = ListingMessage.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()

    seller_store, _ = SellerStore.objects.get_or_create(owner=request.user)
    seller_store_active_listing_count = user_listings.filter(
        status=Listing.Status.APPROVED,
    ).count()

    return render(
        request,
        "accounts/dashboard.html",
        {
            "page_title": "Dashboard",
            "my_listings": my_listings,
            "saved_count": saved_count,
            "unread_count": unread_count,
            "seller_store": seller_store,
            "seller_store_active_listing_count": seller_store_active_listing_count,
            "approved_count": user_listings.filter(status=Listing.Status.APPROVED).count(),
            "pending_count": user_listings.filter(status=Listing.Status.PENDING).count(),
            "archived_count": user_listings.filter(status=Listing.Status.ARCHIVED).count(),
        },
    )


def logout_view(request):
    logout(request)
    return redirect("pages:home")
