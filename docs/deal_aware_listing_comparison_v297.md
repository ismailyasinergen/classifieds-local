# v297 — Deal-aware listing comparison

## Purpose

v297 integrates genuine current discount evidence into the existing public
listing comparison page.

The milestone does not redefine what constitutes a deal. It reuses the
established v276 discovery and v284 presentation contracts that already power
public listing cards and the v296 Deals page.

## User experience

When a selected listing has a valid current reduction, its comparison price
cell shows:

- a `Price dropped` badge;
- the semantic previous price;
- the current price;
- the saving amount;
- the formatted saving percentage;
- an accessible explanation containing the same buyer-facing facts.

Listings without a qualifying reduction continue to show their ordinary
current price without promotional discount language.

The comparison header and empty state link directly to the public `/deals/`
landing page while retaining the normal browse link.

## Discount eligibility

A comparison discount is shown only when the shared v276 service confirms that:

- the listing is approved and unexpired;
- the latest non-baseline transition is a genuine reduction;
- the persisted current listing price matches that transition;
- the previous price is usable for the shared v284 presentation;
- the v293 pricing-integrity guardrail is clear.

Baseline-only history, no-op transitions, later increases, stale reductions,
zero previous prices, guarded raise-then-drop sequences, and non-public
listings do not receive discount presentation.

## Architecture

`listing_comparison_discount_v297.py` performs one batched v276 discovery call
for all selected listings and converts qualifying discoveries through the v284
presentation builder.

Display-ready values are attached only as transient in-memory attributes to the
listing objects used by the current response. No comparison or discount state
is persisted.

The existing v274 session selection contract remains authoritative:

- two to four listings are supported;
- only listing primary keys are stored;
- invalid or no-longer-public selections are pruned;
- user selection order is retained;
- clear and remove actions remain POST-only.

## Performance and privacy

Discount lookup remains constant with respect to the number of selected
listings. No per-listing price-history query is introduced.

Internal guardrail codes and reference prices are not rendered publicly.

## Schema impact

v297 adds no model field and no migration.

## Validation scope

Focused tests cover:

- valid reduction evidence and accessibility;
- baseline and no-op fallback;
- later-increase and stale-transition suppression;
- zero-previous-price and v293 guardrail suppression;
- public visibility pruning;
- selection-order and v274 control preservation;
- Deals navigation;
- constant comparison query count;
- reuse of v276 and v284;
- no-migration compatibility.
