# v292 — Optional Price-Change Reasons

The seller price-confirmation flow accepts an optional structured reason:
market adjustment, promotion, condition update, listing correction, or other.
Free text is intentionally not collected, avoiding unmoderated private or
personal data in price history.

The selected value is included in the signed confirmation payload and written
only to the resulting non-baseline `ListingPriceHistory` transition. Baselines,
legacy rows, direct changes without a reason, and no-op saves use the empty
default. Invalid reason codes are rejected by both the form and the model save
boundary.

Owners can review the reason alongside their latest transition on the seller
pricing dashboard. Reasons are not rendered in the public listing price-history
timeline, preserving the existing public data contract. The dashboard continues
to use one annotated listing query; the extra reason subquery does not add
per-listing queries.

Migration `0022_listingpricehistory_reason_v292` adds a non-destructive
`CharField` with an empty default, so existing history remains valid without a
data backfill. No dependency was added.
