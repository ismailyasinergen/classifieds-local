# v298 — Public Deals SEO metadata

## Purpose

v298 adds request-aware search and social metadata to the public `/deals/`
landing page introduced in v296.

The milestone is presentation-only. It does not change deal qualification,
sorting, public visibility, pagination, listing cards, routes, models, or
database schema.

## Shared head contract

The common `base.html` head now supports optional SEO context values:

- SEO title;
- meta description;
- canonical URL;
- robots directive;
- Open Graph metadata;
- Twitter card metadata;
- JSON-LD structured data.

These elements render only when the current view supplies their context.
Existing pages therefore retain their previous title behavior and do not gain
empty, guessed, or duplicate metadata.

## Deals metadata

The canonical first page is `/deals/`.

Valid later pages retain only a normalized page parameter, for example
`/deals/?page=2`.

The page title, description, canonical URL, Open Graph URL, and JSON-LD URL all
use the same normalized page identity.

## Indexing behavior

A request is indexable only when its raw query string exactly matches the
canonical query for the resolved page.

Examples:

- `/deals/` produces `index,follow`;
- `/deals/?page=2` produces `index,follow`;
- `/deals/?page=1` canonically points to `/deals/` and produces
  `noindex,follow`;
- tracking or unknown parameters preserve a clean canonical URL and produce
  `noindex,follow`;
- page parameters combined with extra parameters canonicalize to the resolved
  page and produce `noindex,follow`.

This keeps tracking, duplicate, unknown, and redundant parameter variants
usable without presenting them as separate indexable pages.

## Structured data

Each response includes a Schema.org `CollectionPage` whose `mainEntity` is an
`ItemList`.

The ItemList contains only the public listings already present on the rendered
page. Each entry includes:

- its global paginated position;
- public absolute detail URL;
- listing title.

The total `numberOfItems` represents the complete eligible Deals collection,
while `itemListElement` represents the current page.

The JSON-LD serializer escapes `<`, `>`, and `&` before the value is marked safe
for the template. Listing titles therefore cannot terminate or inject a script
element.

## Performance

Metadata construction performs no database query. It consumes the paginated
listing objects already selected by the v296 view.

## Deliberate exclusions

v298 does not add:

- a sitemap endpoint;
- a robots.txt endpoint;
- per-listing Product structured data;
- social preview images;
- settings-backed production domain configuration;
- model fields;
- migrations.

These remain separate product or deployment decisions.

## Validation scope

Focused tests cover:

- first-page metadata;
- Open Graph and Twitter values;
- CollectionPage and ItemList JSON-LD;
- page-two canonical identity and positions;
- noncanonical query noindex behavior;
- redundant page-one normalization;
- JSON-LD script-breakout safety;
- empty collection output;
- query-free metadata construction;
- opt-in behavior for other pages;
- no route, model, or migration expansion.
