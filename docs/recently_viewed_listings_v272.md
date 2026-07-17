# v272 — Recently Viewed Listings

## Checkpoint identity

- Base:
  `project-checkpoint-v271-related-listings-recommendations`
- Target:
  `project-checkpoint-v272-recently-viewed-listings`
- Marker:
  `RECENTLY_VIEWED_LISTINGS_V272`

## Selected feature

The listing-detail page now displays recently viewed active listings from the
visitor's current Django session.

## User outcome

A visitor can return to listings opened earlier without repeating a search or
navigating back through several pages.

## Why this follows v271

v271 added category-based Similar listings.

v272 complements that feature with visitor-specific navigation history:

- Similar listings supports discovery.
- Recently viewed supports returning to known listings.

## Exact scope

v272 modifies exactly:

1. `backend/listings/listing_recently_viewed.py`
2. `backend/listings/listing_browse_detail_views.py`
3. `backend/listings/templates/listings/listing_detail.html`
4. `backend/listings/test_recently_viewed_listings_v272.py`
5. `docs/recently_viewed_listings_v272.md`

## Storage boundary

History is stored only in the Django session under:

`recently_viewed_listing_ids_v272`

No browsing-history model or permanent database row is created.

## History rules

- Newest viewed listing is stored first.
- Duplicate IDs are removed.
- Revisiting a listing moves it to the beginning.
- Maximum stored history is 12 listing IDs.
- Only positive integer IDs are retained.

## Display rules

- Default displayed results: 4
- Maximum internal display limit: 8
- Current listing is excluded.
- Session order is preserved.

## Eligibility rules

Displayed and recorded listings must be:

- Approved
- Unexpired
- Publicly viewable

Pending, rejected, archived and expired listings are excluded.

## User interface

The listing detail page displays:

- “Pick up where you left off”
- “Recently viewed”
- Existing marketplace listing cards
- Responsive listing grid

The section remains hidden when there is no eligible history.

## Anonymous and authenticated visitors

The feature works for:

- Anonymous visitors
- Authenticated buyers
- Authenticated sellers

Each browser session has isolated history.

## Privacy boundary

The feature stores only listing primary keys.

It does not store:

- Search terms
- Recipient email addresses
- User messages
- Saved-search data
- Credentials
- Moderation evidence
- Rendered email content

## Compatibility boundary

The existing `ListingDetailView` remains in:

`backend/listings/listing_browse_detail_views.py`

The existing 48-line class contract remains unchanged.

The view now composes:

1. `RecentlyViewedListingsContextMixinV272`
2. `RelatedListingsContextMixinV271`
3. Existing detail-view bases

The `listings.views.ListingDetailView` re-export and existing URL remain
unchanged.

## Read-only database boundary

Reading recently viewed listings performs no database writes.

Session updates occur only after a publicly eligible listing detail is viewed.

## Runtime boundary

v272 does not modify:

- Models
- Database schema
- Migrations
- URLs
- Admin
- Settings
- Saved-search notifications
- Scheduler behavior
- Messaging
- Moderation
- Promotions

The latest listings migration remains:

`0016_savedsearchnotificationauditevent`

Migration `0017` remains absent.

## Validation

The checkpoint validates:

- Session ID normalization
- History deduplication
- Newest-first ordering
- 12-item history cap
- Four-item default display
- Current-listing exclusion
- Pending and expired filtering
- Session isolation
- Anonymous browsing
- Empty-state hiding
- Listing-card reuse
- Existing URL and re-export compatibility
- Existing 48-line detail-view contract
- Database read-only behavior
- Full regression

## Next project action

Perform browser QA of Similar listings and Recently viewed together, then
select the next concrete user-visible marketplace feature.
