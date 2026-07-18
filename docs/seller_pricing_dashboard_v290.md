# Seller Pricing Dashboard (v290)

v290 adds an authenticated seller pricing workspace at `/accounts/seller-pricing/`.
It lists only the signed-in user's listings and links to the existing owner-protected
edit flow. All listing statuses are supported, including non-public listings.

The dashboard shows current and initial asking prices plus the latest meaningful
non-baseline transition. Equal-price rows are ignored. Reductions and increases
show a non-negative absolute change and a decimal percentage when the previous
price is greater than zero. A transition is described as matching the current
price only when its recorded new price equals the listing's persisted price.

Listings are paginated at 20. The default order is latest transition time
descending with nulls last and primary key descending. Newest, price-low, and
price-high alternatives retain stable primary-key tie breakers. Safe status and
sort allowlists ignore unsupported values, and pagination preserves canonical
filter state.

The page uses one owner-scoped summary query plus the paginator count and one
annotated page query. Category data is joined with `select_related`; no query is
issued per listing or price-history row. Correlated subqueries reuse the existing
price-history index and are bounded to the displayed page.

The dashboard does not expose favorites, alert subscribers, recipients, delivery
events, internal price-history identifiers, or moderation metadata. It does not
claim impressions, conversions, or market performance because no supporting
analytics model exists. No model, migration, dependency, or public endpoint is
added.
