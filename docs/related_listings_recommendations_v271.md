# v271 — Product Roadmap Re-entry: Related Listings Recommendations

## Checkpoint identity

- Base:
  `project-checkpoint-v270-saved-search-notification-production-delivery-pilot-supervised-execution-manual-rollout-authorization-closeout-audit`
- Target:
  `project-checkpoint-v271-related-listings-recommendations`
- Marker:
  `RELATED_LISTINGS_RECOMMENDATIONS_V271`

## Roadmap re-entry

v270 closed the saved-search notification audit series.

v271 returns the project to user-visible product development.

This checkpoint does not begin another audit-only chain.

## Selected feature

The selected feature is:

**Related listings recommendations on the listing-detail page.**

## Selection rationale

The marketplace already supports:

- Search and category browsing
- Listing detail pages
- Saved listings
- Saved searches
- Seller stores
- Messaging
- Reports
- Promotions

A buyer who opens an unsuitable listing still needs a quick route to relevant
alternatives.

A related-listings section has high user value because it:

- Reduces the need to return manually to search results
- Improves listing discovery
- Keeps buyers inside the relevant category
- Reuses the existing listing-card interface
- Works for anonymous and authenticated visitors
- Requires no new database schema
- Introduces no background processing
- Introduces no production-email behavior

## Exact v271 scope

v271 modifies exactly:

1. `backend/listings/listing_recommendations.py`
2. `backend/listings/listing_browse_detail_views.py`
3. `backend/listings/templates/listings/listing_detail.html`
4. `backend/listings/test_related_listings_recommendations_v271.py`
5. `docs/related_listings_recommendations_v271.md`

## Recommendation eligibility

A recommendation must:

- Be in the same category as the current listing
- Have status `approved`
- Be unexpired
- Differ from the current listing

Pending, rejected, archived and expired listings are not shown.

## Recommendation ranking

Results are ranked by:

1. Exact location match
2. Top-listing priority
3. Featured status
4. Newest creation timestamp
5. Stable primary-key tie-breaker

## Result limit

The default recommendation count is:

`4`

The internal maximum supported limit is:

`8`

The detail page uses the default count.

## User interface

When recommendations exist, the detail page displays:

- “Keep exploring” supporting copy
- “Similar listings” heading
- A link to the current category
- Existing marketplace listing cards
- A responsive listing grid

When no valid recommendation exists, the section is not rendered.

## Compatibility boundary

The existing extracted `ListingDetailView` remains in:

`backend/listings/listing_browse_detail_views.py`

The v157 class-body line-count contract remains 48 lines.

v271 adds a context mixin rather than rewriting the existing class body.

The `listings.views.ListingDetailView` re-export and the existing
`listing_detail` URL callback remain unchanged.

## Read-only boundary

The recommendation service performs only database reads.

It does not:

- Modify a listing
- Record a view
- Modify a user session
- Modify favorites
- Modify saved searches
- Send email
- Create audit events
- Invoke a management command
- Start a scheduler
- Run a background task

## Privacy boundary

The recommendation result uses only public listing information already
available through approved listing cards.

It does not expose:

- Pending listings
- Expired listings
- Rejected listings
- Private saved-search data
- Recipient email addresses
- Credentials
- Moderation evidence

## Runtime boundary

v271 changes only listing-detail recommendation behavior.

It does not modify:

- Models
- Database schema
- Migrations
- Admin
- URLs
- Settings
- Saved-search notification delivery
- Scheduler behavior
- Messaging behavior
- Moderation behavior

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Validation

The checkpoint validates:

- Recommendation eligibility
- Current-listing exclusion
- Same-category restriction
- Expiration restriction
- Default limit
- Location-first ranking
- Marketplace-priority ranking
- Anonymous detail-page rendering
- Empty-state hiding
- No private-title leakage
- Existing URL callback compatibility
- Existing v157 class-line contract
- Read-only behavior
- Full regression

## Product outcome

Buyers can continue browsing relevant active listings directly from a listing
detail page without returning manually to the search results.

## Next project action

After v271 succeeds, perform browser QA of the Similar listings section and
select the next concrete user-visible roadmap item.
