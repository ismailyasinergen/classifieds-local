from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from listings.models import Listing, ListingFavorite

from .forms import RegisterForm, UserProfileForm
from .models import UserProfile


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("listings:listing_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        UserProfile.objects.get_or_create(user=self.object)
        login(self.request, self.object)
        return response


class MyListingsView(LoginRequiredMixin, ListView):
    model = Listing
    template_name = "accounts/my_listings.html"
    context_object_name = "listings"
    paginate_by = 12

    def get_queryset(self):
        queryset = (
            Listing.objects
            .select_related("category", "owner")
            .prefetch_related("images")
            .filter(owner=self.request.user)
        )

        status = self.request.GET.get("status", "").strip()

        valid_statuses = {
            Listing.Status.APPROVED,
            Listing.Status.PENDING,
            Listing.Status.REJECTED,
            Listing.Status.ARCHIVED,
            Listing.Status.DRAFT,
        }

        if status in valid_statuses:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user_listings = Listing.objects.filter(owner=self.request.user)

        context["status_filter"] = self.request.GET.get("status", "").strip()
        context["counts"] = {
            "all": user_listings.count(),
            "approved": user_listings.filter(status=Listing.Status.APPROVED).count(),
            "pending": user_listings.filter(status=Listing.Status.PENDING).count(),
            "rejected": user_listings.filter(status=Listing.Status.REJECTED).count(),
            "archived": user_listings.filter(status=Listing.Status.ARCHIVED).count(),
        }

        return context


class SavedListingsView(LoginRequiredMixin, ListView):
    model = Listing
    template_name = "accounts/saved_listings.html"
    context_object_name = "listings"
    paginate_by = 12

    def get_queryset(self):
        return (
            Listing.objects
            .select_related("category", "owner")
            .prefetch_related("images")
            .filter(
                favorites__user=self.request.user,
                status=Listing.Status.APPROVED,
            )
            .order_by("-favorites__created_at")
        )


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

    my_listings = (
        user_listings
        .select_related("category")
        .prefetch_related("images")[:6]
    )

    saved_count = ListingFavorite.objects.filter(user=request.user).count()

    unread_count = ListingMessage.objects.filter(
        recipient=request.user,
        is_read=False,
    ).count()

    return render(
        request,
        "accounts/dashboard.html",
        {
            "page_title": "Dashboard",
            "my_listings": my_listings,
            "saved_count": saved_count,
            "unread_count": unread_count,
            "approved_count": user_listings.filter(status=Listing.Status.APPROVED).count(),
            "pending_count": user_listings.filter(status=Listing.Status.PENDING).count(),
            "archived_count": user_listings.filter(status=Listing.Status.ARCHIVED).count(),
        },
    )


def logout_view(request):
    logout(request)
    return redirect("pages:home")


def verification_request_view(request):
    if not request.user.is_authenticated:
        return redirect("accounts:login")

    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        business_name = request.POST.get("business_name", "").strip()
        document = request.FILES.get("verification_document")

        if business_name:
            profile.business_name = business_name

        if document:
            allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}

            if document.content_type not in allowed_types:
                return render(
                    request,
                    "accounts/verification_request.html",
                    {
                        "profile": profile,
                        "error": "Only JPG, PNG, WEBP, or GIF files are allowed.",
                    },
                )

            if document.size > 5 * 1024 * 1024:
                return render(
                    request,
                    "accounts/verification_request.html",
                    {
                        "profile": profile,
                        "error": "Verification document must be under 5 MB.",
                    },
                )

            profile.verification_document = document

        profile.verification_status = UserProfile.VerificationStatus.PENDING
        profile.verification_note = ""
        profile.save()

        return redirect("accounts:verification_request")

    return render(
        request,
        "accounts/verification_request.html",
        {
            "profile": profile,
        },
    )


def verification_queue_view(request):
    if not request.user.is_staff:
        return redirect("pages:home")

    status_filter = request.GET.get("status", "").strip()

    profiles = UserProfile.objects.select_related("user").exclude(
        verification_status=UserProfile.VerificationStatus.NOT_REQUESTED,
    )

    valid_statuses = {
        UserProfile.VerificationStatus.PENDING,
        UserProfile.VerificationStatus.APPROVED,
        UserProfile.VerificationStatus.REJECTED,
    }

    if status_filter in valid_statuses:
        profiles = profiles.filter(verification_status=status_filter)

    counts = {
        "all": UserProfile.objects.exclude(
            verification_status=UserProfile.VerificationStatus.NOT_REQUESTED,
        ).count(),
        "pending": UserProfile.objects.filter(
            verification_status=UserProfile.VerificationStatus.PENDING,
        ).count(),
        "approved": UserProfile.objects.filter(
            verification_status=UserProfile.VerificationStatus.APPROVED,
        ).count(),
        "rejected": UserProfile.objects.filter(
            verification_status=UserProfile.VerificationStatus.REJECTED,
        ).count(),
    }

    return render(
        request,
        "accounts/verification_queue.html",
        {
            "profiles": profiles,
            "counts": counts,
            "status_filter": status_filter,
            "page_title": "Seller Verification",
        },
    )


def verification_approve_view(request, pk):
    if not request.user.is_staff:
        return redirect("pages:home")

    if request.method != "POST":
        return redirect("accounts:verification_queue")

    profile = UserProfile.objects.get(pk=pk)
    profile.verification_status = UserProfile.VerificationStatus.APPROVED
    profile.verification_note = ""
    profile.save(update_fields=["verification_status", "verification_note"])

    return redirect("accounts:verification_queue")


def verification_reject_view(request, pk):
    if not request.user.is_staff:
        return redirect("pages:home")

    if request.method != "POST":
        return redirect("accounts:verification_queue")

    profile = UserProfile.objects.get(pk=pk)
    profile.verification_status = UserProfile.VerificationStatus.REJECTED
    profile.verification_note = request.POST.get("verification_note", "").strip()
    profile.save(update_fields=["verification_status", "verification_note"])

    return redirect("accounts:verification_queue")
