# TRUST_SAFETY_REPORT_VIEWS_REFACTOR_V1
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

# TRUST_SAFETY_REPORT_DETAIL_UI_V1
@staff_member_required
def trust_safety_listing_report_detail(request, pk):
    from accounts.models import ModerationNotice
    from listings.models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related(
            "listing",
            "listing__owner",
            "reporter",
        ),
        pk=pk,
    )

    notices = ModerationNotice.objects.filter(
        listing_report=report,
    ).select_related("recipient", "listing").order_by("-created_at")

    return render(
        request,
        "accounts/trust_safety_listing_report_detail.html",
        {
            "report": report,
            "notices": notices,
            "page_title": "Listing Report Detail",
        },
    )


@staff_member_required
def trust_safety_seller_report_detail(request, pk):
    from accounts.models import ModerationNotice, UserProfile, UserReport

    report = get_object_or_404(
        UserReport.objects.select_related(
            "reported_user",
            "reporter",
            "source_listing",
        ),
        pk=pk,
    )

    reported_profile = UserProfile.objects.filter(
        user=report.reported_user,
    ).first()

    notices = ModerationNotice.objects.filter(
        user_report=report,
    ).select_related("recipient", "listing").order_by("-created_at")

    return render(
        request,
        "accounts/trust_safety_seller_report_detail.html",
        {
            "report": report,
            "reported_profile": reported_profile,
            "notices": notices,
            "page_title": "Seller Report Detail",
        },
    )


# TRUST_SAFETY_DETAIL_ACTIONS_V1
@staff_member_required
@require_POST
def trust_safety_listing_report_review(request, pk):
    from django.utils import timezone
    from accounts.models import ModerationNotice
    from listings.models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "reporter"),
        pk=pk,
    )

    reporter_note = (
        request.POST.get("reporter_note")
        or "We reviewed your report. Thank you for helping keep the marketplace safe."
    )
    admin_note = request.POST.get("admin_note") or ""

    report.status = ListingReport.Status.REVIEWED
    report.action_taken = "reviewed"
    report.reporter_note = reporter_note
    report.reviewed_at = timezone.now()
    if admin_note:
        report.admin_note = admin_note
    report.save()

    ModerationNotice.objects.create(
        recipient=report.reporter,
        title="Listing report reviewed",
        body=reporter_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=report.listing,
        listing_report=report,
    )

    messages.success(request, "Listing report marked reviewed and reporter notified.")
    return redirect("accounts:trust_safety_listing_report_detail", pk=report.pk)


@staff_member_required
@require_POST
def trust_safety_listing_report_dismiss(request, pk):
    from django.utils import timezone
    from accounts.models import ModerationNotice
    from listings.models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "reporter"),
        pk=pk,
    )

    reporter_note = (
        request.POST.get("reporter_note")
        or "We reviewed your report and did not find enough evidence to take action at this time."
    )
    admin_note = request.POST.get("admin_note") or ""

    report.status = ListingReport.Status.DISMISSED
    report.action_taken = "dismissed"
    report.reporter_note = reporter_note
    report.reviewed_at = timezone.now()
    if admin_note:
        report.admin_note = admin_note
    report.save()

    ModerationNotice.objects.create(
        recipient=report.reporter,
        title="Listing report reviewed",
        body=reporter_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=report.listing,
        listing_report=report,
    )

    messages.success(request, "Listing report dismissed and reporter notified.")
    return redirect("accounts:trust_safety_listing_report_detail", pk=report.pk)


@staff_member_required
@require_POST
def trust_safety_listing_report_suspend(request, pk):
    from accounts.models import ModerationNotice
    from listings.models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "listing__owner", "reporter"),
        pk=pk,
    )

    listing = report.listing
    reporter_note = (
        request.POST.get("reporter_note")
        or "We reviewed your report and temporarily hid the listing while we investigate."
    )
    admin_note = request.POST.get("admin_note") or ""

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

    report.action_taken = "suspended_listing"
    report.reporter_note = reporter_note
    if admin_note:
        report.admin_note = admin_note
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

    messages.success(request, "Listing suspended as listing-level moderation. Owner and reporter notified.")
    return redirect("accounts:trust_safety_listing_report_detail", pk=report.pk)


@staff_member_required
@require_POST
def trust_safety_listing_report_archive(request, pk):
    from django.utils import timezone
    from accounts.models import ModerationNotice
    from listings.models import ListingReport

    report = get_object_or_404(
        ListingReport.objects.select_related("listing", "listing__owner", "reporter"),
        pk=pk,
    )

    listing = report.listing
    reporter_note = (
        request.POST.get("reporter_note")
        or "We reviewed your report and removed the listing."
    )
    admin_note = request.POST.get("admin_note") or ""

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
    report.reviewed_at = timezone.now()
    if admin_note:
        report.admin_note = admin_note
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

    messages.success(request, "Listing archived. Owner and reporter notified.")
    return redirect("accounts:trust_safety_listing_report_detail", pk=report.pk)
