"""Sequence-based public discount guardrails for v293."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


FAKE_DISCOUNT_GUARDRAILS_V293 = True

DISCOUNT_GUARDRAIL_CLEAR_V293 = ""
DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293 = "raise_then_drop"
DISCOUNT_GUARDRAIL_CHOICES_V293 = (
    (DISCOUNT_GUARDRAIL_CLEAR_V293, "Eligible for public discount promotion"),
    (
        DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
        "Restricted after a recent price increase",
    ),
)


@dataclass(frozen=True)
class PriceIntegrityEvaluationV293:
    guardrail_status: str
    reference_price: Decimal | None

    @property
    def is_public_discount_eligible(self) -> bool:
        return self.guardrail_status == DISCOUNT_GUARDRAIL_CLEAR_V293

    @property
    def is_restricted(self) -> bool:
        return not self.is_public_discount_eligible


def evaluate_price_transition_integrity_v293(
    *,
    previous_price: Decimal,
    new_price: Decimal,
    prior_previous_price: Decimal | None = None,
    prior_new_price: Decimal | None = None,
    prior_reference_price: Decimal | None = None,
) -> PriceIntegrityEvaluationV293:
    """Evaluate one transition using only the immediately preceding record."""

    previous_price = Decimal(previous_price)
    new_price = Decimal(new_price)
    prior_matches_current = (
        prior_new_price is not None
        and Decimal(prior_new_price) == previous_price
    )

    if new_price > previous_price:
        reference_price = previous_price
        if prior_matches_current and prior_reference_price is not None:
            reference_price = min(
                reference_price,
                Decimal(prior_reference_price),
            )
        return PriceIntegrityEvaluationV293(
            guardrail_status=DISCOUNT_GUARDRAIL_CLEAR_V293,
            reference_price=reference_price,
        )

    if new_price >= previous_price:
        return PriceIntegrityEvaluationV293(
            guardrail_status=DISCOUNT_GUARDRAIL_CLEAR_V293,
            reference_price=None,
        )

    reference_price = None
    if prior_matches_current and prior_reference_price is not None:
        reference_price = Decimal(prior_reference_price)
    elif (
        prior_matches_current
        and prior_previous_price is not None
        and Decimal(prior_previous_price) < previous_price
    ):
        reference_price = Decimal(prior_previous_price)

    if reference_price is not None and new_price >= reference_price:
        return PriceIntegrityEvaluationV293(
            guardrail_status=DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
            reference_price=reference_price,
        )

    return PriceIntegrityEvaluationV293(
        guardrail_status=DISCOUNT_GUARDRAIL_CLEAR_V293,
        reference_price=None,
    )


def evaluate_listing_price_change_v293(
    listing,
    proposed_price: Decimal,
) -> PriceIntegrityEvaluationV293:
    """Preview the guardrail result from one bounded latest-transition query."""

    prior_transition = (
        listing.price_history
        .filter(previous_price__isnull=False)
        .order_by("-changed_at", "-pk")
        .values(
            "previous_price",
            "new_price",
            "discount_reference_price",
        )
        .first()
    )
    return evaluate_price_transition_integrity_v293(
        previous_price=listing.price,
        new_price=proposed_price,
        prior_previous_price=(
            prior_transition["previous_price"] if prior_transition else None
        ),
        prior_new_price=(
            prior_transition["new_price"] if prior_transition else None
        ),
        prior_reference_price=(
            prior_transition["discount_reference_price"]
            if prior_transition
            else None
        ),
    )


def guardrail_warning_v293(reference_price: Decimal | None) -> str:
    if reference_price is None:
        return ""
    return (
        "This reduction will remain in price history but will not be promoted "
        f"as a public discount until the price falls below {reference_price} TL."
    )
