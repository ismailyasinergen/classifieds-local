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


def default_listing_expiry():
    return timezone.now() + timedelta(days=30)


def active_approved_listings(queryset):
    return queryset.filter(
        status=Listing.Status.APPROVED,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    )


def validate_uploaded_images(uploaded_files):
    errors = []

    for uploaded_file in uploaded_files:
        extension = Path(uploaded_file.name).suffix.lower()
        content_type = uploaded_file.content_type

        if extension not in ALLOWED_IMAGE_EXTENSIONS:
            errors.append(f"{uploaded_file.name}: unsupported file extension")
            continue

        if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            errors.append(f"{uploaded_file.name}: unsupported file type")
            continue

        if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
            errors.append(f"{uploaded_file.name}: file is larger than {MAX_IMAGE_SIZE_MB} MB")

    return errors


def save_uploaded_listing_images(listing, uploaded_files):
    saved_count = 0

    for uploaded_file in uploaded_files:
        ListingImage.objects.create(
            listing=listing,
            image=uploaded_file,
        )
        saved_count += 1

    return saved_count


def apply_listing_filters(queryset, request):
    q = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    min_price = request.GET.get("min_price", "").strip()
    max_price = request.GET.get("max_price", "").strip()
    category_slug = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "newest").strip()

    if q:
        queryset = queryset.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(location__icontains=q)
            | Q(category__name__icontains=q)
        )

    if location:
        queryset = queryset.filter(location__icontains=location)

    if category_slug:
        category = Category.objects.filter(slug=category_slug).first()
        if category:
            queryset = queryset.filter(category_id__in=category.get_descendant_ids())

    try:
        if min_price:
            queryset = queryset.filter(price__gte=Decimal(min_price))
    except InvalidOperation:
        pass

    try:
        if max_price:
            queryset = queryset.filter(price__lte=Decimal(max_price))
    except InvalidOperation:
        pass

    if sort == "price_low":
        queryset = queryset.order_by("price")
    elif sort == "price_high":
        queryset = queryset.order_by("-price")
    else:
        queryset = queryset.order_by("-top_listing_priority", "-created_at")

    return queryset


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


class ListingDetailView(SidebarCategoriesMixin, DetailView):
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
        context = super().get_context_data(**kwargs)

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
def listing_favorite_toggle(request, pk):
    listing = get_object_or_404(
        Listing,
        pk=pk,
        status=Listing.Status.APPROVED,
    )

    if listing.owner == request.user:
        messages.warning(request, "You cannot save your own listing.")
        return redirect(request.POST.get("next") or listing.get_absolute_url())

    favorite, created = ListingFavorite.objects.get_or_create(
        user=request.user,
        listing=listing,
    )

    if created:
        messages.success(request, "Listing saved.")
    else:
        favorite.delete()
        messages.success(request, "Listing removed from saved listings.")

    return redirect(request.POST.get("next") or listing.get_absolute_url())



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



@login_required
@require_POST
def listing_feature_priority_update(request, pk):
    listing = get_object_or_404(Listing, pk=pk)

    if not request.user.is_staff:
        messages.warning(request, "Only staff can change featured priority.")
        return redirect(listing.get_absolute_url())

    try:
        priority = int(request.POST.get("featured_priority", 0))
    except ValueError:
        priority = 0

    if priority < 0:
        priority = 0

    listing.featured_priority = priority
    listing.save(update_fields=["featured_priority"])

    messages.success(request, "Featured priority updated.")
    return redirect(request.POST.get("next") or listing.get_absolute_url())



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
def _create_moderation_notice(recipient, title, body, notice_type="report_update", listing=None, listing_report=None):
    from accounts.models import ModerationNotice

    if not recipient:
        return None

    return ModerationNotice.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        notice_type=notice_type,
        listing=listing,
        listing_report=listing_report,
    )


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
    from .saved_searches import create_saved_search_from_request

    saved_search, created, querystring = create_saved_search_from_request(
        request,
        request.POST.get("querystring", ""),
        name=request.POST.get("name", ""),
        path=request.POST.get("path", ""),
    )

    if not saved_search:
        messages.warning(request, "Add a search or filters before saving.")
        return redirect("listings:listing_list")

    if created:
        messages.success(request, "Search saved.")
    else:
        messages.info(request, "Saved search updated.")

    return redirect(saved_search.get_absolute_url())

@login_required
def saved_search_list(request):
    # SAVED_SEARCH_MANAGEMENT_HARDENING_V79
    from django.core.paginator import Paginator
    from django.db.models import Q
    from django.urls import reverse
    from django.utils.http import urlencode

    from .models import SavedSearch

    saved_search_search_query = request.GET.get("q", "").strip()
    saved_searches_base = (
        SavedSearch.objects
        .filter(user=request.user)
        .order_by("-updated_at", "-created_at")
    )

    saved_search_total_count = saved_searches_base.count()
    saved_searches_queryset = saved_searches_base

    if saved_search_search_query:
        saved_searches_queryset = saved_searches_queryset.filter(
            Q(name__icontains=saved_search_search_query)
            | Q(querystring__icontains=saved_search_search_query)
        )

    saved_search_filtered_count = saved_searches_queryset.count()
    paginator = Paginator(saved_searches_queryset, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    pagination_params = {}
    if saved_search_search_query:
        pagination_params["q"] = saved_search_search_query

    saved_search_current_path = reverse("listings:saved_search_list")
    current_querystring = request.GET.urlencode()
    if current_querystring:
        saved_search_current_path = f"{saved_search_current_path}?{current_querystring}"

    return render(
        request,
        "listings/saved_search_list.html",
        {
            "saved_searches": page_obj.object_list,
            "page_obj": page_obj,
            "saved_search_search_query": saved_search_search_query,
            "saved_search_total_count": saved_search_total_count,
            "saved_search_filtered_count": saved_search_filtered_count,
            "saved_search_page_size": paginator.per_page,
            "saved_search_pagination_querystring": urlencode(pagination_params),
            # SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80
            "saved_search_current_path": saved_search_current_path,
            "saved_search_email_alert_count": saved_searches_base.filter(email_notifications_enabled=True).count(),
        },
    )


@login_required
@require_POST
def saved_search_notifications_toggle(request, pk):
    # SAVED_SEARCH_NOTIFICATIONS_FOUNDATION_V80
    from django.urls import reverse
    from django.utils.http import url_has_allowed_host_and_scheme

    from .models import SavedSearch

    saved_search = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    enabled = request.POST.get("enabled") == "on"

    saved_search.email_notifications_enabled = enabled
    saved_search.save(update_fields=["email_notifications_enabled", "updated_at"])

    if enabled:
        messages.success(request, "Email alerts enabled for this saved search.")
    else:
        messages.success(request, "Email alerts disabled for this saved search.")

    next_url = request.POST.get("next", "").strip()
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse("listings:saved_search_list")

    return redirect(next_url)


@login_required
@require_POST
def saved_search_delete(request, pk):
    from .models import SavedSearch

    saved_search = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    saved_search.delete()
    messages.success(request, "Saved search removed.")
    return redirect("listings:saved_search_list")
