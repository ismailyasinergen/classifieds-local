# TRUST_SAFETY_DASHBOARD_VIEWS_REFACTOR_PART_5_V1
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from listings.models import Listing, ListingReport

from .models import ModerationAppeal, ModerationNotice, UserProfile, UserReport


def _listing_status(name, fallback):
    return getattr(getattr(Listing, "Status", object), name, fallback)


LISTING_APPROVED = _listing_status("APPROVED", "approved")
LISTING_PENDING = _listing_status("PENDING", "pending")
LISTING_SUSPENDED = _listing_status("SUSPENDED", "suspended")


def _record_event_safely(**kwargs):
    try:
        from .services.trust_safety_events import record_trust_safety_event
        return record_trust_safety_event(**kwargs)
    except Exception:
        return None


def _is_profile_suspended(profile):
    return bool(
        profile
        and profile.seller_suspended_until
        and profile.seller_suspended_until > timezone.now()
    )


@staff_member_required
def trust_safety_dashboard(request):
    now = timezone.now()

    pending_listing_reports = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).filter(status="pending").order_by("-created_at")

    pending_seller_reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).filter(status="pending").order_by("-created_at")

    pending_appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
    ).prefetch_related("attachments").filter(
        status=ModerationAppeal.Status.PENDING,
    ).order_by("-created_at")

    latest_pending_appeals = list(pending_appeals[:10])
    for appeal in latest_pending_appeals:
        appeal.evidence_file_count = appeal.attachments.count()

    suspended_listings = Listing.objects.select_related("owner").filter(
        status=LISTING_SUSPENDED,
    ).order_by("-updated_at", "-created_at")[:25]

    suspended_sellers = UserProfile.objects.select_related("user").filter(
        seller_suspended_until__gt=now,
    ).order_by("seller_suspended_until")[:25]

    context = {
        "pending_listing_report_count": pending_listing_reports.count(),
        "pending_listing_reports_count": pending_listing_reports.count(),
        "pending_seller_report_count": pending_seller_reports.count(),
        "pending_seller_reports_count": pending_seller_reports.count(),
        "pending_appeal_count": pending_appeals.count(),
        "pending_appeals_count": pending_appeals.count(),
        "latest_listing_reports": pending_listing_reports[:10],
        "latest_seller_reports": pending_seller_reports[:10],
        "latest_pending_appeals": latest_pending_appeals,
        "pending_appeals": latest_pending_appeals,
        "suspended_listings": suspended_listings,
        "suspended_sellers": suspended_sellers,
        "page_title": "Trust & Safety",
    }

    return render(request, "accounts/trust_safety_dashboard.html", context)


@staff_member_required
@require_POST
def trust_safety_restore_listing(request, pk):
    listing = get_object_or_404(Listing.objects.select_related("owner"), pk=pk)

    if listing.status != LISTING_SUSPENDED:
        messages.info(request, "This listing is not currently suspended.")
        return redirect("accounts:trust_safety_dashboard")

    if getattr(listing, "suspended_due_to_seller", False):
        messages.error(
            request,
            "This listing was hidden because the seller was suspended. Lift the seller suspension instead.",
        )
        return redirect("accounts:trust_safety_dashboard")

    listing.status = LISTING_APPROVED
    if hasattr(listing, "suspended_due_to_seller"):
        listing.suspended_due_to_seller = False
    if hasattr(listing, "status_before_seller_suspension"):
        listing.status_before_seller_suspension = ""

    update_fields = ["status"]
    if hasattr(listing, "suspended_due_to_seller"):
        update_fields.append("suspended_due_to_seller")
    if hasattr(listing, "status_before_seller_suspension"):
        update_fields.append("status_before_seller_suspension")

    listing.save(update_fields=update_fields)

    ModerationNotice.objects.create(
        recipient=listing.owner,
        title="Your listing was restored",
        body=f"Your listing '{listing.title}' has been restored by Trust & Safety.",
        notice_type=ModerationNotice.NoticeType.LISTING_ACTION,
        listing=listing,
    )

    _record_event_safely(
        event_type="listing_restored",
        title=f"Listing restored: {listing.title}",
        actor=request.user,
        target_user=listing.owner,
        listing=listing,
        public_note="Listing restored by Trust & Safety.",
    )

    messages.success(request, "Listing restored successfully.")
    return redirect("accounts:trust_safety_dashboard")


@staff_member_required
@require_POST
def trust_safety_lift_seller_suspension(request, pk):
    User = get_user_model()
    seller = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=seller)

    profile.seller_suspended_until = None
    profile.seller_suspension_reason = ""
    profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    seller_hidden_listings = Listing.objects.filter(
        owner=seller,
        status=LISTING_SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension__in=[LISTING_APPROVED, LISTING_PENDING],
    )

    restored_count = 0

    for listing in seller_hidden_listings:
        previous_status = listing.status_before_seller_suspension or LISTING_APPROVED
        listing.status = previous_status
        listing.suspended_due_to_seller = False
        listing.status_before_seller_suspension = ""
        listing.save(
            update_fields=[
                "status",
                "suspended_due_to_seller",
                "status_before_seller_suspension",
            ]
        )
        restored_count += 1

    ModerationNotice.objects.create(
        recipient=seller,
        title="Your seller suspension was lifted",
        body=f"Your seller restriction has been lifted. {restored_count} seller-hidden listing(s) were restored.",
        notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
    )

    _record_event_safely(
        event_type="seller_suspension_lifted",
        title=f"Seller suspension lifted: {seller.username}",
        actor=request.user,
        target_user=seller,
        public_note="Seller suspension lifted by Trust & Safety.",
        metadata={"restored_listing_count": restored_count},
    )

    messages.success(
        request,
        f"Seller suspension lifted. Restored {restored_count} seller-hidden listing(s).",
    )
    return redirect("accounts:trust_safety_dashboard")


def _audit_data():
    now = timezone.now()

    active_profiles = list(
        UserProfile.objects.select_related("user").filter(
            seller_suspended_until__gt=now,
        )
    )
    active_suspended_users = [profile.user for profile in active_profiles]

    active_suspended_public_listings = Listing.objects.select_related("owner").filter(
        owner__in=active_suspended_users,
        status__in=[LISTING_APPROVED, LISTING_PENDING],
    ).order_by("owner__username", "id")

    seller_hidden_candidates = Listing.objects.select_related("owner").filter(
        status=LISTING_SUSPENDED,
        suspended_due_to_seller=True,
    ).order_by("owner__username", "id")

    lifted_seller_hidden_listings = []
    unknown_previous_status_listings = []

    for listing in seller_hidden_candidates:
        profile = UserProfile.objects.filter(user=listing.owner).first()

        if not _is_profile_suspended(profile):
            lifted_seller_hidden_listings.append(listing)

        if listing.status_before_seller_suspension not in [LISTING_APPROVED, LISTING_PENDING]:
            unknown_previous_status_listings.append(listing)

    return {
        "active_suspended_public_listings": active_suspended_public_listings,
        "lifted_seller_hidden_listings": lifted_seller_hidden_listings,
        "unknown_previous_status_listings": unknown_previous_status_listings,
    }


@staff_member_required
def trust_safety_audit(request):
    context = _audit_data()
    context["page_title"] = "Trust & Safety Audit"
    return render(request, "accounts/trust_safety_audit.html", context)


@staff_member_required
@require_POST
def trust_safety_fix_active_suspended_sellers(request):
    data = _audit_data()

    fixed_count = 0

    for listing in data["active_suspended_public_listings"]:
        listing.status_before_seller_suspension = listing.status
        listing.status = LISTING_SUSPENDED
        listing.suspended_due_to_seller = True
        listing.save(
            update_fields=[
                "status",
                "suspended_due_to_seller",
                "status_before_seller_suspension",
            ]
        )
        fixed_count += 1

    _record_event_safely(
        event_type="audit_repair",
        title="Audit repair: active suspended sellers",
        actor=request.user,
        internal_note=f"Moved {fixed_count} public listing(s) to seller-hidden suspended status.",
        metadata={"fixed_count": fixed_count},
    )

    messages.success(
        request,
        f"Audit repair complete. Fixed {fixed_count} listing(s) from actively suspended sellers.",
    )
    return redirect("accounts:trust_safety_audit")


@staff_member_required
@require_POST
def trust_safety_restore_lifted_seller_hidden_listings(request):
    data = _audit_data()

    restored_count = 0

    for listing in data["lifted_seller_hidden_listings"]:
        if listing.status_before_seller_suspension not in [LISTING_APPROVED, LISTING_PENDING]:
            continue

        listing.status = listing.status_before_seller_suspension
        listing.suspended_due_to_seller = False
        listing.status_before_seller_suspension = ""
        listing.save(
            update_fields=[
                "status",
                "suspended_due_to_seller",
                "status_before_seller_suspension",
            ]
        )
        restored_count += 1

    _record_event_safely(
        event_type="audit_repair",
        title="Audit repair: restored lifted seller-hidden listings",
        actor=request.user,
        internal_note=f"Restored {restored_count} seller-hidden listing(s) for sellers no longer suspended.",
        metadata={"restored_count": restored_count},
    )

    messages.success(
        request,
        f"Audit repair complete. Restored {restored_count} seller-hidden listing(s).",
    )
    return redirect("accounts:trust_safety_audit")
