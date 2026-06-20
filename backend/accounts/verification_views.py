# VERIFICATION_VIEWS_REFACTOR_V1
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import UserProfileForm
from .models import UserProfile



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
