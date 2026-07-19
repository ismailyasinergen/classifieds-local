"""Owner-only, stale-safe seller price-change confirmation for v291."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .models import Listing, ListingPriceHistory
from .listing_price_integrity_v293 import (
    evaluate_listing_price_change_v293,
    guardrail_warning_v293,
)


PRICE_CHANGE_CONFIRMATION_V291 = True
PRICE_CHANGE_TOKEN_SALT_V291 = "listings.price-change-confirmation.v291"
PRICE_CHANGE_TOKEN_MAX_AGE_SECONDS_V291 = 15 * 60


class PriceChangeProposalFormV291(forms.Form):
    proposed_price = forms.DecimalField(
        label="New price",
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=forms.NumberInput(
            attrs={
                "min": "0",
                "step": "0.01",
                "inputmode": "decimal",
            }
        ),
    )
    price_change_reason = forms.ChoiceField(
        label="Reason (optional)",
        required=False,
        choices=ListingPriceHistory.Reason.choices,
        help_text="Choose a reason to keep your private pricing record clear.",
    )


@dataclass(frozen=True)
class PriceChangeSummaryV291:
    current_price: Decimal
    proposed_price: Decimal
    direction_label: str
    absolute_change: Decimal
    percentage_display: str
    reason_label: str
    guardrail_warning: str


def _format_percentage_v291(value: Decimal) -> str:
    rounded = value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    return format(rounded, "f").rstrip("0").rstrip(".")


def _build_summary_v291(
    current_price: Decimal,
    proposed_price: Decimal,
    price_change_reason: str = "",
    guardrail_warning: str = "",
) -> PriceChangeSummaryV291:
    absolute_change = abs(proposed_price - current_price)
    percentage_display = ""
    if current_price > 0:
        percentage_display = _format_percentage_v291(
            absolute_change / current_price * Decimal("100")
        )
    return PriceChangeSummaryV291(
        current_price=current_price,
        proposed_price=proposed_price,
        direction_label=(
            "Price reduced" if proposed_price < current_price else "Price increased"
        ),
        absolute_change=absolute_change,
        percentage_display=percentage_display,
        reason_label=dict(ListingPriceHistory.Reason.choices).get(
            price_change_reason,
            "",
        ),
        guardrail_warning=guardrail_warning,
    )


def _make_confirmation_token_v291(
    *,
    listing,
    user,
    proposed_price,
    price_change_reason="",
) -> str:
    return signing.dumps(
        {
            "listing_id": listing.pk,
            "user_id": user.pk,
            "current_price": format(listing.price, "f"),
            "proposed_price": format(proposed_price, "f"),
            "price_change_reason": price_change_reason,
        },
        salt=PRICE_CHANGE_TOKEN_SALT_V291,
        compress=True,
    )


def _load_confirmation_token_v291(token: str) -> dict:
    return signing.loads(
        token,
        salt=PRICE_CHANGE_TOKEN_SALT_V291,
        max_age=PRICE_CHANGE_TOKEN_MAX_AGE_SECONDS_V291,
    )


def _seller_is_suspended_v291(user) -> bool:
    profile = getattr(user, "profile", None)
    return bool(profile and profile.is_seller_suspended)


def _render_v291(request, listing, **context):
    status = context.pop("status", 200)
    return render(
        request,
        "listings/listing_price_change_confirmation_v291.html",
        {
            "page_title": "Change listing price",
            "listing": listing,
            **context,
        },
        status=status,
    )


@login_required
@require_http_methods(["GET", "POST"])
def listing_price_change_confirmation_v291(request, pk):
    """Propose, confirm, and atomically apply one owner-scoped price change."""

    listing = get_object_or_404(
        Listing.objects.select_related("owner"),
        pk=pk,
        owner=request.user,
    )
    if _seller_is_suspended_v291(request.user):
        messages.warning(
            request,
            "Your seller account is temporarily suspended. You cannot change prices right now.",
        )
        return redirect("accounts:dashboard")

    if request.method == "GET":
        return _render_v291(
            request,
            listing,
            form_v291=PriceChangeProposalFormV291(
                initial={"proposed_price": listing.price}
            ),
        )

    confirmation_token = request.POST.get("confirmation_token", "")
    if confirmation_token:
        try:
            payload = _load_confirmation_token_v291(confirmation_token)
            if (
                payload.get("listing_id") != listing.pk
                or payload.get("user_id") != request.user.pk
            ):
                raise signing.BadSignature("Confirmation scope does not match.")
            expected_price = Decimal(payload["current_price"])
            proposed_price = Decimal(payload["proposed_price"])
            price_change_reason = str(
                payload.get("price_change_reason", "") or ""
            )
            if price_change_reason not in dict(ListingPriceHistory.Reason.choices):
                raise signing.BadSignature("Invalid price-change reason.")
        except (signing.BadSignature, signing.SignatureExpired, KeyError, ArithmeticError):
            return _render_v291(
                request,
                listing,
                form_v291=PriceChangeProposalFormV291(
                    initial={"proposed_price": listing.price}
                ),
                confirmation_error_v291=(
                    "This price-change confirmation is invalid or expired. "
                    "Review the current price and try again."
                ),
                status=400,
            )

        with transaction.atomic():
            locked_listing = get_object_or_404(
                Listing.objects.select_for_update(),
                pk=listing.pk,
                owner=request.user,
            )
            if locked_listing.price != expected_price:
                return _render_v291(
                    request,
                    locked_listing,
                    form_v291=PriceChangeProposalFormV291(
                        initial={"proposed_price": locked_listing.price}
                    ),
                    confirmation_error_v291=(
                        "The listing price changed after you reviewed it. "
                        "No update was made; review the latest price and try again."
                    ),
                    status=409,
                )
            if proposed_price == locked_listing.price:
                messages.info(request, "The listing price is already unchanged.")
                return redirect("accounts:seller_pricing_dashboard_v290")

            locked_listing.price = proposed_price
            locked_listing.status = Listing.Status.PENDING
            locked_listing.save(
                update_fields=["price", "status"],
                price_change_reason=price_change_reason,
            )

        messages.success(
            request,
            "Price updated and submitted for approval.",
        )
        return redirect("accounts:seller_pricing_dashboard_v290")

    form = PriceChangeProposalFormV291(request.POST)
    if not form.is_valid():
        return _render_v291(request, listing, form_v291=form)

    proposed_price = form.cleaned_data["proposed_price"]
    price_change_reason = form.cleaned_data["price_change_reason"]
    if proposed_price == listing.price:
        messages.info(request, "Enter a different price to create a price change.")
        return redirect(
            "listings:listing_price_change_confirmation_v291",
            pk=listing.pk,
        )

    integrity_v293 = evaluate_listing_price_change_v293(
        listing,
        proposed_price,
    )
    return _render_v291(
        request,
        listing,
        summary_v291=_build_summary_v291(
            listing.price,
            proposed_price,
            price_change_reason,
            guardrail_warning_v293(integrity_v293.reference_price)
            if integrity_v293.is_restricted
            else "",
        ),
        confirmation_token_v291=_make_confirmation_token_v291(
            listing=listing,
            user=request.user,
            proposed_price=proposed_price,
            price_change_reason=price_change_reason,
        ),
    )
