"""Read-only, streaming price-history integrity audit for v295."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterator

from django.utils import timezone

from .listing_price_integrity_v293 import (
    DISCOUNT_GUARDRAIL_CHOICES_V293,
    DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293,
)
from .models import Listing, ListingPriceHistory


PRICE_HISTORY_INTEGRITY_AUDIT_V295 = True
AUDIT_CHUNK_SIZE_V295 = 1000
DEFAULT_MAX_FINDINGS_V295 = 100
MAX_FINDINGS_V295 = 1000

MISSING_BASELINE_V295 = "missing_baseline"
MULTIPLE_BASELINES_V295 = "multiple_baselines"
BASELINE_NOT_FIRST_V295 = "baseline_not_first"
BROKEN_TRANSITION_CHAIN_V295 = "broken_transition_chain"
NOOP_TRANSITION_V295 = "noop_transition"
CURRENT_PRICE_MISMATCH_V295 = "current_price_mismatch"
FUTURE_TIMESTAMP_V295 = "future_timestamp"
INVALID_REASON_V295 = "invalid_reason"
INVALID_GUARDRAIL_STATUS_V295 = "invalid_guardrail_status"
RESTRICTED_WITHOUT_REFERENCE_V295 = "restricted_without_reference"
INVALID_RESTRICTION_DIRECTION_V295 = "invalid_restriction_direction"
INVALID_RESTRICTION_REFERENCE_V295 = "invalid_restriction_reference"


@dataclass(frozen=True)
class PriceHistoryIntegrityFindingV295:
    code: str
    listing_id: int
    transition_id: int | None = None

    def as_dict(self):
        return {
            "code": self.code,
            "listing_id": self.listing_id,
            "transition_id": self.transition_id,
        }


@dataclass(frozen=True)
class PriceHistoryIntegrityAuditReportV295:
    listing_count: int
    transition_count: int
    finding_count: int
    displayed_findings: tuple[PriceHistoryIntegrityFindingV295, ...]
    finding_counts: dict[str, int]

    @property
    def is_clean(self):
        return self.finding_count == 0

    @property
    def is_truncated(self):
        return self.finding_count > len(self.displayed_findings)

    def as_dict(self):
        return {
            "listing_count": self.listing_count,
            "transition_count": self.transition_count,
            "finding_count": self.finding_count,
            "displayed_finding_count": len(self.displayed_findings),
            "is_clean": self.is_clean,
            "is_truncated": self.is_truncated,
            "finding_counts": dict(sorted(self.finding_counts.items())),
            "findings": [
                finding.as_dict() for finding in self.displayed_findings
            ],
        }


def _listing_rows_v295():
    return (
        Listing.objects
        .order_by("pk")
        .values_list("pk", "price")
        .iterator(chunk_size=AUDIT_CHUNK_SIZE_V295)
    )


def _history_rows_v295():
    return (
        ListingPriceHistory.objects
        .order_by("listing_id", "changed_at", "pk")
        .values(
            "pk",
            "listing_id",
            "previous_price",
            "new_price",
            "changed_at",
            "reason",
            "discount_guardrail_status",
            "discount_reference_price",
        )
        .iterator(chunk_size=AUDIT_CHUNK_SIZE_V295)
    )


def _next_or_none_v295(iterator: Iterator):
    try:
        return next(iterator)
    except StopIteration:
        return None


def audit_listing_price_history_integrity_v295(
    *,
    max_findings=DEFAULT_MAX_FINDINGS_V295,
    audited_at=None,
):
    if max_findings < 1 or max_findings > MAX_FINDINGS_V295:
        raise ValueError(
            f"max_findings must be between 1 and {MAX_FINDINGS_V295}."
        )

    audited_at = audited_at or timezone.now()
    valid_reasons = {value for value, _label in ListingPriceHistory.Reason.choices}
    valid_guardrail_statuses = {
        value for value, _label in DISCOUNT_GUARDRAIL_CHOICES_V293
    }

    findings = []
    finding_counts = Counter()
    listing_count = 0
    transition_count = 0

    history_iterator = iter(_history_rows_v295())
    history = _next_or_none_v295(history_iterator)

    def add_finding(code, listing_id, transition_id=None):
        finding_counts[code] += 1
        if len(findings) < max_findings:
            findings.append(
                PriceHistoryIntegrityFindingV295(
                    code=code,
                    listing_id=listing_id,
                    transition_id=transition_id,
                )
            )

    for listing_id, listing_price in _listing_rows_v295():
        listing_count += 1
        baseline_count = 0
        row_count = 0
        last_new_price = None
        last_transition_id = None

        while history is not None and history["listing_id"] == listing_id:
            row_count += 1
            transition_count += 1
            transition_id = history["pk"]
            previous_price = history["previous_price"]
            new_price = history["new_price"]
            guardrail_status = history["discount_guardrail_status"]
            reference_price = history["discount_reference_price"]

            if history["changed_at"] > audited_at:
                add_finding(
                    FUTURE_TIMESTAMP_V295,
                    listing_id,
                    transition_id,
                )

            if history["reason"] not in valid_reasons:
                add_finding(INVALID_REASON_V295, listing_id, transition_id)

            if guardrail_status not in valid_guardrail_statuses:
                add_finding(
                    INVALID_GUARDRAIL_STATUS_V295,
                    listing_id,
                    transition_id,
                )

            if previous_price is None:
                baseline_count += 1
                if baseline_count > 1:
                    add_finding(
                        MULTIPLE_BASELINES_V295,
                        listing_id,
                        transition_id,
                    )
                if row_count > 1:
                    add_finding(
                        BASELINE_NOT_FIRST_V295,
                        listing_id,
                        transition_id,
                    )
            else:
                if (
                    last_new_price is not None
                    and previous_price != last_new_price
                ):
                    add_finding(
                        BROKEN_TRANSITION_CHAIN_V295,
                        listing_id,
                        transition_id,
                    )
                if previous_price == new_price:
                    add_finding(
                        NOOP_TRANSITION_V295,
                        listing_id,
                        transition_id,
                    )

            if guardrail_status == DISCOUNT_GUARDRAIL_RAISE_THEN_DROP_V293:
                if reference_price is None:
                    add_finding(
                        RESTRICTED_WITHOUT_REFERENCE_V295,
                        listing_id,
                        transition_id,
                    )
                if previous_price is None or previous_price <= new_price:
                    add_finding(
                        INVALID_RESTRICTION_DIRECTION_V295,
                        listing_id,
                        transition_id,
                    )
                if reference_price is not None and new_price < reference_price:
                    add_finding(
                        INVALID_RESTRICTION_REFERENCE_V295,
                        listing_id,
                        transition_id,
                    )

            last_new_price = new_price
            last_transition_id = transition_id
            history = _next_or_none_v295(history_iterator)

        if baseline_count == 0:
            add_finding(MISSING_BASELINE_V295, listing_id)

        if row_count and last_new_price != listing_price:
            add_finding(
                CURRENT_PRICE_MISMATCH_V295,
                listing_id,
                last_transition_id,
            )

    finding_count = sum(finding_counts.values())
    return PriceHistoryIntegrityAuditReportV295(
        listing_count=listing_count,
        transition_count=transition_count,
        finding_count=finding_count,
        displayed_findings=tuple(findings),
        finding_counts=dict(finding_counts),
    )


__all__ = [
    "MAX_FINDINGS_V295",
    "PRICE_HISTORY_INTEGRITY_AUDIT_V295",
    "PriceHistoryIntegrityAuditReportV295",
    "PriceHistoryIntegrityFindingV295",
    "audit_listing_price_history_integrity_v295",
]
