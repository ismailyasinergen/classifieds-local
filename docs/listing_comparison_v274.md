# v274 — Session-Based Listing Comparison

## Checkpoint identity

- Base:
  `project-checkpoint-v273-public-browse-category-navigation-ux-repair`
- Target:
  `project-checkpoint-v274-listing-comparison`
- Marker:
  `LISTING_COMPARISON_V274`

## User outcome

Visitors can select public listings from browse cards or listing detail pages
and compare them side by side without creating an account.

## Exact scope

v274 changes exactly nine files:

1. `backend/listings/listing_comparison_v274.py`
2. `backend/listings/listing_comparison_views_v274.py`
3. `backend/listings/templatetags/listing_comparison_v274.py`
4. `backend/listings/urls.py`
5. `backend/listings/templates/listings/_listing_card.html`
6. `backend/listings/templates/listings/listing_detail.html`
7. `backend/listings/templates/listings/listing_comparison_v274.html`
8. `backend/listings/test_listing_comparison_v274.py`
9. `docs/listing_comparison_v274.md`

## Selection rules

- Minimum useful comparison: 2 listings
- Maximum selection: 4 listings
- User selection order is preserved.
- Selecting an existing item removes it.
- A fifth listing is refused without changing the current selection.
- Clear comparison removes the complete browser-session selection.

## Eligibility rules

Only approved and unexpired listings can be added or displayed.

Pending, rejected, archived, suspended, expired and deleted listings are
automatically excluded or pruned.

## Storage boundary

The session stores only positive listing primary keys under:

`listing_comparison_ids_v274`

No permanent comparison model, tracking model or migration is added.

## User interface

Comparison controls appear on:

- Public listing cards
- Listing detail pages

The comparison page shows:

- Listing image
- Title
- Price
- Location
- Category
- Public seller identity
- Posting date
- Marketplace status
- Category-specific display attributes
- A missing-value marker where one listing lacks an attribute

## Security

- Selection changes require POST.
- CSRF protection remains active.
- Redirect destinations are host-validated.
- Comparison forms return to the current path without reflecting unvalidated raw query parameters.
- Inactive listings return 404 from the toggle endpoint.
- Session values are normalized, deduplicated and bounded.
- Invalid and stale IDs are pruned.

## Compatibility

v274 preserves:

- Existing listing-list behavior
- Existing 48-line `ListingDetailView`
- Existing favorite controls
- v271 Similar listings
- v272 Recently viewed
- v273 compact category browse UX
- Existing card highlights
- Vehicle and real-estate detail behavior
- Saved-search behavior

## Runtime boundary

v274 does not modify:

- Listing model
- Category model
- Settings
- Admin
- Saved-search notifications
- Messaging
- Moderation
- Promotions
- Database schema
- Migrations

Migration `0017` remains absent.

## Manual QA

1. Open `/listings/`.
2. Add two listing cards.
3. Open `/listings/compare/`.
4. Confirm selection order and primary fields.
5. Add a third and fourth listing.
6. Confirm a fifth listing is refused.
7. Remove and re-add a listing.
8. Clear the comparison.
9. Test the control on a listing detail page.
10. Confirm another browser session has a separate selection.
11. Confirm Similar listings, Recently viewed and category browsing remain
    unchanged.

## Next project action

After visual QA, select the next concrete buyer or seller marketplace feature.
