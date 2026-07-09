from __future__ import annotations

import csv

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .listing_moderation_helpers import _create_moderation_notice
from .models import Listing


# V164 extracted from listings.views.


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
