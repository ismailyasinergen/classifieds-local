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
        source_listing = Listing.objects.filter(
            pk=source_listing_id,
            owner=reported_user,
        ).first()

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


@login_required
def my_user_reports(request):
    from .models import UserReport

    reports = UserReport.objects.select_related(
        "reported_user",
        "source_listing",
    ).filter(
        reporter=request.user,
    ).order_by("-created_at")

    return render(
        request,
        "accounts/my_user_reports.html",
        {
            "reports": reports,
            "page_title": "My Seller Reports",
        },
    )


@staff_member_required
def user_report_queue(request):
    from django.db.models import Q
    from .models import UserReport

    status_filter = request.GET.get("status", "").strip()
    reason_filter = request.GET.get("reason", "").strip()
    q = request.GET.get("q", "").strip()

    reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    )

    valid_statuses = {
        UserReport.Status.PENDING,
        UserReport.Status.REVIEWED,
        UserReport.Status.DISMISSED,
    }

    valid_reasons = {choice[0] for choice in UserReport.Reason.choices}

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    if reason_filter in valid_reasons:
        reports = reports.filter(reasons__contains=[reason_filter])

    if q:
        reports = reports.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
        )

    all_reports = UserReport.objects.all()

    counts = {
        "all": all_reports.count(),
        "pending": all_reports.filter(status=UserReport.Status.PENDING).count(),
        "reviewed": all_reports.filter(status=UserReport.Status.REVIEWED).count(),
        "dismissed": all_reports.filter(status=UserReport.Status.DISMISSED).count(),
    }

    return render(
        request,
        "accounts/user_report_queue.html",
        {
            "reports": reports,
            "counts": counts,
            "status_filter": status_filter,
            "reason_filter": reason_filter,
            "reason_choices": UserReport.Reason.choices,
            "q": q,
            "page_title": "Seller Reports",
        },
    )


@staff_member_required
@require_POST
def user_report_review(request, pk):
    from django.utils import timezone
    from .models import UserReport

    report = get_object_or_404(UserReport, pk=pk)
    report.status = UserReport.Status.REVIEWED
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "admin_note", "reviewed_at"])

    messages.success(request, "Seller report marked as reviewed.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_dismiss(request, pk):
    from django.utils import timezone
    from .models import UserReport

    report = get_object_or_404(UserReport, pk=pk)
    report.status = UserReport.Status.DISMISSED
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reviewed_at = timezone.now()
    report.save(update_fields=["status", "admin_note", "reviewed_at"])

    messages.success(request, "Seller report dismissed.")
    return redirect("accounts:user_report_queue")


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


@login_required
def my_user_reports(request):
    from .models import UserReport

    reports = UserReport.objects.select_related(
        "reported_user",
        "source_listing",
    ).filter(
        reporter=request.user,
    ).order_by("-created_at")

    return render(
        request,
        "accounts/my_user_reports.html",
        {
            "reports": reports,
            "page_title": "My Seller Reports",
        },
    )


@staff_member_required
def user_report_queue(request):
    from .models import UserReport

    status_filter = request.GET.get("status", "").strip()
    reason_filter = request.GET.get("reason", "").strip()
    q = request.GET.get("q", "").strip()

    reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    )

    valid_statuses = {
        UserReport.Status.PENDING,
        UserReport.Status.REVIEWED,
        UserReport.Status.DISMISSED,
    }
    valid_reasons = {choice[0] for choice in UserReport.Reason.choices}

    if status_filter in valid_statuses:
        reports = reports.filter(status=status_filter)

    if reason_filter in valid_reasons:
        reports = reports.filter(reasons__contains=[reason_filter])

    if q:
        reports = reports.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
        )

    all_reports = UserReport.objects.all()

    counts = {
        "all": all_reports.count(),
        "pending": all_reports.filter(status=UserReport.Status.PENDING).count(),
        "reviewed": all_reports.filter(status=UserReport.Status.REVIEWED).count(),
        "dismissed": all_reports.filter(status=UserReport.Status.DISMISSED).count(),
    }

    return render(
        request,
        "accounts/user_report_queue.html",
        {
            "reports": reports,
            "counts": counts,
            "status_filter": status_filter,
            "reason_filter": reason_filter,
            "reason_choices": UserReport.Reason.choices,
            "q": q,
            "page_title": "Seller Reports",
        },
    )


@staff_member_required
@require_POST
def user_report_review(request, pk):
    from .models import UserReport

    report = get_object_or_404(UserReport, pk=pk)
    _close_user_report(
        report,
        UserReport.Action.REVIEWED,
        request,
        "We reviewed your seller report. Thank you for helping keep the marketplace safe.",
        UserReport.Status.REVIEWED,
    )

    messages.success(request, "Seller report marked as reviewed.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_dismiss(request, pk):
    from .models import UserReport

    report = get_object_or_404(UserReport, pk=pk)
    _close_user_report(
        report,
        UserReport.Action.DISMISSED,
        request,
        "We reviewed your seller report and did not take action at this time.",
        UserReport.Status.DISMISSED,
    )

    messages.success(request, "Seller report dismissed.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_warn_seller(request, pk):
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reported_user"), pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)
    profile.seller_warning_count = (profile.seller_warning_count or 0) + 1
    profile.save(update_fields=["seller_warning_count"])

    _close_user_report(
        report,
        UserReport.Action.WARNED_SELLER,
        request,
        "We reviewed your report and took action with the seller.",
        UserReport.Status.REVIEWED,
    )

    messages.success(request, "Seller warned and report marked as reviewed.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_suspend_seller(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reported_user"), pk=pk)
    days = _duration_days_from_request(request, default=7)

    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)
    profile.seller_suspended_until = timezone.now() + timedelta(days=days)
    profile.seller_suspension_reason = request.POST.get("admin_note", "").strip() or "Seller suspended from report queue."
    profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    _close_user_report(
        report,
        UserReport.Action.SUSPENDED_SELLER,
        request,
        "We reviewed your report and restricted this seller.",
        UserReport.Status.REVIEWED,
    )

    messages.success(request, f"Seller suspended for {days} day(s).")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_remove_verification(request, pk):
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reported_user"), pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)

    profile.verification_status = UserProfile.VerificationStatus.REJECTED
    profile.verification_note = request.POST.get("admin_note", "").strip() or "Verification removed after moderation review."
    profile.save(update_fields=["verification_status", "verification_note"])

    _close_user_report(
        report,
        UserReport.Action.REMOVED_VERIFICATION,
        request,
        "We reviewed your report and took action on the seller account.",
        UserReport.Status.REVIEWED,
    )

    messages.success(request, "Seller verification removed.")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_archive_seller_listings(request, pk):
    from listings.models import Listing
    from .models import UserReport

    report = get_object_or_404(UserReport.objects.select_related("reported_user"), pk=pk)

    count = Listing.objects.filter(
        owner=report.reported_user,
        status__in=[
            Listing.Status.APPROVED,
            Listing.Status.PENDING,
            Listing.Status.SUSPENDED,
        ],
    ).update(status=Listing.Status.ARCHIVED)

    _close_user_report(
        report,
        UserReport.Action.ARCHIVED_LISTINGS,
        request,
        "We reviewed your report and took action on this seller's listings.",
        UserReport.Status.REVIEWED,
    )

    messages.success(request, f"Archived {count} seller listing(s).")
    return redirect("accounts:user_report_queue")


@staff_member_required
@require_POST
def user_report_block_messaging(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reported_user"), pk=pk)
    days = _duration_days_from_request(request, default=7)

    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)
    profile.seller_messaging_blocked_until = timezone.now() + timedelta(days=days)
    profile.seller_messaging_block_reason = request.POST.get("admin_note", "").strip() or "Seller messaging blocked from report queue."
    profile.save(update_fields=["seller_messaging_blocked_until", "seller_messaging_block_reason"])

    _close_user_report(
        report,
        UserReport.Action.BLOCKED_MESSAGING,
        request,
        "We reviewed your report and restricted this seller.",
        UserReport.Status.REVIEWED,
    )

    messages.success(request, f"Seller messaging block flag set for {days} day(s).")
    return redirect("accounts:user_report_queue")


# FINAL_MODERATION_NOTICE_V1
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST


@login_required
def moderation_notices(request):
    from .models import ModerationNotice

    notices = ModerationNotice.objects.filter(
        recipient=request.user,
    ).select_related(
        "listing",
        "listing_report",
        "user_report",
    )

    return render(
        request,
        "accounts/moderation_notices.html",
        {
            "notices": notices,
            "page_title": "Moderation Notices",
        },
    )


@login_required
@require_POST
def moderation_notice_mark_read(request, pk):
    from .models import ModerationNotice

    notice = get_object_or_404(
        ModerationNotice,
        pk=pk,
        recipient=request.user,
    )
    notice.is_read = True
    notice.save(update_fields=["is_read"])

    return redirect("accounts:moderation_notices")


@login_required
@require_POST
def moderation_notices_mark_all_read(request):
    from .models import ModerationNotice

    ModerationNotice.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    return redirect("accounts:moderation_notices")


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
def user_report_suspend_seller(request, pk):
    from datetime import timedelta
    from django.utils import timezone
    from .models import UserProfile, UserReport

    report = get_object_or_404(UserReport.objects.select_related("reporter", "reported_user", "source_listing"), pk=pk)

    days = _duration_days_from_request(request, default=7)

    profile, _ = UserProfile.objects.get_or_create(user=report.reported_user)
    profile.seller_suspended_until = timezone.now() + timedelta(days=days)
    profile.seller_suspension_reason = request.POST.get("admin_note", "").strip() or "Seller suspended from report queue."
    profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    report.status = UserReport.Status.REVIEWED
    report.action_taken = UserReport.Action.SUSPENDED_SELLER
    report.admin_note = request.POST.get("admin_note", "").strip()
    report.reporter_note = request.POST.get("reporter_note", "").strip() or "We reviewed your report and restricted this seller."
    report.reviewed_at = timezone.now()
    report.action_taken_at = timezone.now()
    report.save(update_fields=["status", "action_taken", "admin_note", "reporter_note", "reviewed_at", "action_taken_at"])

    _create_user_moderation_notice(report.reporter, "Action was taken on your seller report", report.reporter_note, "report_update", report.source_listing, report)
    _create_user_moderation_notice(
        report.reported_user,
        "Your seller account was temporarily restricted",
        f"Your seller account has been temporarily restricted for {days} day(s) after moderation review. During this time, you may not post or edit listings.",
        "seller_action",
        report.source_listing,
        report,
    )

    messages.success(request, f"Seller suspended for {days} day(s). Reporter and seller notified.")
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


# TRUST_SAFETY_DASHBOARD_V1
@staff_member_required
def trust_safety_dashboard(request):
    from django.utils import timezone
    from listings.models import Listing, ListingReport
    from .models import UserProfile, UserReport

    now = timezone.now()

    pending_listing_reports = ListingReport.objects.filter(
        status=ListingReport.Status.PENDING,
    )

    pending_seller_reports = UserReport.objects.filter(
        status=UserReport.Status.PENDING,
    )

    suspended_listings = Listing.objects.filter(
        status=Listing.Status.SUSPENDED,
    )

    suspended_sellers = UserProfile.objects.select_related("user").filter(
        seller_suspended_until__gt=now,
    )

    latest_listing_reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    ).order_by("-created_at")[:5]

    latest_seller_reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).order_by("-created_at")[:5]

    return render(
        request,
        "accounts/trust_safety_dashboard.html",
        {
            "pending_listing_reports_count": pending_listing_reports.count(),
            "pending_seller_reports_count": pending_seller_reports.count(),
            "suspended_listings_count": suspended_listings.count(),
            "suspended_sellers_count": suspended_sellers.count(),
            "latest_listing_reports": latest_listing_reports,
            "latest_seller_reports": latest_seller_reports,
            "suspended_sellers": suspended_sellers[:5],
            "page_title": "Trust & Safety",
        },
    )


# TRUST_SAFETY_RESTORE_ACTIONS_V1
@staff_member_required
@require_POST
def trust_safety_restore_listing(request, pk):
    from listings.models import Listing
    from .models import ModerationNotice

    listing = get_object_or_404(Listing.objects.select_related("owner"), pk=pk)

    if listing.status != Listing.Status.SUSPENDED:
        messages.warning(request, "Only suspended listings can be restored from here.")
        return redirect("accounts:trust_safety_dashboard")

    listing.status = Listing.Status.APPROVED
    listing.save(update_fields=["status"])

    ModerationNotice.objects.create(
        recipient=listing.owner,
        title="Your listing was restored",
        body=f'Your listing "{listing.title}" has been restored after moderation review.',
        notice_type=ModerationNotice.NoticeType.LISTING_ACTION,
        listing=listing,
    )

    messages.success(request, "Listing restored and owner notified.")
    return redirect("accounts:trust_safety_dashboard")


@staff_member_required
@require_POST
def trust_safety_lift_seller_suspension(request, pk):
    from .models import ModerationNotice, UserProfile

    profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)

    profile.seller_suspended_until = None
    profile.seller_suspension_reason = ""
    profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    ModerationNotice.objects.create(
        recipient=profile.user,
        title="Your seller restriction was lifted",
        body="Your seller account restriction has been lifted after moderation review. You may post and edit listings again.",
        notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
    )

    messages.success(request, "Seller suspension lifted and seller notified.")
    return redirect("accounts:trust_safety_dashboard")


@staff_member_required
def trust_safety_dashboard(request):
    from django.utils import timezone
    from listings.models import Listing, ListingReport
    from .models import UserProfile, UserReport

    now = timezone.now()

    pending_listing_reports = ListingReport.objects.filter(
        status=ListingReport.Status.PENDING,
    )

    pending_seller_reports = UserReport.objects.filter(
        status=UserReport.Status.PENDING,
    )

    suspended_listings = Listing.objects.select_related("owner").filter(
        status=Listing.Status.SUSPENDED,
    ).order_by("-created_at")

    suspended_sellers = UserProfile.objects.select_related("user").filter(
        seller_suspended_until__gt=now,
    ).order_by("seller_suspended_until")

    latest_listing_reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    ).order_by("-created_at")[:5]

    latest_seller_reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).order_by("-created_at")[:5]

    return render(
        request,
        "accounts/trust_safety_dashboard.html",
        {
            "pending_listing_reports_count": pending_listing_reports.count(),
            "pending_seller_reports_count": pending_seller_reports.count(),
            "suspended_listings_count": suspended_listings.count(),
            "suspended_sellers_count": suspended_sellers.count(),
            "suspended_listings": suspended_listings[:10],
            "suspended_sellers": suspended_sellers[:10],
            "latest_listing_reports": latest_listing_reports,
            "latest_seller_reports": latest_seller_reports,
            "page_title": "Trust & Safety",
        },
    )


# SELLER_SUSPENSION_SUSPEND_ACTIVE_LISTINGS_V1
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
        or ""
    )

    suspended_until = timezone.now() + timedelta(days=days)

    profile.seller_suspended_until = suspended_until
    profile.seller_suspension_reason = internal_note or "Restricted after moderation review."
    profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    suspended_listing_count = Listing.objects.filter(
        owner=seller,
        status__in=[
            Listing.Status.APPROVED,
            Listing.Status.PENDING,
        ],
    ).update(status=Listing.Status.SUSPENDED)

    report.status = UserReport.Status.REVIEWED
    report.action_taken = "suspended_seller"
    report.reporter_note = reporter_note
    report.action_taken_at = timezone.now()
    if internal_note:
        report.admin_note = internal_note
    report.save(
        update_fields=[
            "status",
            "action_taken",
            "reporter_note",
            "action_taken_at",
            "admin_note",
            "updated_at",
        ]
    )

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
            f"{suspended_listing_count} active listing(s) were temporarily hidden during this restriction."
        ),
        notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
        user_report=report,
        listing=report.source_listing,
    )

    messages.success(
        request,
        f"Seller suspended for {days} day(s). {suspended_listing_count} active listing(s) were temporarily suspended.",
    )

    return redirect("accounts:user_report_queue")


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


@staff_member_required
@require_POST
def trust_safety_lift_seller_suspension(request, pk):
    from listings.models import Listing
    from .models import ModerationNotice, UserProfile

    profile = get_object_or_404(UserProfile.objects.select_related("user"), pk=pk)
    seller = profile.user

    restored_approved_count = Listing.objects.filter(
        owner=seller,
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.APPROVED,
    ).update(
        status=Listing.Status.APPROVED,
        suspended_due_to_seller=False,
        status_before_seller_suspension="",
    )

    restored_pending_count = Listing.objects.filter(
        owner=seller,
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.PENDING,
    ).update(
        status=Listing.Status.PENDING,
        suspended_due_to_seller=False,
        status_before_seller_suspension="",
    )

    restored_count = restored_approved_count + restored_pending_count

    # Safety cleanup: if any old seller-hidden rows have unknown previous status,
    # do not restore them blindly. They stay suspended until reviewed manually.
    unknown_count = Listing.objects.filter(
        owner=seller,
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension="",
    ).count()

    profile.seller_suspended_until = None
    profile.seller_suspension_reason = ""
    profile.save(update_fields=["seller_suspended_until", "seller_suspension_reason"])

    notice_body = (
        "Your seller account restriction has been lifted after moderation review. "
        f"{restored_count} listing(s) hidden because of the seller suspension were restored."
    )

    if unknown_count:
        notice_body += (
            f" {unknown_count} suspended listing(s) need manual admin review because their previous status was not known."
        )

    ModerationNotice.objects.create(
        recipient=seller,
        title="Your seller restriction was lifted",
        body=notice_body,
        notice_type=ModerationNotice.NoticeType.SELLER_ACTION,
    )

    messages.success(
        request,
        f"Seller suspension lifted. {restored_count} seller-suspension listing(s) restored. "
        f"{unknown_count} unknown listing(s) left suspended for manual review.",
    )

    return redirect("accounts:trust_safety_dashboard")


@staff_member_required
@require_POST
def trust_safety_restore_listing(request, pk):
    from listings.models import Listing
    from .models import ModerationNotice

    listing = get_object_or_404(Listing.objects.select_related("owner"), pk=pk)

    if listing.status != Listing.Status.SUSPENDED:
        messages.warning(request, "Only suspended listings can be restored from here.")
        return redirect("accounts:trust_safety_dashboard")

    if listing.suspended_due_to_seller:
        messages.warning(
            request,
            "This listing was hidden because of a seller suspension. Lift the seller suspension to restore seller-hidden listings safely.",
        )
        return redirect("accounts:trust_safety_dashboard")

    listing.status = Listing.Status.APPROVED
    listing.suspended_due_to_seller = False
    listing.status_before_seller_suspension = ""
    listing.save(
        update_fields=[
            "status",
            "suspended_due_to_seller",
            "status_before_seller_suspension",
        ]
    )

    ModerationNotice.objects.create(
        recipient=listing.owner,
        title="Your listing was restored",
        body=f'Your listing "{listing.title}" has been restored after moderation review.',
        notice_type=ModerationNotice.NoticeType.LISTING_ACTION,
        listing=listing,
    )

    messages.success(request, "Listing restored and owner notified.")
    return redirect("accounts:trust_safety_dashboard")


@staff_member_required
def trust_safety_dashboard(request):
    from django.utils import timezone
    from listings.models import Listing, ListingReport
    from .models import UserProfile, UserReport

    now = timezone.now()

    pending_listing_reports = ListingReport.objects.filter(
        status=ListingReport.Status.PENDING,
    )

    pending_seller_reports = UserReport.objects.filter(
        status=UserReport.Status.PENDING,
    )

    suspended_listings = Listing.objects.select_related("owner").filter(
        status=Listing.Status.SUSPENDED,
    ).order_by("-created_at")

    suspended_sellers = UserProfile.objects.select_related("user").filter(
        seller_suspended_until__gt=now,
    ).order_by("seller_suspended_until")

    latest_listing_reports = ListingReport.objects.select_related(
        "listing",
        "reporter",
        "listing__owner",
    ).order_by("-created_at")[:5]

    latest_seller_reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).order_by("-created_at")[:5]

    return render(
        request,
        "accounts/trust_safety_dashboard.html",
        {
            "pending_listing_reports_count": pending_listing_reports.count(),
            "pending_seller_reports_count": pending_seller_reports.count(),
            "suspended_listings_count": suspended_listings.count(),
            "suspended_sellers_count": suspended_sellers.count(),
            "suspended_listings": suspended_listings[:20],
            "suspended_sellers": suspended_sellers[:20],
            "latest_listing_reports": latest_listing_reports,
            "latest_seller_reports": latest_seller_reports,
            "page_title": "Trust & Safety",
        },
    )


# TRUST_SAFETY_AUDIT_UI_V1
@staff_member_required
def trust_safety_audit(request):
    from accounts.models import UserProfile
    from listings.models import Listing

    suspended_profiles = [
        profile
        for profile in UserProfile.objects.select_related("user")
        if profile.is_seller_suspended
    ]
    suspended_users = [profile.user for profile in suspended_profiles]

    active_listings_for_suspended_sellers = Listing.objects.select_related("owner").filter(
        owner__in=suspended_users,
        status__in=[Listing.Status.APPROVED, Listing.Status.PENDING],
    ).order_by("owner__username", "id")

    seller_hidden_for_lifted_sellers = [
        listing
        for listing in Listing.objects.select_related("owner").filter(
            status=Listing.Status.SUSPENDED,
            suspended_due_to_seller=True,
        ).order_by("owner__username", "id")
        if not getattr(listing.owner.profile, "is_seller_suspended", False)
    ]

    seller_hidden_unknown_previous_status = Listing.objects.select_related("owner").filter(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
    ).exclude(
        status_before_seller_suspension__in=[
            Listing.Status.APPROVED,
            Listing.Status.PENDING,
        ]
    ).order_by("owner__username", "id")

    listing_level_suspended = Listing.objects.select_related("owner").filter(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=False,
    ).order_by("owner__username", "id")

    seller_hidden_suspended = Listing.objects.select_related("owner").filter(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
    ).order_by("owner__username", "id")

    warning_count = (
        active_listings_for_suspended_sellers.count()
        + len(seller_hidden_for_lifted_sellers)
        + seller_hidden_unknown_previous_status.count()
    )

    return render(
        request,
        "accounts/trust_safety_audit.html",
        {
            "active_listings_for_suspended_sellers": active_listings_for_suspended_sellers,
            "seller_hidden_for_lifted_sellers": seller_hidden_for_lifted_sellers,
            "seller_hidden_unknown_previous_status": seller_hidden_unknown_previous_status,
            "listing_level_suspended": listing_level_suspended,
            "seller_hidden_suspended": seller_hidden_suspended,
            "warning_count": warning_count,
            "page_title": "Trust & Safety Audit",
        },
    )


@staff_member_required
@require_POST
def trust_safety_fix_active_suspended_sellers(request):
    from accounts.models import UserProfile
    from listings.models import Listing

    suspended_profiles = [
        profile
        for profile in UserProfile.objects.select_related("user")
        if profile.is_seller_suspended
    ]
    suspended_users = [profile.user for profile in suspended_profiles]

    approved_count = Listing.objects.filter(
        owner__in=suspended_users,
        status=Listing.Status.APPROVED,
    ).update(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.APPROVED,
    )

    pending_count = Listing.objects.filter(
        owner__in=suspended_users,
        status=Listing.Status.PENDING,
    ).update(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.PENDING,
    )

    messages.success(
        request,
        f"Fixed seller suspension visibility: {approved_count + pending_count} active listing(s) hidden safely.",
    )
    return redirect("accounts:trust_safety_audit")


@staff_member_required
@require_POST
def trust_safety_restore_lifted_seller_hidden_listings(request):
    from accounts.models import UserProfile
    from listings.models import Listing

    active_suspended_users = [
        profile.user
        for profile in UserProfile.objects.select_related("user")
        if profile.is_seller_suspended
    ]

    restored_approved = Listing.objects.filter(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.APPROVED,
    ).exclude(
        owner__in=active_suspended_users,
    ).update(
        status=Listing.Status.APPROVED,
        suspended_due_to_seller=False,
        status_before_seller_suspension="",
    )

    restored_pending = Listing.objects.filter(
        status=Listing.Status.SUSPENDED,
        suspended_due_to_seller=True,
        status_before_seller_suspension=Listing.Status.PENDING,
    ).exclude(
        owner__in=active_suspended_users,
    ).update(
        status=Listing.Status.PENDING,
        suspended_due_to_seller=False,
        status_before_seller_suspension="",
    )

    messages.success(
        request,
        f"Restored {restored_approved + restored_pending} seller-hidden listing(s) for lifted sellers. Listing-level suspended listings were not touched.",
    )
    return redirect("accounts:trust_safety_audit")


# TRUST_SAFETY_ACTION_LOG_UI_V1
@staff_member_required
def trust_safety_action_log(request):
    from listings.models import ListingReport
    from .models import UserReport

    listing_actions = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).exclude(
        action_taken="",
    ).order_by("-updated_at", "-created_at")[:50]

    seller_actions = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).exclude(
        action_taken="",
    ).order_by("-updated_at", "-created_at")[:50]

    return render(
        request,
        "accounts/trust_safety_action_log.html",
        {
            "listing_actions": listing_actions,
            "seller_actions": seller_actions,
            "page_title": "Trust & Safety Action Log",
        },
    )


# TRUST_SAFETY_ACTION_LOG_UI_FIX_NO_UPDATED_AT_V1
@staff_member_required
def trust_safety_action_log(request):
    from listings.models import ListingReport
    from .models import UserReport

    listing_actions = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).exclude(
        action_taken="",
    ).order_by("-reviewed_at", "-created_at")[:50]

    seller_actions = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).exclude(
        action_taken="",
    ).order_by("-created_at")[:50]

    return render(
        request,
        "accounts/trust_safety_action_log.html",
        {
            "listing_actions": listing_actions,
            "seller_actions": seller_actions,
            "page_title": "Trust & Safety Action Log",
        },
    )


# TRUST_SAFETY_ACTION_LOG_FILTERS_V1
@staff_member_required
def trust_safety_action_log(request):
    from django.db.models import Q
    from listings.models import ListingReport
    from .models import UserReport

    q = (request.GET.get("q") or "").strip()
    action = (request.GET.get("action") or "").strip()
    status = (request.GET.get("status") or "").strip()
    log_type = (request.GET.get("type") or "all").strip()

    listing_actions = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).exclude(
        action_taken="",
    )

    seller_actions = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).exclude(
        action_taken="",
    )

    if q:
        listing_actions = listing_actions.filter(
            Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        )

        seller_actions = seller_actions.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        )

    if action:
        listing_actions = listing_actions.filter(action_taken=action)
        seller_actions = seller_actions.filter(action_taken=action)

    if status:
        listing_actions = listing_actions.filter(status=status)
        seller_actions = seller_actions.filter(status=status)

    if log_type == "listing":
        seller_actions = seller_actions.none()
    elif log_type == "seller":
        listing_actions = listing_actions.none()

    listing_action_choices = (
        ListingReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
        .distinct()
        .order_by("action_taken")
    )

    seller_action_choices = (
        UserReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
        .distinct()
        .order_by("action_taken")
    )

    action_choices = sorted(set(list(listing_action_choices) + list(seller_action_choices)))

    listing_actions = listing_actions.order_by("-reviewed_at", "-created_at")[:100]
    seller_actions = seller_actions.order_by("-action_taken_at", "-created_at")[:100]

    return render(
        request,
        "accounts/trust_safety_action_log.html",
        {
            "listing_actions": listing_actions,
            "seller_actions": seller_actions,
            "action_choices": action_choices,
            "listing_status_choices": ListingReport.Status.choices,
            "seller_status_choices": UserReport.Status.choices,
            "selected_q": q,
            "selected_action": action,
            "selected_status": status,
            "selected_type": log_type,
            "page_title": "Trust & Safety Action Log",
        },
    )


# TRUST_SAFETY_ACTION_LOG_EXPORT_V1
def _trust_safety_action_log_querysets(request):
    from django.db.models import Q
    from listings.models import ListingReport
    from .models import UserReport

    q = (request.GET.get("q") or "").strip()
    action = (request.GET.get("action") or "").strip()
    status = (request.GET.get("status") or "").strip()
    log_type = (request.GET.get("type") or "all").strip()

    listing_actions = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).exclude(
        action_taken="",
    )

    seller_actions = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).exclude(
        action_taken="",
    )

    if q:
        listing_actions = listing_actions.filter(
            Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        )

        seller_actions = seller_actions.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        )

    if action:
        listing_actions = listing_actions.filter(action_taken=action)
        seller_actions = seller_actions.filter(action_taken=action)

    if status:
        listing_actions = listing_actions.filter(status=status)
        seller_actions = seller_actions.filter(status=status)

    if log_type == "listing":
        seller_actions = seller_actions.none()
    elif log_type == "seller":
        listing_actions = listing_actions.none()

    return listing_actions, seller_actions, q, action, status, log_type


@staff_member_required
def trust_safety_action_log(request):
    from listings.models import ListingReport
    from .models import UserReport

    listing_actions, seller_actions, q, action, status, log_type = _trust_safety_action_log_querysets(request)

    listing_action_choices = (
        ListingReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
        .distinct()
        .order_by("action_taken")
    )

    seller_action_choices = (
        UserReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
        .distinct()
        .order_by("action_taken")
    )

    action_choices = sorted(set(list(listing_action_choices) + list(seller_action_choices)))

    listing_actions = listing_actions.order_by("-reviewed_at", "-created_at")[:100]
    seller_actions = seller_actions.order_by("-action_taken_at", "-created_at")[:100]

    return render(
        request,
        "accounts/trust_safety_action_log.html",
        {
            "listing_actions": listing_actions,
            "seller_actions": seller_actions,
            "action_choices": action_choices,
            "listing_status_choices": ListingReport.Status.choices,
            "seller_status_choices": UserReport.Status.choices,
            "selected_q": q,
            "selected_action": action,
            "selected_status": status,
            "selected_type": log_type,
            "querystring": request.GET.urlencode(),
            "page_title": "Trust & Safety Action Log",
        },
    )


@staff_member_required
def trust_safety_action_log_export(request):
    import csv

    from django.http import HttpResponse

    listing_actions, seller_actions, q, action, status, log_type = _trust_safety_action_log_querysets(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trust_safety_action_log.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "record_type",
        "action_taken",
        "status",
        "date",
        "reporter_username",
        "reporter_email",
        "subject_username",
        "subject_email",
        "listing_title",
        "reasons",
        "reporter_note",
        "internal_admin_note",
    ])

    for report in listing_actions.order_by("-reviewed_at", "-created_at"):
        date_value = report.reviewed_at or report.created_at
        owner = report.listing.owner if report.listing and report.listing.owner else None

        writer.writerow([
            "listing",
            report.action_taken,
            report.get_status_display(),
            date_value.isoformat() if date_value else "",
            report.reporter.username if report.reporter else "",
            report.reporter.email if report.reporter else "",
            owner.username if owner else "",
            owner.email if owner else "",
            report.listing.title if report.listing else "",
            report.get_reasons_display() if hasattr(report, "get_reasons_display") else "",
            report.reporter_note or "",
            report.admin_note or "",
        ])

    for report in seller_actions.order_by("-action_taken_at", "-created_at"):
        date_value = report.action_taken_at or report.created_at

        writer.writerow([
            "seller",
            report.action_taken,
            report.get_status_display(),
            date_value.isoformat() if date_value else "",
            report.reporter.username if report.reporter else "",
            report.reporter.email if report.reporter else "",
            report.reported_user.username if report.reported_user else "",
            report.reported_user.email if report.reported_user else "",
            report.source_listing.title if report.source_listing else "",
            report.get_reasons_display() if hasattr(report, "get_reasons_display") else "",
            report.reporter_note or "",
            report.admin_note or "",
        ])

    return response


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


# MODERATION_APPEALS_V1
@login_required
def moderation_appeal_create(request, notice_pk):
    from .models import ModerationAppeal, ModerationNotice

    notice = get_object_or_404(
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        ),
        pk=notice_pk,
        recipient=request.user,
    )

    if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION:
        appeal_type = ModerationAppeal.AppealType.LISTING_ACTION
    elif notice.notice_type == ModerationNotice.NoticeType.SELLER_ACTION:
        appeal_type = ModerationAppeal.AppealType.SELLER_ACTION
    else:
        appeal_type = ModerationAppeal.AppealType.OTHER

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()

        if not message:
            messages.error(request, "Please explain why you are appealing this moderation action.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        existing_pending = ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
            status=ModerationAppeal.Status.PENDING,
        ).first()

        if existing_pending:
            messages.info(request, "You already have a pending appeal for this notice.")
            return redirect("accounts:moderation_appeal_detail", pk=existing_pending.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            message=message,
        )

        messages.success(request, "Your appeal was submitted for admin review.")
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "page_title": "Submit Appeal",
        },
    )


@login_required
def my_moderation_appeals(request):
    from .models import ModerationAppeal

    appeals = ModerationAppeal.objects.filter(
        appellant=request.user,
    ).select_related(
        "listing",
        "moderation_notice",
    )

    return render(
        request,
        "accounts/my_moderation_appeals.html",
        {
            "appeals": appeals,
            "page_title": "My Appeals",
        },
    )


@login_required
def moderation_appeal_detail(request, pk):
    from .models import ModerationAppeal

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        ),
        pk=pk,
        appellant=request.user,
    )

    return render(
        request,
        "accounts/moderation_appeal_detail.html",
        {
            "appeal": appeal,
            "page_title": "Appeal Detail",
        },
    )


@staff_member_required
def moderation_appeal_queue(request):
    from .models import ModerationAppeal

    status = (request.GET.get("status") or ModerationAppeal.Status.PENDING).strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
    )

    if status:
        appeals = appeals.filter(status=status)

    if q:
        from django.db.models import Q
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
        )

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "selected_status": status,
            "selected_q": q,
            "status_choices": ModerationAppeal.Status.choices,
            "page_title": "Moderation Appeals",
        },
    )


@staff_member_required
def moderation_appeal_admin_detail(request, pk):
    from .models import ModerationAppeal

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        ),
        pk=pk,
    )

    return render(
        request,
        "accounts/moderation_appeal_admin_detail.html",
        {
            "appeal": appeal,
            "page_title": "Appeal Admin Detail",
        },
    )


@staff_member_required
@require_POST
def moderation_appeal_decide(request, pk, decision):
    from django.utils import timezone
    from .models import ModerationAppeal, ModerationNotice

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related("appellant", "listing"),
        pk=pk,
    )

    if decision == "approve":
        appeal.status = ModerationAppeal.Status.APPROVED
        default_note = (
            "Your appeal was approved. An admin will apply any needed restoration or restriction changes."
        )
        title = "Your appeal was approved"
    elif decision == "reject":
        appeal.status = ModerationAppeal.Status.REJECTED
        default_note = "Your appeal was reviewed and the moderation action remains in place."
        title = "Your appeal was rejected"
    else:
        messages.error(request, "Invalid appeal decision.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    appeal.decision_note = (request.POST.get("decision_note") or default_note).strip()
    appeal.admin_note = (request.POST.get("admin_note") or appeal.admin_note or "").strip()
    appeal.reviewed_by = request.user
    appeal.reviewed_at = timezone.now()
    appeal.save(
        update_fields=[
            "status",
            "decision_note",
            "admin_note",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title=title,
        body=appeal.decision_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    messages.success(request, "Appeal decision saved and user notified.")
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)


# MODERATION_APPEALS_SAFE_UPLOADS_FINAL_V1
@login_required
def moderation_appeal_create(request, notice_pk):
    from .models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice

    notice = get_object_or_404(
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        ),
        pk=notice_pk,
        recipient=request.user,
    )

    # Only action notices can be appealed. Report updates and appeal decision notices cannot.
    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    # Do not allow appealing restoration/lift notices.
    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION:
        appeal_type = ModerationAppeal.AppealType.LISTING_ACTION
    elif notice.notice_type == ModerationNotice.NoticeType.SELLER_ACTION:
        appeal_type = ModerationAppeal.AppealType.SELLER_ACTION
    else:
        appeal_type = ModerationAppeal.AppealType.OTHER

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_size = 40 * 1024 * 1024
        allowed_prefixes = ("image/", "video/")
        allowed_exact = {"application/pdf"}

        for uploaded in files:
            content_type = uploaded.content_type or ""

            if uploaded.size > max_size:
                messages.error(
                    request,
                    f"{uploaded.name} is too large. Each file must be 40 MB or smaller.",
                )
                return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

            if not (content_type.startswith(allowed_prefixes) or content_type in allowed_exact):
                messages.error(
                    request,
                    f"{uploaded.name} is not allowed. Upload photos, videos, or PDF files only.",
                )
                return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        existing_pending = ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
            status=ModerationAppeal.Status.PENDING,
        ).first()

        if existing_pending:
            messages.info(request, "You already have a pending appeal for this notice.")
            return redirect("accounts:moderation_appeal_detail", pk=existing_pending.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_mb": 40,
            "page_title": "Submit Appeal",
        },
    )


@login_required
def moderation_appeal_detail(request, pk):
    from .models import ModerationAppeal

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
        appellant=request.user,
    )

    return render(
        request,
        "accounts/moderation_appeal_detail.html",
        {
            "appeal": appeal,
            "page_title": "Appeal Detail",
        },
    )


@staff_member_required
def moderation_appeal_admin_detail(request, pk):
    from .models import ModerationAppeal

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    return render(
        request,
        "accounts/moderation_appeal_admin_detail.html",
        {
            "appeal": appeal,
            "page_title": "Appeal Admin Detail",
        },
    )


@staff_member_required
@require_POST
def moderation_appeal_decide(request, pk, decision):
    from django.utils import timezone
    from .models import ModerationAppeal, ModerationNotice

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related("appellant", "listing"),
        pk=pk,
    )

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.warning(request, "This appeal has already been decided.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if decision == "approve":
        appeal.status = ModerationAppeal.Status.APPROVED
        default_note = (
            "Your appeal was approved. This does not automatically lift a restriction. "
            "Admin will apply any needed restoration separately."
        )
        title = "Your appeal was approved"
    elif decision == "reject":
        appeal.status = ModerationAppeal.Status.REJECTED
        default_note = "Your appeal was reviewed and the moderation action remains in place."
        title = "Your appeal was rejected"
    else:
        messages.error(request, "Invalid appeal decision.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    appeal.decision_note = (request.POST.get("decision_note") or default_note).strip()
    appeal.admin_note = (request.POST.get("admin_note") or appeal.admin_note or "").strip()
    appeal.reviewed_by = request.user
    appeal.reviewed_at = timezone.now()
    appeal.save(
        update_fields=[
            "status",
            "decision_note",
            "admin_note",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title=title,
        body=appeal.decision_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    messages.success(
        request,
        "Appeal decision saved and user notified. No restriction was changed automatically.",
    )
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)


# MODERATION_APPEALS_SAFE_UPLOADS_STRICT_FILE_TYPES_V2
@login_required
def moderation_appeal_create(request, notice_pk):
    from pathlib import Path

    from .models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice

    notice = get_object_or_404(
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        ),
        pk=notice_pk,
        recipient=request.user,
    )

    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION:
        appeal_type = ModerationAppeal.AppealType.LISTING_ACTION
    elif notice.notice_type == ModerationNotice.NoticeType.SELLER_ACTION:
        appeal_type = ModerationAppeal.AppealType.SELLER_ACTION
    else:
        appeal_type = ModerationAppeal.AppealType.OTHER

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_size = 40 * 1024 * 1024

        allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_pdf_exts = {".pdf"}
        allowed_video_exts = {".mp4"}

        allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
        allowed_pdf_types = {"application/pdf"}
        allowed_video_types = {"video/mp4"}

        for uploaded in files:
            ext = Path(uploaded.name).suffix.lower()
            content_type = (uploaded.content_type or "").lower()

            if uploaded.size > max_size:
                messages.error(
                    request,
                    f"{uploaded.name} is too large. Each file must be 40 MB or smaller.",
                )
                return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

            is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
            is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
            is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

            if not (is_valid_image or is_valid_pdf or is_valid_video):
                messages.error(
                    request,
                    (
                        f"{uploaded.name} is not allowed. "
                        "Allowed files: .jpg, .jpeg, .png, .webp photos, .pdf files, and .mp4 videos only."
                    ),
                )
                return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        existing_pending = ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
            status=ModerationAppeal.Status.PENDING,
        ).first()

        if existing_pending:
            messages.info(request, "You already have a pending appeal for this notice.")
            return redirect("accounts:moderation_appeal_detail", pk=existing_pending.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_mb": 40,
            "page_title": "Submit Appeal",
        },
    )


# MODERATION_APPEALS_SAFE_UPLOADS_12_FILES_FINAL_V3
@login_required
def moderation_appeal_create(request, notice_pk):
    from pathlib import Path

    from .models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice

    notice = get_object_or_404(
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        ),
        pk=notice_pk,
        recipient=request.user,
    )

    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION:
        appeal_type = ModerationAppeal.AppealType.LISTING_ACTION
    else:
        appeal_type = ModerationAppeal.AppealType.SELLER_ACTION

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_files = 12
        max_size = 40 * 1024 * 1024

        if len(files) > max_files:
            messages.error(request, "You can upload up to 12 files per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_pdf_exts = {".pdf"}
        allowed_video_exts = {".mp4"}

        allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
        allowed_pdf_types = {"application/pdf"}
        allowed_video_types = {"video/mp4"}

        validation_errors = []

        for uploaded in files:
            ext = Path(uploaded.name).suffix.lower()
            content_type = (uploaded.content_type or "").lower()

            if uploaded.size > max_size:
                validation_errors.append(
                    f"{uploaded.name}: too large. Each file must be 40 MB or smaller."
                )
                continue

            is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
            is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
            is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

            if not (is_valid_image or is_valid_pdf or is_valid_video):
                validation_errors.append(
                    f"{uploaded.name}: invalid type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .mp4 only. Videos must be .mp4."
                )

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        existing_pending = ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
            status=ModerationAppeal.Status.PENDING,
        ).first()

        if existing_pending:
            messages.info(request, "You already have a pending appeal for this notice.")
            return redirect("accounts:moderation_appeal_detail", pk=existing_pending.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_mb": 40,
            "max_upload_files": 12,
            "page_title": "Submit Appeal",
        },
    )


# MODERATION_APPEAL_ATTACHMENT_LOCK_AFTER_SUBMIT_V1
@login_required
@require_POST
def moderation_appeal_attachment_delete(request, pk):
    from .models import ModerationAppealAttachment

    attachment = get_object_or_404(
        ModerationAppealAttachment.objects.select_related("appeal", "appeal__appellant"),
        pk=pk,
        appeal__appellant=request.user,
    )

    messages.error(
        request,
        "Evidence files are locked after appeal submission. You cannot delete or add evidence after submitting an appeal.",
    )
    return redirect("accounts:moderation_appeal_detail", pk=attachment.appeal.pk)


# MODERATION_APPEALS_DUPLICATE_CHECK_FINAL_V4
@login_required
def moderation_appeal_create(request, notice_pk):
    import hashlib
    from pathlib import Path

    from .models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice

    notice = get_object_or_404(
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        ),
        pk=notice_pk,
        recipient=request.user,
    )

    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    appeal_type = (
        ModerationAppeal.AppealType.LISTING_ACTION
        if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION
        else ModerationAppeal.AppealType.SELLER_ACTION
    )

    def uploaded_file_hash(uploaded):
        digest = hashlib.sha256()

        try:
            uploaded.seek(0)
        except Exception:
            pass

        for chunk in uploaded.chunks():
            digest.update(chunk)

        try:
            uploaded.seek(0)
        except Exception:
            pass

        return digest.hexdigest()

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_files = 12
        max_size = 40 * 1024 * 1024

        if len(files) > max_files:
            messages.error(request, "You can upload up to 12 files per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_pdf_exts = {".pdf"}
        allowed_video_exts = {".mp4"}

        allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
        allowed_pdf_types = {"application/pdf"}
        allowed_video_types = {"video/mp4"}

        validation_errors = []
        seen_hashes = {}

        for uploaded in files:
            ext = Path(uploaded.name).suffix.lower()
            content_type = (uploaded.content_type or "").lower()

            if uploaded.size > max_size:
                validation_errors.append(
                    f"{uploaded.name}: too large. Each file must be 40 MB or smaller."
                )
                continue

            is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
            is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
            is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

            if not (is_valid_image or is_valid_pdf or is_valid_video):
                validation_errors.append(
                    f"{uploaded.name}: invalid type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .mp4 only. Videos must be .mp4."
                )
                continue

            file_hash = uploaded_file_hash(uploaded)

            if file_hash in seen_hashes:
                validation_errors.append(
                    f"{uploaded.name}: duplicate file. It matches {seen_hashes[file_hash]}."
                )
            else:
                seen_hashes[file_hash] = uploaded.name

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        existing_pending = ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
            status=ModerationAppeal.Status.PENDING,
        ).first()

        if existing_pending:
            messages.info(request, "You already have a pending appeal for this notice.")
            return redirect("accounts:moderation_appeal_detail", pk=existing_pending.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_mb": 40,
            "max_upload_files": 12,
            "page_title": "Submit Appeal",
        },
    )


# MODERATION_APPEALS_TOTAL_200MB_15_FILES_FINAL_V6
@login_required
def moderation_appeal_create(request, notice_pk):
    import hashlib
    from pathlib import Path

    from .models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice

    notice = get_object_or_404(
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        ),
        pk=notice_pk,
        recipient=request.user,
    )

    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    appeal_type = (
        ModerationAppeal.AppealType.LISTING_ACTION
        if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION
        else ModerationAppeal.AppealType.SELLER_ACTION
    )

    def uploaded_file_hash(uploaded):
        digest = hashlib.sha256()

        try:
            uploaded.seek(0)
        except Exception:
            pass

        for chunk in uploaded.chunks():
            digest.update(chunk)

        try:
            uploaded.seek(0)
        except Exception:
            pass

        return digest.hexdigest()

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_files = 15
        max_total_size = 200 * 1024 * 1024

        if len(files) > max_files:
            messages.error(request, "You can upload up to 15 files per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        total_size = sum(uploaded.size or 0 for uploaded in files)

        if total_size > max_total_size:
            messages.error(request, "Total upload size is too large. Maximum total size is 200 MB per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_pdf_exts = {".pdf"}
        allowed_video_exts = {".mp4"}

        allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
        allowed_pdf_types = {"application/pdf"}
        allowed_video_types = {"video/mp4"}

        validation_errors = []
        seen_hashes = {}

        for uploaded in files:
            ext = Path(uploaded.name).suffix.lower()
            content_type = (uploaded.content_type or "").lower()

            is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
            is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
            is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

            if not (is_valid_image or is_valid_pdf or is_valid_video):
                validation_errors.append(
                    f"{uploaded.name}: invalid type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .mp4 only. Videos must be .mp4."
                )
                continue

            file_hash = uploaded_file_hash(uploaded)

            if file_hash in seen_hashes:
                validation_errors.append(
                    f"{uploaded.name}: duplicate file. It matches {seen_hashes[file_hash]}."
                )
            else:
                seen_hashes[file_hash] = uploaded.name

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        existing_pending = ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
            status=ModerationAppeal.Status.PENDING,
        ).first()

        if existing_pending:
            messages.info(request, "You already have a pending appeal for this notice.")
            return redirect("accounts:moderation_appeal_detail", pk=existing_pending.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_files": 15,
            "max_total_upload_mb": 200,
            "page_title": "Submit Appeal",
        },
    )


# TRUST_SAFETY_DASHBOARD_APPEALS_V1
@staff_member_required
def trust_safety_dashboard(request):
    from django.contrib.auth import get_user_model
    from accounts.models import ModerationAppeal, UserProfile, UserReport
    from listings.models import Listing, ListingReport

    User = get_user_model()

    pending_listing_reports = ListingReport.objects.filter(
        status=ListingReport.Status.PENDING,
    ).count()

    pending_seller_reports = UserReport.objects.filter(
        status=UserReport.Status.PENDING,
    ).count()

    pending_appeals = ModerationAppeal.objects.filter(
        status=ModerationAppeal.Status.PENDING,
    ).count()

    suspended_listings = Listing.objects.filter(
        status=Listing.Status.SUSPENDED,
    ).select_related("owner").order_by("-created_at")[:20]

    suspended_sellers = User.objects.filter(
        profile__seller_suspended_until__isnull=False,
    ).select_related("profile").order_by("username")[:20]

    latest_listing_reports = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).order_by("-created_at")[:10]

    latest_seller_reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).order_by("-created_at")[:10]

    latest_pending_appeals = ModerationAppeal.objects.filter(
        status=ModerationAppeal.Status.PENDING,
    ).select_related(
        "appellant",
        "listing",
        "moderation_notice",
    ).prefetch_related(
        "attachments",
    ).order_by("-created_at")[:10]

    return render(
        request,
        "accounts/trust_safety_dashboard.html",
        {
            "pending_listing_reports": pending_listing_reports,
            "pending_seller_reports": pending_seller_reports,
            "pending_appeals": pending_appeals,
            "suspended_listings": suspended_listings,
            "suspended_sellers": suspended_sellers,
            "latest_listing_reports": latest_listing_reports,
            "latest_seller_reports": latest_seller_reports,
            "latest_pending_appeals": latest_pending_appeals,
            "page_title": "Trust & Safety",
        },
    )


# MODERATION_APPEAL_MANUAL_RESOLUTION_PANEL_V1
@staff_member_required
def moderation_appeal_admin_detail(request, pk):
    from .models import ModerationAppeal, UserProfile
    from listings.models import Listing

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "user_report__reported_user",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    seller_to_lift = None

    if appeal.user_report and appeal.user_report.reported_user:
        seller_to_lift = appeal.user_report.reported_user
    elif appeal.appeal_type == ModerationAppeal.AppealType.SELLER_ACTION:
        seller_to_lift = appeal.appellant

    seller_profile = None
    seller_is_suspended = False

    if seller_to_lift:
        seller_profile = UserProfile.objects.filter(user=seller_to_lift).first()
        seller_is_suspended = bool(seller_profile and seller_profile.is_seller_suspended)

    can_restore_listing = (
        appeal.status == ModerationAppeal.Status.APPROVED
        and appeal.listing
        and appeal.listing.status == Listing.Status.SUSPENDED
        and not appeal.listing.suspended_due_to_seller
    )

    listing_restore_blocked_by_seller_suspension = (
        appeal.status == ModerationAppeal.Status.APPROVED
        and appeal.listing
        and appeal.listing.status == Listing.Status.SUSPENDED
        and appeal.listing.suspended_due_to_seller
    )

    return render(
        request,
        "accounts/moderation_appeal_admin_detail.html",
        {
            "appeal": appeal,
            "seller_to_lift": seller_to_lift,
            "seller_profile": seller_profile,
            "seller_is_suspended": seller_is_suspended,
            "can_restore_listing": can_restore_listing,
            "listing_restore_blocked_by_seller_suspension": listing_restore_blocked_by_seller_suspension,
            "page_title": "Appeal Admin Detail",
        },
    )


# MODERATION_APPEAL_DETAIL_OWNER_OR_ADMIN_SAFE_V2
@login_required
def moderation_appeal_detail(request, pk):
    from .models import ModerationAppeal

    appeal = (
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        )
        .prefetch_related("attachments")
        .filter(pk=pk)
        .first()
    )

    if not appeal:
        messages.error(request, "That appeal does not exist.")
        return redirect("accounts:my_moderation_appeals")

    if request.user.is_staff:
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if appeal.appellant_id != request.user.id:
        messages.error(request, "That appeal does not belong to your account.")
        return redirect("accounts:my_moderation_appeals")

    return render(
        request,
        "accounts/moderation_appeal_detail.html",
        {
            "appeal": appeal,
            "page_title": "Appeal Detail",
        },
    )


# MODERATION_APPEALS_DUPLICATE_CHECK_FINAL_V4
@login_required
def moderation_appeal_create(request, notice_pk):
    import hashlib
    from pathlib import Path

    from .models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice

    notice = get_object_or_404(
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        ),
        pk=notice_pk,
        recipient=request.user,
    )

    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    appeal_type = (
        ModerationAppeal.AppealType.LISTING_ACTION
        if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION
        else ModerationAppeal.AppealType.SELLER_ACTION
    )

    def uploaded_file_hash(uploaded):
        digest = hashlib.sha256()

        try:
            uploaded.seek(0)
        except Exception:
            pass

        for chunk in uploaded.chunks():
            digest.update(chunk)

        try:
            uploaded.seek(0)
        except Exception:
            pass

        return digest.hexdigest()

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_files = 12
        max_size = 40 * 1024 * 1024

        if len(files) > max_files:
            messages.error(request, "You can upload up to 12 files per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_pdf_exts = {".pdf"}
        allowed_video_exts = {".mp4"}

        allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
        allowed_pdf_types = {"application/pdf"}
        allowed_video_types = {"video/mp4"}

        validation_errors = []
        seen_hashes = {}

        for uploaded in files:
            ext = Path(uploaded.name).suffix.lower()
            content_type = (uploaded.content_type or "").lower()

            if uploaded.size > max_size:
                validation_errors.append(
                    f"{uploaded.name}: too large. Each file must be 40 MB or smaller."
                )
                continue

            is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
            is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
            is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

            if not (is_valid_image or is_valid_pdf or is_valid_video):
                validation_errors.append(
                    f"{uploaded.name}: invalid type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .mp4 only. Videos must be .mp4."
                )
                continue

            file_hash = uploaded_file_hash(uploaded)

            if file_hash in seen_hashes:
                validation_errors.append(
                    f"{uploaded.name}: duplicate file. It matches {seen_hashes[file_hash]}."
                )
            else:
                seen_hashes[file_hash] = uploaded.name

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        existing_pending = ModerationAppeal.objects.filter(
            appellant=request.user,
            moderation_notice=notice,
            status=ModerationAppeal.Status.PENDING,
        ).first()

        if existing_pending:
            messages.info(request, "You already have a pending appeal for this notice.")
            return redirect("accounts:moderation_appeal_detail", pk=existing_pending.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_mb": 40,
            "max_upload_files": 12,
            "page_title": "Submit Appeal",
        },
    )


# MODERATION_APPEAL_CREATE_SAFE_NOTICE_REDIRECT_V2
@login_required
def moderation_appeal_create(request, notice_pk):
    import hashlib
    from pathlib import Path

    from .models import ModerationAppeal, ModerationAppealAttachment, ModerationNotice

    notice = (
        ModerationNotice.objects.select_related(
            "recipient",
            "listing",
            "listing_report",
            "user_report",
        )
        .filter(pk=notice_pk, recipient=request.user)
        .first()
    )

    if not notice:
        messages.error(
            request,
            "That moderation notice was not found for your account. Please use the current Notices page.",
        )
        return redirect("accounts:moderation_notices")

    existing_appeal = ModerationAppeal.objects.filter(
        appellant=request.user,
        moderation_notice=notice,
    ).order_by("-created_at").first()

    if existing_appeal:
        messages.info(request, "You already submitted an appeal for this notice.")
        return redirect("accounts:moderation_appeal_detail", pk=existing_appeal.pk)

    if notice.notice_type not in [
        ModerationNotice.NoticeType.LISTING_ACTION,
        ModerationNotice.NoticeType.SELLER_ACTION,
    ]:
        messages.error(request, "This notice is an update, not an appealable moderation action.")
        return redirect("accounts:moderation_notices")

    title_lower = (notice.title or "").lower()
    body_lower = (notice.body or "").lower()
    non_appealable_words = ["lifted", "restored", "appeal was approved", "appeal was rejected"]

    if any(word in title_lower or word in body_lower for word in non_appealable_words):
        messages.error(request, "This notice does not need an appeal because it is not an active restriction.")
        return redirect("accounts:moderation_notices")

    appeal_type = (
        ModerationAppeal.AppealType.LISTING_ACTION
        if notice.notice_type == ModerationNotice.NoticeType.LISTING_ACTION
        else ModerationAppeal.AppealType.SELLER_ACTION
    )

    def uploaded_file_hash(uploaded):
        digest = hashlib.sha256()

        try:
            uploaded.seek(0)
        except Exception:
            pass

        for chunk in uploaded.chunks():
            digest.update(chunk)

        try:
            uploaded.seek(0)
        except Exception:
            pass

        return digest.hexdigest()

    if request.method == "POST":
        message = (request.POST.get("message") or "").strip()
        files = request.FILES.getlist("attachments")

        if not message:
            messages.error(request, "Please write an appeal message before submitting.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        max_files = 15
        max_total_size = 200 * 1024 * 1024

        if len(files) > max_files:
            messages.error(request, "You can upload up to 15 files per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        total_size = sum(uploaded.size or 0 for uploaded in files)

        if total_size > max_total_size:
            messages.error(request, "Total upload size is too large. Maximum total size is 200 MB per appeal.")
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        allowed_image_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_pdf_exts = {".pdf"}
        allowed_video_exts = {".mp4"}

        allowed_image_types = {"image/jpeg", "image/png", "image/webp"}
        allowed_pdf_types = {"application/pdf"}
        allowed_video_types = {"video/mp4"}

        validation_errors = []
        seen_hashes = {}

        for uploaded in files:
            ext = Path(uploaded.name).suffix.lower()
            content_type = (uploaded.content_type or "").lower()

            is_valid_image = ext in allowed_image_exts and content_type in allowed_image_types
            is_valid_pdf = ext in allowed_pdf_exts and content_type in allowed_pdf_types
            is_valid_video = ext in allowed_video_exts and content_type in allowed_video_types

            if not (is_valid_image or is_valid_pdf or is_valid_video):
                validation_errors.append(
                    f"{uploaded.name}: invalid type. Allowed: .jpg, .jpeg, .png, .webp, .pdf, .mp4 only. Videos must be .mp4."
                )
                continue

            file_hash = uploaded_file_hash(uploaded)

            if file_hash in seen_hashes:
                validation_errors.append(
                    f"{uploaded.name}: duplicate file. It matches {seen_hashes[file_hash]}."
                )
            else:
                seen_hashes[file_hash] = uploaded.name

        if validation_errors:
            for error in validation_errors:
                messages.error(request, error)
            return redirect("accounts:moderation_appeal_create", notice_pk=notice.pk)

        appeal = ModerationAppeal.objects.create(
            appellant=request.user,
            moderation_notice=notice,
            listing=notice.listing,
            listing_report=notice.listing_report,
            user_report=notice.user_report,
            appeal_type=appeal_type,
            status=ModerationAppeal.Status.PENDING,
            message=message,
        )

        for uploaded in files:
            ModerationAppealAttachment.objects.create(
                appeal=appeal,
                file=uploaded,
                original_name=uploaded.name,
                content_type=uploaded.content_type or "",
                size=uploaded.size or 0,
            )

        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff_users = User.objects.filter(is_staff=True, is_active=True)

        for staff_user in staff_users:
            ModerationNotice.objects.create(
                recipient=staff_user,
                title="New moderation appeal submitted",
                body=(
                    f"{request.user.username} submitted appeal #{appeal.pk}. "
                    "Review it from the Trust & Safety appeals queue."
                ),
                notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
                listing=appeal.listing,
                listing_report=appeal.listing_report,
                user_report=appeal.user_report,
            )

        messages.success(
            request,
            "Your appeal was submitted for admin review. No restriction has been changed automatically.",
        )
        return redirect("accounts:moderation_appeal_detail", pk=appeal.pk)

    return render(
        request,
        "accounts/moderation_appeal_form.html",
        {
            "notice": notice,
            "max_upload_files": 15,
            "max_total_upload_mb": 200,
            "page_title": "Submit Appeal",
        },
    )


# MODERATION_APPEALS_EXPORT_CSV_V1
@staff_member_required
def moderation_appeal_export_csv(request):
    import csv
    from django.http import HttpResponse
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments")

    if status:
        appeals = appeals.filter(status=status)

    if q:
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="moderation_appeals.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "appeal_id",
        "status",
        "appeal_type",
        "created_at",
        "appellant_username",
        "appellant_email",
        "listing_title",
        "evidence_file_count",
        "evidence_total_mb",
        "message",
        "decision_note",
        "internal_admin_note",
        "reviewed_by",
        "reviewed_at",
    ])

    for appeal in appeals.order_by("-created_at"):
        attachments = list(appeal.attachments.all())
        total_size = sum(item.size or 0 for item in attachments)
        total_mb = round(total_size / 1024 / 1024, 2)

        writer.writerow([
            appeal.pk,
            appeal.get_status_display(),
            appeal.get_appeal_type_display(),
            appeal.created_at.isoformat() if appeal.created_at else "",
            appeal.appellant.username if appeal.appellant else "",
            appeal.appellant.email if appeal.appellant else "",
            appeal.listing.title if appeal.listing else "",
            len(attachments),
            total_mb,
            appeal.message or "",
            appeal.decision_note or "",
            appeal.admin_note or "",
            appeal.reviewed_by.username if appeal.reviewed_by else "",
            appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
        ])

    return response


# MODERATION_APPEAL_EVIDENCE_ZIP_EXPORT_V1
@staff_member_required
def moderation_appeal_evidence_zip(request, pk):
    import io
    import zipfile
    from pathlib import Path

    from django.http import HttpResponse

    from .models import ModerationAppeal

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    buffer = io.BytesIO()

    def safe_filename(name):
        name = Path(name or "evidence").name
        name = name.replace("/", "_").replace("\\", "_")
        return name or "evidence"

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        readme = [
            f"Appeal ID: {appeal.pk}",
            f"Status: {appeal.get_status_display()}",
            f"Type: {appeal.get_appeal_type_display()}",
            f"Appellant: {appeal.appellant.username} / {appeal.appellant.email}",
            f"Created: {appeal.created_at}",
            "",
            "Appeal message:",
            appeal.message or "",
            "",
            "Decision note:",
            appeal.decision_note or "",
            "",
            "Internal admin note:",
            appeal.admin_note or "",
            "",
        ]

        if appeal.listing:
            readme.extend([
                f"Related listing: {appeal.listing.title}",
                f"Listing status: {appeal.listing.get_status_display()}",
                "",
            ])

        archive.writestr("APPEAL_SUMMARY.txt", "\n".join(readme))

        attachments = list(appeal.attachments.all())

        if not attachments:
            archive.writestr("NO_EVIDENCE_FILES.txt", "No evidence files were uploaded with this appeal.")
        else:
            used_names = set()

            for index, attachment in enumerate(attachments, start=1):
                original_name = safe_filename(attachment.original_name or attachment.file.name)
                zip_name = f"{index:02d}_{original_name}"

                counter = 2
                while zip_name in used_names:
                    stem = Path(original_name).stem
                    suffix = Path(original_name).suffix
                    zip_name = f"{index:02d}_{stem}_{counter}{suffix}"
                    counter += 1

                used_names.add(zip_name)

                attachment.file.open("rb")
                try:
                    archive.writestr(zip_name, attachment.file.read())
                finally:
                    attachment.file.close()

    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="appeal_{appeal.pk}_evidence.zip"'
    return response


# MODERATION_APPEAL_QUEUE_DEFAULT_ALL_STATUSES_V1
@staff_member_required
def moderation_appeal_queue(request):
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
    ).prefetch_related(
        "attachments",
    ).order_by("-created_at")

    if status:
        appeals = appeals.filter(status=status)

    if q:
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
        )

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "selected_status": status,
            "selected_q": q,
            "status_choices": ModerationAppeal.Status.choices,
            "page_title": "Moderation Appeals",
        },
    )


# MODERATION_APPEALS_BULK_EVIDENCE_ZIP_EXPORT_V1
@staff_member_required
def moderation_appeal_bulk_evidence_zip(request):
    import csv
    import io
    import zipfile
    from pathlib import Path

    from django.db.models import Q
    from django.http import HttpResponse

    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments").order_by("-created_at")

    if status:
        appeals = appeals.filter(status=status)

    if q:
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
        )

    appeals = list(appeals)

    def safe_filename(name):
        name = Path(name or "evidence").name
        name = name.replace("/", "_").replace("\\", "_")
        return name or "evidence"

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        summary_buffer = io.StringIO()
        writer = csv.writer(summary_buffer)

        writer.writerow([
            "appeal_id",
            "status",
            "appeal_type",
            "created_at",
            "appellant_username",
            "appellant_email",
            "listing_title",
            "evidence_file_count",
            "evidence_total_mb",
            "decision_note",
            "reviewed_by",
            "reviewed_at",
        ])

        if not appeals:
            archive.writestr("NO_MATCHING_APPEALS.txt", "No appeals matched this filter.")
        else:
            for appeal in appeals:
                attachments = list(appeal.attachments.all())
                total_size = sum(item.size or 0 for item in attachments)
                total_mb = round(total_size / 1024 / 1024, 2)

                writer.writerow([
                    appeal.pk,
                    appeal.get_status_display(),
                    appeal.get_appeal_type_display(),
                    appeal.created_at.isoformat() if appeal.created_at else "",
                    appeal.appellant.username if appeal.appellant else "",
                    appeal.appellant.email if appeal.appellant else "",
                    appeal.listing.title if appeal.listing else "",
                    len(attachments),
                    total_mb,
                    appeal.decision_note or "",
                    appeal.reviewed_by.username if appeal.reviewed_by else "",
                    appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
                ])

                folder = f"appeal_{appeal.pk:04d}"

                readme = [
                    f"Appeal ID: {appeal.pk}",
                    f"Status: {appeal.get_status_display()}",
                    f"Type: {appeal.get_appeal_type_display()}",
                    f"Appellant: {appeal.appellant.username if appeal.appellant else ''} / {appeal.appellant.email if appeal.appellant else ''}",
                    f"Created: {appeal.created_at}",
                    "",
                    "Appeal message:",
                    appeal.message or "",
                    "",
                    "Decision note:",
                    appeal.decision_note or "",
                    "",
                    "Internal admin note:",
                    appeal.admin_note or "",
                    "",
                ]

                if appeal.listing:
                    readme.extend([
                        f"Related listing: {appeal.listing.title}",
                        f"Listing status: {appeal.listing.get_status_display()}",
                        "",
                    ])

                archive.writestr(f"{folder}/APPEAL_SUMMARY.txt", "\n".join(readme))

                if not attachments:
                    archive.writestr(f"{folder}/NO_EVIDENCE_FILES.txt", "No evidence files were uploaded with this appeal.")
                else:
                    used_names = set()

                    for index, attachment in enumerate(attachments, start=1):
                        original_name = safe_filename(attachment.original_name or attachment.file.name)
                        zip_name = f"{folder}/{index:02d}_{original_name}"

                        counter = 2
                        while zip_name in used_names:
                            stem = Path(original_name).stem
                            suffix = Path(original_name).suffix
                            zip_name = f"{folder}/{index:02d}_{stem}_{counter}{suffix}"
                            counter += 1

                        used_names.add(zip_name)

                        attachment.file.open("rb")
                        try:
                            archive.writestr(zip_name, attachment.file.read())
                        finally:
                            attachment.file.close()

        archive.writestr("ALL_APPEALS_SUMMARY.csv", summary_buffer.getvalue())

    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="filtered_appeals_evidence.zip"'
    return response


# MODERATION_APPEAL_QUEUE_EVIDENCE_SEARCH_TOTALS_V1
@staff_member_required
def moderation_appeal_queue(request):
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
    ).prefetch_related(
        "attachments",
    ).order_by("-created_at")

    if status:
        appeals = appeals.filter(status=status)

    if q:
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    appeals = list(appeals)

    for appeal in appeals:
        evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())
        appeal.evidence_file_count = appeal.attachments.count()
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "selected_status": status,
            "selected_q": q,
            "status_choices": ModerationAppeal.Status.choices,
            "page_title": "Moderation Appeals",
        },
    )


# MODERATION_APPEALS_EXPORT_CSV_EVIDENCE_FILENAMES_V2
@staff_member_required
def moderation_appeal_export_csv(request):
    import csv
    from django.http import HttpResponse
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments")

    if status:
        appeals = appeals.filter(status=status)

    if q:
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="moderation_appeals.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "appeal_id",
        "status",
        "appeal_type",
        "created_at",
        "appellant_username",
        "appellant_email",
        "listing_title",
        "evidence_file_count",
        "evidence_total_mb",
        "evidence_filenames",
        "message",
        "decision_note",
        "internal_admin_note",
        "reviewed_by",
        "reviewed_at",
    ])

    for appeal in appeals.order_by("-created_at"):
        attachments = list(appeal.attachments.all())
        total_size = sum(item.size or 0 for item in attachments)
        total_mb = round(total_size / 1024 / 1024, 2)
        filenames = "; ".join(item.original_name for item in attachments)

        writer.writerow([
            appeal.pk,
            appeal.get_status_display(),
            appeal.get_appeal_type_display(),
            appeal.created_at.isoformat() if appeal.created_at else "",
            appeal.appellant.username if appeal.appellant else "",
            appeal.appellant.email if appeal.appellant else "",
            appeal.listing.title if appeal.listing else "",
            len(attachments),
            total_mb,
            filenames,
            appeal.message or "",
            appeal.decision_note or "",
            appeal.admin_note or "",
            appeal.reviewed_by.username if appeal.reviewed_by else "",
            appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
        ])

    return response


# MODERATION_APPEAL_QUEUE_EVIDENCE_SEARCH_TOTALS_V1
@staff_member_required
def moderation_appeal_queue(request):
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
    ).prefetch_related(
        "attachments",
    ).order_by("-created_at")

    if status:
        appeals = appeals.filter(status=status)

    if q:
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    appeals = list(appeals)

    for appeal in appeals:
        evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())
        appeal.evidence_file_count = appeal.attachments.count()
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "selected_status": status,
            "selected_q": q,
            "status_choices": ModerationAppeal.Status.choices,
            "page_title": "Moderation Appeals",
        },
    )


# MODERATION_APPEALS_EXPORT_CSV_EVIDENCE_FILENAMES_V2
@staff_member_required
def moderation_appeal_export_csv(request):
    import csv
    from django.http import HttpResponse
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments")

    if status:
        appeals = appeals.filter(status=status)

    if q:
        appeals = appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="moderation_appeals.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "appeal_id",
        "status",
        "appeal_type",
        "created_at",
        "appellant_username",
        "appellant_email",
        "listing_title",
        "evidence_file_count",
        "evidence_total_mb",
        "evidence_filenames",
        "message",
        "decision_note",
        "internal_admin_note",
        "reviewed_by",
        "reviewed_at",
    ])

    for appeal in appeals.order_by("-created_at"):
        attachments = list(appeal.attachments.all())
        total_size = sum(item.size or 0 for item in attachments)
        total_mb = round(total_size / 1024 / 1024, 2)
        filenames = "; ".join(item.original_name for item in attachments)

        writer.writerow([
            appeal.pk,
            appeal.get_status_display(),
            appeal.get_appeal_type_display(),
            appeal.created_at.isoformat() if appeal.created_at else "",
            appeal.appellant.username if appeal.appellant else "",
            appeal.appellant.email if appeal.appellant else "",
            appeal.listing.title if appeal.listing else "",
            len(attachments),
            total_mb,
            filenames,
            appeal.message or "",
            appeal.decision_note or "",
            appeal.admin_note or "",
            appeal.reviewed_by.username if appeal.reviewed_by else "",
            appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
        ])

    return response


# MODERATION_APPEAL_QUEUE_STATUS_SUMMARY_V1
@staff_member_required
def moderation_appeal_queue(request):
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    base_appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
    ).prefetch_related(
        "attachments",
    )

    if q:
        base_appeals = base_appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    all_matching_appeals = list(base_appeals)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.PENDING)
    approved_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.APPROVED)
    rejected_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.REJECTED)

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    appeals = base_appeals

    if status:
        appeals = appeals.filter(status=status)

    appeals = list(appeals.order_by("-created_at"))

    for appeal in appeals:
        evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())
        appeal.evidence_file_count = appeal.attachments.count()
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "selected_status": status,
            "selected_q": q,
            "status_choices": ModerationAppeal.Status.choices,
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "page_title": "Moderation Appeals",
        },
    )


# MODERATION_APPEAL_DETAIL_TIMELINE_CONTEXT_V1
@login_required
def moderation_appeal_detail(request, pk):
    from .models import ModerationAppeal

    appeal = (
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "reviewed_by",
        )
        .prefetch_related("attachments")
        .filter(pk=pk)
        .first()
    )

    if not appeal:
        messages.error(request, "That appeal does not exist.")
        return redirect("accounts:my_moderation_appeals")

    if request.user.is_staff:
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if appeal.appellant_id != request.user.id:
        messages.error(request, "That appeal does not belong to your account.")
        return redirect("accounts:my_moderation_appeals")

    evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())

    return render(
        request,
        "accounts/moderation_appeal_detail.html",
        {
            "appeal": appeal,
            "evidence_file_count": appeal.attachments.count(),
            "evidence_total_mb": round(evidence_total_size / 1024 / 1024, 2),
            "page_title": "Appeal Detail",
        },
    )


# MODERATION_APPEAL_ADMIN_DETAIL_TIMELINE_CONTEXT_V1
@staff_member_required
def moderation_appeal_admin_detail(request, pk):
    from .models import ModerationAppeal, UserProfile
    from listings.models import Listing

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "moderation_notice",
            "listing",
            "listing_report",
            "user_report",
            "user_report__reported_user",
            "reviewed_by",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    seller_to_lift = None

    if appeal.user_report and appeal.user_report.reported_user:
        seller_to_lift = appeal.user_report.reported_user
    elif appeal.appeal_type == ModerationAppeal.AppealType.SELLER_ACTION:
        seller_to_lift = appeal.appellant

    seller_profile = None
    seller_is_suspended = False

    if seller_to_lift:
        seller_profile = UserProfile.objects.filter(user=seller_to_lift).first()
        seller_is_suspended = bool(seller_profile and seller_profile.is_seller_suspended)

    can_restore_listing = (
        appeal.status == ModerationAppeal.Status.APPROVED
        and appeal.listing
        and appeal.listing.status == Listing.Status.SUSPENDED
        and not appeal.listing.suspended_due_to_seller
    )

    listing_restore_blocked_by_seller_suspension = (
        appeal.status == ModerationAppeal.Status.APPROVED
        and appeal.listing
        and appeal.listing.status == Listing.Status.SUSPENDED
        and appeal.listing.suspended_due_to_seller
    )

    evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())

    return render(
        request,
        "accounts/moderation_appeal_admin_detail.html",
        {
            "appeal": appeal,
            "seller_to_lift": seller_to_lift,
            "seller_profile": seller_profile,
            "seller_is_suspended": seller_is_suspended,
            "can_restore_listing": can_restore_listing,
            "listing_restore_blocked_by_seller_suspension": listing_restore_blocked_by_seller_suspension,
            "evidence_file_count": appeal.attachments.count(),
            "evidence_total_mb": round(evidence_total_size / 1024 / 1024, 2),
            "page_title": "Appeal Admin Detail",
        },
    )


# MODERATION_APPEAL_DECISION_SAFETY_V1
@staff_member_required
@require_POST
def moderation_appeal_decide(request, pk, decision):
    from django.utils import timezone
    from .models import ModerationAppeal, ModerationNotice

    appeal = get_object_or_404(
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing_report",
            "user_report",
        ).prefetch_related("attachments"),
        pk=pk,
    )

    if appeal.status != ModerationAppeal.Status.PENDING:
        messages.warning(request, "This appeal has already been decided.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    evidence_reviewed = request.POST.get("evidence_reviewed") == "yes"
    decision_note = (request.POST.get("decision_note") or "").strip()
    admin_note = (request.POST.get("admin_note") or "").strip()

    if not evidence_reviewed:
        messages.error(request, "You must confirm that you reviewed the appeal evidence before deciding.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if not decision_note:
        messages.error(request, "Decision note is required and will be shown to the user.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    if decision == "approve":
        appeal.status = ModerationAppeal.Status.APPROVED
        title = "Your appeal was approved"
    elif decision == "reject":
        appeal.status = ModerationAppeal.Status.REJECTED
        title = "Your appeal was rejected"
    else:
        messages.error(request, "Invalid appeal decision.")
        return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)

    appeal.decision_note = decision_note
    appeal.admin_note = admin_note or appeal.admin_note or ""
    appeal.reviewed_by = request.user
    appeal.reviewed_at = timezone.now()
    appeal.save(
        update_fields=[
            "status",
            "decision_note",
            "admin_note",
            "reviewed_by",
            "reviewed_at",
        ]
    )

    ModerationNotice.objects.create(
        recipient=appeal.appellant,
        title=title,
        body=decision_note,
        notice_type=ModerationNotice.NoticeType.REPORT_UPDATE,
        listing=appeal.listing,
        listing_report=appeal.listing_report,
        user_report=appeal.user_report,
    )

    messages.success(
        request,
        "Appeal decision saved and user notified. No listing or seller restriction was changed automatically.",
    )
    return redirect("accounts:moderation_appeal_admin_detail", pk=appeal.pk)


# TRUST_SAFETY_ACTION_LOG_WITH_APPEALS_V1
def _trust_safety_action_log_data(request):
    import datetime
    from django.db.models import Q
    from listings.models import ListingReport
    from .models import UserReport, ModerationAppeal

    selected_type = (request.GET.get("type") or "all").strip()
    selected_action = (request.GET.get("action") or "").strip()
    selected_status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    listing_reports = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).exclude(status="pending")

    seller_reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).exclude(status="pending")

    appeal_actions = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "listing__owner",
        "reviewed_by",
    ).prefetch_related("attachments").exclude(status="pending")

    if selected_type == "listing":
        seller_reports = seller_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "seller":
        listing_reports = listing_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "appeal":
        listing_reports = listing_reports.none()
        seller_reports = seller_reports.none()

    if selected_status:
        listing_reports = listing_reports.filter(status=selected_status)
        seller_reports = seller_reports.filter(status=selected_status)
        appeal_actions = appeal_actions.filter(status=selected_status)

    if selected_action:
        listing_reports = listing_reports.filter(action_taken=selected_action)
        seller_reports = seller_reports.filter(action_taken=selected_action)

        appeal_status_by_action = {
            "appeal_approved": "approved",
            "appeal_rejected": "rejected",
        }

        if selected_action in appeal_status_by_action:
            appeal_actions = appeal_actions.filter(status=appeal_status_by_action[selected_action])
        else:
            appeal_actions = appeal_actions.none()

    if q:
        listing_reports = listing_reports.filter(
            Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

        seller_reports = seller_reports.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

        appeal_actions = appeal_actions.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reviewed_by__username__icontains=q)
            | Q(reviewed_by__email__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    listing_reports = list(listing_reports.order_by("-reviewed_at", "-created_at"))
    seller_reports = list(seller_reports.order_by("-created_at"))
    appeal_actions = list(appeal_actions.order_by("-reviewed_at", "-created_at"))

    listing_action_values = set(
        ListingReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )
    seller_action_values = set(
        UserReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )

    action_values = set(value for value in listing_action_values | seller_action_values if value)
    action_values.update(["appeal_approved", "appeal_rejected"])

    def action_label(value):
        return value.replace("_", " ").capitalize()

    action_choices = [(value, action_label(value)) for value in sorted(action_values)]

    status_choices = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("actioned", "Actioned"),
        ("dismissed", "Dismissed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    return {
        "listing_reports": listing_reports,
        "seller_reports": seller_reports,
        "appeal_actions": appeal_actions,
        "selected_type": selected_type,
        "selected_action": selected_action,
        "selected_status": selected_status,
        "selected_q": q,
        "action_choices": action_choices,
        "status_choices": status_choices,
        "page_title": "Trust & Safety Action Log",
    }


@staff_member_required
def trust_safety_action_log(request):
    return render(
        request,
        "accounts/trust_safety_action_log.html",
        _trust_safety_action_log_data(request),
    )


@staff_member_required
def trust_safety_action_log_export(request):
    import csv
    from django.http import HttpResponse

    data = _trust_safety_action_log_data(request)

    rows = []

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "listing_report",
            "record_id": report.pk,
            "status": report.get_status_display(),
            "action": report.get_action_taken_display() if report.action_taken else "",
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.listing.owner.username if report.listing and report.listing.owner else "",
            "subject_email": report.listing.owner.email if report.listing and report.listing.owner else "",
            "listing_title": report.listing.title if report.listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "seller_report",
            "record_id": report.pk,
            "status": report.get_status_display(),
            "action": report.get_action_taken_display() if report.action_taken else "",
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.reported_user.username if report.reported_user else "",
            "subject_email": report.reported_user.email if report.reported_user else "",
            "listing_title": report.source_listing.title if report.source_listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        action = "appeal_approved" if appeal.status == "approved" else "appeal_rejected"
        rows.append({
            "sort_date": date_value,
            "record_type": "appeal",
            "record_id": appeal.pk,
            "status": appeal.get_status_display(),
            "action": action.replace("_", " ").capitalize(),
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": appeal.appellant.username if appeal.appellant else "",
            "reporter_or_appellant_email": appeal.appellant.email if appeal.appellant else "",
            "subject_username": appeal.listing.owner.username if appeal.listing and appeal.listing.owner else "",
            "subject_email": appeal.listing.owner.email if appeal.listing and appeal.listing.owner else "",
            "listing_title": appeal.listing.title if appeal.listing else "",
            "details_or_message": appeal.message or "",
            "public_note_or_decision_note": appeal.decision_note or "",
            "internal_admin_note": appeal.admin_note or "",
        })

    rows.sort(key=lambda row: row["sort_date"] or "", reverse=True)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trust_safety_action_log.csv"'

    writer = csv.DictWriter(
        response,
        fieldnames=[
            "record_type",
            "record_id",
            "status",
            "action",
            "date",
            "reporter_or_appellant_username",
            "reporter_or_appellant_email",
            "subject_username",
            "subject_email",
            "listing_title",
            "details_or_message",
            "public_note_or_decision_note",
            "internal_admin_note",
        ],
    )
    writer.writeheader()

    for row in rows:
        row.pop("sort_date", None)
        writer.writerow(row)

    return response


# MODERATION_APPEAL_QUEUE_PAGINATION_V1
@staff_member_required
def moderation_appeal_queue(request):
    from django.core.paginator import Paginator
    from django.db.models import Q
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()

    base_appeals = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
    ).prefetch_related(
        "attachments",
    )

    if q:
        base_appeals = base_appeals.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    all_matching_appeals = list(base_appeals)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.PENDING)
    approved_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.APPROVED)
    rejected_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.REJECTED)

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    appeals_queryset = base_appeals

    if status:
        appeals_queryset = appeals_queryset.filter(status=status)

    appeals_queryset = appeals_queryset.order_by("-created_at")

    paginator = Paginator(appeals_queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    appeals = list(page_obj.object_list)

    for appeal in appeals:
        evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())
        appeal.evidence_file_count = appeal.attachments.count()
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    query_params = request.GET.copy()
    query_params.pop("page", None)
    querystring_without_page = query_params.urlencode()

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": querystring_without_page,
            "selected_status": status,
            "selected_q": q,
            "status_choices": ModerationAppeal.Status.choices,
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "page_title": "Moderation Appeals",
        },
    )


# TRUST_SAFETY_ACTION_LOG_PAGINATION_V1
@staff_member_required
def trust_safety_action_log(request):
    import datetime
    from django.core.paginator import Paginator

    data = _trust_safety_action_log_data(request)

    action_rows = []

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        action_label = "Appeal approved" if appeal.status == "approved" else "Appeal rejected"

        action_rows.append({
            "kind": "appeal",
            "object": appeal,
            "title": f"Appeal #{appeal.pk}",
            "action_label": action_label,
            "status_label": appeal.get_status_display(),
            "date": date_value,
            "actor_line": (
                f"Appellant: {appeal.appellant.username} / {appeal.appellant.email}"
                if appeal.appellant else "Appellant unavailable"
            ),
            "subject_line": (
                f"Listing: {appeal.listing.title}"
                if appeal.listing else "No related listing"
            ),
            "public_note": appeal.decision_note or "",
            "admin_note": appeal.admin_note or "",
        })

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at

        action_rows.append({
            "kind": "listing",
            "object": report,
            "title": f"Listing report #{report.pk}",
            "action_label": report.get_action_taken_display() if report.action_taken else "Listing report reviewed",
            "status_label": report.get_status_display(),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Listing: {report.listing.title} by {report.listing.owner.username} / {report.listing.owner.email}"
                if report.listing and report.listing.owner else "Listing unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at

        action_rows.append({
            "kind": "seller",
            "object": report,
            "title": f"Seller report #{report.pk}",
            "action_label": report.get_action_taken_display() if report.action_taken else "Seller report reviewed",
            "status_label": report.get_status_display(),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Reported seller: {report.reported_user.username} / {report.reported_user.email}"
                if report.reported_user else "Reported seller unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    fallback_date = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    action_rows.sort(key=lambda row: row["date"] or fallback_date, reverse=True)

    paginator = Paginator(action_rows, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    data.update({
        "action_rows": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "querystring_without_page": query_params.urlencode(),
        "total_action_rows": len(action_rows),
    })

    return render(request, "accounts/trust_safety_action_log.html", data)


# TRUST_SAFETY_ACTION_LOG_DATE_FILTERS_V1
def _trust_safety_action_log_data(request):
    import datetime
    from django.db.models import Q
    from django.utils import timezone
    from listings.models import ListingReport
    from .models import UserReport, ModerationAppeal

    selected_type = (request.GET.get("type") or "all").strip()
    selected_action = (request.GET.get("action") or "").strip()
    selected_status = (request.GET.get("status") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()
    q = (request.GET.get("q") or "").strip()

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(selected_date_from)
    date_to = parse_date(selected_date_to)

    if date_from:
        date_from_dt = timezone.make_aware(datetime.datetime.combine(date_from, datetime.time.min))
    else:
        date_from_dt = None

    if date_to:
        date_to_dt = timezone.make_aware(datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min))
    else:
        date_to_dt = None

    listing_reports = ListingReport.objects.select_related(
        "listing",
        "listing__owner",
        "reporter",
    ).exclude(status="pending")

    seller_reports = UserReport.objects.select_related(
        "reported_user",
        "reporter",
        "source_listing",
    ).exclude(status="pending")

    appeal_actions = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "listing__owner",
        "reviewed_by",
    ).prefetch_related("attachments").exclude(status="pending")

    if selected_type == "listing":
        seller_reports = seller_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "seller":
        listing_reports = listing_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "appeal":
        listing_reports = listing_reports.none()
        seller_reports = seller_reports.none()

    if selected_status:
        listing_reports = listing_reports.filter(status=selected_status)
        seller_reports = seller_reports.filter(status=selected_status)
        appeal_actions = appeal_actions.filter(status=selected_status)

    if selected_action:
        listing_reports = listing_reports.filter(action_taken=selected_action)
        seller_reports = seller_reports.filter(action_taken=selected_action)

        appeal_status_by_action = {
            "appeal_approved": "approved",
            "appeal_rejected": "rejected",
        }

        if selected_action in appeal_status_by_action:
            appeal_actions = appeal_actions.filter(status=appeal_status_by_action[selected_action])
        else:
            appeal_actions = appeal_actions.none()

    if q:
        listing_reports = listing_reports.filter(
            Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

        seller_reports = seller_reports.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

        appeal_actions = appeal_actions.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reviewed_by__username__icontains=q)
            | Q(reviewed_by__email__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    listing_reports = list(listing_reports.order_by("-reviewed_at", "-created_at"))
    seller_reports = list(seller_reports.order_by("-created_at"))
    appeal_actions = list(appeal_actions.order_by("-reviewed_at", "-created_at"))

    def action_date(obj, kind):
        if kind == "listing":
            return obj.reviewed_at or obj.created_at
        if kind == "seller":
            return getattr(obj, "action_taken_at", None) or obj.created_at
        return obj.reviewed_at or obj.created_at

    def in_date_range(obj, kind):
        value = action_date(obj, kind)
        if not value:
            return False
        if date_from_dt and value < date_from_dt:
            return False
        if date_to_dt and value >= date_to_dt:
            return False
        return True

    if date_from_dt or date_to_dt:
        listing_reports = [item for item in listing_reports if in_date_range(item, "listing")]
        seller_reports = [item for item in seller_reports if in_date_range(item, "seller")]
        appeal_actions = [item for item in appeal_actions if in_date_range(item, "appeal")]

    listing_action_values = set(
        ListingReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )
    seller_action_values = set(
        UserReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )

    action_values = set(value for value in listing_action_values | seller_action_values if value)
    action_values.update(["appeal_approved", "appeal_rejected"])

    def action_label(value):
        return value.replace("_", " ").capitalize()

    action_choices = [(value, action_label(value)) for value in sorted(action_values)]

    status_choices = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),
        ("actioned", "Actioned"),
        ("dismissed", "Dismissed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    return {
        "listing_reports": listing_reports,
        "seller_reports": seller_reports,
        "appeal_actions": appeal_actions,
        "selected_type": selected_type,
        "selected_action": selected_action,
        "selected_status": selected_status,
        "selected_date_from": selected_date_from,
        "selected_date_to": selected_date_to,
        "selected_q": q,
        "action_choices": action_choices,
        "status_choices": status_choices,
        "page_title": "Trust & Safety Action Log",
    }


# TRUST_SAFETY_ACTION_LOG_SAFE_ACTION_LABELS_V2
def _trust_safety_safe_label(value):
    if not value:
        return ""
    return str(value).replace("_", " ").replace("-", " ").capitalize()


def _trust_safety_safe_status_label(obj):
    if hasattr(obj, "get_status_display"):
        try:
            return obj.get_status_display()
        except Exception:
            pass
    return _trust_safety_safe_label(getattr(obj, "status", ""))


def _trust_safety_safe_action_label(obj, default_label):
    value = getattr(obj, "action_taken", "")
    if not value:
        return default_label

    display_method = getattr(obj, "get_action_taken_display", None)
    if callable(display_method):
        try:
            return display_method()
        except Exception:
            pass

    return _trust_safety_safe_label(value)


@staff_member_required
def trust_safety_action_log(request):
    import datetime
    from django.core.paginator import Paginator

    data = _trust_safety_action_log_data(request)

    action_rows = []

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        action_label = "Appeal approved" if appeal.status == "approved" else "Appeal rejected"

        action_rows.append({
            "kind": "appeal",
            "object": appeal,
            "title": f"Appeal #{appeal.pk}",
            "action_label": action_label,
            "status_label": _trust_safety_safe_status_label(appeal),
            "date": date_value,
            "actor_line": (
                f"Appellant: {appeal.appellant.username} / {appeal.appellant.email}"
                if appeal.appellant else "Appellant unavailable"
            ),
            "subject_line": (
                f"Listing: {appeal.listing.title}"
                if appeal.listing else "No related listing"
            ),
            "public_note": appeal.decision_note or "",
            "admin_note": appeal.admin_note or "",
        })

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at

        action_rows.append({
            "kind": "listing",
            "object": report,
            "title": f"Listing report #{report.pk}",
            "action_label": _trust_safety_safe_action_label(report, "Listing report reviewed"),
            "status_label": _trust_safety_safe_status_label(report),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Listing: {report.listing.title} by {report.listing.owner.username} / {report.listing.owner.email}"
                if report.listing and report.listing.owner else "Listing unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at

        action_rows.append({
            "kind": "seller",
            "object": report,
            "title": f"Seller report #{report.pk}",
            "action_label": _trust_safety_safe_action_label(report, "Seller report reviewed"),
            "status_label": _trust_safety_safe_status_label(report),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Reported seller: {report.reported_user.username} / {report.reported_user.email}"
                if report.reported_user else "Reported seller unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    fallback_date = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    action_rows.sort(key=lambda row: row["date"] or fallback_date, reverse=True)

    paginator = Paginator(action_rows, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    data.update({
        "action_rows": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "querystring_without_page": query_params.urlencode(),
        "total_action_rows": len(action_rows),
    })

    return render(request, "accounts/trust_safety_action_log.html", data)


@staff_member_required
def trust_safety_action_log_export(request):
    import csv
    from django.http import HttpResponse

    data = _trust_safety_action_log_data(request)

    rows = []

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "listing_report",
            "record_id": report.pk,
            "status": _trust_safety_safe_status_label(report),
            "action": _trust_safety_safe_action_label(report, "Listing report reviewed"),
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.listing.owner.username if report.listing and report.listing.owner else "",
            "subject_email": report.listing.owner.email if report.listing and report.listing.owner else "",
            "listing_title": report.listing.title if report.listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "seller_report",
            "record_id": report.pk,
            "status": _trust_safety_safe_status_label(report),
            "action": _trust_safety_safe_action_label(report, "Seller report reviewed"),
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.reported_user.username if report.reported_user else "",
            "subject_email": report.reported_user.email if report.reported_user else "",
            "listing_title": report.source_listing.title if report.source_listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        action = "Appeal approved" if appeal.status == "approved" else "Appeal rejected"

        rows.append({
            "sort_date": date_value,
            "record_type": "appeal",
            "record_id": appeal.pk,
            "status": _trust_safety_safe_status_label(appeal),
            "action": action,
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": appeal.appellant.username if appeal.appellant else "",
            "reporter_or_appellant_email": appeal.appellant.email if appeal.appellant else "",
            "subject_username": appeal.listing.owner.username if appeal.listing and appeal.listing.owner else "",
            "subject_email": appeal.listing.owner.email if appeal.listing and appeal.listing.owner else "",
            "listing_title": appeal.listing.title if appeal.listing else "",
            "details_or_message": appeal.message or "",
            "public_note_or_decision_note": appeal.decision_note or "",
            "internal_admin_note": appeal.admin_note or "",
        })

    rows.sort(key=lambda row: row["sort_date"] or "", reverse=True)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trust_safety_action_log.csv"'

    writer = csv.DictWriter(
        response,
        fieldnames=[
            "record_type",
            "record_id",
            "status",
            "action",
            "date",
            "reporter_or_appellant_username",
            "reporter_or_appellant_email",
            "subject_username",
            "subject_email",
            "listing_title",
            "details_or_message",
            "public_note_or_decision_note",
            "internal_admin_note",
        ],
    )
    writer.writeheader()

    for row in rows:
        row.pop("sort_date", None)
        writer.writerow(row)

    return response


# TRUST_SAFETY_ACTION_LOG_QUICK_DATE_BUTTONS_V1
_previous_trust_safety_action_log_data_for_quick_dates = _trust_safety_action_log_data

def _trust_safety_action_log_data(request):
    from django.utils import timezone
    import datetime

    data = _previous_trust_safety_action_log_data_for_quick_dates(request)

    today = timezone.localdate()
    last_7_days = today - datetime.timedelta(days=6)
    last_30_days = today - datetime.timedelta(days=29)

    data.update({
        "quick_today": today.isoformat(),
        "quick_last_7_days": last_7_days.isoformat(),
        "quick_last_30_days": last_30_days.isoformat(),
    })

    return data


# MODERATION_APPEALS_DATE_FILTERS_V1
def _moderation_appeals_filtered_queryset(request):
    import datetime
    from django.db.models import Q
    from django.utils import timezone
    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(selected_date_from)
    date_to = parse_date(selected_date_to)

    qs = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments")

    if q:
        qs = qs.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    if date_from:
        date_from_dt = timezone.make_aware(datetime.datetime.combine(date_from, datetime.time.min))
        qs = qs.filter(created_at__gte=date_from_dt)

    if date_to:
        date_to_dt = timezone.make_aware(datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min))
        qs = qs.filter(created_at__lt=date_to_dt)

    if status:
        qs = qs.filter(status=status)

    return qs, {
        "status": status,
        "q": q,
        "date_from": selected_date_from,
        "date_to": selected_date_to,
    }


@staff_member_required
def moderation_appeal_queue(request):
    import datetime
    from django.core.paginator import Paginator
    from django.utils import timezone
    from .models import ModerationAppeal

    filtered_qs, filters = _moderation_appeals_filtered_queryset(request)

    # Counts should respect search/date filters but not the selected status.
    count_qs, _ = _moderation_appeals_filtered_queryset(request)
    if filters["status"]:
        count_qs = count_qs.model.objects.filter(pk__in=count_qs.values_list("pk", flat=True))
        count_qs = count_qs.exclude(pk__in=[])

        # Rebuild count base without status.
        fake_get = request.GET.copy()
        fake_get.pop("status", None)
        request.GET = fake_get
        count_qs, _ = _moderation_appeals_filtered_queryset(request)
        request.GET = fake_get.copy()
        request.GET["status"] = filters["status"]

    all_matching_appeals = list(count_qs)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.PENDING)
    approved_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.APPROVED)
    rejected_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.REJECTED)

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    paginator = Paginator(filtered_qs.order_by("-created_at"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    appeals = list(page_obj.object_list)

    for appeal in appeals:
        evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())
        appeal.evidence_file_count = appeal.attachments.count()
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()
    quick_last_7_days = today - datetime.timedelta(days=6)
    quick_last_30_days = today - datetime.timedelta(days=29)

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": filters["status"],
            "selected_q": filters["q"],
            "selected_date_from": filters["date_from"],
            "selected_date_to": filters["date_to"],
            "status_choices": ModerationAppeal.Status.choices,
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "quick_today": today.isoformat(),
            "quick_last_7_days": quick_last_7_days.isoformat(),
            "quick_last_30_days": quick_last_30_days.isoformat(),
            "page_title": "Moderation Appeals",
        },
    )


@staff_member_required
def moderation_appeal_export_csv(request):
    import csv
    from django.http import HttpResponse

    appeals, filters = _moderation_appeals_filtered_queryset(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="moderation_appeals.csv"'

    writer = csv.writer(response)

    writer.writerow([
        "appeal_id",
        "status",
        "appeal_type",
        "created_at",
        "appellant_username",
        "appellant_email",
        "listing_title",
        "evidence_file_count",
        "evidence_total_mb",
        "evidence_filenames",
        "message",
        "decision_note",
        "internal_admin_note",
        "reviewed_by",
        "reviewed_at",
    ])

    for appeal in appeals.order_by("-created_at"):
        attachments = list(appeal.attachments.all())
        total_size = sum(item.size or 0 for item in attachments)
        total_mb = round(total_size / 1024 / 1024, 2)
        filenames = "; ".join(item.original_name for item in attachments)

        writer.writerow([
            appeal.pk,
            appeal.get_status_display(),
            appeal.get_appeal_type_display(),
            appeal.created_at.isoformat() if appeal.created_at else "",
            appeal.appellant.username if appeal.appellant else "",
            appeal.appellant.email if appeal.appellant else "",
            appeal.listing.title if appeal.listing else "",
            len(attachments),
            total_mb,
            filenames,
            appeal.message or "",
            appeal.decision_note or "",
            appeal.admin_note or "",
            appeal.reviewed_by.username if appeal.reviewed_by else "",
            appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
        ])

    return response


@staff_member_required
def moderation_appeal_bulk_evidence_zip(request):
    import csv
    import io
    import zipfile
    from pathlib import Path
    from django.http import HttpResponse

    appeals, filters = _moderation_appeals_filtered_queryset(request)
    appeals = list(appeals.order_by("-created_at"))

    def safe_filename(name):
        name = Path(name or "evidence").name
        name = name.replace("/", "_").replace("\\", "_")
        return name or "evidence"

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        summary_buffer = io.StringIO()
        writer = csv.writer(summary_buffer)

        writer.writerow([
            "appeal_id",
            "status",
            "appeal_type",
            "created_at",
            "appellant_username",
            "appellant_email",
            "listing_title",
            "evidence_file_count",
            "evidence_total_mb",
            "decision_note",
            "reviewed_by",
            "reviewed_at",
        ])

        if not appeals:
            archive.writestr("NO_MATCHING_APPEALS.txt", "No appeals matched this filter.")
        else:
            for appeal in appeals:
                attachments = list(appeal.attachments.all())
                total_size = sum(item.size or 0 for item in attachments)
                total_mb = round(total_size / 1024 / 1024, 2)

                writer.writerow([
                    appeal.pk,
                    appeal.get_status_display(),
                    appeal.get_appeal_type_display(),
                    appeal.created_at.isoformat() if appeal.created_at else "",
                    appeal.appellant.username if appeal.appellant else "",
                    appeal.appellant.email if appeal.appellant else "",
                    appeal.listing.title if appeal.listing else "",
                    len(attachments),
                    total_mb,
                    appeal.decision_note or "",
                    appeal.reviewed_by.username if appeal.reviewed_by else "",
                    appeal.reviewed_at.isoformat() if appeal.reviewed_at else "",
                ])

                folder = f"appeal_{appeal.pk:04d}"

                archive.writestr(
                    f"{folder}/APPEAL_SUMMARY.txt",
                    "\n".join([
                        f"Appeal ID: {appeal.pk}",
                        f"Status: {appeal.get_status_display()}",
                        f"Type: {appeal.get_appeal_type_display()}",
                        f"Appellant: {appeal.appellant.username if appeal.appellant else ''} / {appeal.appellant.email if appeal.appellant else ''}",
                        f"Created: {appeal.created_at}",
                        "",
                        "Appeal message:",
                        appeal.message or "",
                        "",
                        "Decision note:",
                        appeal.decision_note or "",
                        "",
                        "Internal admin note:",
                        appeal.admin_note or "",
                    ]),
                )

                if not attachments:
                    archive.writestr(f"{folder}/NO_EVIDENCE_FILES.txt", "No evidence files were uploaded with this appeal.")
                else:
                    used_names = set()

                    for index, attachment in enumerate(attachments, start=1):
                        original_name = safe_filename(attachment.original_name or attachment.file.name)
                        zip_name = f"{folder}/{index:02d}_{original_name}"

                        counter = 2
                        while zip_name in used_names:
                            stem = Path(original_name).stem
                            suffix = Path(original_name).suffix
                            zip_name = f"{folder}/{index:02d}_{stem}_{counter}{suffix}"
                            counter += 1

                        used_names.add(zip_name)

                        attachment.file.open("rb")
                        try:
                            archive.writestr(zip_name, attachment.file.read())
                        finally:
                            attachment.file.close()

        archive.writestr("ALL_APPEALS_SUMMARY.csv", summary_buffer.getvalue())

    buffer.seek(0)

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="filtered_appeals_evidence.zip"'
    return response


# MODERATION_APPEALS_DATE_FILTERS_SAFE_FINAL_V2
def _moderation_appeals_filtered_queryset(request, include_status=True):
    import datetime

    from django.db.models import Q
    from django.utils import timezone

    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(selected_date_from)
    date_to = parse_date(selected_date_to)

    qs = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments")

    if q:
        qs = qs.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    if date_from:
        date_from_dt = timezone.make_aware(
            datetime.datetime.combine(date_from, datetime.time.min)
        )
        qs = qs.filter(created_at__gte=date_from_dt)

    if date_to:
        date_to_dt = timezone.make_aware(
            datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
        )
        qs = qs.filter(created_at__lt=date_to_dt)

    if include_status and status:
        qs = qs.filter(status=status)

    return qs, {
        "status": status,
        "q": q,
        "date_from": selected_date_from,
        "date_to": selected_date_to,
    }


@staff_member_required
def moderation_appeal_queue(request):
    import datetime

    from django.core.paginator import Paginator
    from django.utils import timezone

    from .models import ModerationAppeal

    filtered_qs, filters = _moderation_appeals_filtered_queryset(
        request,
        include_status=True,
    )

    count_qs, _ = _moderation_appeals_filtered_queryset(
        request,
        include_status=False,
    )

    all_matching_appeals = list(count_qs)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(
        1 for appeal in all_matching_appeals
        if appeal.status == ModerationAppeal.Status.PENDING
    )
    approved_count = sum(
        1 for appeal in all_matching_appeals
        if appeal.status == ModerationAppeal.Status.APPROVED
    )
    rejected_count = sum(
        1 for appeal in all_matching_appeals
        if appeal.status == ModerationAppeal.Status.REJECTED
    )

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    paginator = Paginator(filtered_qs.order_by("-created_at"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    appeals = list(page_obj.object_list)

    for appeal in appeals:
        evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())
        appeal.evidence_file_count = appeal.attachments.count()
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()
    quick_last_7_days = today - datetime.timedelta(days=6)
    quick_last_30_days = today - datetime.timedelta(days=29)

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": filters["status"],
            "selected_q": filters["q"],
            "selected_date_from": filters["date_from"],
            "selected_date_to": filters["date_to"],
            "status_choices": ModerationAppeal.Status.choices,
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "quick_today": today.isoformat(),
            "quick_last_7_days": quick_last_7_days.isoformat(),
            "quick_last_30_days": quick_last_30_days.isoformat(),
            "page_title": "Moderation Appeals",
        },
    )


# TRUST_SAFETY_ACTION_LOG_CLEAN_DATE_EXPORT_FINAL_V3
def _ts_label(value):
    if not value:
        return ""
    return str(value).replace("_", " ").replace("-", " ").capitalize()


def _ts_status_label(obj):
    method = getattr(obj, "get_status_display", None)
    if callable(method):
        try:
            return method()
        except Exception:
            pass
    return _ts_label(getattr(obj, "status", ""))


def _ts_action_label(obj, fallback):
    value = getattr(obj, "action_taken", "")
    if not value:
        return fallback

    method = getattr(obj, "get_action_taken_display", None)
    if callable(method):
        try:
            return method()
        except Exception:
            pass

    return _ts_label(value)


def _trust_safety_action_log_data(request):
    import datetime

    from django.db.models import Q
    from django.db.models.functions import Coalesce
    from django.utils import timezone

    from listings.models import ListingReport
    from .models import UserReport, ModerationAppeal

    selected_type = (request.GET.get("type") or "all").strip()
    selected_action = (request.GET.get("action") or "").strip()
    selected_status = (request.GET.get("status") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()
    q = (request.GET.get("q") or "").strip()

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(selected_date_from)
    date_to = parse_date(selected_date_to)

    date_from_dt = None
    date_to_dt = None

    if date_from:
        date_from_dt = timezone.make_aware(
            datetime.datetime.combine(date_from, datetime.time.min)
        )

    if date_to:
        date_to_dt = timezone.make_aware(
            datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
        )

    listing_reports = (
        ListingReport.objects.select_related(
            "listing",
            "listing__owner",
            "reporter",
        )
        .exclude(status="pending")
        .annotate(action_date=Coalesce("reviewed_at", "created_at"))
    )

    seller_reports = (
        UserReport.objects.select_related(
            "reported_user",
            "reporter",
            "source_listing",
        )
        .exclude(status="pending")
        .annotate(action_date=Coalesce("action_taken_at", "created_at"))
    )

    appeal_actions = (
        ModerationAppeal.objects.select_related(
            "appellant",
            "listing",
            "listing__owner",
            "reviewed_by",
        )
        .prefetch_related("attachments")
        .exclude(status="pending")
        .annotate(action_date=Coalesce("reviewed_at", "created_at"))
    )

    if selected_type == "listing":
        seller_reports = seller_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "seller":
        listing_reports = listing_reports.none()
        appeal_actions = appeal_actions.none()
    elif selected_type == "appeal":
        listing_reports = listing_reports.none()
        seller_reports = seller_reports.none()

    if selected_status:
        listing_reports = listing_reports.filter(status=selected_status)
        seller_reports = seller_reports.filter(status=selected_status)
        appeal_actions = appeal_actions.filter(status=selected_status)

    if selected_action:
        listing_reports = listing_reports.filter(action_taken=selected_action)
        seller_reports = seller_reports.filter(action_taken=selected_action)

        appeal_status_by_action = {
            "appeal_approved": "approved",
            "appeal_rejected": "rejected",
        }

        if selected_action in appeal_status_by_action:
            appeal_actions = appeal_actions.filter(status=appeal_status_by_action[selected_action])
        else:
            appeal_actions = appeal_actions.none()

    if date_from_dt:
        listing_reports = listing_reports.filter(action_date__gte=date_from_dt)
        seller_reports = seller_reports.filter(action_date__gte=date_from_dt)
        appeal_actions = appeal_actions.filter(action_date__gte=date_from_dt)

    if date_to_dt:
        listing_reports = listing_reports.filter(action_date__lt=date_to_dt)
        seller_reports = seller_reports.filter(action_date__lt=date_to_dt)
        appeal_actions = appeal_actions.filter(action_date__lt=date_to_dt)

    if q:
        listing_reports = listing_reports.filter(
            Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

        seller_reports = seller_reports.filter(
            Q(reported_user__username__icontains=q)
            | Q(reported_user__email__icontains=q)
            | Q(reporter__username__icontains=q)
            | Q(reporter__email__icontains=q)
            | Q(source_listing__title__icontains=q)
            | Q(details__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reporter_note__icontains=q)
            | Q(action_taken__icontains=q)
        ).distinct()

        appeal_actions = appeal_actions.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(listing__owner__username__icontains=q)
            | Q(listing__owner__email__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(reviewed_by__username__icontains=q)
            | Q(reviewed_by__email__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    listing_reports = list(listing_reports.order_by("-action_date", "-created_at"))
    seller_reports = list(seller_reports.order_by("-action_date", "-created_at"))
    appeal_actions = list(appeal_actions.order_by("-action_date", "-created_at"))

    listing_action_values = set(
        ListingReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )
    seller_action_values = set(
        UserReport.objects.exclude(action_taken="")
        .values_list("action_taken", flat=True)
    )

    action_values = set(value for value in listing_action_values | seller_action_values if value)
    action_values.update(["appeal_approved", "appeal_rejected"])

    action_choices = [(value, _ts_label(value)) for value in sorted(action_values)]

    status_choices = [
        ("reviewed", "Reviewed"),
        ("actioned", "Actioned"),
        ("dismissed", "Dismissed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    today = timezone.localdate()

    return {
        "listing_reports": listing_reports,
        "seller_reports": seller_reports,
        "appeal_actions": appeal_actions,
        "selected_type": selected_type,
        "selected_action": selected_action,
        "selected_status": selected_status,
        "selected_date_from": selected_date_from,
        "selected_date_to": selected_date_to,
        "selected_q": q,
        "action_choices": action_choices,
        "status_choices": status_choices,
        "quick_today": today.isoformat(),
        "quick_last_7_days": (today - datetime.timedelta(days=6)).isoformat(),
        "quick_last_30_days": (today - datetime.timedelta(days=29)).isoformat(),
        "page_title": "Trust & Safety Action Log",
    }


@staff_member_required
def trust_safety_action_log(request):
    import datetime

    from django.core.paginator import Paginator

    data = _trust_safety_action_log_data(request)

    action_rows = []

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        action_rows.append({
            "kind": "appeal",
            "object": appeal,
            "title": f"Appeal #{appeal.pk}",
            "action_label": "Appeal approved" if appeal.status == "approved" else "Appeal rejected",
            "status_label": _ts_status_label(appeal),
            "date": date_value,
            "actor_line": (
                f"Appellant: {appeal.appellant.username} / {appeal.appellant.email}"
                if appeal.appellant else "Appellant unavailable"
            ),
            "subject_line": (
                f"Listing: {appeal.listing.title}"
                if appeal.listing else "No related listing"
            ),
            "public_note": appeal.decision_note or "",
            "admin_note": appeal.admin_note or "",
        })

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at
        action_rows.append({
            "kind": "listing",
            "object": report,
            "title": f"Listing report #{report.pk}",
            "action_label": _ts_action_label(report, "Listing report reviewed"),
            "status_label": _ts_status_label(report),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Listing: {report.listing.title} by {report.listing.owner.username} / {report.listing.owner.email}"
                if report.listing and report.listing.owner else "Listing unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at
        action_rows.append({
            "kind": "seller",
            "object": report,
            "title": f"Seller report #{report.pk}",
            "action_label": _ts_action_label(report, "Seller report reviewed"),
            "status_label": _ts_status_label(report),
            "date": date_value,
            "actor_line": (
                f"Reporter: {report.reporter.username} / {report.reporter.email}"
                if report.reporter else "Reporter unavailable"
            ),
            "subject_line": (
                f"Reported seller: {report.reported_user.username} / {report.reported_user.email}"
                if report.reported_user else "Reported seller unavailable"
            ),
            "public_note": report.reporter_note or "",
            "admin_note": report.admin_note or "",
        })

    fallback_date = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    action_rows.sort(key=lambda row: row["date"] or fallback_date, reverse=True)

    paginator = Paginator(action_rows, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    data.update({
        "action_rows": page_obj.object_list,
        "page_obj": page_obj,
        "paginator": paginator,
        "querystring_without_page": query_params.urlencode(),
        "total_action_rows": len(action_rows),
    })

    return render(request, "accounts/trust_safety_action_log.html", data)


@staff_member_required
def trust_safety_action_log_export(request):
    import csv

    from django.http import HttpResponse

    data = _trust_safety_action_log_data(request)

    rows = []

    for report in data["listing_reports"]:
        date_value = report.reviewed_at or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "listing_report",
            "record_id": report.pk,
            "status": _ts_status_label(report),
            "action": _ts_action_label(report, "Listing report reviewed"),
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.listing.owner.username if report.listing and report.listing.owner else "",
            "subject_email": report.listing.owner.email if report.listing and report.listing.owner else "",
            "listing_title": report.listing.title if report.listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for report in data["seller_reports"]:
        date_value = getattr(report, "action_taken_at", None) or report.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "seller_report",
            "record_id": report.pk,
            "status": _ts_status_label(report),
            "action": _ts_action_label(report, "Seller report reviewed"),
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": report.reporter.username if report.reporter else "",
            "reporter_or_appellant_email": report.reporter.email if report.reporter else "",
            "subject_username": report.reported_user.username if report.reported_user else "",
            "subject_email": report.reported_user.email if report.reported_user else "",
            "listing_title": report.source_listing.title if report.source_listing else "",
            "details_or_message": report.details or "",
            "public_note_or_decision_note": report.reporter_note or "",
            "internal_admin_note": report.admin_note or "",
        })

    for appeal in data["appeal_actions"]:
        date_value = appeal.reviewed_at or appeal.created_at
        rows.append({
            "sort_date": date_value,
            "record_type": "appeal",
            "record_id": appeal.pk,
            "status": _ts_status_label(appeal),
            "action": "Appeal approved" if appeal.status == "approved" else "Appeal rejected",
            "date": date_value.isoformat() if date_value else "",
            "reporter_or_appellant_username": appeal.appellant.username if appeal.appellant else "",
            "reporter_or_appellant_email": appeal.appellant.email if appeal.appellant else "",
            "subject_username": appeal.listing.owner.username if appeal.listing and appeal.listing.owner else "",
            "subject_email": appeal.listing.owner.email if appeal.listing and appeal.listing.owner else "",
            "listing_title": appeal.listing.title if appeal.listing else "",
            "details_or_message": appeal.message or "",
            "public_note_or_decision_note": appeal.decision_note or "",
            "internal_admin_note": appeal.admin_note or "",
        })

    rows.sort(key=lambda row: row["sort_date"] or "", reverse=True)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trust_safety_action_log.csv"'

    writer = csv.DictWriter(
        response,
        fieldnames=[
            "record_type",
            "record_id",
            "status",
            "action",
            "date",
            "reporter_or_appellant_username",
            "reporter_or_appellant_email",
            "subject_username",
            "subject_email",
            "listing_title",
            "details_or_message",
            "public_note_or_decision_note",
            "internal_admin_note",
        ],
    )
    writer.writeheader()

    for row in rows:
        row.pop("sort_date", None)
        writer.writerow(row)

    return response


# MODERATION_APPEALS_HAS_EVIDENCE_FILTER_FINAL_V1
def _moderation_appeals_filtered_queryset(request, include_status=True):
    import datetime

    from django.db.models import Q
    from django.utils import timezone

    from .models import ModerationAppeal

    status = (request.GET.get("status") or "").strip()
    q = (request.GET.get("q") or "").strip()
    evidence_filter = (request.GET.get("evidence") or "").strip()
    selected_date_from = (request.GET.get("date_from") or "").strip()
    selected_date_to = (request.GET.get("date_to") or "").strip()

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(selected_date_from)
    date_to = parse_date(selected_date_to)

    qs = ModerationAppeal.objects.select_related(
        "appellant",
        "listing",
        "moderation_notice",
        "reviewed_by",
    ).prefetch_related("attachments")

    if q:
        qs = qs.filter(
            Q(appellant__username__icontains=q)
            | Q(appellant__email__icontains=q)
            | Q(listing__title__icontains=q)
            | Q(message__icontains=q)
            | Q(decision_note__icontains=q)
            | Q(admin_note__icontains=q)
            | Q(attachments__original_name__icontains=q)
        ).distinct()

    if date_from:
        date_from_dt = timezone.make_aware(
            datetime.datetime.combine(date_from, datetime.time.min)
        )
        qs = qs.filter(created_at__gte=date_from_dt)

    if date_to:
        date_to_dt = timezone.make_aware(
            datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
        )
        qs = qs.filter(created_at__lt=date_to_dt)

    if evidence_filter == "has_evidence":
        qs = qs.filter(attachments__isnull=False).distinct()
    elif evidence_filter == "no_evidence":
        qs = qs.filter(attachments__isnull=True)

    if include_status and status:
        qs = qs.filter(status=status)

    return qs, {
        "status": status,
        "q": q,
        "evidence": evidence_filter,
        "date_from": selected_date_from,
        "date_to": selected_date_to,
    }


@staff_member_required
def moderation_appeal_queue(request):
    import datetime

    from django.core.paginator import Paginator
    from django.utils import timezone

    from .models import ModerationAppeal

    filtered_qs, filters = _moderation_appeals_filtered_queryset(
        request,
        include_status=True,
    )

    count_qs, _ = _moderation_appeals_filtered_queryset(
        request,
        include_status=False,
    )

    all_matching_appeals = list(count_qs)

    total_appeals = len(all_matching_appeals)
    pending_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.PENDING)
    approved_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.APPROVED)
    rejected_count = sum(1 for appeal in all_matching_appeals if appeal.status == ModerationAppeal.Status.REJECTED)

    total_evidence_files = 0
    total_evidence_size = 0

    for appeal in all_matching_appeals:
        attachments = list(appeal.attachments.all())
        total_evidence_files += len(attachments)
        total_evidence_size += sum(item.size or 0 for item in attachments)

    paginator = Paginator(filtered_qs.order_by("-created_at"), 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    appeals = list(page_obj.object_list)

    for appeal in appeals:
        evidence_total_size = sum(item.size or 0 for item in appeal.attachments.all())
        appeal.evidence_file_count = appeal.attachments.count()
        appeal.evidence_total_mb = round(evidence_total_size / 1024 / 1024, 2)

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()

    return render(
        request,
        "accounts/moderation_appeal_queue.html",
        {
            "appeals": appeals,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_status": filters["status"],
            "selected_q": filters["q"],
            "selected_evidence": filters["evidence"],
            "selected_date_from": filters["date_from"],
            "selected_date_to": filters["date_to"],
            "status_choices": ModerationAppeal.Status.choices,
            "evidence_choices": [
                ("", "All evidence statuses"),
                ("has_evidence", "Has evidence"),
                ("no_evidence", "No evidence"),
            ],
            "total_appeals": total_appeals,
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "total_evidence_files": total_evidence_files,
            "total_evidence_mb": round(total_evidence_size / 1024 / 1024, 2),
            "quick_today": today.isoformat(),
            "quick_last_7_days": (today - datetime.timedelta(days=6)).isoformat(),
            "quick_last_30_days": (today - datetime.timedelta(days=29)).isoformat(),
            "page_title": "Moderation Appeals",
        },
    )



# TRUST_SAFETY_EVENT_LOG_VIEW_V1
@staff_member_required
def trust_safety_event_log(request):
    import datetime

    from django.core.paginator import Paginator
    from django.db.models import Q
    from django.utils import timezone

    from .models import TrustSafetyEvent

    q = (request.GET.get("q") or "").strip()
    event_type = (request.GET.get("event_type") or "").strip()
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()

    events = TrustSafetyEvent.objects.select_related(
        "actor",
        "target_user",
        "listing",
        "listing_report",
        "user_report",
        "appeal",
    ).order_by("-created_at")

    if event_type:
        events = events.filter(event_type=event_type)

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(date_from_raw)
    date_to = parse_date(date_to_raw)

    if date_from:
        events = events.filter(
            created_at__gte=timezone.make_aware(
                datetime.datetime.combine(date_from, datetime.time.min)
            )
        )

    if date_to:
        events = events.filter(
            created_at__lt=timezone.make_aware(
                datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
            )
        )

    if q:
        events = events.filter(
            Q(title__icontains=q)
            | Q(public_note__icontains=q)
            | Q(internal_note__icontains=q)
            | Q(actor__username__icontains=q)
            | Q(actor__email__icontains=q)
            | Q(target_user__username__icontains=q)
            | Q(target_user__email__icontains=q)
            | Q(listing__title__icontains=q)
        ).distinct()

    paginator = Paginator(events, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    today = timezone.localdate()

    return render(
        request,
        "accounts/trust_safety_event_log.html",
        {
            "events": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "querystring_without_page": query_params.urlencode(),
            "selected_q": q,
            "selected_event_type": event_type,
            "selected_date_from": date_from_raw,
            "selected_date_to": date_to_raw,
            "event_type_choices": TrustSafetyEvent.EventType.choices,
            "quick_today": today.isoformat(),
            "quick_last_7_days": (today - datetime.timedelta(days=6)).isoformat(),
            "quick_last_30_days": (today - datetime.timedelta(days=29)).isoformat(),
            "page_title": "Trust & Safety Events",
        },
    )


@staff_member_required
def trust_safety_event_log_export(request):
    import csv
    import datetime

    from django.db.models import Q
    from django.http import HttpResponse
    from django.utils import timezone

    from .models import TrustSafetyEvent

    q = (request.GET.get("q") or "").strip()
    event_type = (request.GET.get("event_type") or "").strip()
    date_from_raw = (request.GET.get("date_from") or "").strip()
    date_to_raw = (request.GET.get("date_to") or "").strip()

    events = TrustSafetyEvent.objects.select_related(
        "actor",
        "target_user",
        "listing",
        "listing_report",
        "user_report",
        "appeal",
    ).order_by("-created_at")

    if event_type:
        events = events.filter(event_type=event_type)

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(value)
        except ValueError:
            return None

    date_from = parse_date(date_from_raw)
    date_to = parse_date(date_to_raw)

    if date_from:
        events = events.filter(
            created_at__gte=timezone.make_aware(
                datetime.datetime.combine(date_from, datetime.time.min)
            )
        )

    if date_to:
        events = events.filter(
            created_at__lt=timezone.make_aware(
                datetime.datetime.combine(date_to + datetime.timedelta(days=1), datetime.time.min)
            )
        )

    if q:
        events = events.filter(
            Q(title__icontains=q)
            | Q(public_note__icontains=q)
            | Q(internal_note__icontains=q)
            | Q(actor__username__icontains=q)
            | Q(actor__email__icontains=q)
            | Q(target_user__username__icontains=q)
            | Q(target_user__email__icontains=q)
            | Q(listing__title__icontains=q)
        ).distinct()

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="trust_safety_events.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "event_id",
        "event_type",
        "created_at",
        "title",
        "actor_username",
        "actor_email",
        "target_username",
        "target_email",
        "listing_title",
        "listing_report_id",
        "seller_report_id",
        "appeal_id",
        "public_note",
        "internal_note",
    ])

    for event in events:
        writer.writerow([
            event.pk,
            event.get_event_type_display(),
            event.created_at.isoformat() if event.created_at else "",
            event.title,
            event.actor.username if event.actor else "",
            event.actor.email if event.actor else "",
            event.target_user.username if event.target_user else "",
            event.target_user.email if event.target_user else "",
            event.listing.title if event.listing else "",
            event.listing_report_id or "",
            event.user_report_id or "",
            event.appeal_id or "",
            event.public_note,
            event.internal_note,
        ])

    return response
