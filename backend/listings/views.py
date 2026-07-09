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


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}

MAX_IMAGE_SIZE_MB = 8
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024












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


@staff_member_required
def moderation_queue(request):
    listings = (
        Listing.objects
        .select_related("category", "owner")
        .prefetch_related("images")
        .filter(status=Listing.Status.PENDING)
        .order_by("-top_listing_priority", "-created_at")
    )

    return render(
        request,
        "listings/moderation_queue.html",
        {
            "listings": listings,
            "page_title": "Moderation Queue",
        },
    )


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



@staff_member_required
def moderation_queue(request):
    status_filter = request.GET.get("status", "").strip()
    featured_filter = request.GET.get("featured", "").strip()

    listings = (
        Listing.objects
        .select_related("category", "owner")
        .prefetch_related("images")
        .all()
    )

    valid_statuses = {
        Listing.Status.PENDING,
        Listing.Status.APPROVED,
        Listing.Status.REJECTED,
        Listing.Status.ARCHIVED,
        Listing.Status.DRAFT,
    }

    if status_filter in valid_statuses:
        listings = listings.filter(status=status_filter)

    if featured_filter == "1":
        listings = listings.filter(is_featured=True)

    listings = listings.order_by("-top_listing_priority", "-created_at")

    all_listings = Listing.objects.all()

    counts = {
        "all": all_listings.count(),
        "pending": all_listings.filter(status=Listing.Status.PENDING).count(),
        "approved": all_listings.filter(status=Listing.Status.APPROVED).count(),
        "rejected": all_listings.filter(status=Listing.Status.REJECTED).count(),
        "archived": all_listings.filter(status=Listing.Status.ARCHIVED).count(),
        "featured": all_listings.filter(is_featured=True).count(),
    }

    return render(
        request,
        "listings/moderation_queue.html",
        {
            "listings": listings,
            "counts": counts,
            "status_filter": status_filter,
            "featured_filter": featured_filter,
            "page_title": "Moderation Queue",
        },
    )



from .listing_promotion_views import listing_feature_priority_update  # V152 re-export



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


@login_required
def listing_report_create(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        status=Listing.Status.APPROVED,
    )

    if listing.owner == request.user:
        messages.warning(request, "You cannot report your own listing.")
        return redirect(listing.get_absolute_url())

    from .models import ListingReport

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        details = request.POST.get("details", "").strip()

        valid_reasons = {
            ListingReport.Reason.SCAM,
            ListingReport.Reason.WRONG_CATEGORY,
            ListingReport.Reason.PROHIBITED,
            ListingReport.Reason.DUPLICATE,
            ListingReport.Reason.OTHER,
        }

        if reason not in valid_reasons:
            messages.warning(request, "Please choose a valid report reason.")
            return redirect("listings:listing_report", pk=listing.pk)

        ListingReport.objects.create(
            listing=listing,
            reporter=request.user,
            reason=reason,
            details=details,
        )

        messages.success(request, "Report submitted. Admin will review it.")
        return redirect(listing.get_absolute_url())

    return render(
        request,
        "listings/report_form.html",
        {
            "listing": listing,
            "reason_choices": ListingReport.Reason.choices,
            "page_title": "Report Listing",
        },
    )


@staff_member_required
def listing_report_queue(request):
    from .models import ListingReport

    status_filter = request.GET.get("status", "").strip()

    reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    )

    valid_statuses = {
        ListingReport.Status.PENDING,
        ListingReport.Status.REVIEWED,
        ListingReport.Status.DISMISSED,
    }

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    all_reports = ListingReport.objects.all()

    counts = {
        "all": all_reports.count(),
        "pending": all_reports.filter(status=ListingReport.Status.PENDING).count(),
        "reviewed": all_reports.filter(status=ListingReport.Status.REVIEWED).count(),
        "dismissed": all_reports.filter(status=ListingReport.Status.DISMISSED).count(),
    }

    return render(
        request,
        "listings/report_queue.html",
        {
            "reports": reports,
            "counts": counts,
            "status_filter": status_filter,
            "page_title": "Listing Reports",
        },
    )


@staff_member_required
@require_POST
def listing_report_review(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport, pk=pk)
    report.status = ListingReport.Status.REVIEWED
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "admin_note", "reviewed_at"])

    messages.success(request, "Report marked as reviewed.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_dismiss(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport, pk=pk)
    report.status = ListingReport.Status.DISMISSED
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "admin_note", "reviewed_at"])

    messages.success(request, "Report dismissed.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_archive_listing(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing"),
        pk=pk,
    )

    report.listing.status = Listing.Status.ARCHIVED
    report.listing.save(update_fields=["status"])

    report.status = ListingReport.Status.REVIEWED
    report.admin_note = request.POST.get("admin_note", "").strip() or "Listing archived from report queue."
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "admin_note", "reviewed_at"])

    messages.success(request, "Listing archived and report marked as reviewed.")
    return redirect("listings:report_queue")



@staff_member_required
def listing_report_queue(request):
    from django.db.models import Q
    from .models import ListingReport

    status_filter = request.GET.get("status", "").strip()
    reason_filter = request.GET.get("reason", "").strip()
    q = request.GET.get("q", "").strip()

    reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    )

    valid_statuses = {
        ListingReport.Status.PENDING,
        ListingReport.Status.REVIEWED,
        ListingReport.Status.DISMISSED,
    }

    valid_reasons = {
        ListingReport.Reason.SCAM,
        ListingReport.Reason.WRONG_CATEGORY,
        ListingReport.Reason.PROHIBITED,
        ListingReport.Reason.DUPLICATE,
        ListingReport.Reason.OTHER,
    }

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    if reason_filter in valid_reasons:
        reports = reports.filter(reason=reason_filter)

    if q:
        reports = reports.filter(
            Q(listing__title__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
        )

    all_reports = ListingReport.objects.all()

    counts = {
        "all": all_reports.count(),
        "pending": all_reports.filter(status=ListingReport.Status.PENDING).count(),
        "reviewed": all_reports.filter(status=ListingReport.Status.REVIEWED).count(),
        "dismissed": all_reports.filter(status=ListingReport.Status.DISMISSED).count(),
    }

    return render(
        request,
        "listings/report_queue.html",
        {
            "reports": reports,
            "counts": counts,
            "status_filter": status_filter,
            "reason_filter": reason_filter,
            "reason_choices": ListingReport.Reason.choices,
            "q": q,
            "page_title": "Listing Reports",
        },
    )



@staff_member_required
def listing_report_export_csv(request):
    import csv
    from django.db.models import Q
    from django.http import HttpResponse
    from .models import ListingReport

    status_filter = request.GET.get("status", "").strip()
    reason_filter = request.GET.get("reason", "").strip()
    q = request.GET.get("q", "").strip()

    reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    )

    valid_statuses = {
        ListingReport.Status.PENDING,
        ListingReport.Status.REVIEWED,
        ListingReport.Status.DISMISSED,
    }

    valid_reasons = {
        ListingReport.Reason.SCAM,
        ListingReport.Reason.WRONG_CATEGORY,
        ListingReport.Reason.PROHIBITED,
        ListingReport.Reason.DUPLICATE,
        ListingReport.Reason.OTHER,
    }

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    if reason_filter in valid_reasons:
        reports = reports.filter(reason=reason_filter)

    if q:
        reports = reports.filter(
            Q(listing__title__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="listing_reports.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Report ID",
        "Listing ID",
        "Listing Title",
        "Listing Status",
        "Reporter Username",
        "Reporter Email",
        "Owner Username",
        "Owner Email",
        "Reason",
        "Report Status",
        "Details",
        "Admin Note",
        "Created At",
        "Reviewed At",
    ])

    for report in reports:
        writer.writerow([
            report.id,
            report.listing.id,
            report.listing.title,
            report.listing.get_status_display(),
            report.reporter.username,
            report.reporter.email,
            report.listing.owner.username,
            report.listing.owner.email,
            report.get_reason_display(),
            report.get_status_display(),
            report.details,
            report.admin_note,
            report.created_at,
            report.reviewed_at or "",
        ])

    return response



@login_required
def listing_report_create(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        status=Listing.Status.APPROVED,
    )

    if listing.owner == request.user:
        messages.warning(request, "You cannot report your own listing.")
        return redirect(listing.get_absolute_url())

    from .models import ListingReport

    existing_report = ListingReport.objects.filter(
        listing=listing,
        reporter=request.user,
    ).order_by("-created_at").first()

    if existing_report and existing_report.status == ListingReport.Status.PENDING:
        messages.info(request, "You already have a pending report for this listing.")
        return redirect("listings:my_reports")

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        details = request.POST.get("details", "").strip()

        valid_reasons = {
            ListingReport.Reason.SCAM,
            ListingReport.Reason.WRONG_CATEGORY,
            ListingReport.Reason.PROHIBITED,
            ListingReport.Reason.DUPLICATE,
            ListingReport.Reason.OTHER,
        }

        if reason not in valid_reasons:
            messages.warning(request, "Please choose a valid report reason.")
            return redirect("listings:listing_report", pk=listing.pk)

        ListingReport.objects.create(
            listing=listing,
            reporter=request.user,
            reason=reason,
            details=details,
            status=ListingReport.Status.PENDING,
        )

        messages.success(request, "Report submitted. Admin will review it.")
        return redirect("listings:my_reports")

    return render(
        request,
        "listings/report_form.html",
        {
            "listing": listing,
            "reason_choices": ListingReport.Reason.choices,
            "page_title": "Report Listing",
        },
    )


@login_required
def my_listing_reports(request):
    from .models import ListingReport

    reports = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
    ).filter(
        reporter=request.user,
    ).order_by("-created_at")

    return render(
        request,
        "listings/my_reports.html",
        {
            "reports": reports,
            "page_title": "My Reports",
        },
    )


@login_required
def listing_report_create(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        status=Listing.Status.APPROVED,
    )

    if listing.owner == request.user:
        messages.warning(request, "You cannot report your own listing.")
        return redirect(listing.get_absolute_url())

    from .models import ListingReport

    existing_report = ListingReport.objects.filter(
        listing=listing,
        reporter=request.user,
    ).order_by("-created_at").first()

    if existing_report:
        messages.info(request, "You already reported this listing. You can track it in My Reports.")
        return redirect("listings:my_reports")

    if request.method == "POST":
        selected_reasons = request.POST.getlist("reasons")
        details = request.POST.get("details", "").strip()

        valid_reasons = {choice[0] for choice in ListingReport.Reason.choices}
        selected_reasons = [reason for reason in selected_reasons if reason in valid_reasons]

        if not selected_reasons:
            messages.warning(request, "Please choose at least one report reason.")
            return redirect("listings:listing_report", pk=listing.pk)

        ListingReport.objects.create(
            listing=listing,
            reporter=request.user,
            reason=selected_reasons[0],
            reasons=selected_reasons,
            details=details,
            status=ListingReport.Status.PENDING,
        )

        messages.success(request, "Report submitted. Admin will review it.")
        return redirect("listings:my_reports")

    return render(
        request,
        "listings/report_form.html",
        {
            "listing": listing,
            "reason_choices": ListingReport.Reason.choices,
            "page_title": "Report Listing",
        },
    )


@login_required
def my_listing_reports(request):
    from .models import ListingReport

    reports = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
    ).filter(
        reporter=request.user,
    ).order_by("-created_at")

    return render(
        request,
        "listings/my_reports.html",
        {
            "reports": reports,
            "page_title": "My Reports",
        },
    )


@staff_member_required
def listing_report_queue(request):
    from django.db.models import Q
    from .models import ListingReport

    status_filter = request.GET.get("status", "").strip()
    reason_filter = request.GET.get("reason", "").strip()
    q = request.GET.get("q", "").strip()

    reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    )

    valid_statuses = {
        ListingReport.Status.PENDING,
        ListingReport.Status.REVIEWED,
        ListingReport.Status.DISMISSED,
    }

    valid_reasons = {choice[0] for choice in ListingReport.Reason.choices}

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    if reason_filter in valid_reasons:
        reports = reports.filter(Q(reason=reason_filter) | Q(reasons__contains=[reason_filter]))

    if q:
        reports = reports.filter(
            Q(listing__title__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
        )

    all_reports = ListingReport.objects.all()

    counts = {
        "all": all_reports.count(),
        "pending": all_reports.filter(status=ListingReport.Status.PENDING).count(),
        "reviewed": all_reports.filter(status=ListingReport.Status.REVIEWED).count(),
        "dismissed": all_reports.filter(status=ListingReport.Status.DISMISSED).count(),
    }

    return render(
        request,
        "listings/report_queue.html",
        {
            "reports": reports,
            "counts": counts,
            "status_filter": status_filter,
            "reason_filter": reason_filter,
            "reason_choices": ListingReport.Reason.choices,
            "q": q,
            "page_title": "Listing Reports",
        },
    )


# FINAL_REPORT_MODERATION_OVERRIDES_V2
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


def _safe_reporter_note(request, default):
    return request.POST.get("reporter_note", "").strip() or default


@login_required
def listing_report_create(request, pk):
    from .models import ListingReport

    listing = get_object_or_404(
        Listing,
        pk=pk,
        status=Listing.Status.APPROVED,
    )

    if listing.owner == request.user:
        messages.warning(request, "You cannot report your own listing.")
        return redirect(listing.get_absolute_url())

    existing_report = ListingReport.objects.filter(
        listing=listing,
        reporter=request.user,
    ).order_by("-created_at").first()

    if existing_report:
        messages.info(request, "You already reported this listing. You can track it in My Reports.")
        return redirect("listings:my_reports")

    if request.method == "POST":
        selected_reasons = request.POST.getlist("reasons")
        details = request.POST.get("details", "").strip()

        valid_reasons = {choice[0] for choice in ListingReport.Reason.choices}
        selected_reasons = [reason for reason in selected_reasons if reason in valid_reasons]

        if not selected_reasons:
            messages.warning(request, "Please choose at least one report reason.")
            return redirect("listings:listing_report", pk=listing.pk)

        ListingReport.objects.create(
            listing=listing,
            reporter=request.user,
            reason=selected_reasons[0],
            reasons=selected_reasons,
            details=details,
            status=ListingReport.Status.PENDING,
        )

        messages.success(request, "Report submitted. Admin will review it.")
        return redirect("listings:my_reports")

    return render(
        request,
        "listings/report_form.html",
        {
            "listing": listing,
            "reason_choices": ListingReport.Reason.choices,
            "page_title": "Report Listing",
        },
    )


@login_required
def my_listing_reports(request):
    from .models import ListingReport

    reports = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
    ).filter(
        reporter=request.user,
    ).order_by("-created_at")

    return render(
        request,
        "listings/my_reports.html",
        {
            "reports": reports,
            "page_title": "My Reports",
        },
    )


@staff_member_required
def listing_report_queue(request):
    from .models import Listing, ListingReport

    status_filter = request.GET.get("status", "").strip()
    listing_status_filter = request.GET.get("listing_status", "").strip()
    reason_filter = request.GET.get("reason", "").strip()
    q = request.GET.get("q", "").strip()

    reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    )

    valid_statuses = {
        ListingReport.Status.PENDING,
        ListingReport.Status.REVIEWED,
        ListingReport.Status.DISMISSED,
    }
    valid_listing_statuses = {
        Listing.Status.APPROVED,
        Listing.Status.SUSPENDED,
        Listing.Status.ARCHIVED,
        Listing.Status.PENDING,
        Listing.Status.REJECTED,
        Listing.Status.DRAFT,
    }
    valid_reasons = {choice[0] for choice in ListingReport.Reason.choices}

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    if listing_status_filter in valid_listing_statuses:
        reports = reports.filter(listing__status=listing_status_filter)

    if reason_filter in valid_reasons:
        reports = reports.filter(Q(reason=reason_filter) | Q(reasons__contains=[reason_filter]))

    if q:
        reports = reports.filter(
            Q(listing__title__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
        )

    all_reports = ListingReport.objects.select_related("listing").all()

    counts = {
        "all": all_reports.count(),
        "pending": all_reports.filter(status=ListingReport.Status.PENDING).count(),
        "reviewed": all_reports.filter(status=ListingReport.Status.REVIEWED).count(),
        "dismissed": all_reports.filter(status=ListingReport.Status.DISMISSED).count(),
    }

    listing_status_counts = {
        "approved": all_reports.filter(listing__status=Listing.Status.APPROVED).count(),
        "suspended": all_reports.filter(listing__status=Listing.Status.SUSPENDED).count(),
        "archived": all_reports.filter(listing__status=Listing.Status.ARCHIVED).count(),
    }

    return render(
        request,
        "listings/report_queue.html",
        {
            "reports": reports,
            "counts": counts,
            "listing_status_counts": listing_status_counts,
            "status_filter": status_filter,
            "listing_status_filter": listing_status_filter,
            "reason_filter": reason_filter,
            "reason_choices": ListingReport.Reason.choices,
            "listing_status_choices": Listing.Status.choices,
            "q": q,
            "page_title": "Listing Reports",
        },
    )


@staff_member_required
def listing_report_export_csv(request):
    import csv
    from .models import Listing, ListingReport

    status_filter = request.GET.get("status", "").strip()
    listing_status_filter = request.GET.get("listing_status", "").strip()
    reason_filter = request.GET.get("reason", "").strip()
    q = request.GET.get("q", "").strip()

    reports = ListingReport.objects.select_related("listing", "reporter", "listing__owner")

    valid_statuses = {
        ListingReport.Status.PENDING,
        ListingReport.Status.REVIEWED,
        ListingReport.Status.DISMISSED,
    }
    valid_listing_statuses = {
        Listing.Status.APPROVED,
        Listing.Status.SUSPENDED,
        Listing.Status.ARCHIVED,
        Listing.Status.PENDING,
        Listing.Status.REJECTED,
        Listing.Status.DRAFT,
    }
    valid_reasons = {choice[0] for choice in ListingReport.Reason.choices}

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    if listing_status_filter in valid_listing_statuses:
        reports = reports.filter(listing__status=listing_status_filter)

    if reason_filter in valid_reasons:
        reports = reports.filter(Q(reason=reason_filter) | Q(reasons__contains=[reason_filter]))

    if q:
        reports = reports.filter(
            Q(listing__title__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="listing_reports.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Report ID",
        "Listing ID",
        "Listing Title",
        "Listing Status",
        "Reporter",
        "Owner",
        "Reasons",
        "Report Status",
        "Action Taken",
        "Details",
        "Reporter Note",
        "Internal Admin Note",
        "Created At",
        "Reviewed At",
    ])

    for report in reports:
        writer.writerow([
            report.id,
            report.listing.id,
            report.listing.title,
            report.listing.get_status_display(),
            report.reporter.username,
            report.listing.owner.username,
            report.get_reasons_display(),
            report.get_status_display(),
            report.action_taken,
            report.details,
            report.reporter_note,
            report.admin_note,
            report.created_at,
            report.reviewed_at or "",
        ])

    return response


@staff_member_required
@require_POST
def listing_report_suspend_listing(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport.objects.select_related("listing"), pk=pk)

    report.listing.status = Listing.Status.SUSPENDED
    report.listing.save(update_fields=["status"])

    report.action_taken = "listing_suspended"
    report.admin_note = request.POST.get("admin_note", "").strip() or "Listing temporarily suspended during review."
    report.reporter_note = _safe_reporter_note(
        request,
        "We reviewed your report and temporarily hid the listing while we investigate.",
    )
    report.reviewed_at = timezone.now()
    report.save(update_fields=["action_taken", "admin_note", "reporter_note", "reviewed_at"])

    messages.success(request, "Listing temporarily suspended. Report remains pending.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_review(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport, pk=pk)
    report.status = ListingReport.Status.REVIEWED
    report.action_taken = "reviewed"
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = _safe_reporter_note(
        request,
        "We reviewed your report. Thank you for helping keep the marketplace safe.",
    )
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at"])

    messages.success(request, "Report marked as reviewed.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_dismiss(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport, pk=pk)
    report.status = ListingReport.Status.DISMISSED
    report.action_taken = "dismissed"
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = _safe_reporter_note(
        request,
        "We reviewed your report and did not take action at this time.",
    )
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at"])

    messages.success(request, "Report dismissed.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_archive_listing(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport.objects.select_related("listing"), pk=pk)

    report.listing.status = Listing.Status.ARCHIVED
    report.listing.save(update_fields=["status"])

    report.status = ListingReport.Status.REVIEWED
    report.action_taken = "listing_archived"
    report.admin_note = request.POST.get("admin_note", "").strip() or "Listing archived from report queue."
    report.reporter_note = _safe_reporter_note(
        request,
        "We reviewed your report and took action on the listing.",
    )
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at"])

    messages.success(request, "Listing archived and report marked as reviewed.")
    return redirect("listings:report_queue")


_ReportOriginalListingCreateView = ListingCreateView
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


_ReportOriginalListingUpdateView = ListingUpdateView
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


# FINAL_LISTING_REPORT_NOTICE_ACTIONS_V1


@staff_member_required
@require_POST
def listing_report_review(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport.objects.select_related("listing", "reporter"), pk=pk)

    report.status = ListingReport.Status.REVIEWED
    report.action_taken = "reviewed"
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report. Thank you for helping keep the marketplace safe."
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at"])

    _create_moderation_notice(
        recipient=report.reporter,
        title="Your listing report was reviewed",
        body=report.reporter_note,
        notice_type="report_update",
        listing=report.listing,
        listing_report=report,
    )

    messages.success(request, "Report marked as reviewed and reporter notified.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_dismiss(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(ListingReport.objects.select_related("listing", "reporter"), pk=pk)

    report.status = ListingReport.Status.DISMISSED
    report.action_taken = "dismissed"
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and did not take action at this time."
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at"])

    _create_moderation_notice(
        recipient=report.reporter,
        title="Your listing report was reviewed",
        body=report.reporter_note,
        notice_type="report_update",
        listing=report.listing,
        listing_report=report,
    )

    messages.success(request, "Report dismissed and reporter notified.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_suspend_listing(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "reporter", "listing__owner"),
        pk=pk,
    )

    report.listing.status = Listing.Status.SUSPENDED
    report.listing.save(update_fields=["status"])

    report.action_taken = "listing_suspended"
    report.admin_note = request.POST.get("admin_note", "").strip() or "Listing temporarily suspended during review."
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and temporarily hid the listing while we investigate."
    report.reviewed_at = timezone.now()
    report.save(update_fields=["action_taken", "admin_note", "reporter_note", "reviewed_at"])

    _create_moderation_notice(
        recipient=report.reporter,
        title="Action was taken on a listing you reported",
        body=report.reporter_note,
        notice_type="report_update",
        listing=report.listing,
        listing_report=report,
    )

    _create_moderation_notice(
        recipient=report.listing.owner,
        title="Your listing was temporarily hidden",
        body=f'Your listing "{report.listing.title}" has been temporarily hidden while we review a moderation issue. Please check your listing details or contact support if you think this is a mistake.',
        notice_type="listing_action",
        listing=report.listing,
        listing_report=report,
    )

    messages.success(request, "Listing suspended. Reporter and listing owner notified.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_archive_listing(request, pk):
    from django.utils import timezone
    from .models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "reporter", "listing__owner"),
        pk=pk,
    )

    report.listing.status = Listing.Status.ARCHIVED
    report.listing.save(update_fields=["status"])

    report.status = ListingReport.Status.REVIEWED
    report.action_taken = "listing_archived"
    report.admin_note = request.POST.get("admin_note", "").strip() or "Listing archived from report queue."
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and took action on the listing."
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at"])

    _create_moderation_notice(
        recipient=report.reporter,
        title="Action was taken on a listing you reported",
        body=report.reporter_note,
        notice_type="report_update",
        listing=report.listing,
        listing_report=report,
    )

    _create_moderation_notice(
        recipient=report.listing.owner,
        title="Your listing was removed after moderation review",
        body=f'Your listing "{report.listing.title}" was removed after moderation review.',
        notice_type="listing_action",
        listing=report.listing,
        listing_report=report,
    )

    messages.success(request, "Listing archived. Reporter and listing owner notified.")
    return redirect("listings:report_queue")


# SAFE_LISTING_LEVEL_SUSPENSION_TRACKING_FINAL_V1
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .listing_filter_helpers import apply_listing_filters  # LISTING_FILTER_HELPER_EXTRACTION_V142
from .listing_moderation_helpers import _create_moderation_notice  # LISTING_MODERATION_HELPER_EXTRACTION_V143
from .listing_lifecycle_helpers import default_listing_expiry  # DEFAULT_LISTING_EXPIRY_HELPER_EXTRACTION_V145
from .listing_visibility_helpers import active_approved_listings  # ACTIVE_APPROVED_LISTINGS_HELPER_EXTRACTION_V146
from .listing_image_helpers import save_uploaded_listing_images  # SAVE_UPLOADED_LISTING_IMAGES_HELPER_EXTRACTION_V147
from .listing_image_helpers import validate_uploaded_images  # VALIDATE_UPLOADED_IMAGES_HELPER_EXTRACTION_V148
from .listing_favorite_views import listing_favorite_toggle  # V155 re-export
from .listing_browse_detail_views import ListingDetailView  # V157 re-export


@staff_member_required
@require_POST
def listing_report_suspend_listing(request, pk):
    from accounts.models import ModerationNotice
    from .models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "listing__owner", "reporter"),
        pk=pk,
    )

    listing = report.listing

    reporter_note = (
        request.POST.get("reporter_note")
        or request.POST.get("message_to_reporter")
        or "We reviewed your report and temporarily hid the listing while we investigate."
    )

    internal_note = (
        request.POST.get("admin_note")
        or request.POST.get("note")
        or ""
    )

    listing.status = listing.Status.SUSPENDED
    listing.suspended_due_to_seller = False
    listing.status_before_seller_suspension = ""
    listing.save(
        update_fields=[
            "status",
            "suspended_due_to_seller",
            "status_before_seller_suspension",
        ]
    )

    report.status = ListingReport.Status.REVIEWED
    report.action_taken = "suspended_listing"
    report.reporter_note = reporter_note
    if internal_note:
        report.admin_note = internal_note
    report.save()

    ModerationNotice.objects.create(
        recipient=report.reporter,
        title="Listing report update",
        body=reporter_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=listing,
        listing_report=report,
    )

    ModerationNotice.objects.create(
        recipient=listing.owner,
        title="Your listing was temporarily suspended",
        body=f'Your listing "{listing.title}" was temporarily hidden for moderation review.',
        notice_type=ModerationNotice.NoticeType.LISTING_ACTION,
        listing=listing,
        listing_report=report,
    )

    messages.success(request, "Listing suspended as listing-level moderation action.")
    return redirect("listings:report_queue")


@staff_member_required
@require_POST
def listing_report_archive_listing(request, pk):
    from accounts.models import ModerationNotice
    from .models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "listing__owner", "reporter"),
        pk=pk,
    )

    listing = report.listing

    reporter_note = (
        request.POST.get("reporter_note")
        or request.POST.get("message_to_reporter")
        or "We reviewed your report and removed the listing."
    )

    internal_note = (
        request.POST.get("admin_note")
        or request.POST.get("note")
        or ""
    )

    listing.status = listing.Status.ARCHIVED
    listing.suspended_due_to_seller = False
    listing.status_before_seller_suspension = ""
    listing.save(
        update_fields=[
            "status",
            "suspended_due_to_seller",
            "status_before_seller_suspension",
        ]
    )

    report.status = ListingReport.Status.REVIEWED
    report.action_taken = "archived_listing"
    report.reporter_note = reporter_note
    if internal_note:
        report.admin_note = internal_note
    report.save()

    ModerationNotice.objects.create(
        recipient=report.reporter,
        title="Listing report reviewed",
        body=reporter_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=listing,
        listing_report=report,
    )

    ModerationNotice.objects.create(
        recipient=listing.owner,
        title="Your listing was archived",
        body=f'Your listing "{listing.title}" was removed after moderation review.',
        notice_type=ModerationNotice.NoticeType.LISTING_ACTION,
        listing=listing,
        listing_report=report,
    )

    messages.success(request, "Listing archived and owner notified.")
    return redirect("listings:report_queue")

# Attribute-aware browse filters.
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

# TRUST_SAFETY_REPORT_EVENT_WIRING_V2
_TrustSafetyOriginalListingReportReview = listing_report_review
@staff_member_required
@require_POST
def listing_report_review(request, pk):
    response = _TrustSafetyOriginalListingReportReview(request, pk)

    try:
        from accounts.services.report_trust_safety_events import record_listing_report_reviewed
        from .models import ListingReport

        report = ListingReport.objects.select_related("listing", "listing__owner", "reporter").get(pk=pk)
        record_listing_report_reviewed(report, actor=request.user)
    except Exception:
        pass

    return response


_TrustSafetyOriginalListingReportDismiss = listing_report_dismiss
@staff_member_required
@require_POST
def listing_report_dismiss(request, pk):
    response = _TrustSafetyOriginalListingReportDismiss(request, pk)

    try:
        from accounts.services.report_trust_safety_events import record_listing_report_reviewed
        from .models import ListingReport

        report = ListingReport.objects.select_related("listing", "listing__owner", "reporter").get(pk=pk)
        record_listing_report_reviewed(report, actor=request.user, dismissed=True)
    except Exception:
        pass

    return response


_TrustSafetyOriginalListingReportSuspendListing = listing_report_suspend_listing
@staff_member_required
@require_POST
def listing_report_suspend_listing(request, pk):
    response = _TrustSafetyOriginalListingReportSuspendListing(request, pk)

    try:
        from accounts.services.report_trust_safety_events import record_listing_report_suspended
        from .models import ListingReport

        report = ListingReport.objects.select_related("listing", "listing__owner", "reporter").get(pk=pk)
        record_listing_report_suspended(report, actor=request.user)
    except Exception:
        pass

    return response


_TrustSafetyOriginalListingReportArchiveListing = listing_report_archive_listing
@staff_member_required
@require_POST
def listing_report_archive_listing(request, pk):
    response = _TrustSafetyOriginalListingReportArchiveListing(request, pk)

    try:
        from accounts.services.report_trust_safety_events import record_listing_report_archived
        from .models import ListingReport

        report = ListingReport.objects.select_related("listing", "listing__owner", "reporter").get(pk=pk)
        record_listing_report_archived(report, actor=request.user)
    except Exception:
        pass

    return response
# SAVED_SEARCH_FOUNDATION_V77
# SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80
# SELLER_STORE_SAVED_SEARCH_CREATE_INTEGRATION_V122
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
