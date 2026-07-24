import uuid

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from listings.models import Listing

from .doping_catalog_v342 import (
    PRICE_GROUP_LABELS_V342,
    PROMOTION_DEFINITIONS_V342,
    DurationModeV342,
    PromotionCodeV342,
    quote_promotion_v342,
    resolve_price_group_v342,
)
from .models import ListingPromotion, PromotionPackage


def _catalog_package_cards_v342(packages):
    cards = []

    for package in packages:
        try:
            code = PromotionCodeV342(package.catalog_code)
            definition = PROMOTION_DEFINITIONS_V342[code]

            if definition.duration_mode == DurationModeV342.FIXED_WEEKS:
                requested_week_values = definition.allowed_weeks
            else:
                requested_week_values = (None,)

            quotes = []

            for weeks in requested_week_values:
                quote = quote_promotion_v342(
                    code,
                    package.price_group,
                    requested_weeks=weeks,
                )
                quotes.append(
                    {
                        "quote": quote,
                        "discount_percent": int(
                            quote.discount_percent * 100
                        ),
                    }
                )
        except (KeyError, ValueError):
            continue

        cards.append(
            {
                "package": package,
                "definition": definition,
                "quotes": tuple(quotes),
            }
        )

    return tuple(cards)


@login_required
def listing_promotion_packages(request, pk):
    listing = get_object_or_404(
        Listing.objects.select_related(
            "owner",
            "category",
            "category__parent",
        ),
        pk=pk,
        owner=request.user,
    )

    price_group = resolve_price_group_v342(listing.category)

    if price_group is None:
        packages = PromotionPackage.objects.none()
        price_group_label = ""
    else:
        packages = (
            PromotionPackage.objects
            .filter(
                is_active=True,
                catalog_code__gt="",
                price_group=price_group,
            )
            .order_by(
                "catalog_code",
                "pk",
            )
        )
        price_group_label = PRICE_GROUP_LABELS_V342[price_group]

    package_cards = _catalog_package_cards_v342(packages)

    promotions = (
        ListingPromotion.objects
        .filter(
            listing=listing,
            user=request.user,
        )
        .select_related("package")[:10]
    )

    return render(
        request,
        "promotions/package_list.html",
        {
            "listing": listing,
            "packages": packages,
            "package_cards": package_cards,
            "price_group": price_group,
            "price_group_label": price_group_label,
            "promotions": promotions,
            "page_title": "Promote Listing",
        },
    )


@login_required
@require_POST
def listing_promotion_request(request, pk, package_id):
    listing = get_object_or_404(
        Listing.objects.select_related(
            "category",
            "category__parent",
        ),
        pk=pk,
        owner=request.user,
    )
    package = get_object_or_404(
        PromotionPackage,
        pk=package_id,
        is_active=True,
    )

    create_kwargs = {
        "listing": listing,
        "package": package,
        "user": request.user,
        "payment_reference": (
            f"PROMO-{uuid.uuid4().hex[:10].upper()}"
        ),
    }

    if package.catalog_code:
        price_group = resolve_price_group_v342(listing.category)

        if (
            price_group is None
            or package.price_group != price_group.value
        ):
            messages.warning(
                request,
                "This promotion is not available for the listing category.",
            )
            return redirect(
                "promotions:listing_packages",
                pk=listing.pk,
            )

        try:
            code = PromotionCodeV342(package.catalog_code)
            definition = PROMOTION_DEFINITIONS_V342[code]
        except (KeyError, ValueError):
            messages.warning(
                request,
                "This promotion package has an invalid catalog identity.",
            )
            return redirect(
                "promotions:listing_packages",
                pk=listing.pk,
            )

        raw_weeks = request.POST.get(
            "requested_weeks",
            "",
        ).strip()

        if definition.duration_mode == DurationModeV342.FIXED_WEEKS:
            try:
                requested_weeks = int(raw_weeks)
            except (TypeError, ValueError):
                requested_weeks = None
        else:
            requested_weeks = None

            if raw_weeks:
                messages.warning(
                    request,
                    "This promotion does not accept a week duration.",
                )
                return redirect(
                    "promotions:listing_packages",
                    pk=listing.pk,
                )

        try:
            quote = quote_promotion_v342(
                code,
                price_group,
                requested_weeks=requested_weeks,
            )
        except ValueError as exc:
            messages.warning(
                request,
                str(exc),
            )
            return redirect(
                "promotions:listing_packages",
                pk=listing.pk,
            )

        if (
            package.duration_mode
            != definition.duration_mode.value
            or package.price != quote.unit_price
        ):
            messages.warning(
                request,
                "Promotion pricing changed. Reload the catalog and try again.",
            )
            return redirect(
                "promotions:listing_packages",
                pk=listing.pk,
            )

        duplicate_exists = ListingPromotion.objects.filter(
            listing=listing,
            user=request.user,
            promotion_code_snapshot=code,
            status__in=(
                ListingPromotion.Status.PENDING,
                ListingPromotion.Status.ACTIVE,
            ),
        ).exists()

        if duplicate_exists:
            messages.warning(
                request,
                "This listing already has a pending or active request "
                "for the selected promotion.",
            )
            return redirect(
                "promotions:listing_packages",
                pk=listing.pk,
            )

        create_kwargs.update(
            {
                "price_snapshot": quote.total_price,
                "promotion_code_snapshot": code,
                "price_group_snapshot": price_group,
                "duration_mode_snapshot": (
                    definition.duration_mode
                ),
                "requested_weeks": quote.requested_weeks,
                "unit_price_snapshot": quote.unit_price,
                "discount_percent_snapshot": (
                    quote.discount_percent
                ),
            }
        )
    else:
        create_kwargs["price_snapshot"] = package.price

    promotion = ListingPromotion.objects.create(**create_kwargs)

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

    try:
        promotion.activate()
    except ValidationError as exc:
        messages.warning(
            request,
            "Promotion could not be activated: "
            f"{exc.messages[0]}",
        )
        return redirect("promotions:admin_queue")

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
