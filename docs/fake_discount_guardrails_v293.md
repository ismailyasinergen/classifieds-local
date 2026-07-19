# v293 — Fake-Discount Guardrails

v293 prevents a raise-then-drop sequence from receiving public discount
promotion while preserving the underlying price change. It does not block a
seller from changing a price and does not create a moderation decision.

Each transition stores a guardrail status and, when applicable, the earliest
price before a consecutive increase sequence. A later reduction remains
restricted while its new price is greater than or equal to that reference. The
restriction propagates across repeated reductions and clears automatically once
the price falls below the reference. This sequence rule avoids introducing an
arbitrary or legally implied time window.

Restricted reductions remain visible as factual increases and reductions in the
public 20-entry history timeline. They are excluded from listing-card discount
presentation, public price-drop filters, recent/biggest-drop sorting, period and
minimum-drop filters, listing-specific alerts, and saved-search price-drop
matching. Sellers receive an accessible warning during confirmation and on the
owner-only pricing dashboard. Internal status and reference values are never
rendered publicly.

The check adds one indexed latest-transition query only when a persisted price
actually changes. Collection rendering remains bounded and does not introduce
N+1 queries. Migration `0023_listingpricehistory_discount_guardrail_v293` is
additive and defaults existing history to public-discount eligible.
