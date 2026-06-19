import uuid

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .models import ListingPromotion, PromotionPackage


@login_required
def listing_promotion_packages(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related("owner", "category"),
        pk=pk,
        owner=request.user,
    )

    packages = PromotionPackage.objects.filter(is_active=True)

    promotions = ListingPromotion.objects.filter(
        listing=listing,
        user=request.user,
    ).select_related("package")[:10]

    return render(
        request,
        "promotions/package_list.html",
        {
            "listing": listing,
            "packages": packages,
            "promotions": promotions,
            "page_title": "Promote Listing",
        },
    )


@login_required
@require_POST
def listing_promotion_request(request, pk, package_id):
    listing = get_object_or_404(Listing, pk=pk, owner=request.user)
    package = get_object_or_404(PromotionPackage, pk=package_id, is_active=True)

    promotion = ListingPromotion.objects.create(
        listing=listing,
        package=package,
        user=request.user,
        price_snapshot=package.price,
        payment_reference=f"PROMO-{uuid.uuid4().hex[:10].upper()}",
    )

    messages.success(
        request,
        "Promotion request created. Complete the simulated payment step.",
    )

    return redirect("promotions:payment", pk=promotion.pk)


@login_required
def promotion_payment_page(request, pk):
    promotion = get_object_or_404(
        ListingPromotion.objects.select_related("listing", "package", "user"),
        pk=pk,
        user=request.user,
    )

    if request.method == "POST":
        proof = request.FILES.get("payment_proof")

        if not proof:
            messages.warning(request, "Please choose a payment proof image.")
            return redirect("promotions:payment", pk=promotion.pk)

        allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}

        if proof.content_type not in allowed_types:
            messages.warning(request, "Only JPG, PNG, WEBP, or GIF files are allowed.")
            return redirect("promotions:payment", pk=promotion.pk)

        if proof.size > 5 * 1024 * 1024:
            messages.warning(request, "Payment proof image must be under 5 MB.")
            return redirect("promotions:payment", pk=promotion.pk)

        promotion.payment_proof = proof
        promotion.save(update_fields=["payment_proof"])

        messages.success(request, "Payment proof uploaded. Admin will review it.")
        return redirect("promotions:payment", pk=promotion.pk)

    return render(
        request,
        "promotions/payment.html",
        {
            "promotion": promotion,
            "page_title": "Payment Pending",
        },
    )


@login_required
def my_promotions(request):
    promotions = (
        ListingPromotion.objects
        .select_related("listing", "package", "user")
        .filter(user=request.user)
        .order_by("-created_at")
    )

    return render(
        request,
        "promotions/my_promotions.html",
        {
            "promotions": promotions,
            "page_title": "My Promotions",
        },
    )


@staff_member_required
def promotion_admin_queue(request):
    status_filter = request.GET.get("status", "").strip()
    payment_filter = request.GET.get("payment", "").strip()

    promotions = ListingPromotion.objects.select_related(
        "listing",
        "package",
        "user",
    )

    valid_statuses = {
        ListingPromotion.Status.PENDING,
        ListingPromotion.Status.ACTIVE,
        ListingPromotion.Status.REJECTED,
        ListingPromotion.Status.EXPIRED,
    }

    if status_filter in valid_statuses:
        promotions = promotions.filter(status=status_filter)

    if payment_filter in {
        ListingPromotion.PaymentStatus.UNPAID,
        ListingPromotion.PaymentStatus.PAID,
    }:
        promotions = promotions.filter(payment_status=payment_filter)

    promotions = promotions.order_by("-created_at")

    all_promotions = ListingPromotion.objects.all()

    counts = {
        "all": all_promotions.count(),
        "pending": all_promotions.filter(status=ListingPromotion.Status.PENDING).count(),
        "active": all_promotions.filter(status=ListingPromotion.Status.ACTIVE).count(),
        "rejected": all_promotions.filter(status=ListingPromotion.Status.REJECTED).count(),
        "expired": all_promotions.filter(status=ListingPromotion.Status.EXPIRED).count(),
        "cancelled": all_promotions.filter(status=ListingPromotion.Status.CANCELLED).count(),
        "unpaid": all_promotions.filter(payment_status=ListingPromotion.PaymentStatus.UNPAID).count(),
        "paid": all_promotions.filter(payment_status=ListingPromotion.PaymentStatus.PAID).count(),
    }

    return render(
        request,
        "promotions/admin_queue.html",
        {
            "promotions": promotions,
            "counts": counts,
            "status_filter": status_filter,
            "payment_filter": payment_filter,
            "page_title": "Promotion Requests",
        },
    )


@staff_member_required
@require_POST
def promotion_mark_paid(request, pk):
    promotion = get_object_or_404(ListingPromotion, pk=pk)

    if promotion.payment_status == ListingPromotion.PaymentStatus.PAID:
        messages.info(request, "Promotion is already marked as paid.")
        return redirect("promotions:admin_queue")

    promotion.mark_paid()

    messages.success(request, "Promotion marked as paid.")
    return redirect("promotions:admin_queue")


@staff_member_required
@require_POST
def promotion_approve(request, pk):
    promotion = get_object_or_404(ListingPromotion, pk=pk)

    if promotion.status != ListingPromotion.Status.PENDING:
        messages.warning(request, "Only pending promotions can be approved.")
        return redirect("promotions:admin_queue")

    if promotion.payment_status != ListingPromotion.PaymentStatus.PAID:
        messages.warning(request, "Promotion must be marked as paid before approval.")
        return redirect("promotions:admin_queue")

    promotion.activate()

    messages.success(request, "Promotion approved and applied.")
    return redirect("promotions:admin_queue")


@staff_member_required
@require_POST
def promotion_reject(request, pk):
    promotion = get_object_or_404(ListingPromotion, pk=pk)

    if promotion.status != ListingPromotion.Status.PENDING:
        messages.warning(request, "Only pending promotions can be rejected.")
        return redirect("promotions:admin_queue")

    promotion.reject()

    messages.success(request, "Promotion rejected.")
    return redirect("promotions:admin_queue")



@login_required
@require_POST
def promotion_cancel(request, pk):
    promotion = get_object_or_404(
        ListingPromotion,
        pk=pk,
        user=request.user,
    )

    if promotion.status != ListingPromotion.Status.PENDING:
        messages.warning(request, "Only pending promotion requests can be cancelled.")
        return redirect("promotions:my_promotions")

    promotion.status = ListingPromotion.Status.CANCELLED
    promotion.save(update_fields=["status"])

    messages.success(request, "Promotion request cancelled.")
    return redirect("promotions:my_promotions")



@login_required
def promotion_receipt(request, pk):
    promotion = get_object_or_404(
        ListingPromotion.objects.select_related("listing", "package", "user"),
        pk=pk,
    )

    if promotion.user != request.user and not request.user.is_staff:
        messages.warning(request, "You cannot view this receipt.")
        return redirect("promotions:my_promotions")

    if promotion.payment_status != ListingPromotion.PaymentStatus.PAID:
        messages.warning(request, "Receipt is available only after payment is marked as paid.")
        return redirect("promotions:my_promotions")

    return render(
        request,
        "promotions/receipt.html",
        {
            "promotion": promotion,
            "page_title": "Promotion Receipt",
        },
    )
