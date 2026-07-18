# v291 — Seller Price-Change Confirmation

Seller price changes use the authenticated owner-only route
`/listings/<id>/price/`. General listing edits display the current price but
cannot change it, preventing the confirmation step from being bypassed.

The first POST validates a decimal price and renders a review containing the
current and proposed values, direction, absolute change, and percentage where
the current price is greater than zero. It does not write to the database. A
short-lived signed token binds the listing, owner, current price, and proposed
price to the confirmation POST.

Confirmation locks the owner-scoped listing and compares its persisted price
with the reviewed value. A concurrent or repeated update returns a conflict and
does not write another transition. A valid confirmation updates the price,
marks the listing pending approval, and relies on the existing atomic
`Listing.save()` history mechanism to record exactly one transition.

Suspended sellers cannot use the flow. Normal login, ownership, CSRF, and
template escaping protections apply. No new public endpoint or dependency was
added, and v291 requires no database migration.
