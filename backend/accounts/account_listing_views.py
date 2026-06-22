from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from listings.models import Listing


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
