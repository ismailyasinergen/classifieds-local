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


# FINAL_SELLER_REPORT_MODERATION_OVERRIDES_V2
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


def _safe_user_reporter_note(request, default):
    return request.POST.get("reporter_note", "").strip() or default


def _duration_days_from_request(request, default=7):
    try:
        days = int(request.POST.get("duration_days", default))
    except (TypeError, ValueError):
        days = default
    return max(1, min(days, 365))


def _close_user_report(report, action, request, default_reporter_note, close_status=None):
    from django.utils import timezone

    report.action_taken = action
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = _safe_user_reporter_note(request, default_reporter_note)
    report.action_taken_at = timezone.now()

    if close_status:
        report.status = close_status
        report.reviewed_at = timezone.now()

    report.save(
        update_fields=[
            "action_taken",
            "admin_note",
            "reporter_note",
            "action_taken_at",
            "status",
            "reviewed_at",
        ]
    )


@login_required
def user_report_create(request, pk):
    from django.contrib.auth import get_user_model
    from listings.models import Listing
    from .models import UserReport

    User = get_user_model()
    reported_user = get_object_or_404(User, pk=pk)

    if reported_user == request.user:
        messages.warning(request, "You cannot report yourself.")
        return redirect("pages:home")

    source_listing_id = request.GET.get("listing") or request.POST.get("source_listing")
    source_listing = None

    if source_listing_id:
        source_listing = Listing.objects.filter(pk=source_listing_id, owner=reported_user).first()

    existing_report = UserReport.objects.filter(
        reported_user=reported_user,
        reporter=request.user,
        status=UserReport.Status.PENDING,
    ).order_by("-created_at").first()

    if existing_report:
        messages.info(request, "You already have a pending seller report for this seller.")
        return redirect("accounts:my_user_reports")

    if request.method == "POST":
        selected_reasons = request.POST.getlist("reasons")
        details = request.POST.get("details", "").strip()

        valid_reasons = {choice[0] for choice in UserReport.Reason.choices}
        selected_reasons = [reason for reason in selected_reasons if reason in valid_reasons]

        if not selected_reasons:
            messages.warning(request, "Please choose at least one seller report reason.")
            return redirect("accounts:user_report", pk=reported_user.pk)

        UserReport.objects.create(
            reported_user=reported_user,
            reporter=request.user,
            source_listing=source_listing,
            reasons=selected_reasons,
            details=details,
            status=UserReport.Status.PENDING,
        )

        messages.success(request, "Seller report submitted. Admin will review it.")
        return redirect("accounts:my_user_reports")

    return render(
        request,
        "accounts/user_report_form.html",
        {
            "reported_user": reported_user,
            "source_listing": source_listing,
            "reason_choices": UserReport.Reason.choices,
            "page_title": "Report Seller",
        },
    )


# FINAL_SELLER_REPORT_NOTICE_ACTIONS_V1
def _create_user_moderation_notice(recipient, title, body, notice_type="report_update", listing=None, user_report=None):
    from .models import ModerationNotice

    if not recipient:
        return None

    return ModerationNotice.objects.create(
        recipient=recipient,
        title=title,
        body=body,
        notice_type=notice_type,
        listing=listing,
        user_report=user_report,
    )


@staff_member_required
@require_POST
def user_report_review(request, pk):
    from django.utils import timezone
    from .models import UserReport

    report = get_object_or_404(UserReport.objects.select_related("reporter", "reported_user", "source_listing"), pk=pk)

    report.status = UserReport.Status.REVIEWED
    report.action_taken = UserReport.Action.REVIEWED
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your seller report. Thank you for helping keep the marketplace safe."
    report.reviewed_at = timezone.now()
    report.action_taken_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at", "action_taken_at"])

    _create_user_moderation_notice(
        recipient=report.reporter,
        title="Your seller report was reviewed",
        body=report.reporter_note,
        notice_type="report_update",
        listing=report.source_listing,
        user_report=report,
    )

    messages.success(request, "Seller report marked as reviewed and reporter notified.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_dismiss(request, pk):
    from django.utils import timezone
    from .models import UserReport

    report = get_object_or_404(UserReport.objects.select_related("reporter", "reported_user", "source_listing"), pk=pk)

    report.status = UserReport.Status.DISMISSED
    report.action_taken = UserReport.Action.DISMISSED
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your seller report and did not take action at this time."
    report.reviewed_at = timezone.now()
    report.action_taken_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at", "action_taken_at"])

    _create_user_moderation_notice(
        recipient=report.reporter,
        title="Your seller report was reviewed",
        body=report.reporter_note,
        notice_type="report_update",
        listing=report.source_listing,
        user_report=report,
    )

    messages.success(request, "Seller report dismissed and reporter notified.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_warn_seller(request, pk):
    from django.utils import timezone
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reporter", "reported_user", "source_listing"), pk=pk)

    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)
    profile.seller_warning_count = (profile.seller_warning_count or 0) + 1
    profile.save(update_fields=["seller_warning_count"])

    report.status = UserReport.Status.REVIEWED
    report.action_taken = UserReport.Action.WARNED_SELLER
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and took action with the seller."
    report.reviewed_at = timezone.now()
    report.action_taken_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at", "action_taken_at"])

    _create_user_moderation_notice(report.reporter, "Action was taken on your seller report", report.reporter_note, "report_update", report.source_listing, report)
    _create_user_moderation_notice(
        report.reported_user,
        "Your seller account received a warning",
        "Your account received a warning after moderation review. Please follow marketplace rules to avoid restrictions.",
        "seller_action",
        report.source_listing,
        report,
    )

    messages.success(request, "Seller warned. Reporter and seller notified.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_remove_verification(request, pk):
    from django.utils import timezone
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reporter", "reported_user", "source_listing"), pk=pk)

    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)
    profile.verification_status = UserProfile.VerificationStatus.REJECTED
    profile.verification_note = request.POST.get("admin_note", "").strip() or "Verification removed after moderation review."
    profile.save(update_fields=["verification_status", "verification_note"])

    report.status = UserReport.Status.REVIEWED
    report.action_taken = UserReport.Action.REMOVED_VERIFICATION
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and took action on the seller account."
    report.reviewed_at = timezone.now()
    report.action_taken_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at", "action_taken_at"])

    _create_user_moderation_notice(report.reporter, "Action was taken on your seller report", report.reporter_note, "report_update", report.source_listing, report)
    _create_user_moderation_notice(
        report.reported_user,
        "Your seller verification was removed",
        "Your seller verification was removed after moderation review. You may request verification again if eligible.",
        "seller_action",
        report.source_listing,
        report,
    )

    messages.success(request, "Seller verification removed. Reporter and seller notified.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_archive_seller_listings(request, pk):
    from django.utils import timezone
    from listings.models import Listing
    from .models import UserReport

    report = get_object_or_404(UserReport.objects.select_related("reporter", "reported_user", "source_listing"), pk=pk)

    count = Listing.objects.filter(
        owner=report.reported_user,
        status__in=[Listing.Status.APPROVED, Listing.Status.PENDING, Listing.Status.SUSPENDED],
    ).update(status=Listing.Status.ARCHIVED)

    report.status = UserReport.Status.REVIEWED
    report.action_taken = UserReport.Action.ARCHIVED_LISTINGS
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and took action on this seller's listings."
    report.reviewed_at = timezone.now()
    report.action_taken_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at", "action_taken_at"])

    _create_user_moderation_notice(report.reporter, "Action was taken on your seller report", report.reporter_note, "report_update", report.source_listing, report)
    _create_user_moderation_notice(
        report.reported_user,
        "Your listings were removed after moderation review",
        f"{count} of your active listing(s) were removed after moderation review.",
        "seller_action",
        report.source_listing,
        report,
    )

    messages.success(request, f"Archived {count} seller listing(s). Reporter and seller notified.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_block_messaging(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reporter", "reported_user", "source_listing"), pk=pk)

    days = _duration_days_from_request(request, default=7)

    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)
    profile.seller_messaging_blocked_until = timezone.now() + timedelta(days=days)
    profile.seller_messaging_block_reason = request.POST.get("admin_note", "").strip() or "Seller messaging blocked from report queue."
    profile.save(update_fields=["seller_messaging_blocked_until", "seller_messaging_block_reason"])

    report.status = UserReport.Status.REVIEWED
    report.action_taken = UserReport.Action.BLOCKED_MESSAGING
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and restricted this seller."
    report.reviewed_at = timezone.now()
    report.action_taken_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at", "action_taken_at"])

    _create_user_moderation_notice(report.reporter, "Action was taken on your seller report", report.reporter_note, "report_update", report.source_listing, report)
    _create_user_moderation_notice(
        report.reported_user,
        "Your messaging access was temporarily restricted",
        f"Your seller messaging access was temporarily restricted for {days} day(s) after moderation review.",
        "seller_action",
        report.source_listing,
        report,
    )

    messages.success(request, f"Seller messaging block flag set for {days} day(s). Reporter and seller notified.")
    return redirect("accounts:user_report_queue")

# SELLER_SUSPENSION_SUSPEND_ACTIVE_LISTINGS_V1


# SAFE_SELLER_SUSPENSION_TRACKING_FINAL_V1
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST


@staff_member_required
@require_POST
def user_report_suspend_seller(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    from listings.models import Listing
    from .models import ModerationNotice, UserProfile, UserReport

    report = get_object_or_404(
        UserReport.objects.select_related("reported_user", "reporter", "source_listing"),
        pk=pk,
    )

    seller = report.reported_user
    profile, _ = UserProfile.objects.get_or_create(user=seller)

    raw_days = (
        request.POST.get("duration_days")
        or request.POST.get("suspension_days")
        or request.POST.get("days")
        or "7"
    )

    try:
        days = max(1, min(int(raw_days), 365))
    except (TypeError, ValueError):
        days = 7

    reporter_note = (
        request.POST.get("reporter_note")
        or request.POST.get("message_to_reporter")
        or "We reviewed your report and restricted this seller."
    )

    internal_note = (
        request.POST.get("admin_note")
        or request.POST.get("note")
        or "Restricted after moderation review."
    )

    suspended_until = timezone.now() + timedelta(days=days)

    profile.seller_suspended_until = suspended_until
    profile.seller_suspension_reason = internal_note
    profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    approved_count = Listing.objects.filter(
        owner=seller,
        status=Listing.Status.APPROVED,
    ).update(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.APPROVED,
    )

    pending_count = Listing.objects.filter(
        owner=seller,
        status=Listing.Status.PENDING,
    ).update(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.PENDING,
    )

    hidden_count = approved_count + pending_count

    report.status = UserReport.Status.REVIEWED
    report.action_taken = "suspended_seller"
    report.reporter_note = reporter_note
    report.action_taken_at = timezone.now()
    report.admin_note = internal_note
    report.save()

    ModerationNotice.objects.create(
        recipient=report.reporter,
        title="Seller report reviewed",
        body=reporter_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        user_report=report,
        listing=report.source_listing,
    )

    ModerationNotice.objects.create(
        recipient=seller,
        title="Your seller account was temporarily suspended",
        body=(
            f"Your seller account has been temporarily suspended until "
            f"{suspended_until.strftime('%b %d, %Y %H:%M')}. "
            f"{hidden_count} active listing(s) were temporarily hidden during this restriction. "
            "Listings already suspended by listing-level moderation were not changed."
        ),
        notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
        user_report=report,
        listing=report.source_listing,
    )

    messages.success(
        request,
        f"Seller suspended for {days} day(s). {hidden_count} active listing(s) were hidden because of seller suspension.",
    )

    return redirect("accounts:user_report_queue")
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


# TRUST_SAFETY_USER_REPORT_EVENT_WIRING_V2
_TrustSafetyOriginalUserReportReview = user_report_review
@staff_member_required
@require_POST
def user_report_review(request, pk):
    response = _TrustSafetyOriginalUserReportReview(request, pk)

    try:
        from .models import UserReport
        from .services.report_trust_safety_events import record_user_report_reviewed

        report = UserReport.objects.select_related("reported_user", "reporter", "source_listing").get(pk=pk)
        record_user_report_reviewed(report, actor=request.user)
    except Exception:
        pass

    return response


_TrustSafetyOriginalUserReportDismiss = user_report_dismiss
@staff_member_required
@require_POST
def user_report_dismiss(request, pk):
    response = _TrustSafetyOriginalUserReportDismiss(request, pk)

    try:
        from .models import UserReport
        from .services.report_trust_safety_events import record_user_report_reviewed

        report = UserReport.objects.select_related("reported_user", "reporter", "source_listing").get(pk=pk)
        record_user_report_reviewed(report, actor=request.user, dismissed=True)
    except Exception:
        pass

    return response


_TrustSafetyOriginalUserReportWarnSeller = user_report_warn_seller
@staff_member_required
@require_POST
def user_report_warn_seller(request, pk):
    response = _TrustSafetyOriginalUserReportWarnSeller(request, pk)

    try:
        from .models import UserReport
        from .services.report_trust_safety_events import record_user_report_warning

        report = UserReport.objects.select_related("reported_user", "reporter", "source_listing").get(pk=pk)
        record_user_report_warning(report, actor=request.user)
    except Exception:
        pass

    return response


_TrustSafetyOriginalUserReportSuspendSeller = user_report_suspend_seller
@staff_member_required
@require_POST
def user_report_suspend_seller(request, pk):
    response = _TrustSafetyOriginalUserReportSuspendSeller(request, pk)

    try:
        from .models import UserReport
        from .services.report_trust_safety_events import record_user_report_suspension

        report = UserReport.objects.select_related("reported_user", "reporter", "source_listing").get(pk=pk)
        record_user_report_suspension(report, actor=request.user)
    except Exception:
        pass

    return response


_TrustSafetyOriginalUserReportRemoveVerification = user_report_remove_verification
@staff_member_required
@require_POST
def user_report_remove_verification(request, pk):
    response = _TrustSafetyOriginalUserReportRemoveVerification(request, pk)

    try:
        from .models import UserReport
        from .services.report_trust_safety_events import record_user_report_verification_removed

        report = UserReport.objects.select_related("reported_user", "reporter", "source_listing").get(pk=pk)
        record_user_report_verification_removed(report, actor=request.user)
    except Exception:
        pass

    return response


_TrustSafetyOriginalUserReportArchiveSellerListings = user_report_archive_seller_listings
@staff_member_required
@require_POST
def user_report_archive_seller_listings(request, pk):
    response = _TrustSafetyOriginalUserReportArchiveSellerListings(request, pk)

    try:
        from .models import UserReport
        from .services.report_trust_safety_events import record_user_report_listings_archived

        report = UserReport.objects.select_related("reported_user", "reporter", "source_listing").get(pk=pk)
        record_user_report_listings_archived(report, actor=request.user)
    except Exception:
        pass

    return response


_TrustSafetyOriginalUserReportBlockMessaging = user_report_block_messaging
@staff_member_required
@require_POST
def user_report_block_messaging(request, pk):
    response = _TrustSafetyOriginalUserReportBlockMessaging(request, pk)

    try:
        from .models import UserReport
        from .services.report_trust_safety_events import record_user_report_messaging_blocked

        report = UserReport.objects.select_related("reported_user", "reporter", "source_listing").get(pk=pk)
        record_user_report_messaging_blocked(report, actor=request.user)
    except Exception:
        pass

    return response
